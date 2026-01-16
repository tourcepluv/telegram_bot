from __future__ import annotations

from app.constants import PLATFORM_LABELS


def instruction_ios(subscription_url: str) -> str:
    return (
        "📱 Настройка VPN на iOS\n\n"
        "1. Установите v2RayTUN из App Store:\n"
        "🔗 https://apps.apple.com/ru/app/v2raytun/id6476628951\n\n"
        "2. Скопируйте вашу конфигурацию:\n\n"
        "👇🏻Чтобы скопировать просто нажми на ссылку\n"
        f"{subscription_url}\n\n"
        "3. Откройте приложение и нажмите \"+\" → \"Добавить из буфера\"\n\n"
        "4. Выберите сервер.\n\n"
        "⚠️ Разрешите установку VPN-профиля в настройках iOS"
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
