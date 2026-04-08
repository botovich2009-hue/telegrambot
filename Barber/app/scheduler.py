from __future__ import annotations

from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.constants import REMINDER_DELTA
from app.database import Database


def reminder_job_id(booking_id: int) -> str:
    return f"reminder_{booking_id}"


async def send_reminder(bot, user_id: int, time_hm: str) -> None:
    await bot.send_message(
        chat_id=user_id,
        text=f"Напоминаем, что вы записаны на стрижку завтра в <b>{time_hm}</b>. Ждём вас.",
        parse_mode="HTML",
    )


async def schedule_reminder_if_needed(
    *,
    scheduler: AsyncIOScheduler,
    db: Database,
    bot,
    booking_id: int,
    user_id: int,
    day_iso: str,
    time_hm: str,
) -> None:
    visit_dt = datetime.strptime(f"{day_iso} {time_hm}", "%Y-%m-%d %H:%M")
    run_dt = visit_dt - REMINDER_DELTA
    now = datetime.now()
    if run_dt <= now:
        return

    job_id = reminder_job_id(booking_id)
    scheduler.add_job(
        send_reminder,
        "date",
        run_date=run_dt,
        id=job_id,
        replace_existing=True,
        args=[bot, user_id, time_hm],
        misfire_grace_time=3600,
    )
    await db.save_reminder(booking_id, job_id, run_dt.replace(microsecond=0).isoformat())


async def cancel_reminder(*, scheduler: AsyncIOScheduler, db: Database, booking_id: int) -> None:
    job_id = reminder_job_id(booking_id)
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass
    await db.delete_reminder(booking_id)


async def restore_reminders(*, scheduler: AsyncIOScheduler, db: Database, bot) -> None:
    rows = await db.list_reminders()
    now = datetime.now()
    for r in rows:
        run_dt = datetime.fromisoformat(r["run_at"])
        if run_dt <= now:
            # missed/too late: drop
            await db.delete_reminder(int(r["booking_id"]))
            continue
        booking_id = int(r["booking_id"])
        scheduler.add_job(
            send_reminder,
            "date",
            run_date=run_dt,
            id=reminder_job_id(booking_id),
            replace_existing=True,
            args=[bot, int(r["user_id"]), str(r["time"])],
            misfire_grace_time=3600,
        )

