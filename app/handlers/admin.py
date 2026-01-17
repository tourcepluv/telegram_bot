from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.repo import create_promo, create_server, get_payment_sum, list_payments, list_promos, list_servers


router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_id_list


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
