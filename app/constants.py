from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tariff:
    code: str
    name: str
    monthly_price_rub: int
    description: str
    is_recommended: bool = False


TARIFFS: dict[str, Tariff] = {
    "T1": Tariff(
        code="T1",
        name="Обычный режим",
        monthly_price_rub=100,
        description="Для повседневного использования. Подходит, когда всё работает штатно.",
    ),
    "T2": Tariff(
        code="T2",
        name="Мобильная стабильность",
        monthly_price_rub=150,
        description="Когда в мобильной сети приложения ведут себя нестабильно.",
    ),
    "T3": Tariff(
        code="T3",
        name="🔥 Всегда онлайн",
        monthly_price_rub=220,
        description="Комбо-режим: стабильность и в обычных условиях, и в нестабильных.",
        is_recommended=True,
    ),
}

TARIFF_TEXT_ORDER = ["T1", "T2", "T3"]
TARIFF_BUTTON_ORDER = ["T3", "T1", "T2"]

PLATFORM_LABELS = {
    "ios": "iOS",
    "android": "Android",
    "macos": "macOS",
    "windows": "Windows",
}

AUTO_NAME_PREFIX = {
    "ios": "iOS",
    "android": "Android",
    "macos": "Mac",
    "windows": "PC",
}
