from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from app.keyboards.common import back_to_menu

router = Router()


@router.callback_query(lambda c: c.data == "menu:prices")
async def show_prices(call: CallbackQuery) -> None:
    text = (
        "<b>Прайс-лист</b>\n\n"
        "Мужская стрижка — <b>1500₽</b>\n"
        "Стрижка + борода — <b>2000₽</b>\n"
        "Оформление бороды — <b>1000₽</b>\n"
    )
    await call.message.edit_text(text=text, reply_markup=back_to_menu())
    await call.answer()


@router.callback_query(lambda c: c.data == "menu:portfolio")
async def show_portfolio(call: CallbackQuery) -> None:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Смотреть портфолио",
                    url="https://ru.pinterest.com/crystalwithluv/_created/",
                )
            ],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:home")],
        ]
    )
    await call.message.edit_text(
        text="<b>Портфолио</b>\n\nНажмите кнопку ниже, чтобы посмотреть работы.",
        reply_markup=kb,
    )
    await call.answer()

