from __future__ import annotations

import base64
import uuid

import httpx

from app.config import settings


class YooKassaClient:
    def __init__(self) -> None:
        auth = f"{settings.yookassa_shop_id}:{settings.yookassa_secret_key}"
        token = base64.b64encode(auth.encode()).decode()
        self._client = httpx.AsyncClient(
            base_url="https://api.yookassa.ru/v3",
            headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"},
        )

    async def create_payment(self, amount_rub: int, description: str, metadata: dict) -> dict:
        payload = {
            "amount": {"value": f"{amount_rub:.2f}", "currency": "RUB"},
            "capture": True,
            "confirmation": {"type": "redirect", "return_url": settings.return_url},
            "description": description,
            "metadata": metadata,
        }
        headers = {"Idempotence-Key": str(uuid.uuid4())}
        response = await self._client.post("/payments", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    async def get_payment(self, payment_id: str) -> dict:
        response = await self._client.get(f"/payments/{payment_id}")
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self._client.aclose()
