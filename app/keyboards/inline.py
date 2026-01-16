from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.config import settings
from app.constants import PLATFORM_LABELS, TARIFFS, TARIFF_BUTTON_ORDER
from app.keyboards.callbacks import (
    DeviceActionCallback,
    DeviceSelectCallback,
    PlatformCallback,
    TariffCallback,
    TopUpCallback,
)


def start_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🚀 Подключить", callback_data="start_onboarding")]]
    )


def tariffs_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for code in TARIFF_BUTTON_ORDER:
        tariff = TARIFFS[code]
        text = f"✅ {tariff.name} — {tariff.monthly_price_rub} ₽"
        if tariff.is_recommended:
            text = f"⭐ {tariff.name} — {tariff.monthly_price_rub} ₽"
        buttons.append([InlineKeyboardButton(text=text, callback_data=TariffCallback(code=code).pack())])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def platform_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=PLATFORM_LABELS["ios"], callback_data=PlatformCallback(platform="ios").pack())],
            [InlineKeyboardButton(text=PLATFORM_LABELS["android"], callback_data=PlatformCallback(platform="android").pack())],
            [InlineKeyboardButton(text=PLATFORM_LABELS["macos"], callback_data=PlatformCallback(platform="macos").pack())],
            [InlineKeyboardButton(text=PLATFORM_LABELS["windows"], callback_data=PlatformCallback(platform="windows").pack())],
        ]
    )


def skip_name_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Пропустить", callback_data="skip_device_name")]]
    )


def nearly_ready_keyboard(offer_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Пополнить", callback_data="topup_prepare")],
            [InlineKeyboardButton(text="Оферта", url=offer_url)],
        ]
    )


def topup_amounts_keyboard(amounts: list[int], context: str) -> InlineKeyboardMarkup:
    rows = []
    for amount in amounts:
        rows.append([InlineKeyboardButton(text=f"{amount} ₽", callback_data=TopUpCallback(amount=amount, context=context).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def help_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Написать в поддержку", url=f"https://t.me/{settings.support_username}")]
        ]
    )


def devices_actions_keyboard(device_id: int) -> InlineKeyboardMarkup:
    actions = [
        ("🔑 Подписка", "subscription"),
        ("📘 Инструкция", "instruction"),
        ("🔄 Сменить тариф", "change_tariff"),
        ("♻️ Перевыпустить ключ", "reissue"),
        ("🗑 Удалить устройство", "delete"),
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=DeviceActionCallback(device_id=device_id, action=action).pack())]
            for label, action in actions
        ]
    )


def devices_list_keyboard(devices: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=DeviceSelectCallback(device_id=device_id).pack())]
            for device_id, name in devices
        ]
    )


def devices_overview_keyboard(has_devices: bool) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text="➕ Добавить устройство", callback_data="devices_add")]]
    if has_devices:
        buttons.append([InlineKeyboardButton(text="✏️ Управление устройствами", callback_data="devices_manage")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def balance_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Пополнить", callback_data="topup_prepare")],
            [InlineKeyboardButton(text="📱 Мои устройства", callback_data="open_devices")],
        ]
    )


def promo_prompt_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎟 Ввести промокод", callback_data="promo_enter")],
            [InlineKeyboardButton(text="Пропустить", callback_data="promo_skip")],
        ]
    )
