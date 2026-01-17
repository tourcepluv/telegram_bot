from __future__ import annotations

import secrets

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.texts import START_MESSAGE
from app.db.repo import create_referral, get_or_create_user, list_users, log_event
from app.keyboards.inline import start_button
from app.keyboards.reply import main_menu


router = Router()


def _generate_ref_code() -> str:
    return secrets.token_hex(4)


@router.message(CommandStart())
async def start_handler(message: Message, session: AsyncSession, state: FSMContext) -> None:
    payload = message.text.split(" ", maxsplit=1)
    ref_code = payload[1] if len(payload) > 1 else ""
    referral_code = _generate_ref_code()
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username, referral_code)

    if ref_code.startswith("ref_"):
        inviter_code = ref_code.replace("ref_", "", 1)
        inviter = next((candidate for candidate in await list_users(session) if candidate.referral_code == inviter_code), None)
        if inviter and inviter.id != user.id:
            await create_referral(session, inviter.id, user.id)

    await state.clear()
    await message.answer(START_MESSAGE, reply_markup=start_button())
    try:
        temp_message = await message.answer(" ", reply_markup=main_menu())
        await temp_message.delete()
    except Exception:  # noqa: BLE001
        pass
    await log_event(session, user.id, "start")
