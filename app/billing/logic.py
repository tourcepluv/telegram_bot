from __future__ import annotations

import math

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.texts import PAUSED_TEXT, RESUMED_TEXT
from app.db.repo import get_daily_cost, list_active_devices, list_user_devices, list_users, set_device_paused
from app.marzban.client import MarzbanClient


async def run_daily_billing(session: AsyncSession, bot: Bot, marzban: MarzbanClient) -> None:
    users = await list_users(session)
    for user in users:
        active_devices = await list_active_devices(session, user.id)
        if not active_devices:
            continue
        daily_cost = await get_daily_cost(session, user.id)
        if daily_cost <= 0:
            continue
        if user.balance_kopeks >= daily_cost:
            user.balance_kopeks -= daily_cost
            await session.commit()
            days_left = calculate_days_left(user.balance_kopeks, daily_cost)
            if days_left <= 1:
                await bot.send_message(user.tg_id, "Баланс на исходе. Рекомендуем пополнить заранее.")
            elif days_left <= 3:
                await bot.send_message(user.tg_id, "Баланс подходит к концу. Проверьте, хватит ли на нужный срок.")
            continue
        device_ids = [device.id for device in active_devices]
        await set_device_paused(session, device_ids, True)
        for device in active_devices:
            try:
                await marzban.update_user(device.marzban_username, {"status": "disabled"})
            except Exception as exc:  # noqa: BLE001
                print(f"Marzban disable error: {exc}")
        await bot.send_message(user.tg_id, PAUSED_TEXT)


async def try_resume_after_topup(session: AsyncSession, bot: Bot, marzban: MarzbanClient, user_id: int) -> None:
    devices = await list_user_devices(session, user_id)
    paused_devices = [device for device in devices if device.is_paused]
    if not paused_devices:
        return
    daily_cost = await get_daily_cost(session, user_id)
    if daily_cost <= 0:
        return
    user = next(user for user in await list_users(session) if user.id == user_id)
    if user.balance_kopeks < daily_cost:
        return
    await set_device_paused(session, [device.id for device in paused_devices], False)
    for device in paused_devices:
        try:
            await marzban.update_user(device.marzban_username, {"status": "active"})
        except Exception as exc:  # noqa: BLE001
            print(f"Marzban resume error: {exc}")
    await bot.send_message(user.tg_id, RESUMED_TEXT)


def calculate_days_left(balance_kopeks: int, daily_cost: int) -> int:
    if daily_cost <= 0:
        return 0
    return max(0, math.floor(balance_kopeks / daily_cost))
