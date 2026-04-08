from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def times_kb(day_iso: str, times: list[str]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(times), 3):
        chunk = times[i : i + 3]
        rows.append(
            [
                InlineKeyboardButton(
                    text=t,
                    callback_data=f"book:time:{day_iso}:{t}",
                )
                for t in chunk
            ]
        )

    rows.append([InlineKeyboardButton(text="⬅️ Назад к датам", callback_data="book:pick_date")])
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="book:confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="menu:home"),
            ]
        ]
    )


def cancel_my_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отменить запись", callback_data="book:cancel_my:yes"),
                InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:home"),
            ]
        ]
    )

