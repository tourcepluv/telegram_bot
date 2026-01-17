from __future__ import annotations

import datetime as dt
import json

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Payment
from app.db.repo import (
    create_promo,
    create_server,
    get_payment_sum,
    list_events_counts,
    list_last_event_counts,
    list_payments,
    list_payments_in_period,
    list_promos,
    list_promo_redemptions_in_period,
    list_servers,
    list_users_created_in_period,
)
from app.keyboards.inline import admin_period_keyboard, admin_reports_keyboard


router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_id_list


class AdminState(StatesGroup):
    entering_password = State()
    entering_period = State()


@router.message(Command("admin_stats"))
async def admin_stats(message: Message, session: AsyncSession) -> None:
    if not _is_admin(message.from_user.id):
        return
    payments_sum = await get_payment_sum(session)
    await message.answer(f"Сумма успешных оплат: {payments_sum // 100} ₽")


@router.message(Command("admin_payments"))
async def admin_payments(message: Message, session: AsyncSession) -> None:
    if not _is_admin(message.from_user.id):
        return
    payments = await list_payments(session)
    lines = ["Последние оплаты:"]
    for payment in payments:
        lines.append(f"{payment.id}: {payment.amount_kopeks // 100} ₽")
    await message.answer("\n".join(lines))


@router.message(Command("admin_addpromo"))
async def admin_addpromo(message: Message, session: AsyncSession) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /admin_addpromo CODE [campaign] [max_uses] [bonus_rub]")
        return
    code = parts[1]
    campaign = parts[2] if len(parts) > 2 else None
    max_uses = int(parts[3]) if len(parts) > 3 else None
    bonus_rub = int(parts[4]) if len(parts) > 4 else settings.promo_bonus_rub
    promo = await create_promo(session, code, bonus_rub * 100, max_uses, campaign)
    await message.answer(f"Промокод {promo.code} создан.")


@router.message(Command("admin_promos"))
async def admin_promos(message: Message, session: AsyncSession) -> None:
    if not _is_admin(message.from_user.id):
        return
    promos = await list_promos(session)
    lines = ["Промокоды:"]
    for promo in promos:
        lines.append(f"{promo.code} — {promo.bonus_kopeks // 100} ₽")
    await message.answer("\n".join(lines))


@router.message(Command("admin_addserver"))
async def admin_addserver(message: Message, session: AsyncSession) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 4:
        await message.answer("Использование: /admin_addserver POOL TAG CAPACITY")
        return
    pool = parts[1]
    tag = parts[2]
    capacity = int(parts[3])
    await create_server(session, tag, pool, capacity)
    await message.answer(f"Сервер {tag} добавлен в {pool}.")


@router.message(Command("admin_servers"))
async def admin_servers(message: Message, session: AsyncSession) -> None:
    if not _is_admin(message.from_user.id):
        return
    servers = await list_servers(session)
    lines = ["Сервера:"]
    for server in servers:
        lines.append(f"{server.tag} ({server.pool}) — {server.active_count}/{server.capacity}")
    await message.answer("\n".join(lines))


@router.message(Command("admin"))
async def admin_entry(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    if settings.admin_password:
        await state.set_state(AdminState.entering_password)
        await message.answer("Введите пароль администратора:")
        return
    await state.clear()
    await message.answer("Админ-меню:", reply_markup=admin_reports_keyboard())


@router.message(AdminState.entering_password)
async def admin_password_entered(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        await state.clear()
        return
    if settings.admin_password and message.text.strip() != settings.admin_password:
        await message.answer("Неверный пароль. Попробуйте ещё раз.")
        return
    await state.clear()
    await message.answer("Админ-меню:", reply_markup=admin_reports_keyboard())


@router.callback_query(F.data == "admin_period")
async def admin_period_menu(query: CallbackQuery) -> None:
    if not _is_admin(query.from_user.id):
        return
    await query.message.answer("Выберите период:", reply_markup=admin_period_keyboard())
    await query.answer()


def _period_range(label: str) -> tuple[dt.date, dt.date]:
    today = dt.date.today()
    if label == "today":
        return today, today
    if label == "yesterday":
        day = today - dt.timedelta(days=1)
        return day, day
    if label == "7d":
        return today - dt.timedelta(days=6), today
    if label == "30d":
        return today - dt.timedelta(days=29), today
    return today, today


def _period_datetimes(date_from: dt.date, date_to: dt.date) -> tuple[dt.datetime, dt.datetime]:
    start_at = dt.datetime.combine(date_from, dt.time.min)
    end_at = dt.datetime.combine(date_to, dt.time.max)
    return start_at, end_at


@router.callback_query(F.data.startswith("admin_period:"))
async def admin_period_selected(query: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(query.from_user.id):
        return
    _, label = query.data.split(":", 1)
    date_from, date_to = _period_range(label)
    await state.update_data(report_from=date_from.isoformat(), report_to=date_to.isoformat())
    await query.message.answer(f"Период установлен: {date_from} — {date_to}")
    await query.answer()


@router.callback_query(F.data == "admin_report:funnel")
async def admin_report_funnel(query: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not _is_admin(query.from_user.id):
        return
    data = await state.get_data()
    date_from = dt.date.fromisoformat(data.get("report_from", dt.date.today().isoformat()))
    date_to = dt.date.fromisoformat(data.get("report_to", dt.date.today().isoformat()))
    start_at, end_at = _period_datetimes(date_from, date_to)
    event_counts = await list_events_counts(session, start_at, end_at)
    last_event_counts = await list_last_event_counts(session, start_at, end_at)
    new_users = await list_users_created_in_period(session, start_at, end_at)
    payments = await list_payments_in_period(session, start_at, end_at)
    paid_users = len({payment.owner_id for payment in payments})
    tariff_screen_users = event_counts.get("tariff_screen", 0)
    invoice_users = event_counts.get("invoice_created", 0)
    pay_conv = round((paid_users / invoice_users) * 100, 1) if invoice_users else 0.0

    tariff_stats = {"T1": {"count": 0, "sum": 0}, "T2": {"count": 0, "sum": 0}, "T3": {"count": 0, "sum": 0}}
    for payment in payments:
        try:
            context = json.loads(payment.context_json)
        except json.JSONDecodeError:
            continue
        if context.get("action") not in {"onboarding", "add_device"}:
            continue
        code = context.get("tariff_code")
        if code in tariff_stats:
            tariff_stats[code]["count"] += 1
            tariff_stats[code]["sum"] += payment.amount_kopeks // 100

    total_paid = sum(item["sum"] for item in tariff_stats.values()) or 1
    p100_share = round(tariff_stats["T1"]["sum"] / total_paid * 100, 1)
    p150_share = round(tariff_stats["T2"]["sum"] / total_paid * 100, 1)
    p220_share = round(tariff_stats["T3"]["sum"] / total_paid * 100, 1)

    result = await session.execute(
        select(Payment.owner_id, func.count(Payment.id), func.max(Payment.created_at))
        .where(Payment.status == "succeeded")
        .group_by(Payment.owner_id)
    )
    payment_stats = {row[0]: {"count": row[1], "last_at": row[2]} for row in result.all()}
    renewed = sum(
        1
        for user_id, info in payment_stats.items()
        if info["count"] >= 2 and any(p.owner_id == user_id for p in payments)
    )
    churned = sum(
        1
        for info in payment_stats.values()
        if info["last_at"] and info["last_at"] < start_at
    )
    churn_rate = round((churned / (renewed + churned)) * 100, 1) if (renewed + churned) else 0.0

    stage_labels = {
        "start": "start",
        "connect_click": "подключить",
        "tariff_screen": "тарифы",
        "invoice_created": "счёт",
        "payment_success": "оплата",
        "sub_issued": "выдано",
        "ios_guide_opened": "инструкция iOS",
        "android_guide_opened": "инструкция Android",
    }
    top_drop = sorted(last_event_counts.items(), key=lambda item: item[1], reverse=True)[:3]
    drop_lines = [f"{stage_labels.get(stage, stage)} — {count}" for stage, count in top_drop] or ["—"]

    await query.message.answer(
        "📊 Отчёт: Воронка и оплаты\n"
        f"Период: {date_from} — {date_to}\n\n"
        "👥 Пользователи\n"
        f"• Новые: {new_users}\n"
        f"• Дошли до тарифов: {tariff_screen_users}\n"
        f"• Создали счёт: {invoice_users}\n"
        f"• Оплатили: {paid_users} ({pay_conv}%)\n\n"
        "💳 Оплаты по тарифам\n"
        f"✅ 100 ₽: {tariff_stats['T1']['count']} (₽{tariff_stats['T1']['sum']}) — {p100_share}%\n"
        f"📶 150 ₽: {tariff_stats['T2']['count']} (₽{tariff_stats['T2']['sum']}) — {p150_share}%\n"
        f"⭐ 220 ₽: {tariff_stats['T3']['count']} (₽{tariff_stats['T3']['sum']}) — {p220_share}%\n\n"
        "🔁 Удержание (оценка по оплатам)\n"
        f"• Продлили: {renewed}\n"
        f"• Не продлили: {churned} ({churn_rate}%)\n\n"
        "🚧 Где отвалились (топ)\n\n"
        + "\n".join(drop_lines)
    )
    await query.answer()


@router.callback_query(F.data == "admin_report:promos")
async def admin_report_promos(query: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not _is_admin(query.from_user.id):
        return
    data = await state.get_data()
    date_from = dt.date.fromisoformat(data.get("report_from", dt.date.today().isoformat()))
    date_to = dt.date.fromisoformat(data.get("report_to", dt.date.today().isoformat()))
    start_at, end_at = _period_datetimes(date_from, date_to)
    promos = await list_promos(session)
    redemptions = await list_promo_redemptions_in_period(session, start_at, end_at)
    payments = await list_payments_in_period(session, start_at, end_at)
    if not promos:
        await query.message.answer("Промокоды не найдены.")
        await query.answer()
        return

    by_promo: dict[int, dict] = {
        promo.id: {
            "code": promo.code,
            "entered": 0,
            "users": set(),
            "paid": 0,
            "revenue": 0,
        }
        for promo in promos
    }
    for redemption in redemptions:
        item = by_promo.get(redemption.promo_id)
        if not item:
            continue
        item["entered"] += 1
        item["users"].add(redemption.user_id)

    users_by_promo = {promo_id: data["users"] for promo_id, data in by_promo.items()}
    for payment in payments:
        for promo_id, users in users_by_promo.items():
            if payment.owner_id in users:
                by_promo[promo_id]["paid"] += 1
                by_promo[promo_id]["revenue"] += payment.amount_kopeks // 100

    lines = ["🎟 Отчёт: Промокоды", f"Период: {date_from} — {date_to}", ""]
    for promo_id, data in by_promo.items():
        entered = data["entered"]
        paid = data["paid"]
        revenue = data["revenue"]
        users_count = len(data["users"])
        cr = round((paid / entered) * 100, 1) if entered else 0.0
        lines.append(
            f"{data['code']} — вводов: {entered}, users: {users_count}, оплат: {paid} (₽{revenue}), CR: {cr}%"
        )
    await query.message.answer("\n".join(lines))
    await query.answer()
