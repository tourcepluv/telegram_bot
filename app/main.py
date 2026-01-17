from __future__ import annotations

import asyncio
import json
import secrets

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.logic import run_daily_billing, try_resume_after_topup
from app.billing.scheduler import setup_scheduler
from app.config import settings
from app.db.base import Base
from app.db.repo import (
    create_device,
    ensure_servers,
    get_device,
    get_payment_by_provider_id,
    get_referral,
    get_user_by_id,
    log_event,
    mark_payment_status,
    mark_referral_rewarded,
    set_user_flags,
    update_device_subscription,
    update_user_balance,
)
from app.db.session import AsyncSessionLocal, engine
from app.handlers import admin, devices, menu, onboarding, start
from app.marzban.client import MarzbanClient
from app.payments.yookassa_client import YooKassaClient
from app.servers.allocator import allocate_server
from app.constants import TARIFFS


app = FastAPI()


class DependenciesMiddleware:
    def __init__(self, sessionmaker, marzban: MarzbanClient, yookassa: YooKassaClient) -> None:
        self._sessionmaker = sessionmaker
        self._marzban = marzban
        self._yookassa = yookassa

    async def __call__(self, handler, event, data):
        async with self._sessionmaker() as session:
            data["session"] = session
            data["marzban"] = self._marzban
            data["yookassa"] = self._yookassa
            return await handler(event, data)


bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))

storage = MemoryStorage()

dp = Dispatcher(storage=storage)

dp.include_router(start.router)

dp.include_router(onboarding.router)

dp.include_router(menu.router)

dp.include_router(devices.router)

dp.include_router(admin.router)

marzban_client = MarzbanClient()
yookassa_client = YooKassaClient()

scheduler = None


@app.on_event("startup")
async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await ensure_servers(session, "EU", settings.eu_tags_list, settings.eu_server_capacity)
        await ensure_servers(session, "RU", settings.ru_tags_list, settings.ru_server_capacity)
    dp.update.middleware(DependenciesMiddleware(AsyncSessionLocal, marzban_client, yookassa_client))

    global scheduler
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    scheduler = AsyncIOScheduler(timezone=settings.timezone)

    async def billing_job() -> None:
        async with AsyncSessionLocal() as session:
            await run_daily_billing(session, bot, marzban_client)

    setup_scheduler(scheduler, billing_job, timezone=settings.timezone)
    scheduler.start()
    asyncio.create_task(dp.start_polling(bot))


@app.on_event("shutdown")
async def on_shutdown() -> None:
    if scheduler:
        scheduler.shutdown()
    await marzban_client.close()
    await yookassa_client.close()
    await bot.session.close()


@app.post(settings.webhook_path)
async def yookassa_webhook(request: Request) -> JSONResponse:
    payload = await request.json()
    payment_id = payload.get("object", {}).get("id")
    if not payment_id:
        return JSONResponse({"status": "ignored"})

    async with AsyncSessionLocal() as session:
        payment = await get_payment_by_provider_id(session, payment_id)
        if not payment:
            return JSONResponse({"status": "unknown"})

        payment_status = await yookassa_client.get_payment(payment_id)
        status = payment_status.get("status")
        if status != "succeeded":
            return JSONResponse({"status": "pending"})

        if payment.status == "succeeded":
            return JSONResponse({"status": "already_processed"})

        await mark_payment_status(session, payment_id, "succeeded")
        await update_user_balance(session, payment.owner_id, payment.amount_kopeks)
        user = await get_user_by_id(session, payment.owner_id)
        if not user:
            return JSONResponse({"status": "user_missing"})
        await log_event(session, user.id, "payment_success")
        if not user.has_made_first_payment:
            await set_user_flags(session, user.id, has_made_first_payment=True)
            referral = await get_referral(session, user.id)
            if referral and not referral.rewarded and payment.amount_kopeks >= settings.ref_min_payment_rub * 100:
                await update_user_balance(session, referral.inviter_user_id, settings.ref_bonus_rub * 100)
                await mark_referral_rewarded(session, referral.id)

        context = json.loads(payment.context_json)
        invoice_message_id = context.get("invoice_message_id")
        if isinstance(invoice_message_id, int):
            try:
                await bot.delete_message(user.tg_id, invoice_message_id)
            except Exception:  # noqa: BLE001
                pass
        action = context.get("action")
        if action in {"onboarding", "add_device"}:
            tariff_code = context["tariff_code"]
            platform = context["platform"]
            display_name = context["display_name"]
            internal_code = context["internal_code"]
            marzban_username = f"tg{user.tg_id}_{internal_code}"
            server_tags = []
            if tariff_code == "T1":
                server = await allocate_server(session, "EU")
                server_tags = [server.tag]
            elif tariff_code == "T2":
                server = await allocate_server(session, "RU")
                server_tags = [server.tag]
            else:
                eu_server = await allocate_server(session, "EU")
                ru_server = await allocate_server(session, "RU")
                server_tags = [eu_server.tag, ru_server.tag]

            device = await create_device(
                session=session,
                owner_id=user.id,
                display_name=display_name,
                internal_code=internal_code,
                platform=platform,
                tariff_code=tariff_code,
                marzban_username=marzban_username,
                server_tags_csv=",".join(server_tags),
            )

            proxy_list = settings.marzban_proxy_list or ["vless"]
            proxies: dict[str, dict] = {}
            if "vless" in proxy_list:
                proxies["vless"] = {"flow": "xtls-rprx-vision"}
            if "vmess" in proxy_list:
                proxies["vmess"] = {}
            if "shadowsocks" in proxy_list:
                proxies["shadowsocks"] = {}
            payload = {
                "username": marzban_username,
                "status": "active",
                "expire": None,
                "data_limit": 0,
                "data_limit_reset_strategy": "no_reset",
                "proxies": proxies,
                "inbounds": {"vless": server_tags},
                "note": TARIFFS[tariff_code].name,
                "level": settings.marzban_level,
                "limit_ip": settings.marzban_limit_ip,
            }
            try:
                response = await marzban_client.create_user(payload)
                subscription_url = response.get("subscription_url")
                if subscription_url:
                    await update_device_subscription(session, device.id, subscription_url)
            except Exception as exc:  # noqa: BLE001
                print(f"Marzban create error: {exc}")
                for tag in server_tags:
                    from app.servers.allocator import release_server

                    await release_server(session, tag)

            await devices.send_subscription_and_instruction(
                bot,
                user.tg_id,
                device_id=device.id,
                session=session,
            )
            await log_event(session, user.id, "sub_issued")
        else:
            await try_resume_after_topup(session, bot, marzban_client, user.id)
        return JSONResponse({"status": "ok"})


@app.get("/pay/return", response_class=HTMLResponse)
async def payment_return() -> str:
    return "<h3>Оплата принята, вернитесь в Telegram.</h3>"
