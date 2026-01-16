from __future__ import annotations

from app.constants import TARIFFS, TARIFF_TEXT_ORDER


def tariffs_message() -> str:
    lines = ["<b>Тарифы:</b>", ""]
    for code in TARIFF_TEXT_ORDER:
        tariff = TARIFFS[code]
        title = f"<b>{tariff.name} — {tariff.monthly_price_rub} ₽/мес за устройство</b>"
        if tariff.is_recommended:
            title += " <i>(рекомендуем)</i>"
        lines.append(title)
        lines.append(f"“{tariff.description}”")
        lines.append("")
    return "\n".join(lines).strip()


START_MESSAGE = (
    "Привет! Поможем подключить стабильный доступ к сервису.\n"
    "Настроим всё в пару шагов, без лишней технички.\n"
    "Доступ работает, когда мобильная сеть ведёт себя нестабильно.\n"
    "Нажмите кнопку ниже, чтобы начать."
)

STEP_DEVICE = "Шаг 2/3: выберите устройство:"
STEP_NAME = (
    "Шаг 3/3: как назовём устройство? Можно написать… "
    "Или нажмите «Пропустить» — имя создастся автоматически."
)

NEARLY_READY = (
    "🎉 <b>Почти готово!</b>\n"
    "Мы настроили устройство <b>{display_name}</b> ({tariff_name}). Осталось активировать доступ.\n"
    "💳 <b>К оплате:</b> {monthly_price} ₽/мес\n"
    "💰 <b>Ваш баланс:</b> {balance} ₽\n"
    "Пополняя баланс, вы соглашаетесь с офертой."
)

PROMO_PROMPT = "🎁 Есть промокод на бонус?"

def help_text(support_username: str) -> str:
    return (
        "Если нужна помощь — мы на связи.\n"
        f"<a href=\"https://t.me/{support_username}\">@{support_username}</a>"
    )

PAUSED_TEXT = "Доступ приостановлен до пополнения."
RESUMED_TEXT = "Доступ восстановлен."

BALANCE_TEMPLATE = (
    "💰 Баланс: {balance} ₽\n"
    "📱 Активных устройств: {active_devices}\n"
    "💸 Списание в день: {daily_cost} ₽/день\n"
    "⏳ Примерно хватит на: {days_left} дней"
)

DEVICES_HEADER = "Ваши устройства:"

SUBSCRIPTION_MESSAGE = (
    "Ваша подписка: {subscription_url}\n"
    "⚠️ Не пересылайте ссылку."
)
