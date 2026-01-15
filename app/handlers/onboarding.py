from __future__ import annotations

import json
import secrets

from aiogram import Router
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.constants import AUTO_NAME_PREFIX, PLATFORM_LABELS, TARIFFS
from app.content.texts import NEARLY_READY, STEP_DEVICE, STEP_NAME, tariffs_message
from app.db.repo import (
    count_promo_redemptions,
    get_or_create_user,
    get_promo,
    has_user_redeemed,
    redeem_promo,
    save_payment,
    set_user_flags,
    update_user_balance,
)
from app.keyboards.callbacks import PlatformCallback, TariffCallback, TopUpCallback
from app.keyboards.inline import nearly_ready_keyboard, platform_keyboard, skip_name_keyboard, tariffs_keyboard, topup_amounts_keyboard
from app.payments.yookassa_client import YooKassaClient


router = Router()


class OnboardingState(StatesGroup):
    choosing_tariff = State()
    choosing_platform = State()
    choosing_name = State()
    entering_promo = State()


def _generate_internal_code() -> str:
    return secrets.token_hex(6)


def _build_auto_name(platform: str) -> str:
    prefix = AUTO_NAME_PREFIX[platform]
    return f"{prefix}-{secrets.token_hex(6)}"


@router.callback_query(Text("start_onboarding"))
async def start_onboarding(query: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OnboardingState.choosing_tariff)
    await query.message.answer(tariffs_message(), reply_markup=tariffs_keyboard())
    await query.answer()


@router.callback_query(Text("promo_skip"))
async def promo_skip(query: CallbackQuery, session: AsyncSession) -> None:
    user = await get_or_create_user(session, query.from_user.id, query.from_user.username, secrets.token_hex(4))
    await set_user_flags(session, user.id, has_seen_promo_prompt=True)
    await query.message.answer("Если что — промокод можно будет ввести позже в поддержке.")
    await query.answer()


@router.callback_query(Text("promo_enter"))
async def promo_enter(query: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    user = await get_or_create_user(session, query.from_user.id, query.from_user.username, secrets.token_hex(4))
    await set_user_flags(session, user.id, has_seen_promo_prompt=True)
    await state.set_state(OnboardingState.entering_promo)
    await query.message.answer("Введите промокод:")
    await query.answer()


@router.message(OnboardingState.entering_promo)
async def promo_code_entered(message: Message, state: FSMContext, session: AsyncSession) -> None:
    code = message.text.strip()
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username, secrets.token_hex(4))
    promo = await get_promo(session, code)
    if not promo or not promo.is_active:
        await message.answer("Промокод не найден или уже неактивен.")
        await state.clear()
        return
    if await has_user_redeemed(session, promo.id, user.id):
        await message.answer("Вы уже использовали этот промокод.")
        await state.clear()
        return
    if promo.max_uses is not None:
        redemptions = await count_promo_redemptions(session, promo.id)
        if redemptions >= promo.max_uses:
            await message.answer("Лимит промокода исчерпан.")
            await state.clear()
            return
    await redeem_promo(session, promo.id, user.id)
    await update_user_balance(session, user.id, promo.bonus_kopeks)
    await message.answer(f"Бонус начислен: {promo.bonus_kopeks // 100} ₽")
    await state.clear()


@router.callback_query(OnboardingState.choosing_tariff, TariffCallback.filter())
async def tariff_selected(query: CallbackQuery, callback_data: TariffCallback, state: FSMContext) -> None:
    data = await state.get_data()
    action = data.get("action", "onboarding")
    await state.update_data(tariff_code=callback_data.code, action=action)
    await state.set_state(OnboardingState.choosing_platform)
    await query.message.answer(STEP_DEVICE, reply_markup=platform_keyboard())
    await query.answer()


@router.callback_query(OnboardingState.choosing_platform, PlatformCallback.filter())
async def platform_selected(query: CallbackQuery, callback_data: PlatformCallback, state: FSMContext) -> None:
    await state.update_data(platform=callback_data.platform)
    await state.set_state(OnboardingState.choosing_name)
    await query.message.answer(STEP_NAME, reply_markup=skip_name_keyboard())
    await query.answer()


@router.callback_query(Text("skip_device_name"))
async def skip_name(query: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    platform = data["platform"]
    display_name = _build_auto_name(platform)
    await _finish_device_setup(query.message, state, display_name, session)
    await query.answer()


@router.message(OnboardingState.choosing_name)
async def name_entered(message: Message, state: FSMContext, session: AsyncSession) -> None:
    display_name = message.text.strip()
    await _finish_device_setup(message, state, display_name, session)


async def _finish_device_setup(message: Message, state: FSMContext, display_name: str, session: AsyncSession) -> None:
    data = await state.get_data()
    tariff = TARIFFS[data["tariff_code"]]
    internal_code = _generate_internal_code()
    await state.update_data(display_name=display_name, internal_code=internal_code)
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username, secrets.token_hex(4))
    user_data = {
        "display_name": display_name,
        "tariff_name": tariff.name,
        "monthly_price": tariff.monthly_price_rub,
        "balance": user.balance_kopeks // 100,
    }
    await message.answer(
        NEARLY_READY.format(**user_data),
        reply_markup=nearly_ready_keyboard(settings.offer_url),
    )


@router.callback_query(Text("topup_prepare"))
async def topup_prepare(query: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    tariff_code = data.get("tariff_code", "T1")
    action = data.get("action", "onboarding")
    tariff = TARIFFS[tariff_code]
    amounts = _amounts_for_tariff(tariff_code)
    await query.message.answer(
        f"Выберите сумму пополнения (стоимость {tariff.monthly_price_rub} ₽/мес):",
        reply_markup=topup_amounts_keyboard(amounts, context=action),
    )
    await query.answer()


@router.callback_query(TopUpCallback.filter())
async def topup_amount(
    query: CallbackQuery,
    callback_data: TopUpCallback,
    state: FSMContext,
    session: AsyncSession,
    yookassa: YooKassaClient,
) -> None:
    data = await state.get_data()
    user = await get_or_create_user(session, query.from_user.id, query.from_user.username, secrets.token_hex(4))
    context = {
        "action": callback_data.context or data.get("action", "onboarding"),
        "tariff_code": data.get("tariff_code"),
        "platform": data.get("platform"),
        "display_name": data.get("display_name"),
        "internal_code": data.get("internal_code"),
    }
    try:
        payment = await yookassa.create_payment(
            amount_rub=callback_data.amount,
            description="Пополнение баланса",
            metadata={"tg_id": user.tg_id, "context": json.dumps(context, ensure_ascii=False)},
        )
    except Exception as exc:  # noqa: BLE001
        await query.message.answer("Не удалось создать платеж. Попробуйте позже.")
        print(f"YooKassa error: {exc}")
        return

    provider_id = payment.get("id")
    confirmation_url = payment.get("confirmation", {}).get("confirmation_url")
    await save_payment(
        session=session,
        owner_id=user.id,
        amount_kopeks=callback_data.amount * 100,
        status="pending",
        provider="yookassa",
        provider_payment_id=provider_id,
        context=context,
    )
    if confirmation_url:
        await query.message.answer(f"Оплатить: {confirmation_url}")
    await query.answer()


def _amounts_for_tariff(tariff_code: str) -> list[int]:
    if tariff_code == "T1":
        return [100, 200, 300, 400, 500, 1000]
    if tariff_code == "T2":
        return [150, 200, 300, 400, 500, 1000]
    return [220, 300, 400, 500, 1000]
