from __future__ import annotations

from datetime import datetime


def fmt_date_ru(iso_day: str) -> str:
    # iso_day: YYYY-MM-DD
    dt = datetime.strptime(iso_day, "%Y-%m-%d")
    return dt.strftime("%d.%m.%Y")


def fmt_datetime_ru(iso_day: str, time_hm: str) -> str:
    dt = datetime.strptime(f"{iso_day} {time_hm}", "%Y-%m-%d %H:%M")
    return dt.strftime("%d.%m.%Y %H:%M")


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

