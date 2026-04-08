from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import load_config
from app.database import Database
from app.middlewares.subscription import SubscriptionMiddleware
from app.scheduler import restore_reminders


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    config = load_config()
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    db = Database(config.db_path)
    await db.connect()

    scheduler = AsyncIOScheduler()
    scheduler.start()
    await restore_reminders(scheduler=scheduler, db=db, bot=bot)

    # Shared dependencies via dispatcher workflow data
    dp["config"] = config
    dp["db"] = db
    dp["scheduler"] = scheduler

    dp.message.middleware(SubscriptionMiddleware(config))
    dp.callback_query.middleware(SubscriptionMiddleware(config))

    from app.handlers.start import router as start_router
    from app.handlers.prices_portfolio import router as pp_router
    from app.handlers.booking import router as booking_router
    from app.handlers.admin import router as admin_router

    dp.include_router(start_router)
    dp.include_router(pp_router)
    dp.include_router(booking_router)
    dp.include_router(admin_router)

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

