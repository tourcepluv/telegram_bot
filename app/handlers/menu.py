from __future__ import annotations

import secrets

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import TARIFFS
from app.content.texts import (
    BALANCE_TEMPLATE,
    HELP_ANDROID_TEXT,
    HELP_DEVICES_TEXT,
    HELP_IOS_TEXT,
    HELP_MACOS_TEXT,
    HELP_MENU_TEXT,
    HELP_NOT_WORKING_TEXT,
    HELP_PAYMENT_TEXT,
    HELP_REISSUE_TEXT,
    HELP_SLOW_TEXT,
    HELP_SUPPORT_TEXT,
    HELP_WINDOWS_TEXT,
)
from app.db.repo import get_daily_cost, get_or_create_user, list_active_devices, list_user_devices
from app.keyboards.inline import (
    balance_keyboard,
    help_back_keyboard,
    help_support_keyboard,
    help_topics_keyboard,
)
from app.keyboards.reply import main_menu
from app.handlers.onboarding import OnboardingState


router = Router()


@router.message(F.text == "💰 Баланс")
async def balance_view(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    try:
        await message.delete()
    except Exception:  # noqa: BLE001
        pass
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username, secrets.token_hex(4))
    active_devices = await list_active_devices(session, user.id)
    daily_cost = await get_daily_cost(session, user.id)
    monthly_cost = sum(TARIFFS[device.tariff_code].monthly_price_rub for device in active_devices)
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
            monthly_cost=monthly_cost,
            days_left=days_text,
        ),
        reply_markup=balance_keyboard(),
    )


@router.message(F.text == "🆘 Помощь")
async def help_view(message: Message, state: FSMContext) -> None:
    from app.config import settings

    await state.clear()
    try:
        await message.delete()
    except Exception:  # noqa: BLE001
        pass
    await message.answer(HELP_MENU_TEXT, reply_markup=help_topics_keyboard())


@router.callback_query(F.data == "help_back")
async def help_back(query: CallbackQuery) -> None:
    await query.message.answer(HELP_MENU_TEXT, reply_markup=help_topics_keyboard())
    await query.answer()


@router.callback_query(F.data == "help_ios")
async def help_ios(query: CallbackQuery) -> None:
    await query.message.answer(HELP_IOS_TEXT, reply_markup=help_back_keyboard())
    await query.answer()


@router.callback_query(F.data == "help_android")
async def help_android(query: CallbackQuery) -> None:
    await query.message.answer(HELP_ANDROID_TEXT, reply_markup=help_back_keyboard())
    await query.answer()


@router.callback_query(F.data == "help_macos")
async def help_macos(query: CallbackQuery) -> None:
    await query.message.answer(HELP_MACOS_TEXT, reply_markup=help_back_keyboard())
    await query.answer()


@router.callback_query(F.data == "help_windows")
async def help_windows(query: CallbackQuery) -> None:
    await query.message.answer(HELP_WINDOWS_TEXT, reply_markup=help_back_keyboard())
    await query.answer()


@router.callback_query(F.data == "help_reissue")
async def help_reissue(query: CallbackQuery) -> None:
    await query.message.answer(HELP_REISSUE_TEXT, reply_markup=help_back_keyboard())
    await query.answer()


@router.callback_query(F.data == "help_not_working")
async def help_not_working(query: CallbackQuery) -> None:
    await query.message.answer(HELP_NOT_WORKING_TEXT, reply_markup=help_back_keyboard())
    await query.answer()


@router.callback_query(F.data == "help_slow")
async def help_slow(query: CallbackQuery) -> None:
    await query.message.answer(HELP_SLOW_TEXT, reply_markup=help_back_keyboard())
    await query.answer()


@router.callback_query(F.data == "help_payment")
async def help_payment(query: CallbackQuery) -> None:
    await query.message.answer(HELP_PAYMENT_TEXT, reply_markup=help_back_keyboard())
    await query.answer()


@router.callback_query(F.data == "help_devices")
async def help_devices(query: CallbackQuery) -> None:
    await query.message.answer(HELP_DEVICES_TEXT, reply_markup=help_back_keyboard())
    await query.answer()


@router.callback_query(F.data == "help_support")
async def help_support(query: CallbackQuery) -> None:
    from app.config import settings

    await query.message.answer(
        HELP_SUPPORT_TEXT.replace("@pluxvpn_help", f"@{settings.support_username}"),
        reply_markup=help_support_keyboard(),
    )
    await query.answer()


@router.message(F.text == "📱 Мои устройства")
async def devices_menu(message: Message, session: AsyncSession, state: FSMContext) -> None:
    from app.handlers.devices import show_devices

    await state.clear()
    try:
        await message.delete()
    except Exception:  # noqa: BLE001
        pass
    await show_devices(message, session)


@router.callback_query(F.data == "open_devices")
async def open_devices_callback(query: CallbackQuery, session: AsyncSession) -> None:
    from app.handlers.devices import show_devices_for_user

    user = await get_or_create_user(session, query.from_user.id, query.from_user.username, secrets.token_hex(4))
    await show_devices_for_user(query.message.chat.id, user.id, session, query.bot)
    await query.answer()


@router.callback_query(F.data == "open_referral")
async def referral_callback(query: CallbackQuery, session: AsyncSession) -> None:
    await query.message.bot.delete_message(query.message.chat.id, query.message.message_id)
    user = await get_or_create_user(session, query.from_user.id, query.from_user.username, secrets.token_hex(4))
    me = await query.bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{user.referral_code}"
    await query.message.answer(
        f"🎁 Пригласить друга (+50 ₽)\n{link}\n\n"
        "Приглашайте друзей и получайте бонусы после их первой оплаты.",
        reply_markup=main_menu(),
    )
    await query.answer()


@router.message(F.text == "➕ Добавить устройство")
async def add_device(message: Message, state: FSMContext) -> None:
    await state.clear()
    try:
        await message.delete()
    except Exception:  # noqa: BLE001
        pass
    await state.set_state(OnboardingState.choosing_tariff)
    await state.update_data(action="add_device")
    await message.answer("Выберите тариф для нового устройства:")
    from app.content.texts import tariffs_message
    from app.keyboards.inline import tariffs_keyboard

    prompt = await message.answer(tariffs_message(), reply_markup=tariffs_keyboard())
    await state.update_data(tariffs_message_id=prompt.message_id)


@router.message(F.text == "💳 Пополнить")
async def topup_menu(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    try:
        await message.delete()
    except Exception:  # noqa: BLE001
        pass
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username, secrets.token_hex(4))
    devices = await list_user_devices(session, user.id)
    tariff_code = "T1"
    if devices:
        tariff_code = max(devices, key=lambda device: TARIFFS[device.tariff_code].monthly_price_rub).tariff_code
    await state.update_data(tariff_code=tariff_code, action="topup")
    from app.handlers.onboarding import _amounts_for_tariff
    from app.keyboards.inline import topup_amounts_keyboard

    tariff = TARIFFS[tariff_code]
    await message.answer(
        "💳 Выберите сумму пополнения\n"
        f"Стоимость тарифа: {tariff.monthly_price_rub} ₽/мес\n\n"
        "Можно пополнить сразу на несколько месяцев.",
        reply_markup=topup_amounts_keyboard(_amounts_for_tariff(tariff_code), context="topup"),
    )


@router.message(F.text == "🎁 Пригласить друга")
async def referral_view(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    try:
        await message.delete()
    except Exception:  # noqa: BLE001
        pass
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username, secrets.token_hex(4))
    me = await message.bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{user.referral_code}"
    await message.answer(
        f"🎁 Пригласить друга (+50 ₽)\n{link}\n\n"
        "Приглашайте друзей и получайте бонусы после их первой оплаты.",
        reply_markup=main_menu(),
    )
