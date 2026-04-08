from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu(is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="Записаться", callback_data="menu:book"),
        ],
        [
            InlineKeyboardButton(text="Моя запись", callback_data="menu:my"),
            InlineKeyboardButton(text="Отменить запись", callback_data="menu:cancel_my"),
        ],
        [
            InlineKeyboardButton(text="Прайсы", callback_data="menu:prices"),
            InlineKeyboardButton(text="Портфолио", callback_data="menu:portfolio"),
        ],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text="Админ-панель", callback_data="menu:admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:home")]]
    )


def subscription_required_kb(channel_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться", url=channel_link)],
            [InlineKeyboardButton(text="Проверить подписку", callback_data="sub:check")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:home")],
        ]
    )

