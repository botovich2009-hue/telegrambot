from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


@dataclass(frozen=True)
class CalendarMonth:
    year: int
    month: int

    @property
    def first_day(self) -> date:
        return date(self.year, self.month, 1)

    def shift(self, delta_months: int) -> "CalendarMonth":
        y = self.year
        m = self.month + delta_months
        while m < 1:
            m += 12
            y -= 1
        while m > 12:
            m -= 12
            y += 1
        return CalendarMonth(y, m)


def _cb(prefix: str, payload: str) -> str:
    return f"{prefix}:{payload}"


def calendar_kb(
    *,
    prefix: str,
    month: CalendarMonth,
    enabled_days: set[str],
    min_day: date,
    max_day: date,
) -> InlineKeyboardMarkup:
    """
    Inline-calendar. enabled_days contains ISO days that should be clickable.
    """
    cal = calendar.Calendar(firstweekday=0)  # Monday
    month_name = datetime(month.year, month.month, 1).strftime("%B %Y")

    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=f"📅 {month_name}", callback_data=_cb(prefix, "noop"))],
        [
            InlineKeyboardButton(text="Пн", callback_data=_cb(prefix, "noop")),
            InlineKeyboardButton(text="Вт", callback_data=_cb(prefix, "noop")),
            InlineKeyboardButton(text="Ср", callback_data=_cb(prefix, "noop")),
            InlineKeyboardButton(text="Чт", callback_data=_cb(prefix, "noop")),
            InlineKeyboardButton(text="Пт", callback_data=_cb(prefix, "noop")),
            InlineKeyboardButton(text="Сб", callback_data=_cb(prefix, "noop")),
            InlineKeyboardButton(text="Вс", callback_data=_cb(prefix, "noop")),
        ],
    ]

    for week in cal.monthdatescalendar(month.year, month.month):
        row: list[InlineKeyboardButton] = []
        for d in week:
            if d.month != month.month:
                row.append(InlineKeyboardButton(text=" ", callback_data=_cb(prefix, "noop")))
                continue
            if d < min_day or d > max_day:
                row.append(InlineKeyboardButton(text=f"{d.day}", callback_data=_cb(prefix, "noop")))
                continue
            iso = d.isoformat()
            if iso in enabled_days:
                row.append(InlineKeyboardButton(text=f"{d.day}", callback_data=_cb(prefix, f"day={iso}")))
            else:
                row.append(InlineKeyboardButton(text=f"{d.day}", callback_data=_cb(prefix, "noop")))
        rows.append(row)

    prev_m = month.shift(-1)
    next_m = month.shift(1)
    can_prev = prev_m.first_day >= date(min_day.year, min_day.month, 1)
    can_next = next_m.first_day <= date(max_day.year, max_day.month, 1)

    nav_row = []
    nav_row.append(
        InlineKeyboardButton(
            text="⬅️" if can_prev else " ",
            callback_data=_cb(prefix, f"month={prev_m.year}-{prev_m.month:02d}") if can_prev else _cb(prefix, "noop"),
        )
    )
    nav_row.append(InlineKeyboardButton(text="Выбрать", callback_data=_cb(prefix, "noop")))
    nav_row.append(
        InlineKeyboardButton(
            text="➡️" if can_next else " ",
            callback_data=_cb(prefix, f"month={next_m.year}-{next_m.month:02d}") if can_next else _cb(prefix, "noop"),
        )
    )
    rows.append(nav_row)

    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

