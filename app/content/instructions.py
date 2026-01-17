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
            "🤖 Настройка VPN на Android\n\n"
            "1. Установите HIddify из Play Market:\n"
            "🔗 https://play.google.com/store/apps/details?id=app.hiddify.com&hl=ru\n\n"
            "2. Скопируйте вашу конфигурацию:\n\n"
            "👇🏻Чтобы скопировать просто нажми на ссылку\n"
            f"{subscription_url}\n\n"
            "3. Откройте приложение и нажмите \"+\" → \"Добавить из буфера\"\n\n"
            "4. Выберите сервер."
        )
    if platform == "macos":
        return (
            "🍎 Настройка VPN на MacOS\n\n"
            "1. Установите V2Box из App Store или по ссылке ниже скачайте файл:\n"
            "🔗 https://apps.apple.com/us/app/v2box-v2ray-client/id6446814690?l=ru\n\n"
            "2. Скопируйте вашу конфигурацию:\n\n"
            "👇🏻Чтобы скопировать просто нажми на ссылку\n"
            f"{subscription_url}\n\n"
            "3. Нажмите \"+\" → в правом верхнем углу.\n\n"
            "4. Нажмите \"Вставить из буфера\"\n\n"
            "5. Выберите сервер и включите VPN"
        )
    if platform == "windows":
        return (
            "💻 Настройка VPN на Windows\n\n"
            "1. Скачайте и установите NekoBox:\n"
            "🔗 https://disk.yandex.ru/d/4t4dFk4tHJPmVg\n\n"
            "2. Скопируйте вашу конфигурацию:\n\n"
            "👇🏻Чтобы скопировать просто нажми на ссылку\n"
            f"{subscription_url}\n\n"
            "3. Нажмите \"Сервер\" → \"Добавить из буфера обмена\"\n\n"
            "4. Выберите сервер и включите VPN"
        )
    return instruction_placeholder(platform_label=PLATFORM_LABELS.get(platform, platform))
