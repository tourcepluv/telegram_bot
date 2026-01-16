from __future__ import annotations

from app.constants import PLATFORM_LABELS


def instruction_ios(subscription_url: str) -> str:
    return (
        "📲 Настройка на iOS (1 минута)\n\n"
        "Установите v2RayTun из App Store:\n"
        "🔗 https://apps.apple.com/ru/app/v2raytun/id6476628951\n\n"
        "Скопируйте вашу конфигурацию:\n"
        f"<code>{subscription_url}</code>\n\n"
        "Откройте v2RayTun → “+” → “Добавить из буфера”\n\n"
        "Включите подключение ✅\n\n"
        "⚠️ Если iOS попросит VPN-профиль — разрешите в настройках."
    )


def instruction_placeholder(platform_label: str) -> str:
    return (
        f"Инструкция для {platform_label} готовится. "
        "Скоро обновим этот раздел."
    )


def get_instruction(platform: str, subscription_url: str) -> str:
    if platform == "ios":
        return instruction_ios(subscription_url)
    return instruction_placeholder(platform_label=PLATFORM_LABELS.get(platform, platform))
