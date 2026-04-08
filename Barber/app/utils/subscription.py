from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubscriptionCheck:
    ok: bool
    status: str | None = None
    error: str | None = None


async def check_subscription(bot, channel_id: int, user_id: int) -> SubscriptionCheck:
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        status = getattr(member, "status", None)
        ok = status in ("member", "administrator", "creator")
        return SubscriptionCheck(ok=ok, status=status)
    except Exception as e:
        return SubscriptionCheck(ok=False, error=type(e).__name__)

