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
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.strategy import FSMStrategy
from aiohttp import web

from config import settings
from infrastructure import init_db, redis_client
from telegram.handlers import router


async def health_handler(request):
    """Health check endpoint for Railway"""
    return web.Response(
        text='{"status":"healthy","version":"1.0.0"}',
        content_type="application/json"
    )


async def main():
    """Initialize and run the bot"""
    # Logging - .strip() fix for spaces in LOG_LEVEL
    log_level = settings.LOG_LEVEL.strip() if settings.LOG_LEVEL else "INFO"
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout
    )
    logger = logging.getLogger(__name__)
    logger.info(f"Starting SRE Bot v1.0.0 | Log Level: {log_level}")

    # Initialize Redis (fallback to memory if Redis fails)
    storage = MemoryStorage()
    try:
        await redis_client.connect()
        storage = RedisStorage.from_url(settings.REDIS_URL)
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis unavailable, using memory storage: {e}")

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database init failed: {e}")
        raise

    # Initialize bot - HTML MODE (not MarkdownV2)
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=storage, fsm_strategy=FSMStrategy.USER_IN_CHAT)
    dp.include_router(router)

    # Start healthcheck web server (REQUIRED for Railway)
    app = web.Application()
    app.router.add_get("/health", health_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health server running on port {port}")

    # Startup
    async def on_startup():
        logger.info("SRE Bot starting...")
        # Auto-detect Railway domain for webhook
        railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
        if railway_domain and not settings.TELEGRAM_WEBHOOK_URL:
            webhook_url = f"https://{railway_domain}/webhook"
            try:
                await bot.set_webhook(url=webhook_url)
                logger.info(f"Auto webhook set: {webhook_url}")
            except Exception as e:
                logger.warning(f"Webhook setup failed: {e}")
        elif settings.TELEGRAM_WEBHOOK_URL:
            try:
                await bot.set_webhook(
                    url=settings.TELEGRAM_WEBHOOK_URL,
                    secret_token=settings.TELEGRAM_WEBHOOK_SECRET
                )
                logger.info(f"Webhook set: {settings.TELEGRAM_WEBHOOK_URL}")
            except Exception as e:
                logger.warning(f"Webhook setup failed: {e}")

    async def on_shutdown():
        logger.info("SRE Bot shutting down...")
        await bot.session.close()
        try:
            if storage != MemoryStorage():
                await storage.close()
        except:
            pass
        await runner.cleanup()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Start bot (polling mode - works perfectly with Railway now)
    try:
        logger.info("Starting bot in polling mode...")
        await dp.start_polling(bot)
    finally:
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
