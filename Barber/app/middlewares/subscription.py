from __future__ import annotations

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message

from app.config import Config
from app.utils.subscription import check_subscription


class SubscriptionMiddleware(BaseMiddleware):
    """
    Adds a lightweight subscription gate for booking flows.
    This middleware itself doesn't block; it only adds a helper flag to data.
    Handlers that open booking UI must enforce it.
    """

    def __init__(self, config: Config):
        self.config = config

    async def __call__(self, handler, event, data):
        bot: Bot = data["bot"]
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        if isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        is_subscribed = False
        sub_status = None
        sub_error = None
        if user_id is not None:
            res = await check_subscription(bot, self.config.channel_id, user_id)
            is_subscribed = res.ok
            sub_status = res.status
            sub_error = res.error

        data["is_subscribed"] = is_subscribed
        data["sub_status"] = sub_status
        data["sub_error"] = sub_error
        return await handler(event, data)

