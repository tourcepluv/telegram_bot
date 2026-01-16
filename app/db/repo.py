from __future__ import annotations

import json
from typing import Iterable

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import TARIFFS
from app.db.models import Device, Payment, PromoCode, PromoRedemption, Referral, Server, User


async def get_or_create_user(session: AsyncSession, tg_id: int, username: str | None, referral_code: str) -> User:
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()
    if user:
        return user
    user = User(tg_id=tg_id, username=username, referral_code=referral_code)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user_balance(session: AsyncSession, user_id: int, delta_kopeks: int) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    user.balance_kopeks += delta_kopeks
    await session.commit()
    await session.refresh(user)
    return user


async def list_user_devices(session: AsyncSession, user_id: int) -> list[Device]:
    result = await session.execute(select(Device).where(Device.owner_id == user_id))
    return list(result.scalars().all())


async def create_device(
    session: AsyncSession,
    owner_id: int,
    display_name: str,
    internal_code: str,
    platform: str,
    tariff_code: str,
    marzban_username: str,
    server_tags_csv: str,
) -> Device:
    device = Device(
        owner_id=owner_id,
        display_name=display_name,
        internal_code=internal_code,
        platform=platform,
        tariff_code=tariff_code,
        marzban_username=marzban_username,
        server_tags_csv=server_tags_csv,
    )
    session.add(device)
    await session.commit()
    await session.refresh(device)
    return device


async def update_device_subscription(session: AsyncSession, device_id: int, subscription_url: str) -> None:
    result = await session.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one()
    device.subscription_url = subscription_url
    await session.commit()


async def update_device_tariff(session: AsyncSession, device_id: int, tariff_code: str, server_tags_csv: str) -> None:
    result = await session.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one()
    device.tariff_code = tariff_code
    device.server_tags_csv = server_tags_csv
    await session.commit()


async def delete_device(session: AsyncSession, device_id: int) -> Device:
    result = await session.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one()
    await session.delete(device)
    await session.commit()
    return device


async def set_device_paused(session: AsyncSession, device_ids: Iterable[int], paused: bool) -> None:
    await session.execute(update(Device).where(Device.id.in_(list(device_ids))).values(is_paused=paused))
    await session.commit()


async def save_payment(
    session: AsyncSession,
    owner_id: int,
    amount_kopeks: int,
    status: str,
    provider: str,
    provider_payment_id: str,
    context: dict,
) -> Payment:
    payment = Payment(
        owner_id=owner_id,
        amount_kopeks=amount_kopeks,
        status=status,
        provider=provider,
        provider_payment_id=provider_payment_id,
        context_json=json.dumps(context, ensure_ascii=False),
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def mark_payment_status(session: AsyncSession, provider_payment_id: str, status: str) -> Payment:
    result = await session.execute(select(Payment).where(Payment.provider_payment_id == provider_payment_id))
    payment = result.scalar_one()
    payment.status = status
    await session.commit()
    await session.refresh(payment)
    return payment


async def get_payment_by_provider_id(session: AsyncSession, provider_payment_id: str) -> Payment | None:
    result = await session.execute(select(Payment).where(Payment.provider_payment_id == provider_payment_id))
    return result.scalar_one_or_none()


async def list_active_devices(session: AsyncSession, user_id: int) -> list[Device]:
    result = await session.execute(
        select(Device).where(Device.owner_id == user_id, Device.is_paused.is_(False))
    )
    return list(result.scalars().all())


async def list_devices_by_ids(session: AsyncSession, device_ids: list[int]) -> list[Device]:
    result = await session.execute(select(Device).where(Device.id.in_(device_ids)))
    return list(result.scalars().all())


async def get_device(session: AsyncSession, device_id: int) -> Device | None:
    result = await session.execute(select(Device).where(Device.id == device_id))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def set_user_flags(session: AsyncSession, user_id: int, **fields) -> None:
    await session.execute(update(User).where(User.id == user_id).values(**fields))
    await session.commit()


async def list_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User))
    return list(result.scalars().all())


async def list_payments(session: AsyncSession, limit: int = 20) -> list[Payment]:
    result = await session.execute(
        select(Payment).where(Payment.status == "succeeded").order_by(Payment.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def get_payment_sum(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.coalesce(func.sum(Payment.amount_kopeks), 0)).where(Payment.status == "succeeded")
    )
    return int(result.scalar_one())


async def create_server(session: AsyncSession, tag: str, pool: str, capacity: int) -> Server:
    server = Server(tag=tag, pool=pool, capacity=capacity, active_count=0, is_full=False)
    session.add(server)
    await session.commit()
    await session.refresh(server)
    return server


async def list_servers(session: AsyncSession) -> list[Server]:
    result = await session.execute(select(Server))
    return list(result.scalars().all())


async def update_server_usage(session: AsyncSession, tag: str, delta: int) -> Server:
    result = await session.execute(select(Server).where(Server.tag == tag))
    server = result.scalar_one()
    server.active_count = max(0, server.active_count + delta)
    server.is_full = server.active_count >= server.capacity
    await session.commit()
    await session.refresh(server)
    return server


async def ensure_servers(session: AsyncSession, pool: str, tags: list[str], capacity: int) -> None:
    for tag in tags:
        result = await session.execute(select(Server).where(Server.tag == tag))
        if result.scalar_one_or_none():
            continue
        session.add(Server(tag=tag, pool=pool, capacity=capacity, active_count=0, is_full=False))
    await session.commit()


async def create_promo(session: AsyncSession, code: str, bonus_kopeks: int, max_uses: int | None, campaign: str | None) -> PromoCode:
    promo = PromoCode(code=code, bonus_kopeks=bonus_kopeks, max_uses=max_uses, campaign=campaign)
    session.add(promo)
    await session.commit()
    await session.refresh(promo)
    return promo


async def list_promos(session: AsyncSession) -> list[PromoCode]:
    result = await session.execute(select(PromoCode))
    return list(result.scalars().all())


async def get_promo(session: AsyncSession, code: str) -> PromoCode | None:
    result = await session.execute(select(PromoCode).where(PromoCode.code == code))
    return result.scalar_one_or_none()


async def count_promo_redemptions(session: AsyncSession, promo_id: int) -> int:
    result = await session.execute(select(func.count(PromoRedemption.id)).where(PromoRedemption.promo_id == promo_id))
    return int(result.scalar_one())


async def redeem_promo(session: AsyncSession, promo_id: int, user_id: int) -> PromoRedemption:
    redemption = PromoRedemption(promo_id=promo_id, user_id=user_id)
    session.add(redemption)
    await session.commit()
    await session.refresh(redemption)
    return redemption


async def has_user_redeemed(session: AsyncSession, promo_id: int, user_id: int) -> bool:
    result = await session.execute(
        select(PromoRedemption).where(PromoRedemption.promo_id == promo_id, PromoRedemption.user_id == user_id)
    )
    return result.scalar_one_or_none() is not None


async def create_referral(session: AsyncSession, inviter_id: int, invited_id: int) -> Referral:
    referral = Referral(inviter_user_id=inviter_id, invited_user_id=invited_id, rewarded=False)
    session.add(referral)
    await session.commit()
    await session.refresh(referral)
    return referral


async def get_referral(session: AsyncSession, invited_id: int) -> Referral | None:
    result = await session.execute(select(Referral).where(Referral.invited_user_id == invited_id))
    return result.scalar_one_or_none()


async def mark_referral_rewarded(session: AsyncSession, referral_id: int) -> None:
    result = await session.execute(select(Referral).where(Referral.id == referral_id))
    referral = result.scalar_one()
    referral.rewarded = True
    referral.rewarded_at = func.now()
    await session.commit()


async def get_daily_cost(session: AsyncSession, user_id: int) -> int:
    devices = await list_active_devices(session, user_id)
    monthly_sum = sum(TARIFFS[device.tariff_code].monthly_price_rub for device in devices)
    return int((monthly_sum * 100 + 29) // 30)
