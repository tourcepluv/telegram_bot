from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class TariffCallback(CallbackData, prefix="tariff"):
    code: str


class PlatformCallback(CallbackData, prefix="platform"):
    platform: str


class DeviceActionCallback(CallbackData, prefix="device_action"):
    device_id: int
    action: str


class DeviceSelectCallback(CallbackData, prefix="device_select"):
    device_id: int


class TopUpCallback(CallbackData, prefix="topup"):
    amount: int
    context: str


class SubscriptionCopyCallback(CallbackData, prefix="copy_sub"):
    device_id: int
