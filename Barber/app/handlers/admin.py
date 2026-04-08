from __future__ import annotations

import re
from datetime import date, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Config
from app.constants import SCHEDULE_DAYS_AHEAD
from app.database import Database
from app.keyboards.admin import (
    admin_bookings_list_kb,
    admin_cancel_confirm_kb,
    admin_day_actions_kb,
    admin_menu_kb,
    admin_slots_kb,
)
from app.keyboards.calendar import CalendarMonth, calendar_kb
from app.scheduler import cancel_reminder
from app.states.admin import AdminFSM
from app.utils.formatters import esc, fmt_date_ru

router = Router()

_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def _date_range() -> tuple[date, date]:
    today = date.today()
    return today, today + timedelta(days=SCHEDULE_DAYS_AHEAD)


def _ensure_admin(config: Config, user_id: int) -> bool:
    return user_id == config.admin_id


@router.callback_query(lambda c: c.data == "menu:admin")
async def open_admin_panel(call: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not _ensure_admin(config, call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await state.set_state(AdminFSM.choosing_action)
    await call.message.edit_text("<b>Админ-панель</b>\n\nВыберите действие.", reply_markup=admin_menu_kb())
    await call.answer()


@router.callback_query(lambda c: c.data == "admin:home")
async def admin_home(call: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not _ensure_admin(config, call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await state.set_state(AdminFSM.choosing_action)
    await call.message.edit_text("<b>Админ-панель</b>\n\nВыберите действие.", reply_markup=admin_menu_kb())
    await call.answer()


@router.callback_query(F.data.startswith("admin:action:"))
async def admin_choose_action(call: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not _ensure_admin(config, call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    action = call.data.split(":", 2)[2]
    await state.update_data(action=action)
    await state.set_state(AdminFSM.picking_date)
    await _render_admin_calendar(call)


@router.callback_query(lambda c: c.data == "admin:pick_date")
async def admin_pick_date(call: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not _ensure_admin(config, call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminFSM.picking_date)
    await _render_admin_calendar(call)


async def _render_admin_calendar(call: CallbackQuery, month: CalendarMonth | None = None) -> None:
    start, end = _date_range()
    # Admin can pick any day in range; enable all days in month window
    enabled = set()
    d = start
    while d <= end:
        enabled.add(d.isoformat())
        d += timedelta(days=1)
    m = month or CalendarMonth(start.year, start.month)
    kb = calendar_kb(prefix="admcal", month=m, enabled_days=enabled, min_day=start, max_day=end)
    await call.message.edit_text("<b>Выберите дату</b>", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("admcal:"))
async def admin_calendar_callbacks(call: CallbackQuery, config: Config, db: Database, state: FSMContext) -> None:
    if not _ensure_admin(config, call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    payload = call.data.split(":", 1)[1]
    if payload == "noop":
        await call.answer()
        return
    if payload.startswith("month="):
        ym = payload.split("=", 1)[1]
        y, m = ym.split("-", 1)
        await _render_admin_calendar(call, month=CalendarMonth(int(y), int(m)))
        return
    if not payload.startswith("day="):
        await call.answer()
        return

    day_iso = payload.split("=", 1)[1]
    await state.update_data(day=day_iso)
    data = await state.get_data()
    action = data.get("action")

    if action == "add_day":
        await db.upsert_working_day(day_iso, is_open=True)
        await call.message.edit_text(
            text=f"✅ Рабочий день добавлен: <b>{fmt_date_ru(day_iso)}</b>",
            reply_markup=admin_menu_kb(),
        )
        await state.clear()
        await call.answer()
        return

    if action in ("close_day", "open_day"):
        closed = action == "close_day"
        await db.set_day_closed(day_iso, closed=closed)
        await call.message.edit_text(
            text=(
                ("🔒 День закрыт: " if closed else "🔓 День открыт: ")
                + f"<b>{fmt_date_ru(day_iso)}</b>"
            ),
            reply_markup=admin_menu_kb(),
        )
        await state.clear()
        await call.answer()
        return

    if action == "slots":
        slots = await db.list_slots_for_day(day_iso, only_enabled=False)
        await call.message.edit_text(
            text=f"<b>Слоты на {fmt_date_ru(day_iso)}</b>\n\nУдаляйте или добавляйте слоты.",
            reply_markup=admin_slots_kb(day_iso, slots),
        )
        await call.answer()
        return

    if action == "view":
        is_open = await db.is_day_open(day_iso)
        slots = await db.list_slots_for_day(day_iso, only_enabled=True)
        free = await db.list_free_slots_for_day(day_iso) if is_open else []
        bookings = await db.list_bookings_for_day(day_iso)

        lines = [f"<b>Расписание на {fmt_date_ru(day_iso)}</b>"]
        lines.append(f"Статус дня: <b>{'Открыт' if is_open else 'Закрыт'}</b>")
        lines.append("")
        if bookings:
            lines.append("<b>Записи:</b>")
            for b in bookings:
                lines.append(f"• <b>{b.time}</b> — {esc(b.name)} ({esc(b.phone)})")
        else:
            lines.append("<b>Записей нет</b>")

        lines.append("")
        lines.append(f"Всего слотов: <b>{len(slots)}</b>")
        lines.append(f"Свободных: <b>{len(free)}</b>")
        if free:
            lines.append("Свободное время: " + ", ".join(f"<b>{t}</b>" for t in free))

        await call.message.edit_text("\n".join(lines), reply_markup=admin_day_actions_kb(day_iso))
        await state.clear()
        await call.answer()
        return

    if action == "cancel_booking":
        bookings = await db.list_bookings_for_day(day_iso)
        if not bookings:
            await call.message.edit_text(
                text=f"На <b>{fmt_date_ru(day_iso)}</b> нет активных записей.",
                reply_markup=admin_menu_kb(),
            )
            await state.clear()
            await call.answer()
            return
        items = [(b.id, b.time, b.name) for b in bookings]
        await call.message.edit_text(
            text=f"<b>Выберите запись для отмены</b>\nДата: {fmt_date_ru(day_iso)}",
            reply_markup=admin_bookings_list_kb(day_iso, items),
        )
        await call.answer()
        return

    await call.message.edit_text("Неизвестное действие.", reply_markup=admin_menu_kb())
    await state.clear()
    await call.answer()


@router.callback_query(F.data.startswith("admin:slots:add:"))
async def admin_slots_add(call: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not _ensure_admin(config, call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    day_iso = call.data.split(":", 3)[3]
    await state.update_data(day=day_iso)
    await state.set_state(AdminFSM.entering_time)
    await call.message.edit_text(
        text=(
            f"<b>Добавить слот</b>\nДата: {fmt_date_ru(day_iso)}\n\n"
            "Отправьте время в формате <b>HH:MM</b> (например, <code>10:30</code>)."
        ),
        reply_markup=None,
    )
    await call.answer()


@router.message(AdminFSM.entering_time)
async def admin_enter_time(message: Message, config: Config, db: Database, state: FSMContext) -> None:
    if not _ensure_admin(config, message.from_user.id):
        return
    t = (message.text or "").strip()
    if not _TIME_RE.match(t):
        await message.answer("Неверный формат. Нужно <b>HH:MM</b>, например <code>10:30</code>.")
        return
    data = await state.get_data()
    day_iso = data.get("day")
    if not day_iso:
        await state.clear()
        await message.answer("Сессия устарела. Откройте админ-панель заново.")
        return
    await db.add_time_slot(day_iso, t)
    slots = await db.list_slots_for_day(day_iso, only_enabled=False)
    await state.clear()
    await message.answer(
        text=f"✅ Слот добавлен: <b>{fmt_date_ru(day_iso)}</b> <b>{t}</b>",
    )
    await message.answer(
        text=f"<b>Слоты на {fmt_date_ru(day_iso)}</b>",
        reply_markup=admin_slots_kb(day_iso, slots),
    )


@router.callback_query(F.data.startswith("admin:slots:del:"))
async def admin_slots_del(call: CallbackQuery, config: Config, db: Database) -> None:
    if not _ensure_admin(config, call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    _, _, _, day_iso, time_hm = call.data.split(":", 4)
    # Will fail silently if slot already gone; booking FK prevents deletion if booked
    try:
        await db.delete_time_slot(day_iso, time_hm)
        await call.answer("Удалено ✅")
    except Exception:
        await call.answer("Нельзя удалить (возможно, слот занят).", show_alert=True)
    slots = await db.list_slots_for_day(day_iso, only_enabled=False)
    await call.message.edit_text(
        text=f"<b>Слоты на {fmt_date_ru(day_iso)}</b>\n\nУдаляйте или добавляйте слоты.",
        reply_markup=admin_slots_kb(day_iso, slots),
    )


@router.callback_query(F.data.startswith("admin:close:"))
async def admin_close_day(call: CallbackQuery, config: Config, db: Database) -> None:
    if not _ensure_admin(config, call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    day_iso = call.data.split(":", 2)[2]
    await db.set_day_closed(day_iso, closed=True)
    await call.answer("День закрыт")
    await call.message.edit_text(
        text=f"🔒 День закрыт: <b>{fmt_date_ru(day_iso)}</b>",
        reply_markup=admin_menu_kb(),
    )


@router.callback_query(F.data.startswith("admin:open:"))
async def admin_open_day(call: CallbackQuery, config: Config, db: Database) -> None:
    if not _ensure_admin(config, call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    day_iso = call.data.split(":", 2)[2]
    await db.set_day_closed(day_iso, closed=False)
    await call.answer("День открыт")
    await call.message.edit_text(
        text=f"🔓 День открыт: <b>{fmt_date_ru(day_iso)}</b>",
        reply_markup=admin_menu_kb(),
    )


@router.callback_query(F.data.startswith("admin:cancel:"))
async def admin_cancel_pick(call: CallbackQuery, config: Config, db: Database, state: FSMContext) -> None:
    if not _ensure_admin(config, call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    booking_id = int(call.data.split(":", 2)[2])
    b = await db.get_booking(booking_id)
    if not b or b.status != "active":
        await call.answer("Запись не найдена.", show_alert=True)
        return
    await state.update_data(cancel_booking_id=booking_id)
    await state.set_state(AdminFSM.confirming_cancel)
    await call.message.edit_text(
        text=(
            "<b>Отменить запись клиента?</b>\n\n"
            f"Дата: <b>{fmt_date_ru(b.date)}</b>\n"
            f"Время: <b>{b.time}</b>\n"
            f"Имя: <b>{esc(b.name)}</b>\n"
            f"Телефон: <b>{esc(b.phone)}</b>\n"
            f"User ID: <code>{b.user_id}</code>\n"
        ),
        reply_markup=admin_cancel_confirm_kb(booking_id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin:cancel_confirm:"))
async def admin_cancel_confirm(call: CallbackQuery, config: Config, db: Database, state: FSMContext, scheduler) -> None:
    if not _ensure_admin(config, call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    booking_id = int(call.data.split(":", 2)[2])
    b = await db.get_booking(booking_id)
    if not b or b.status != "active":
        await call.answer("Запись не найдена.", show_alert=True)
        await state.clear()
        return
    await db.cancel_booking(booking_id)
    await cancel_reminder(scheduler=scheduler, db=db, booking_id=booking_id)
    await state.clear()

    # notify client
    try:
        await call.bot.send_message(
            chat_id=b.user_id,
            text=(
                "<b>Ваша запись отменена администратором</b>\n\n"
                f"Дата: <b>{fmt_date_ru(b.date)}</b>\n"
                f"Время: <b>{b.time}</b>\n"
            ),
        )
    except Exception:
        pass

    await call.message.edit_text(
        text=f"✅ Запись отменена: <b>{fmt_date_ru(b.date)}</b> <b>{b.time}</b>",
        reply_markup=admin_menu_kb(),
    )
    await call.answer()

