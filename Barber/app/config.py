from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_id: int

    # Channel subscription requirement
    channel_id: int
    channel_link: str

    # Where to post schedule updates
    schedule_channel_id: int

    shop_name: str
    timezone: str
    db_path: str


def _must_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"ENV {name} is required")
    return v


def load_config() -> Config:
    """
    Loads configuration from `.env` + environment variables.
    """
    load_dotenv()

    channel_id = int(_must_env("CHANNEL_ID"))
    schedule_channel_id = int(os.getenv("SCHEDULE_CHANNEL_ID", str(channel_id)))

    return Config(
        bot_token=_must_env("BOT_TOKEN"),
        admin_id=int(_must_env("ADMIN_ID")),
        channel_id=channel_id,
        channel_link=_must_env("CHANNEL_LINK"),
        schedule_channel_id=schedule_channel_id,
        shop_name=os.getenv("SHOP_NAME", "Barber Shop"),
        timezone=os.getenv("TIMEZONE", "Europe/Moscow"),
        db_path=os.getenv("DB_PATH", "data/barber.db"),
    )

