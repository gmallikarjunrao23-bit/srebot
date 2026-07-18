"""
SRE Bot - Main Entry Point
Telegram-first AI-powered monitoring platform
"""
import asyncio
import logging
import sys
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.strategy import FSMStrategy

from config import settings
from infrastructure import init_db, redis_client
from telegram.handlers import router


async def main():
    """Initialize and run the bot"""
    # Logging
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout
    )
    logger = logging.getLogger(__name__)
    
    # Initialize Redis
    await redis_client.connect()
    storage = RedisStorage.from_url(settings.REDIS_URL)
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize bot
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, parse_mode=ParseMode.MARKDOWN_V2)
    dp = Dispatcher(storage=storage, fsm_strategy=FSMStrategy.USER_IN_CHAT)
    
    # Include routers
    dp.include_router(router)
    
    # Startup/shutdown
    async def on_startup():
        logger.info("SRE Bot starting...")
        if settings.TELEGRAM_WEBHOOK_URL:
            await bot.set_webhook(
                url=settings.TELEGRAM_WEBHOOK_URL,
                secret_token=settings.TELEGRAM_WEBHOOK_SECRET
            )
            logger.info(f"Webhook set to {settings.TELEGRAM_WEBHOOK_URL}")
    
    async def on_shutdown():
        logger.info("SRE Bot shutting down...")
        await redis_client.disconnect()
        await bot.session.close()
    
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Start polling or webhook
    try:
        if settings.TELEGRAM_WEBHOOK_URL:
            from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
            from aiohttp import web
            
            app = web.Application()
            webhook_handler = SimpleRequestHandler(
                dispatcher=dp,
                bot=bot,
                secret_token=settings.TELEGRAM_WEBHOOK_SECRET
            )
            webhook_handler.register(app, path="/webhook")
            setup_application(app, dp, bot=bot)
            
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080)))
            await site.start()
            await asyncio.Event().wait()
        else:
            await dp.start_polling(bot)
    finally:
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())

