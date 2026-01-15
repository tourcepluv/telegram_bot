from __future__ import annotations

import secrets

from aiogram import Router
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import TARIFFS
from app.content.texts import BALANCE_TEMPLATE, help_text
from app.db.repo import get_daily_cost, get_or_create_user, list_active_devices, list_user_devices
from app.keyboards.inline import balance_keyboard, help_keyboard
from app.keyboards.reply import main_menu
from app.handlers.onboarding import OnboardingState


router = Router()


@router.message(Text("💰 Баланс"))
async def balance_view(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username, secrets.token_hex(4))
    active_devices = await list_active_devices(session, user.id)
    daily_cost = await get_daily_cost(session, user.id)
    if daily_cost > 0:
        days_left = user.balance_kopeks // daily_cost
        days_text = str(days_left)
    else:
        days_text = "—"
    tariff_code = "T1"
    devices = await list_user_devices(session, user.id)
    if devices:
        tariff_code = max(devices, key=lambda device: TARIFFS[device.tariff_code].monthly_price_rub).tariff_code
    await state.update_data(tariff_code=tariff_code, action="topup")
    await message.answer(
        BALANCE_TEMPLATE.format(
            balance=user.balance_kopeks // 100,
            active_devices=len(active_devices),
            daily_cost=daily_cost // 100,
            days_left=days_text,
        ),
        reply_markup=balance_keyboard(),
    )


@router.message(Text("🆘 Помощь"))
async def help_view(message: Message) -> None:
    from app.config import settings

    await message.answer(help_text(settings.support_username), reply_markup=help_keyboard())


@router.message(Text("📱 Мои устройства"))
async def devices_menu(message: Message, session: AsyncSession) -> None:
    from app.handlers.devices import show_devices

    await show_devices(message, session)


@router.callback_query(Text("open_devices"))
async def open_devices_callback(query: CallbackQuery, session: AsyncSession) -> None:
    from app.handlers.devices import show_devices

    await show_devices(query.message, session)
    await query.answer()


@router.message(Text("➕ Добавить устройство"))
async def add_device(message: Message, state: FSMContext) -> None:
    await state.set_state(OnboardingState.choosing_tariff)
    await state.update_data(action="add_device")
    await message.answer("Выберите тариф для нового устройства:")
    from app.content.texts import tariffs_message
    from app.keyboards.inline import tariffs_keyboard

    await message.answer(tariffs_message(), reply_markup=tariffs_keyboard())


@router.message(Text("💳 Пополнить"))
async def topup_menu(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username, secrets.token_hex(4))
    devices = await list_user_devices(session, user.id)
    tariff_code = "T1"
    if devices:
        tariff_code = max(devices, key=lambda device: TARIFFS[device.tariff_code].monthly_price_rub).tariff_code
    await state.update_data(tariff_code=tariff_code, action="topup")
    from app.handlers.onboarding import _amounts_for_tariff
    from app.keyboards.inline import topup_amounts_keyboard

    await message.answer(
        "Выберите сумму пополнения:",
        reply_markup=topup_amounts_keyboard(_amounts_for_tariff(tariff_code), context="topup"),
    )


@router.message(Text("🎁 Рефералы"))
async def referral_view(message: Message, session: AsyncSession) -> None:
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username, secrets.token_hex(4))
    link = f"https://t.me/{message.bot.username}?start=ref_{user.referral_code}"
    await message.answer(
        f"Ваша реферальная ссылка:\n{link}\n\n"
        "Приглашайте друзей и получайте бонусы после их первой оплаты.",
        reply_markup=main_menu(),
    )
