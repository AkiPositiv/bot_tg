#!/usr/bin/env python3
"""
Telegram RPG Bot - Main Entry Point v3.0
Enhanced with Interactive Battles and Kingdom Wars
"""
import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import settings
from config.database import init_db
from handlers import setup_handlers
from middlewares.auth import AuthMiddleware
from middlewares.throttling import ThrottlingMiddleware
from middlewares.war_block import WarBlockMiddleware
from services.user_service import UserService
from utils.logging_config import setup_logging
from war_scheduler import enhanced_war_scheduler

async def main():
    """Main bot function"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")
        
        # Initialize bot and dispatcher
        bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        dp = Dispatcher(storage=MemoryStorage())
        
        # Initialize services
        user_service = UserService()
        
        # Setup middlewares
        dp.message.middleware(AuthMiddleware(user_service))
        dp.callback_query.middleware(AuthMiddleware(user_service))
        dp.message.middleware(ThrottlingMiddleware(settings.RATE_LIMIT))
        dp.callback_query.middleware(ThrottlingMiddleware(settings.RATE_LIMIT))
        dp.message.middleware(WarBlockMiddleware())
        dp.callback_query.middleware(WarBlockMiddleware())
        
        # Setup handlers
        setup_handlers(dp)
        
        # Start enhanced war scheduler
        enhanced_war_scheduler.set_bot(bot)
        enhanced_war_scheduler.start()
        logger.info("Enhanced Kingdom War Scheduler started")
        
        logger.info("Starting RPG Bot v3.0...")
        await dp.start_polling(bot, skip_updates=True)
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        sys.exit(1)
    finally:
        # Stop enhanced war scheduler on shutdown
        enhanced_war_scheduler.stop()

if __name__ == "__main__":
    asyncio.run(main())