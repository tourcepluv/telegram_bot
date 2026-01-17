from __future__ import annotations

import secrets

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import TARIFFS
from app.content.instructions import get_instruction
from app.content.texts import DEVICES_HEADER, SUBSCRIPTION_MESSAGE, SUBSCRIPTION_RETRIEVE_MESSAGE
from app.db.repo import (
    delete_device,
    get_device,
    get_or_create_user,
    list_user_devices,
    log_event,
    update_device_subscription,
    update_device_tariff,
)
from app.keyboards.callbacks import DeviceActionCallback, DeviceSelectCallback, TariffCallback
from app.keyboards.inline import (
    devices_actions_keyboard,
    devices_list_keyboard,
    devices_overview_keyboard,
    invite_friend_keyboard,
    tariffs_keyboard,
)
from app.keyboards.reply import main_menu
from app.marzban.client import MarzbanClient
from app.servers.allocator import allocate_server, release_server


router = Router()


class DeviceState(StatesGroup):
    changing_tariff = State()


async def _render_devices_list(session: AsyncSession, user_id: int) -> str:
    devices = await list_user_devices(session, user_id)
    if not devices:
        return "У вас пока нет устройств."
    lines = [DEVICES_HEADER]
    for index, device in enumerate(devices, start=1):
        tariff = TARIFFS[device.tariff_code]
        status = "✅ Активно" if not device.is_paused else "⏸️ Приостановлено"
        daily = tariff.monthly_price_rub / 30
        lines.append(
            f"{index}. {device.display_name}\n"
            f"{tariff.name} — {tariff.monthly_price_rub} ₽/мес\n"
            f"{status}\n"
            f"Стоимость в день: {daily:.2f} ₽"
        )
    return "\n\n".join(lines)


async def show_devices_for_user(chat_id: int, user_id: int, session: AsyncSession, bot: Bot) -> None:
    text = await _render_devices_list(session, user_id)
    devices = await list_user_devices(session, user_id)
    await bot.send_message(chat_id, text, reply_markup=devices_overview_keyboard(bool(devices)))


async def show_devices(message: Message, session: AsyncSession) -> None:
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username, secrets.token_hex(4))
    await show_devices_for_user(message.chat.id, user.id, session, message.bot)


@router.callback_query(F.data == "devices_manage")
async def devices_manage(query: CallbackQuery, session: AsyncSession) -> None:
    user = await get_or_create_user(session, query.from_user.id, query.from_user.username, secrets.token_hex(4))
    devices = await list_user_devices(session, user.id)
    if not devices:
        await query.message.answer("У вас пока нет устройств.")
    else:
        await query.message.answer(
            "Выберите устройство:", reply_markup=devices_list_keyboard([(device.id, device.display_name) for device in devices])
        )
    await query.answer()


@router.callback_query(F.data == "devices_add")
async def devices_add(query: CallbackQuery, state: FSMContext) -> None:
    from app.content.texts import tariffs_message
    from app.handlers.onboarding import OnboardingState
    from app.keyboards.inline import tariffs_keyboard

    await state.set_state(OnboardingState.choosing_tariff)
    await state.update_data(action="add_device")
    await query.message.answer("Выберите тариф для нового устройства:")
    await query.message.answer(tariffs_message(), reply_markup=tariffs_keyboard())
    await query.answer()


@router.callback_query(DeviceSelectCallback.filter())
async def device_selected(query: CallbackQuery, callback_data: DeviceSelectCallback, session: AsyncSession) -> None:
    await query.message.answer("Выберите действие:", reply_markup=devices_actions_keyboard(callback_data.device_id))
    await query.answer()


@router.callback_query(DeviceActionCallback.filter())
async def device_action(
    query: CallbackQuery,
    callback_data: DeviceActionCallback,
    session: AsyncSession,
    marzban: MarzbanClient,
    state: FSMContext,
) -> None:
    device = await get_device(session, callback_data.device_id)
    if not device:
        await query.message.answer("Устройство не найдено.")
        await query.answer()
        return

    if callback_data.action == "subscription":
        if device.subscription_url:
            await query.message.answer(
                SUBSCRIPTION_RETRIEVE_MESSAGE.format(subscription_url=device.subscription_url),
                disable_web_page_preview=True,
            )
        else:
            try:
                response = await marzban.get_user(device.marzban_username)
                subscription_url = response.get("subscription_url")
                if subscription_url:
                    await update_device_subscription(session, device.id, subscription_url)
                    await query.message.answer(
                        SUBSCRIPTION_RETRIEVE_MESSAGE.format(subscription_url=subscription_url),
                        disable_web_page_preview=True,
                    )
            except Exception as exc:  # noqa: BLE001
                print(f"Marzban fetch error: {exc}")
                await query.message.answer("Не удалось получить подписку. Попробуйте позже.")
    elif callback_data.action == "instruction":
        if not device.subscription_url:
            await query.message.answer("Сначала получите подписку.")
        else:
            await query.message.answer(
                get_instruction(device.platform, device.subscription_url),
                reply_markup=invite_friend_keyboard(),
                disable_web_page_preview=True,
            )
            await log_event(session, device.owner_id, f"{device.platform}_guide_opened")
    elif callback_data.action == "change_tariff":
        await state.update_data(change_device_id=device.id)
        await state.set_state(DeviceState.changing_tariff)
        await query.message.answer("Выберите новый тариф:", reply_markup=tariffs_keyboard())
    elif callback_data.action == "reissue":
        try:
            await marzban.update_user(device.marzban_username, {"status": "disabled"})
            await marzban.update_user(device.marzban_username, {"status": "active"})
            response = await marzban.get_user(device.marzban_username)
            subscription_url = response.get("subscription_url")
            if subscription_url:
                await update_device_subscription(session, device.id, subscription_url)
                await query.message.answer(
                    SUBSCRIPTION_RETRIEVE_MESSAGE.format(subscription_url=subscription_url),
                    disable_web_page_preview=True,
                )
        except Exception as exc:  # noqa: BLE001
            print(f"Marzban reissue error: {exc}")
            await query.message.answer("Не удалось перевыпустить ключ.")
    elif callback_data.action == "delete":
        server_tags = device.server_tags_csv.split(",") if device.server_tags_csv else []
        try:
            await marzban.delete_user(device.marzban_username)
        except Exception as exc:  # noqa: BLE001
            print(f"Marzban delete error: {exc}")
            await marzban.update_user(device.marzban_username, {"status": "disabled"})
        await delete_device(session, device.id)
        for tag in server_tags:
            await release_server(session, tag)
        await query.message.answer("Устройство удалено.")
    await query.answer()


@router.callback_query(DeviceState.changing_tariff, TariffCallback.filter())
async def change_tariff_callback(
    query: CallbackQuery,
    callback_data: TariffCallback,
    session: AsyncSession,
    marzban: MarzbanClient,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    device_id = data.get("change_device_id")
    if not device_id:
        await query.message.answer("Не удалось определить устройство.")
        await query.answer()
        return

    device = await get_device(session, device_id)
    if not device:
        await query.message.answer("Устройство не найдено.")
        await query.answer()
        return

    old_tags = device.server_tags_csv.split(",") if device.server_tags_csv else []
    for tag in old_tags:
        await release_server(session, tag)

    if callback_data.code == "T1":
        tags = [(await allocate_server(session, "EU")).tag]
    elif callback_data.code == "T2":
        tags = [(await allocate_server(session, "RU")).tag]
    else:
        tags = [(await allocate_server(session, "EU")).tag, (await allocate_server(session, "RU")).tag]

    await update_device_tariff(session, device.id, callback_data.code, ",".join(tags))
    try:
        await marzban.update_user(device.marzban_username, {"inbounds": {"vless": tags}})
    except Exception as exc:  # noqa: BLE001
        print(f"Marzban update error: {exc}")
        await query.message.answer("Не удалось сменить тариф. Попробуйте позже.")
        return
    await query.message.answer("Тариф обновлён.")
    await state.clear()
    await query.answer()


async def send_subscription_and_instruction(
    bot: Bot,
    user_id: int,
    device_id: int,
    session: AsyncSession,
) -> None:
    device = await get_device(session, device_id)
    if not device or not device.subscription_url:
        return
    await bot.send_message(
        user_id,
        SUBSCRIPTION_MESSAGE.format(subscription_url=device.subscription_url),
        disable_web_page_preview=True,
    )
    await bot.send_message(
        user_id,
        get_instruction(device.platform, device.subscription_url),
        reply_markup=invite_friend_keyboard(),
        disable_web_page_preview=True,
    )
    await log_event(session, device.owner_id, f"{device.platform}_guide_opened")
