from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import AsyncSessionLocal
from models.user import User
from utils.formulas import GameFormulas
from config.settings import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self):
        pass
    
    async def get_user(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.id == telegram_id)
            )
            return result.scalar_one_or_none()
    
    async def create_user(self, telegram_id: int, name: str, gender: str, kingdom: str) -> User:
        """Create new user"""
        async with AsyncSessionLocal() as session:
            user = User(
                id=telegram_id,
                name=name,
                gender=gender,
                kingdom=kingdom,
                money=settings.STARTING_MONEY,
                inventory_size=settings.STARTING_INVENTORY_SIZE
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info(f"Created new user: {user.name} (ID: {telegram_id})")
            return user
    
    async def update_user(self, telegram_id: int, **kwargs) -> bool:
        """Update user fields"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                update(User).where(User.id == telegram_id).values(**kwargs)
            )
            await session.commit()
            return result.rowcount > 0
    
    async def add_experience(self, user_id: int, exp: int) -> bool:
        """Add experience and check for level up"""
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                return False
            
            user.experience += exp
            
            # Check for level up
            while user.experience >= GameFormulas.experience_for_level(user.level + 1):
                user.experience -= GameFormulas.experience_for_level(user.level + 1)
                user.level += 1
                user.free_stat_points += settings.STAT_POINTS_PER_LEVEL
                logger.info(f"User {user.name} leveled up to {user.level}")
            
            await session.commit()
            return True
    
    async def distribute_stat_points(self, user_id: int, stats: dict) -> bool:
        """Distribute stat points"""
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                return False
            
            total_points = sum(stats.values())
            if total_points > user.free_stat_points:
                return False
            
            # Apply stat increases
            for stat, points in stats.items():
                if hasattr(user, stat):
                    setattr(user, stat, getattr(user, stat) + points)
            
            user.free_stat_points -= total_points
            await session.commit()
            return True
    
    async def restore_hp_mana(self, user_id: int, hp: int = None, mana: int = None) -> bool:
        """Restore HP and/or mana"""
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                return False
            
            if hp is not None:
                user.current_hp = min(user.current_hp + hp, user.max_hp)
            
            if mana is not None:
                user.current_mana = min(user.current_mana + mana, user.max_mana)
            
            await session.commit()
            return True
    
    async def update_last_active(self, user_id: int) -> bool:
        """Update last active timestamp"""
        from sqlalchemy import func
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                update(User).where(User.id == user_id).values(last_active=func.now())
            )
            await session.commit()
            return result.rowcount > 0