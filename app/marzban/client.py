from __future__ import annotations

import httpx

from app.config import settings


class MarzbanClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.marzban_base_url,
            headers={"Authorization": f"Bearer {settings.marzban_api_token}"},
        )

    async def create_user(self, payload: dict) -> dict:
        response = await self._client.post("/api/user", json=payload)
        response.raise_for_status()
        return response.json()

    async def update_user(self, username: str, payload: dict) -> dict:
        response = await self._client.put(f"/api/user/{username}", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_user(self, username: str) -> dict:
        response = await self._client.get(f"/api/user/{username}")
        response.raise_for_status()
        return response.json()

    async def delete_user(self, username: str) -> None:
        response = await self._client.delete(f"/api/user/{username}")
        if response.status_code in {200, 204, 404}:
            return
        response.raise_for_status()

    async def close(self) -> None:
        await self._client.aclose()
