from __future__ import annotations

import re


_PHONE_RE = re.compile(r"^\+?\d{10,15}$")


def normalize_phone(raw: str) -> str | None:
    s = raw.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if s.startswith("8") and len(s) == 11:
        # common RU format: 8XXXXXXXXXX -> +7XXXXXXXXXX
        s = "+7" + s[1:]
    if s.startswith("7") and len(s) == 11:
        s = "+7" + s[1:]
    if not s.startswith("+") and s.isdigit():
        s = "+" + s
    return s if _PHONE_RE.match(s) else None

