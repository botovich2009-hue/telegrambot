from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Добавить рабочий день", callback_data="admin:action:add_day"),
            ],
            [
                InlineKeyboardButton(text="🕒 Слоты времени (добавить/удалить)", callback_data="admin:action:slots"),
            ],
            [
                InlineKeyboardButton(text="🔒 Закрыть день", callback_data="admin:action:close_day"),
                InlineKeyboardButton(text="🔓 Открыть день", callback_data="admin:action:open_day"),
            ],
            [
                InlineKeyboardButton(text="📋 Расписание на дату", callback_data="admin:action:view"),
            ],
            [
                InlineKeyboardButton(text="❌ Отменить запись клиента", callback_data="admin:action:cancel_booking"),
            ],
            [
                InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:home"),
            ],
        ]
    )


def admin_slots_kb(day_iso: str, slots: list[str]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text="➕ Добавить слот", callback_data=f"admin:slots:add:{day_iso}"),
            InlineKeyboardButton(text="⬅️ Выбрать другую дату", callback_data="admin:pick_date"),
        ]
    ]
    for t in slots:
        rows.append([InlineKeyboardButton(text=f"Удалить {t}", callback_data=f"admin:slots:del:{day_iso}:{t}")])
    rows.append([InlineKeyboardButton(text="⬅️ Админ-меню", callback_data="admin:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_day_actions_kb(day_iso: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔒 Закрыть день", callback_data=f"admin:close:{day_iso}"),
                InlineKeyboardButton(text="🔓 Открыть день", callback_data=f"admin:open:{day_iso}"),
            ],
            [InlineKeyboardButton(text="⬅️ Выбрать другую дату", callback_data="admin:pick_date")],
            [InlineKeyboardButton(text="⬅️ Админ-меню", callback_data="admin:home")],
        ]
    )


def admin_bookings_list_kb(day_iso: str, booking_ids: list[tuple[int, str, str]]) -> InlineKeyboardMarkup:
    # booking_ids: [(id, time, name), ...]
    rows: list[list[InlineKeyboardButton]] = []
    for bid, t, n in booking_ids:
        rows.append([InlineKeyboardButton(text=f"{t} — {n}", callback_data=f"admin:cancel:{bid}")])
    rows.append([InlineKeyboardButton(text="⬅️ Выбрать другую дату", callback_data="admin:pick_date")])
    rows.append([InlineKeyboardButton(text="⬅️ Админ-меню", callback_data="admin:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_cancel_confirm_kb(booking_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, отменить", callback_data=f"admin:cancel_confirm:{booking_id}"),
                InlineKeyboardButton(text="❌ Нет", callback_data="admin:home"),
            ]
        ]
    )

