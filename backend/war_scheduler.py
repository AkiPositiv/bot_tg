#!/usr/bin/env python3
"""
Enhanced Kingdom War Scheduler - запускает войны в указанное время с полным функционалом
"""
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from services.enhanced_kingdom_war_service import EnhancedKingdomWarService
import logging
import pytz

logger = logging.getLogger(__name__)

class EnhancedKingdomWarScheduler:
    def __init__(self, bot=None):
        self.scheduler = AsyncIOScheduler()
        self.war_service = EnhancedKingdomWarService()
        self.tashkent_tz = pytz.timezone('Asia/Tashkent')
        self.bot = bot  # For sending notifications
    
    def start(self):
        """Запуск планировщика войн"""
        # Планировщик уведомлений за 30 минут до войн
        for hour in [8, 13, 18]:
            # Pre-war notifications (30 minutes before)
            pre_war_hour = hour
            pre_war_minute = 30 if hour > 0 else 30
            if hour == 8:
                pre_war_hour = 7
            elif hour == 13:
                pre_war_hour = 12
            elif hour == 18:
                pre_war_hour = 17
                
            self.scheduler.add_job(
                self.send_pre_war_notifications,
                trigger=CronTrigger(hour=pre_war_hour, minute=30, timezone=self.tashkent_tz),
                id=f'pre_war_notification_{hour}',
                args=[hour]
            )
            
            # War start
            self.scheduler.add_job(
                self.process_scheduled_wars,
                trigger=CronTrigger(hour=hour, minute=0, timezone=self.tashkent_tz),
                id=f'enhanced_kingdom_war_{hour}',
                args=[hour]
            )
        
        # Планирование войн на завтра каждый день в полночь
        self.scheduler.add_job(
            self.schedule_tomorrow_wars,
            trigger=CronTrigger(hour=0, minute=0, timezone=self.tashkent_tz),
            id='schedule_enhanced_wars'
        )
        
        # Планирование войн на сегодня при запуске
        self.scheduler.add_job(
            self.schedule_today_wars,
            id='schedule_today_enhanced_wars'
        )
        
        # HP/MP restoration after wars (5 minutes after war end)
        for hour in [8, 13, 18]:
            restore_hour = hour
            restore_minute = 5
            if hour == 23:  # Edge case for midnight
                restore_hour = 0
                
            self.scheduler.add_job(
                self.restore_participants,
                trigger=CronTrigger(hour=restore_hour, minute=restore_minute, timezone=self.tashkent_tz),
                id=f'restore_participants_{hour}',
                args=[hour]
            )
        
        self.scheduler.start()
        logger.info("Enhanced Kingdom War Scheduler started")
    
    async def send_pre_war_notifications(self, war_hour: int):
        """Отправка уведомлений за 30 минут до войны"""
        try:
            if not self.bot:
                logger.warning("Bot not set for notifications")
                return
            
            # Get wars for this hour
            from datetime import datetime
            now = datetime.now(self.tashkent_tz)
            wars_today = await self.war_service.get_scheduled_wars(now)
            
            war_announcements = []
            for war in wars_today:
                war_time_tashkent = war.scheduled_time.astimezone(self.tashkent_tz)
                if war_time_tashkent.hour == war_hour:
                    war_announcements.append(war)
            
            if not war_announcements:
                return
            
            # Create notification message
            notification_text = (
                f"⚠️ **УВЕДОМЛЕНИЕ О ВОЙНЕ** ⚠️\n\n"
                f"🕐 До начала войны: **30 минут**\n"
                f"🏰 Время начала: **{war_hour}:00** (Ташкентское время)\n\n"
                f"**Участвующие королевства:**\n"
            )
            
            for war in war_announcements:
                from config.settings import GameConstants
                kingdom_info = GameConstants.KINGDOMS.get(war.defending_kingdom, {})
                emoji = kingdom_info.get('emoji', '🏰')
                name = kingdom_info.get('name', war.defending_kingdom)
                notification_text += f"🛡️ **{emoji} {name}** - ожидает нападения\n"
            
            notification_text += (
                f"\n💡 **Как участвовать:**\n"
                f"🗡️ Атакуйте вражеские королевства\n"
                f"🛡️ Защищайте своё королевство\n"
                f"💰 Получайте 40% золота побеждённых\n\n"
                f"⏰ **Подготовьтесь к битве!**"
            )
            
            # Send to war channel if configured
            if self.war_service.war_channel_id:
                try:
                    await self.bot.send_message(self.war_service.war_channel_id, notification_text)
                    logger.info(f"Pre-war notification sent for {war_hour}:00 war")
                except Exception as e:
                    logger.error(f"Error sending war notification to channel: {e}")
            else:
                logger.warning("War channel ID not configured")
                
        except Exception as e:
            logger.error(f"Error sending pre-war notifications for {war_hour}:00: {e}")
    
    async def process_scheduled_wars(self, hour: int):
        """Обработка запланированных войн с enhanced функционалом"""
        try:
            # Получить все запланированные войны на этот час
            now = datetime.now(self.tashkent_tz)
            wars = await self.war_service.get_scheduled_wars(now)
            
            wars_started = 0
            war_results = []
            
            for war in wars:
                # Проверить, что время войны соответствует текущему часу
                war_time_tashkent = war.scheduled_time.astimezone(self.tashkent_tz)
                if war_time_tashkent.hour == hour:
                    success = await self.war_service.start_enhanced_war(war.id)
                    if success:
                        wars_started += 1
                        war_results.append(war.id)
                        logger.info(f"Started enhanced war {war.id} for kingdom {war.defending_kingdom}")
            
            # Send war results to channel
            if war_results and self.bot:
                summary = await self.war_service.get_war_summary_for_channel(war_results)
                if summary and self.war_service.war_channel_id:
                    try:
                        await self.bot.send_message(self.war_service.war_channel_id, summary)
                    except Exception as e:
                        logger.error(f"Error sending war summary to channel: {e}")
            
            logger.info(f"Processed {wars_started} enhanced wars at {hour}:00 Tashkent time")
            
        except Exception as e:
            logger.error(f"Error processing enhanced wars at {hour}:00: {e}")
    
    async def schedule_today_wars(self):
        """Планирование войн на сегодня (при запуске бота)"""
        try:
            today = datetime.now(self.tashkent_tz)
            await self.war_service.schedule_daily_wars(today)
            logger.info("Scheduled enhanced wars for today")
        except Exception as e:
            logger.error(f"Error scheduling today's enhanced wars: {e}")
    
    async def schedule_tomorrow_wars(self):
        """Планирование войн на завтра"""
        try:
            tomorrow = datetime.now(self.tashkent_tz) + timedelta(days=1)
            await self.war_service.schedule_daily_wars(tomorrow)
            logger.info("Scheduled enhanced wars for tomorrow")
        except Exception as e:
            logger.error(f"Error scheduling tomorrow's enhanced wars: {e}")
    
    async def restore_participants(self, war_hour: int):
        """Восстановить HP/MP участников через 5 минут после войны"""
        try:
            from datetime import datetime, timedelta
            
            # Найти завершённые войны этого часа и восстановить участников
            end_time = datetime.now(self.tashkent_tz).replace(hour=war_hour, minute=5, second=0)
            
            # Get recently finished wars
            from config.database import AsyncSessionLocal
            from models.kingdom_war import KingdomWar, WarParticipation, WarStatusEnum
            from models.user import User
            from sqlalchemy import select, and_
            
            async with AsyncSessionLocal() as session:
                # Find wars that finished around this time
                search_time_start = end_time - timedelta(minutes=10)
                search_time_end = end_time + timedelta(minutes=10)
                
                finished_wars = await session.execute(
                    select(KingdomWar).where(
                        and_(
                            KingdomWar.status == WarStatusEnum.finished,
                            KingdomWar.finished_at >= search_time_start,
                            KingdomWar.finished_at <= search_time_end
                        )
                    )
                )
                
                wars_list = finished_wars.scalars().all()
                total_restored = 0
                
                for war in wars_list:
                    # Get all participants
                    participants = await session.execute(
                        select(WarParticipation).where(WarParticipation.war_id == war.id)
                    )
                    
                    for participation in participants.scalars():
                        # Restore HP and MP to full
                        user = await session.get(User, participation.user_id)
                        if user:
                            user.current_hp = user.hp
                            user.current_mana = user.mana
                            total_restored += 1
                
                await session.commit()
                
                if total_restored > 0:
                    logger.info(f"Restored HP/MP for {total_restored} war participants")
                    
                    # Send notification to war channel if configured
                    if self.bot and self.war_service.war_channel_id:
                        restoration_message = (
                            f"🩹 **ВОССТАНОВЛЕНИЕ УЧАСТНИКОВ**\n\n"
                            f"⚡ Восстановлено здоровье и мана у {total_restored} участников войн\n"
                            f"🕐 Время: {end_time.strftime('%H:%M')} (Ташкентское время)\n\n"
                            f"Все участники готовы к новым сражениям!"
                        )
                        try:
                            await self.bot.send_message(self.war_service.war_channel_id, restoration_message)
                        except Exception as e:
                            logger.error(f"Error sending restoration notification: {e}")
            
        except Exception as e:
            logger.error(f"Error restoring participants for {war_hour}:00 wars: {e}")
    
    def set_bot(self, bot):
        """Установить бота для отправки уведомлений"""
        self.bot = bot
        self.war_service.bot = bot
    
    def stop(self):
        """Остановка планировщика"""
        self.scheduler.shutdown()
        logger.info("Enhanced Kingdom War Scheduler stopped")

# Глобальный экземпляр планировщика
enhanced_war_scheduler = EnhancedKingdomWarScheduler()