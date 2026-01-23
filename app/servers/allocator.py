from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Server


async def allocate_server(session: AsyncSession, pool: str) -> Server:
    result = await session.execute(
        select(Server).where(Server.pool == pool, Server.is_full.is_(False)).order_by(Server.active_count.asc())
    )
    server = result.scalars().first()
    if not server:
        raise RuntimeError(f"Нет доступных серверов в пуле {pool}")
    server.active_count += 1
    server.is_full = server.active_count >= server.capacity
    await session.commit()
    await session.refresh(server)
    return server


async def release_server(session: AsyncSession, tag: str) -> None:
    result = await session.execute(select(Server).where(Server.tag == tag))
    server = result.scalars().first()
    if not server:
        return
    server.active_count = max(0, server.active_count - 1)
    server.is_full = server.active_count >= server.capacity
    await session.commit()
