from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="📱 Мои устройства")],
            [KeyboardButton(text="➕ Добавить устройство"), KeyboardButton(text="💳 Пополнить")],
            [KeyboardButton(text="🎁 Рефералы"), KeyboardButton(text="🆘 Помощь")],
        ],
        resize_keyboard=True,
    )
