from __future__ import annotations

from datetime import date, datetime, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Config
from app.constants import SCHEDULE_DAYS_AHEAD, PHONE_HINT
from app.database import Database
from app.keyboards.booking import cancel_my_kb, confirm_kb, times_kb
from app.keyboards.calendar import CalendarMonth, calendar_kb
from app.keyboards.common import back_to_menu, subscription_required_kb
from app.scheduler import cancel_reminder, schedule_reminder_if_needed
from app.states.booking import BookingFSM
from app.utils.formatters import esc, fmt_date_ru
from app.utils.phone import normalize_phone

router = Router()


def _date_range() -> tuple[date, date]:
    today = date.today()
    return today, today + timedelta(days=SCHEDULE_DAYS_AHEAD)


async def _enabled_days_for_calendar(db: Database, start: date, end: date) -> set[str]:
    enabled: set[str] = set()
    d = start
    while d <= end:
        iso = d.isoformat()
        if await db.day_has_any_free_slots(iso):
            enabled.add(iso)
        d += timedelta(days=1)
    return enabled


async def _show_subscription_gate(call: CallbackQuery, config: Config) -> None:
    await call.message.edit_text(
        text="Для записи необходимо подписаться на канал",
        reply_markup=subscription_required_kb(config.channel_link),
    )
    await call.answer()


@router.callback_query(lambda c: c.data == "sub:check")
async def sub_check(
    call: CallbackQuery,
    config: Config,
    is_subscribed: bool,
    sub_status: str | None,
    sub_error: str | None,
) -> None:
    if not is_subscribed:
        if sub_error:
            await call.answer(
                "Не удалось проверить подписку.\n\n"
                "Чаще всего причина: бот не добавлен в канал как администратор "
                "или указан неверный CHANNEL_ID.",
                show_alert=True,
            )
        else:
            await call.answer(
                f"Подписка не найдена (статус: {sub_status}).",
                show_alert=True,
            )
        return
    await call.answer("Подписка подтверждена ✅")
    # Return to booking entry
    await call.message.edit_text(
        text="Подписка подтверждена ✅\n\nТеперь вы можете записаться.",
        reply_markup=back_to_menu(),
    )


@router.callback_query(lambda c: c.data == "menu:book")
async def menu_book(call: CallbackQuery, config: Config, db: Database, state: FSMContext, is_subscribed: bool) -> None:
    if not is_subscribed:
        await _show_subscription_gate(call, config)
        return

    b = await db.get_active_booking_by_user(call.from_user.id)
    if b:
        await call.message.edit_text(
            text=(
                "<b>У вас уже есть активная запись</b>\n\n"
                f"Дата: <b>{fmt_date_ru(b.date)}</b>\n"
                f"Время: <b>{b.time}</b>\n"
            ),
            reply_markup=cancel_my_kb(),
        )
        await call.answer()
        return

    await state.clear()
    await state.set_state(BookingFSM.picking_date)
    await _render_booking_calendar(call, db=db, month=None)


@router.callback_query(lambda c: c.data == "book:pick_date")
async def pick_date_again(call: CallbackQuery, config: Config, db: Database, state: FSMContext, is_subscribed: bool) -> None:
    if not is_subscribed:
        await _show_subscription_gate(call, config)
        return
    await state.set_state(BookingFSM.picking_date)
    await _render_booking_calendar(call, db=db, month=None)


async def _render_booking_calendar(call: CallbackQuery, *, db: Database, month: CalendarMonth | None) -> None:
    start, end = _date_range()
    enabled = await _enabled_days_for_calendar(db, start, end)
    if not enabled:
        await call.message.edit_text(
            text="<b>Свободных слотов на ближайший месяц нет.</b>\n\nПопробуйте позже.",
            reply_markup=back_to_menu(),
        )
        await call.answer()
        return

    m = month or CalendarMonth(start.year, start.month)
    kb = calendar_kb(prefix="bookcal", month=m, enabled_days=enabled, min_day=start, max_day=end)
    await call.message.edit_text(
        text="<b>Выберите дату</b>",
        reply_markup=kb,
    )
    await call.answer()


@router.callback_query(F.data.startswith("bookcal:"))
async def book_calendar_callbacks(call: CallbackQuery, db: Database, state: FSMContext) -> None:
    data = call.data.split(":", 1)[1]
    if data == "noop":
        await call.answer()
        return
    if data.startswith("month="):
        ym = data.split("=", 1)[1]
        y, m = ym.split("-", 1)
        await _render_booking_calendar(call, db=db, month=CalendarMonth(int(y), int(m)))
        return
    if data.startswith("day="):
        iso = data.split("=", 1)[1]
        await state.update_data(day=iso)
        await state.set_state(BookingFSM.picking_time)
        times = await db.list_free_slots_for_day(iso)
        if not times:
            await call.answer("На эту дату нет свободного времени.", show_alert=True)
            await state.set_state(BookingFSM.picking_date)
            await _render_booking_calendar(call, db=db, month=None)
            return
        await call.message.edit_text(
            text=f"<b>Дата:</b> {fmt_date_ru(iso)}\n\n<b>Выберите время</b>",
            reply_markup=times_kb(iso, times),
        )
        await call.answer()


@router.callback_query(F.data.startswith("book:time:"))
async def pick_time(call: CallbackQuery, state: FSMContext) -> None:
    _, _, day, time_hm = call.data.split(":", 3)
    await state.update_data(day=day, time=time_hm)
    await state.set_state(BookingFSM.entering_name)
    await call.message.edit_text(
        text=(
            f"<b>Вы выбрали:</b> {fmt_date_ru(day)} в <b>{time_hm}</b>\n\n"
            "Введите ваше <b>имя</b>."
        ),
        reply_markup=back_to_menu(),
    )
    await call.answer()


@router.message(BookingFSM.entering_name)
async def enter_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Имя слишком короткое. Введите имя ещё раз.")
        return
    await state.update_data(name=name)
    await state.set_state(BookingFSM.entering_phone)
    await message.answer(
        text=f"Введите номер телефона.\n\n<i>{PHONE_HINT}</i>",
        reply_markup=back_to_menu(),
    )


@router.message(BookingFSM.entering_phone)
async def enter_phone(message: Message, state: FSMContext) -> None:
    phone = normalize_phone(message.text or "")
    if not phone:
        await message.answer(f"Неверный формат номера.\n\n<i>{PHONE_HINT}</i>")
        return
    await state.update_data(phone=phone)
    data = await state.get_data()
    day = data["day"]
    time_hm = data["time"]
    name = data["name"]
    await state.set_state(BookingFSM.confirming)
    await message.answer(
        text=(
            "<b>Проверьте данные:</b>\n\n"
            f"Дата: <b>{fmt_date_ru(day)}</b>\n"
            f"Время: <b>{time_hm}</b>\n"
            f"Имя: <b>{esc(name)}</b>\n"
            f"Телефон: <b>{esc(phone)}</b>\n"
        ),
        reply_markup=confirm_kb(),
    )


@router.callback_query(lambda c: c.data == "book:confirm")
async def confirm_booking(
    call: CallbackQuery,
    config: Config,
    db: Database,
    state: FSMContext,
    scheduler,
) -> None:
    data = await state.get_data()
    day = data.get("day")
    time_hm = data.get("time")
    name = data.get("name")
    phone = data.get("phone")
    if not (day and time_hm and name and phone):
        await call.answer("Сессия устарела. Начните заново.", show_alert=True)
        await state.clear()
        return

    try:
        booking_id = await db.create_booking(
            user_id=call.from_user.id,
            username=call.from_user.username,
            day=day,
            time_hm=time_hm,
            name=name,
            phone=phone,
        )
    except ValueError as e:
        await call.answer(str(e), show_alert=True)
        await state.clear()
        await call.message.edit_text("Не удалось создать запись. Попробуйте выбрать другое время.", reply_markup=back_to_menu())
        return
    except Exception:
        await call.answer("Ошибка при сохранении записи.", show_alert=True)
        return

    # schedule reminder
    await schedule_reminder_if_needed(
        scheduler=scheduler,
        db=db,
        bot=call.bot,
        booking_id=booking_id,
        user_id=call.from_user.id,
        day_iso=day,
        time_hm=time_hm,
    )

    await state.clear()

    await call.message.edit_text(
        text=(
            "<b>Запись подтверждена ✅</b>\n\n"
            f"Дата: <b>{fmt_date_ru(day)}</b>\n"
            f"Время: <b>{time_hm}</b>\n\n"
            "Если планы изменятся — вы можете отменить запись в меню."
        ),
        reply_markup=back_to_menu(),
    )
    await call.answer()

    # notify admin
    await call.bot.send_message(
        chat_id=config.admin_id,
        text=(
            "<b>Новая запись</b>\n\n"
            f"Дата: <b>{fmt_date_ru(day)}</b>\n"
            f"Время: <b>{time_hm}</b>\n"
            f"Имя: <b>{esc(name)}</b>\n"
            f"Телефон: <b>{esc(phone)}</b>\n"
            f"User ID: <code>{call.from_user.id}</code>\n"
            + (f"Username: @{esc(call.from_user.username)}\n" if call.from_user.username else "")
        ),
    )

    # post to schedule channel
    await call.bot.send_message(
        chat_id=config.schedule_channel_id,
        text=(
            "<b>Новая запись</b>\n"
            f"{fmt_date_ru(day)} • <b>{time_hm}</b>\n"
            f"{esc(name)} • {esc(phone)}"
        ),
    )


@router.callback_query(lambda c: c.data == "menu:my")
async def my_booking(call: CallbackQuery, db: Database) -> None:
    b = await db.get_active_booking_by_user(call.from_user.id)
    if not b:
        await call.message.edit_text(
            text="У вас нет активной записи.",
            reply_markup=back_to_menu(),
        )
        await call.answer()
        return
    await call.message.edit_text(
        text=(
            "<b>Ваша запись</b>\n\n"
            f"Дата: <b>{fmt_date_ru(b.date)}</b>\n"
            f"Время: <b>{b.time}</b>\n"
            f"Имя: <b>{esc(b.name)}</b>\n"
            f"Телефон: <b>{esc(b.phone)}</b>\n"
        ),
        reply_markup=cancel_my_kb(),
    )
    await call.answer()


@router.callback_query(lambda c: c.data == "menu:cancel_my")
async def cancel_my_menu(call: CallbackQuery, db: Database) -> None:
    b = await db.get_active_booking_by_user(call.from_user.id)
    if not b:
        await call.message.edit_text("У вас нет активной записи.", reply_markup=back_to_menu())
        await call.answer()
        return
    await call.message.edit_text(
        text=(
            "<b>Отменить запись?</b>\n\n"
            f"Дата: <b>{fmt_date_ru(b.date)}</b>\n"
            f"Время: <b>{b.time}</b>\n"
        ),
        reply_markup=cancel_my_kb(),
    )
    await call.answer()


@router.callback_query(lambda c: c.data == "book:cancel_my:yes")
async def cancel_my_yes(call: CallbackQuery, config: Config, db: Database, scheduler) -> None:
    b = await db.get_active_booking_by_user(call.from_user.id)
    if not b:
        await call.answer("Активной записи нет.", show_alert=True)
        return
    await db.cancel_booking(b.id)
    await cancel_reminder(scheduler=scheduler, db=db, booking_id=b.id)

    await call.message.edit_text(
        text="<b>Запись отменена ✅</b>\n\nСлот снова доступен для записи.",
        reply_markup=back_to_menu(),
    )
    await call.answer()

    # notify admin and schedule channel
    await call.bot.send_message(
        chat_id=config.admin_id,
        text=(
            "<b>Отмена записи</b>\n\n"
            f"Дата: <b>{fmt_date_ru(b.date)}</b>\n"
            f"Время: <b>{b.time}</b>\n"
            f"User ID: <code>{call.from_user.id}</code>"
        ),
    )
    await call.bot.send_message(
        chat_id=config.schedule_channel_id,
        text=(
            "<b>Отмена записи</b>\n"
            f"{fmt_date_ru(b.date)} • <b>{b.time}</b>"
        ),
    )

