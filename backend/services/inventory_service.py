from sqlalchemy import select, and_, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import AsyncSessionLocal
from models.item import Item, UserItem, ItemTypeEnum
from models.user import User
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)

class InventoryService:
    def __init__(self):
        pass
    
    async def get_user_inventory(self, user_id: int) -> List[UserItem]:
        """Get user's inventory"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserItem).where(UserItem.user_id == user_id)
                .order_by(UserItem.is_equipped.desc(), UserItem.obtained_at.desc())
            )
            return result.scalars().all()
    
    async def get_equipped_items(self, user_id: int) -> Dict[str, UserItem]:
        """Get equipped items by type"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserItem).where(
                    and_(
                        UserItem.user_id == user_id,
                        UserItem.is_equipped == True
                    )
                )
            )
            equipped_items = result.scalars().all()
            
            # Group by item type
            equipped_by_type = {}
            for user_item in equipped_items:
                await session.refresh(user_item, ['item'])
                equipped_by_type[user_item.item.item_type.value] = user_item
            
            return equipped_by_type
    
    async def equip_item(self, user_id: int, user_item_id: int) -> tuple[bool, str]:
        """Equip an item"""
        async with AsyncSessionLocal() as session:
            # Get the item to equip
            user_item = await session.get(UserItem, user_item_id)
            if not user_item or user_item.user_id != user_id:
                return False, "Предмет не найден"
            
            await session.refresh(user_item, ['item'])
            item = user_item.item
            
            # Check if item can be equipped
            if item.item_type not in [ItemTypeEnum.weapon, ItemTypeEnum.armor]:
                return False, "Этот предмет нельзя экипировать"
            
            # Check level requirement
            user = await session.get(User, user_id)
            if user.level < item.level_required:
                return False, f"Требуемый уровень: {item.level_required}"
            
            # Unequip existing item of the same type
            await session.execute(
                update(UserItem).where(
                    and_(
                        UserItem.user_id == user_id,
                        UserItem.is_equipped == True,
                        UserItem.id != user_item_id
                    )
                ).values(is_equipped=False)
                .execution_options(synchronize_session="fetch")
            )
            
            # Equip the new item
            user_item.is_equipped = True
            
            # Update user stats
            await self._update_user_stats(user_id, session)
            
            await session.commit()
            
            logger.info(f"User {user_id} equipped {item.name}")
            return True, f"Экипировано: {item.name}"
    
    async def unequip_item(self, user_id: int, user_item_id: int) -> tuple[bool, str]:
        """Unequip an item"""
        async with AsyncSessionLocal() as session:
            # Get the item to unequip
            user_item = await session.get(UserItem, user_item_id)
            if not user_item or user_item.user_id != user_id:
                return False, "Предмет не найден"
            
            if not user_item.is_equipped:
                return False, "Предмет не экипирован"
            
            await session.refresh(user_item, ['item'])
            item = user_item.item
            
            # Unequip the item
            user_item.is_equipped = False
            
            # Update user stats
            await self._update_user_stats(user_id, session)
            
            await session.commit()
            
            logger.info(f"User {user_id} unequipped {item.name}")
            return True, f"Снято: {item.name}"
    
    async def sell_item(self, user_id: int, user_item_id: int, quantity: int = 1) -> tuple[bool, str]:
        """Sell an item"""
        async with AsyncSessionLocal() as session:
            user_item = await session.get(UserItem, user_item_id)
            if not user_item or user_item.user_id != user_id:
                return False, "Предмет не найден"
            
            if user_item.is_equipped:
                return False, "Нельзя продать экипированный предмет"
            
            if user_item.quantity < quantity:
                return False, f"Недостаточно предметов. Есть: {user_item.quantity}"
            
            await session.refresh(user_item, ['item'])
            item = user_item.item
            
            # Calculate sell price (50% of buy price)
            sell_price = int(item.price * 0.5 * quantity)
            
            # Update user money
            user = await session.get(User, user_id)
            user.money += sell_price
            
            # Remove or reduce quantity
            if user_item.quantity <= quantity:
                await session.delete(user_item)
            else:
                user_item.quantity -= quantity
            
            await session.commit()
            
            logger.info(f"User {user_id} sold {quantity}x {item.name} for {sell_price} gold")
            return True, f"Продано: {quantity}x {item.name} за {sell_price} золота"
    
    async def use_item(self, user_id: int, user_item_id: int) -> tuple[bool, str]:
        """Use a consumable item"""
        async with AsyncSessionLocal() as session:
            user_item = await session.get(UserItem, user_item_id)
            if not user_item or user_item.user_id != user_id:
                return False, "Предмет не найден"
            
            await session.refresh(user_item, ['item'])
            item = user_item.item
            
            if item.item_type != ItemTypeEnum.consumable:
                return False, "Этот предмет нельзя использовать"
            
            user = await session.get(User, user_id)
            
            # Apply item effects based on item name/type
            effect_applied = False
            effect_text = ""
            
            if "зелье здоровья" in item.name.lower() or "health" in item.name.lower():
                heal_amount = item.hp_bonus or 30
                old_hp = user.current_hp
                user.current_hp = min(user.current_hp + heal_amount, user.hp)
                actual_heal = user.current_hp - old_hp
                effect_text = f"Восстановлено {actual_heal} HP"
                effect_applied = True
            
            elif "зелье маны" in item.name.lower() or "mana" in item.name.lower():
                mana_amount = item.mana_bonus or 25
                old_mana = user.current_mana
                user.current_mana = min(user.current_mana + mana_amount, user.mana)
                actual_mana = user.current_mana - old_mana
                effect_text = f"Восстановлено {actual_mana} маны"
                effect_applied = True
            
            if not effect_applied:
                return False, "Неизвестный эффект предмета"
            
            # Remove one item
            if user_item.quantity <= 1:
                await session.delete(user_item)
            else:
                user_item.quantity -= 1
            
            await session.commit()
            
            logger.info(f"User {user_id} used {item.name}")
            return True, f"Использовано: {item.name}. {effect_text}"
    
    async def _update_user_stats(self, user_id: int, session: AsyncSession):
        """Update user stats based on equipped items"""
        user = await session.get(User, user_id)
        
        # Get all equipped items
        result = await session.execute(
            select(UserItem).where(
                and_(
                    UserItem.user_id == user_id,
                    UserItem.is_equipped == True
                )
            )
        )
        equipped_items = result.scalars().all()
        
        # Calculate total bonuses from equipped items
        total_strength_bonus = 0
        total_armor_bonus = 0
        total_hp_bonus = 0
        total_agility_bonus = 0
        total_mana_bonus = 0
        
        for user_item in equipped_items:
            await session.refresh(user_item, ['item'])
            item = user_item.item
            
            total_strength_bonus += item.strength_bonus or 0
            total_armor_bonus += item.armor_bonus or 0
            total_hp_bonus += item.hp_bonus or 0
            total_agility_bonus += item.agility_bonus or 0
            total_mana_bonus += item.mana_bonus or 0
        
        # For now, we need to extend the User model to store base stats and equipment bonuses
        # Since this is a complex change, let's implement a simple solution:
        # We'll store the current total stats (base + equipment) in the existing fields
        
        # Get base stats from level and distributed points
        from config.settings import GameConstants
        from utils.formulas import GameFormulas
        
        base_stats = GameConstants.BASE_STATS.copy()
        stat_points = GameFormulas.stat_points_for_level(user.level)
        
        # This is simplified - in a real system you'd track base stats separately
        # For now, we just ensure minimum stats with equipment bonuses
        min_strength = base_stats['strength'] + total_strength_bonus
        min_armor = base_stats['armor'] + total_armor_bonus
        min_hp = base_stats['hp'] + total_hp_bonus
        min_agility = base_stats['agility'] + total_agility_bonus
        min_mana = base_stats['mana'] + total_mana_bonus
        
        # Apply bonuses if they would increase stats
        if user.strength < min_strength:
            user.strength = min_strength
        if user.armor < min_armor:
            user.armor = min_armor
        if user.hp < min_hp:
            old_max_hp = user.hp
            user.hp = min_hp
            # Proportionally adjust current HP
            if old_max_hp > 0:
                hp_ratio = user.current_hp / old_max_hp
                user.current_hp = int(user.hp * hp_ratio)
        if user.agility < min_agility:
            user.agility = min_agility
        if user.mana < min_mana:
            old_max_mana = user.mana
            user.mana = min_mana
            # Proportionally adjust current mana
            if old_max_mana > 0:
                mana_ratio = user.current_mana / old_max_mana
                user.current_mana = int(user.mana * mana_ratio)
        
        logger.info(f"Updated stats for user {user_id}: STR+{total_strength_bonus}, ARM+{total_armor_bonus}, HP+{total_hp_bonus}, AGI+{total_agility_bonus}, MANA+{total_mana_bonus}")
        
    async def get_inventory_stats(self, user_id: int) -> dict:
        """Get inventory statistics"""
        async with AsyncSessionLocal() as session:
            total_items = await session.scalar(
                select(func.count(UserItem.id)).where(UserItem.user_id == user_id)
            )
            
            equipped_items = await session.scalar(
                select(func.count(UserItem.id)).where(
                    and_(
                        UserItem.user_id == user_id,
                        UserItem.is_equipped == True
                    )
                )
            )
            
            user = await session.get(User, user_id)
            
            return {
                'total_items': total_items or 0,
                'equipped_items': equipped_items or 0,
                'inventory_size': user.inventory_size,
                'free_slots': user.inventory_size - (total_items or 0)
            }