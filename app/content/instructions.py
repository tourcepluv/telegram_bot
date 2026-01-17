from __future__ import annotations

from app.constants import PLATFORM_LABELS


def instruction_ios(subscription_url: str) -> str:
    return (
        "📲 Настройка на iOS (1 минута)\n\n"
        "Установите V2Box из App Store:\n"
        "🔗 https://apps.apple.com/app/id6446814690\n\n"
        "Скопируйте вашу конфигурацию:\n"
        f"<code>{subscription_url}</code>\n\n"
        "Откройте V2Box → “+” → “Добавить из буфера”\n\n"
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
    if platform == "android":
        return (
            "📲 Настройка на Android (1 минута)\n\n"
            "Установите Hiddify из Google Play:\n"
            "🔗 https://play.google.com/store/apps/details?id=app.hiddify.com&hl=ru\n\n"
            "Скопируйте вашу конфигурацию:\n"
            f"<code>{subscription_url}</code>\n\n"
            "Откройте Hiddify → “+” → “Добавить из буфера”\n\n"
            "Включите подключение ✅"
        )
    if platform == "macos":
        return (
            "💻 Настройка на macOS (1 минута)\n\n"
            "Установите V2Box из App Store:\n"
            "🔗 https://apps.apple.com/us/app/v2box-v2ray-client/id6446814690?l=ru\n\n"
            "Скопируйте вашу конфигурацию:\n"
            f"<code>{subscription_url}</code>\n\n"
            "Откройте V2Box → “+” → “Добавить из буфера”\n\n"
            "Включите подключение ✅"
        )
    if platform == "windows":
        return (
            "🖥 Настройка на Windows (1 минута)\n\n"
            "Установите NekoBox:\n"
            "🔗 https://disk.yandex.ru/d/4t4dFk4tHJPmVg\n\n"
            "Скопируйте вашу конфигурацию:\n"
            f"<code>{subscription_url}</code>\n\n"
            "Откройте NekoBox → “+” → “Добавить из буфера”\n\n"
            "Включите подключение ✅"
        )
    return instruction_placeholder(platform_label=PLATFORM_LABELS.get(platform, platform))
