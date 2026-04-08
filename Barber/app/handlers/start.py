from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from app.config import Config
from app.keyboards.common import main_menu

router = Router()


def _is_admin(config: Config, user_id: int) -> bool:
    return user_id == config.admin_id


@router.message(CommandStart())
async def start_cmd(message: Message, config: Config) -> None:
    is_admin = _is_admin(config, message.from_user.id)
    await message.answer(
        text=(
            f"<b>{config.shop_name}</b>\n\n"
            "Выберите действие в меню ниже."
        ),
        reply_markup=main_menu(is_admin),
    )


@router.callback_query(lambda c: c.data == "menu:home")
async def menu_home(call: CallbackQuery, config: Config) -> None:
    is_admin = _is_admin(config, call.from_user.id)
    await call.message.edit_text(
        text=(f"<b>{config.shop_name}</b>\n\n" "Выберите действие в меню ниже."),
        reply_markup=main_menu(is_admin),
    )
    await call.answer()

