from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Iterable, Optional

import aiosqlite

from .schema import SCHEMA_SQL


def _iso_now() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class Booking:
    id: int
    user_id: int
    username: str | None
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    name: str
    phone: str
    status: str
    created_at: str


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA_SQL)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if not self._conn:
            raise RuntimeError("DB is not connected")
        return self._conn

    async def execute(self, sql: str, params: Iterable[Any] = ()) -> None:
        await self.conn.execute(sql, tuple(params))
        await self.conn.commit()

    async def fetchone(self, sql: str, params: Iterable[Any] = ()) -> Optional[aiosqlite.Row]:
        cur = await self.conn.execute(sql, tuple(params))
        row = await cur.fetchone()
        await cur.close()
        return row

    async def fetchall(self, sql: str, params: Iterable[Any] = ()) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(sql, tuple(params))
        rows = await cur.fetchall()
        await cur.close()
        return list(rows)

    # ---- Working days / slots ----
    async def upsert_working_day(self, day: str, is_open: bool = True) -> None:
        await self.execute(
            """
            INSERT INTO working_days(date, is_open)
            VALUES(?, ?)
            ON CONFLICT(date) DO UPDATE SET is_open=excluded.is_open
            """,
            (day, 1 if is_open else 0),
        )

    async def set_day_closed(self, day: str, closed: bool) -> None:
        await self.upsert_working_day(day, is_open=not closed)

    async def is_day_open(self, day: str) -> bool:
        row = await self.fetchone("SELECT is_open FROM working_days WHERE date=?", (day,))
        return bool(row and row["is_open"] == 1)

    async def list_open_working_days(self, start_day: str, end_day: str) -> list[str]:
        rows = await self.fetchall(
            """
            SELECT date FROM working_days
            WHERE date BETWEEN ? AND ? AND is_open=1
            ORDER BY date
            """,
            (start_day, end_day),
        )
        return [r["date"] for r in rows]

    async def add_time_slot(self, day: str, time_hm: str) -> None:
        await self.upsert_working_day(day, is_open=True)
        await self.execute(
            """
            INSERT OR IGNORE INTO time_slots(date, time, is_enabled)
            VALUES(?, ?, 1)
            """,
            (day, time_hm),
        )

    async def delete_time_slot(self, day: str, time_hm: str) -> None:
        await self.execute("DELETE FROM time_slots WHERE date=? AND time=?", (day, time_hm))

    async def list_slots_for_day(self, day: str, only_enabled: bool = True) -> list[str]:
        rows = await self.fetchall(
            """
            SELECT time FROM time_slots
            WHERE date=? AND (?=0 OR is_enabled=1)
            ORDER BY time
            """,
            (day, 0 if only_enabled else 1),
        )
        return [r["time"] for r in rows]

    async def list_free_slots_for_day(self, day: str) -> list[str]:
        rows = await self.fetchall(
            """
            SELECT s.time
            FROM time_slots s
            JOIN working_days d ON d.date=s.date
            LEFT JOIN bookings b ON b.date=s.date AND b.time=s.time AND b.status='active'
            WHERE s.date=? AND s.is_enabled=1 AND d.is_open=1 AND b.id IS NULL
            ORDER BY s.time
            """,
            (day,),
        )
        return [r["time"] for r in rows]

    async def day_has_any_free_slots(self, day: str) -> bool:
        row = await self.fetchone(
            """
            SELECT 1
            FROM time_slots s
            JOIN working_days d ON d.date=s.date
            LEFT JOIN bookings b ON b.date=s.date AND b.time=s.time AND b.status='active'
            WHERE s.date=? AND s.is_enabled=1 AND d.is_open=1 AND b.id IS NULL
            LIMIT 1
            """,
            (day,),
        )
        return row is not None

    # ---- Bookings ----
    async def get_active_booking_by_user(self, user_id: int) -> Booking | None:
        row = await self.fetchone(
            """
            SELECT * FROM bookings
            WHERE user_id=? AND status='active'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id,),
        )
        if not row:
            return None
        return Booking(
            id=row["id"],
            user_id=row["user_id"],
            username=row["username"],
            date=row["date"],
            time=row["time"],
            name=row["name"],
            phone=row["phone"],
            status=row["status"],
            created_at=row["created_at"],
        )

    async def create_booking(
        self,
        *,
        user_id: int,
        username: str | None,
        day: str,
        time_hm: str,
        name: str,
        phone: str,
    ) -> int:
        # one active booking per user
        existing = await self.get_active_booking_by_user(user_id)
        if existing:
            raise ValueError("User already has an active booking")

        # ensure slot exists and day open and free
        if not await self.is_day_open(day):
            raise ValueError("Day is closed")

        slot_row = await self.fetchone(
            "SELECT 1 FROM time_slots WHERE date=? AND time=? AND is_enabled=1",
            (day, time_hm),
        )
        if not slot_row:
            raise ValueError("Slot does not exist")

        busy = await self.fetchone(
            "SELECT 1 FROM bookings WHERE date=? AND time=? AND status='active' LIMIT 1",
            (day, time_hm),
        )
        if busy:
            raise ValueError("Slot already booked")

        cur = await self.conn.execute(
            """
            INSERT INTO bookings(user_id, username, date, time, name, phone, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, username, day, time_hm, name, phone, _iso_now()),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def cancel_booking(self, booking_id: int) -> None:
        await self.execute(
            """
            UPDATE bookings
            SET status='cancelled', cancelled_at=?
            WHERE id=? AND status='active'
            """,
            (_iso_now(), booking_id),
        )

    async def cancel_booking_by_user(self, user_id: int) -> int | None:
        b = await self.get_active_booking_by_user(user_id)
        if not b:
            return None
        await self.cancel_booking(b.id)
        return b.id

    async def list_bookings_for_day(self, day: str) -> list[Booking]:
        rows = await self.fetchall(
            """
            SELECT * FROM bookings
            WHERE date=? AND status='active'
            ORDER BY time
            """,
            (day,),
        )
        return [
            Booking(
                id=r["id"],
                user_id=r["user_id"],
                username=r["username"],
                date=r["date"],
                time=r["time"],
                name=r["name"],
                phone=r["phone"],
                status=r["status"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    async def get_booking(self, booking_id: int) -> Booking | None:
        row = await self.fetchone("SELECT * FROM bookings WHERE id=?", (booking_id,))
        if not row:
            return None
        return Booking(
            id=row["id"],
            user_id=row["user_id"],
            username=row["username"],
            date=row["date"],
            time=row["time"],
            name=row["name"],
            phone=row["phone"],
            status=row["status"],
            created_at=row["created_at"],
        )

    # ---- Reminders persistence ----
    async def save_reminder(self, booking_id: int, job_id: str, run_at_iso: str) -> None:
        await self.execute(
            """
            INSERT INTO reminders(booking_id, job_id, run_at)
            VALUES(?, ?, ?)
            ON CONFLICT(booking_id) DO UPDATE SET job_id=excluded.job_id, run_at=excluded.run_at
            """,
            (booking_id, job_id, run_at_iso),
        )

    async def delete_reminder(self, booking_id: int) -> None:
        await self.execute("DELETE FROM reminders WHERE booking_id=?", (booking_id,))

    async def list_reminders(self) -> list[aiosqlite.Row]:
        return await self.fetchall(
            """
            SELECT r.booking_id, r.job_id, r.run_at, b.user_id, b.date, b.time, b.status
            FROM reminders r
            JOIN bookings b ON b.id=r.booking_id
            WHERE b.status='active'
            """,
            (),
        )

