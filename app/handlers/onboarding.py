from __future__ import annotations

import json
import secrets

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.constants import AUTO_NAME_PREFIX, PLATFORM_LABELS, TARIFFS
from app.content.texts import NEARLY_READY, PROMO_PROMPT, STEP_DEVICE, STEP_NAME_TEMPLATE, tariffs_message
from app.db.repo import (
    count_promo_redemptions,
    create_device,
    get_or_create_user,
    get_promo,
    get_daily_cost,
    has_user_redeemed,
    log_event,
    redeem_promo,
    save_payment,
    set_user_flags,
    update_device_subscription,
    update_user_balance,
)
from app.keyboards.callbacks import PlatformCallback, TariffCallback, TopUpCallback
from app.keyboards.inline import (
    nearly_ready_keyboard,
    platform_keyboard,
    promo_prompt_keyboard,
    skip_name_keyboard,
    tariffs_keyboard,
    topup_amounts_keyboard,
)
from app.keyboards.reply import main_menu
from app.marzban.client import MarzbanClient
from app.payments.yookassa_client import YooKassaClient
from app.servers.allocator import allocate_server, release_server


router = Router()


class OnboardingState(StatesGroup):
    choosing_tariff = State()
    choosing_platform = State()
    choosing_name = State()
    entering_promo = State()


async def _handle_menu_shortcut(message: Message, state: FSMContext, session: AsyncSession) -> bool:
    menu_actions = {
        "💰 Баланс": "balance_view",
        "📱 Мои устройства": "devices_menu",
        "➕ Добавить устройство": "add_device",
        "💳 Пополнить": "topup_menu",
        "🎁 Пригласить друга": "referral_view",
        "🆘 Помощь": "help_view",
    }
    if message.text not in menu_actions:
        return False
    await state.clear()
    from app.handlers import menu

    handler = getattr(menu, menu_actions[message.text])
    if message.text in {"💰 Баланс", "📱 Мои устройства", "💳 Пополнить", "🎁 Пригласить друга"}:
        await handler(message, session, state)
    elif message.text == "➕ Добавить устройство":
        await handler(message, state)
    else:
        await handler(message, state)
    return True


def _generate_internal_code() -> str:
    return secrets.token_hex(6)


def _daily_cost_for_tariff(tariff_code: str) -> int:
    tariff = TARIFFS[tariff_code]
    return int((tariff.monthly_price_rub * 100 + 29) // 30)


def _build_auto_name(platform: str) -> str:
    prefix = AUTO_NAME_PREFIX[platform]
    return f"{prefix}-{secrets.token_hex(6)}"


def _device_name_example(platform: str) -> str:
    examples = {
        "ios": "iPhone",
        "android": "Android",
        "macos": "MacBook",
        "windows": "Рабочий",
    }
    return examples.get(platform, "Рабочий")


@router.callback_query(F.data == "start_onboarding")
async def start_onboarding(query: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    user = await get_or_create_user(session, query.from_user.id, query.from_user.username, secrets.token_hex(4))
    await log_event(session, user.id, "connect_click")
    if not user.has_seen_promo_prompt and not user.has_made_first_payment:
        await log_event(session, user.id, "promo_screen")
        await query.message.answer(PROMO_PROMPT, reply_markup=promo_prompt_keyboard())
        await query.answer()
        return
    await state.set_state(OnboardingState.choosing_tariff)
    prompt = await query.message.answer(tariffs_message(), reply_markup=tariffs_keyboard())
    await state.update_data(tariffs_message_id=prompt.message_id)
    await log_event(session, user.id, "tariff_screen")
    await query.answer()


@router.callback_query(F.data == "promo_skip")
async def promo_skip(query: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await get_or_create_user(session, query.from_user.id, query.from_user.username, secrets.token_hex(4))
    await set_user_flags(session, user.id, has_seen_promo_prompt=True)
    await log_event(session, user.id, "promo_skipped")
    await state.set_state(OnboardingState.choosing_tariff)
    await query.message.answer("Если что — промокод можно будет ввести позже в поддержке.")
    prompt = await query.message.answer(tariffs_message(), reply_markup=tariffs_keyboard())
    await state.update_data(tariffs_message_id=prompt.message_id)
    await log_event(session, user.id, "tariff_screen")
    await query.answer()


@router.callback_query(F.data == "promo_enter")
async def promo_enter(query: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    user = await get_or_create_user(session, query.from_user.id, query.from_user.username, secrets.token_hex(4))
    await set_user_flags(session, user.id, has_seen_promo_prompt=True)
    await state.set_state(OnboardingState.entering_promo)
    await log_event(session, user.id, "promo_entered")
    await query.message.answer("Введите промокод:")
    await query.answer()


@router.message(OnboardingState.entering_promo)
async def promo_code_entered(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if await _handle_menu_shortcut(message, state, session):
        return
    code = (message.text or "").strip()
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username, secrets.token_hex(4))
    promo = await get_promo(session, code)
    if not promo or not promo.is_active:
        await message.answer("Промокод не найден или уже неактивен.")
        await state.set_state(OnboardingState.choosing_tariff)
        prompt = await message.answer(tariffs_message(), reply_markup=tariffs_keyboard())
        await state.update_data(tariffs_message_id=prompt.message_id)
        await log_event(session, user.id, "tariff_screen")
        return
    if await has_user_redeemed(session, promo.id, user.id):
        await message.answer("Вы уже использовали этот промокод.")
        await state.set_state(OnboardingState.choosing_tariff)
        prompt = await message.answer(tariffs_message(), reply_markup=tariffs_keyboard())
        await state.update_data(tariffs_message_id=prompt.message_id)
        await log_event(session, user.id, "tariff_screen")
        return
    if promo.max_uses is not None:
        redemptions = await count_promo_redemptions(session, promo.id)
        if redemptions >= promo.max_uses:
            await message.answer("Лимит промокода исчерпан.")
            await state.set_state(OnboardingState.choosing_tariff)
            prompt = await message.answer(tariffs_message(), reply_markup=tariffs_keyboard())
            await state.update_data(tariffs_message_id=prompt.message_id)
            await log_event(session, user.id, "tariff_screen")
            return
    await redeem_promo(session, promo.id, user.id)
    user = await update_user_balance(session, user.id, promo.bonus_kopeks)
    await log_event(session, user.id, "promo_entered", {"code": promo.code})
    await message.answer(
        f"Бонус начислен: {promo.bonus_kopeks // 100} ₽\n💰 Баланс: {user.balance_kopeks // 100} ₽",
        reply_markup=main_menu(),
    )
    await state.set_state(OnboardingState.choosing_tariff)
    prompt = await message.answer(tariffs_message(), reply_markup=tariffs_keyboard())
    await state.update_data(tariffs_message_id=prompt.message_id)
    await log_event(session, user.id, "tariff_screen")


@router.callback_query(OnboardingState.choosing_tariff, TariffCallback.filter())
async def tariff_selected(
    query: CallbackQuery,
    callback_data: TariffCallback,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    data = await state.get_data()
    prev_id = data.get("tariffs_message_id")
    if prev_id and query.message:
        await query.message.delete()
    action = data.get("action", "onboarding")
    await state.update_data(tariff_code=callback_data.code, action=action)
    await state.set_state(OnboardingState.choosing_platform)
    prompt = await query.message.answer(STEP_DEVICE, reply_markup=platform_keyboard())
    await state.update_data(device_prompt_id=prompt.message_id)
    await log_event(session, query.from_user.id, f"tariff_selected_{TARIFFS[callback_data.code].monthly_price_rub}")
    await query.answer()


@router.callback_query(OnboardingState.choosing_platform, PlatformCallback.filter())
async def platform_selected(
    query: CallbackQuery,
    callback_data: PlatformCallback,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    data = await state.get_data()
    prev_id = data.get("device_prompt_id")
    if prev_id and query.message:
        await query.message.delete()
    await state.update_data(platform=callback_data.platform)
    await state.set_state(OnboardingState.choosing_name)
    prompt = await query.message.answer(
        STEP_NAME_TEMPLATE.format(example=_device_name_example(callback_data.platform)),
        reply_markup=skip_name_keyboard(),
    )
    await state.update_data(name_prompt_id=prompt.message_id)
    await log_event(session, query.from_user.id, "device_count_selected")
    await query.answer()


@router.callback_query(F.data == "skip_device_name")
async def skip_name(query: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    prev_id = data.get("name_prompt_id")
    if prev_id and query.message:
        await query.message.delete()
    data = await state.get_data()
    platform = data["platform"]
    display_name = _build_auto_name(platform)
    await _finish_device_setup(query.message, state, display_name, session)
    await log_event(session, query.from_user.id, "device_name_skipped")
    await query.answer()


@router.message(OnboardingState.choosing_name)
async def name_entered(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if await _handle_menu_shortcut(message, state, session):
        return
    display_name = message.text.strip()
    await _finish_device_setup(message, state, display_name, session)
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username, secrets.token_hex(4))
    await log_event(session, user.id, "device_name_entered")


async def _finish_device_setup(message: Message, state: FSMContext, display_name: str, session: AsyncSession) -> None:
    data = await state.get_data()
    prev_id = data.get("name_prompt_id")
    if prev_id:
        try:
            await message.bot.delete_message(message.chat.id, prev_id)
        except Exception:  # noqa: BLE001
            pass
    tariff = TARIFFS[data["tariff_code"]]
    internal_code = _generate_internal_code()
    await state.update_data(display_name=display_name, internal_code=internal_code)
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username, secrets.token_hex(4))
    user_data = {
        "display_name": display_name,
        "tariff_name": tariff.name,
        "monthly_price": tariff.monthly_price_rub,
        "balance": user.balance_kopeks // 100,
        "offer_url": settings.offer_url,
    }
    current_daily_cost = await get_daily_cost(session, user.id)
    allow_skip_topup = user.balance_kopeks >= current_daily_cost + _daily_cost_for_tariff(tariff.code)
    ready_message = await message.answer(
        NEARLY_READY.format(**user_data),
        reply_markup=nearly_ready_keyboard(allow_skip_topup),
        disable_web_page_preview=True,
    )
    await state.update_data(ready_message_id=ready_message.message_id)


@router.callback_query(F.data == "topup_prepare")
async def topup_prepare(query: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    prev_id = data.get("ready_message_id")
    if prev_id and query.message:
        await query.message.delete()
    tariff_code = data.get("tariff_code", "T1")
    action = data.get("action", "onboarding")
    tariff = TARIFFS[tariff_code]
    amounts = _amounts_for_tariff(tariff_code)
    prompt = await query.message.answer(
        "💳 Выберите сумму пополнения\n"
        f"Стоимость тарифа: {tariff.monthly_price_rub} ₽/мес\n\n"
        "Можно пополнить сразу на несколько месяцев.",
        reply_markup=topup_amounts_keyboard(amounts, context=action),
    )
    await state.update_data(topup_prompt_id=prompt.message_id)
    await log_event(session, query.from_user.id, "invoice_created")
    await query.answer()


@router.callback_query(F.data == "onboarding_use_balance")
async def onboarding_use_balance(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    marzban: MarzbanClient,
) -> None:
    data = await state.get_data()
    required_fields = ("tariff_code", "platform", "display_name", "internal_code")
    if not all(data.get(field) for field in required_fields):
        await query.message.answer("Не удалось продолжить. Начните заново через /start.")
        await state.clear()
        await query.answer()
        return

    user = await get_or_create_user(session, query.from_user.id, query.from_user.username, secrets.token_hex(4))
    tariff_code = data["tariff_code"]
    current_daily_cost = await get_daily_cost(session, user.id)
    required_daily = current_daily_cost + _daily_cost_for_tariff(tariff_code)
    if user.balance_kopeks < required_daily:
        await query.message.answer("Недостаточно средств для активации. Пополните баланс.")
        await topup_prepare(query, state, session)
        return

    prev_id = data.get("ready_message_id")
    if prev_id and query.message:
        await query.message.delete()

    platform = data["platform"]
    display_name = data["display_name"]
    internal_code = data["internal_code"]
    marzban_username = f"tg{user.tg_id}_{internal_code}"
    if tariff_code == "T1":
        server = await allocate_server(session, "EU")
        server_tags = [server.tag]
    elif tariff_code == "T2":
        server = await allocate_server(session, "RU")
        server_tags = [server.tag]
    else:
        eu_server = await allocate_server(session, "EU")
        ru_server = await allocate_server(session, "RU")
        server_tags = [eu_server.tag, ru_server.tag]

    device = await create_device(
        session=session,
        owner_id=user.id,
        display_name=display_name,
        internal_code=internal_code,
        platform=platform,
        tariff_code=tariff_code,
        marzban_username=marzban_username,
        server_tags_csv=",".join(server_tags),
    )

    proxy_list = settings.marzban_proxy_list or ["vless"]
    proxies: dict[str, dict] = {}
    if "vless" in proxy_list:
        proxies["vless"] = {"flow": "xtls-rprx-vision"}
    if "vmess" in proxy_list:
        proxies["vmess"] = {}
    if "shadowsocks" in proxy_list:
        proxies["shadowsocks"] = {}
    payload = {
        "username": marzban_username,
        "status": "active",
        "expire": None,
        "data_limit": 0,
        "data_limit_reset_strategy": "no_reset",
        "proxies": proxies,
        "inbounds": {"vless": server_tags},
        "note": TARIFFS[tariff_code].name,
        "level": settings.marzban_level,
        "limit_ip": settings.marzban_limit_ip,
    }
    try:
        response = await marzban.create_user(payload)
        subscription_url = response.get("subscription_url")
        if subscription_url:
            await update_device_subscription(session, device.id, subscription_url)
    except Exception as exc:  # noqa: BLE001
        print(f"Marzban create error: {exc}")
        for tag in server_tags:
            await release_server(session, tag)
        await query.message.answer("Не удалось активировать тариф. Попробуйте позже.")
        await query.answer()
        return

    from app.handlers import devices

    await devices.send_subscription_and_instruction(query.bot, user.tg_id, device.id, session)
    await log_event(session, user.id, "sub_issued")
    await state.clear()
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
    prev_id = data.get("topup_prompt_id")
    if prev_id and query.message:
        await query.message.delete()
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
    if confirmation_url:
        invoice_message = await query.message.answer(
            "Счёт на оплату\n\n"
            f"💳 К оплате: {callback_data.amount} ₽\n"
            f"Оплати по ссылке ниже:\n{confirmation_url}"
        )
        await state.update_data(invoice_message_id=invoice_message.message_id)
        context["invoice_message_id"] = invoice_message.message_id
    await save_payment(
        session=session,
        owner_id=user.id,
        amount_kopeks=callback_data.amount * 100,
        status="pending",
        provider="yookassa",
        provider_payment_id=provider_id,
        context=context,
    )
    await log_event(session, user.id, "payment_started")
    await query.answer()


def _amounts_for_tariff(tariff_code: str) -> list[int]:
    if tariff_code == "T1":
        return [100, 200, 300, 400, 500, 1000]
    if tariff_code == "T2":
        return [150, 200, 300, 400, 500, 1000]
    return [220, 300, 400, 500, 1000]
