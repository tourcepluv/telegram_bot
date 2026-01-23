from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.config import settings
from app.constants import PLATFORM_LABELS, TARIFFS, TARIFF_BUTTON_ORDER
from app.keyboards.callbacks import (
    DeviceActionCallback,
    DeviceSelectCallback,
    PlatformCallback,
    PromoDeleteCallback,
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
        if tariff.code == "T3":
            text = f"⭐🔥 {tariff.name.replace('🔥 ', '')} — {tariff.monthly_price_rub} ₽"
        elif tariff.code == "T1":
            text = f"✅ {tariff.name} — {tariff.monthly_price_rub} ₽"
        else:
            text = f"📶 {tariff.name} — {tariff.monthly_price_rub} ₽"
        buttons.append([InlineKeyboardButton(text=text, callback_data=TariffCallback(code=code).pack())])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def platform_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=PLATFORM_LABELS["ios"], callback_data=PlatformCallback(platform="ios").pack()),
                InlineKeyboardButton(text=PLATFORM_LABELS["android"], callback_data=PlatformCallback(platform="android").pack()),
            ],
            [
                InlineKeyboardButton(text=PLATFORM_LABELS["macos"], callback_data=PlatformCallback(platform="macos").pack()),
                InlineKeyboardButton(text=PLATFORM_LABELS["windows"], callback_data=PlatformCallback(platform="windows").pack()),
            ],
        ]
    )


def skip_name_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Пропустить", callback_data="skip_device_name")]]
    )


def nearly_ready_keyboard(allow_skip_topup: bool = False) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="💳 Пополнить", callback_data="topup_prepare")]]
    if allow_skip_topup:
        rows.append([InlineKeyboardButton(text="✅ Продолжить без пополнения", callback_data="onboarding_use_balance")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def topup_amounts_keyboard(amounts: list[int], context: str) -> InlineKeyboardMarkup:
    rows = []
    row: list[InlineKeyboardButton] = []
    for amount in amounts:
        row.append(InlineKeyboardButton(text=f"{amount} ₽", callback_data=TopUpCallback(amount=amount, context=context).pack()))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def help_topics_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ iPhone / iPad (V2Box)", callback_data="help_ios"),
                InlineKeyboardButton(text="✅ Android (Hiddify)", callback_data="help_android"),
            ],
            [
                InlineKeyboardButton(text="✅ macOS (V2Box)", callback_data="help_macos"),
                InlineKeyboardButton(text="✅ Windows (NekoBox)", callback_data="help_windows"),
            ],
            [
                InlineKeyboardButton(text="🔁 Перевыпустить ключ", callback_data="help_reissue"),
                InlineKeyboardButton(text="❌ Не работает / не подключается", callback_data="help_not_working"),
            ],
            [
                InlineKeyboardButton(text="🐢 Низкая скорость", callback_data="help_slow"),
                InlineKeyboardButton(text="💳 Не могу оплатить", callback_data="help_payment"),
            ],
            [
                InlineKeyboardButton(text="📱 Устройства (добавить/удалить)", callback_data="help_devices"),
                InlineKeyboardButton(text="💬 Чат поддержки", callback_data="help_support"),
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="help_back")],
        ]
    )


def help_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="help_back")]]
    )


def help_support_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Чат поддержки", url=f"https://t.me/{settings.support_username}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="help_back")],
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


def invite_friend_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Пригласить друга", callback_data="open_referral")],
        ]
    )


def admin_reports_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Отчёт: Воронка и оплаты", callback_data="admin_report:funnel")],
            [InlineKeyboardButton(text="🎟 Отчёт: Промокоды", callback_data="admin_report:promos")],
            [InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_promo_create")],
            [InlineKeyboardButton(text="🎟 Промокоды", callback_data="admin_promo_list")],
            [InlineKeyboardButton(text="⚙️ Настройки периода", callback_data="admin_period")],
        ]
    )


def admin_period_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Сегодня", callback_data="admin_period:today")],
            [InlineKeyboardButton(text="Вчера", callback_data="admin_period:yesterday")],
            [InlineKeyboardButton(text="7 дней", callback_data="admin_period:7d")],
            [InlineKeyboardButton(text="30 дней", callback_data="admin_period:30d")],
        ]
    )


def promo_delete_keyboard(promo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить промокод", callback_data=PromoDeleteCallback(promo_id=promo_id).pack())]
        ]
    )
