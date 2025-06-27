from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import AsyncSessionLocal
from models.item import Item, UserItem, ItemTypeEnum, RarityEnum
from models.user import User
from services.user_service import UserService
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class ShopService:
    def __init__(self):
        self.user_service = UserService()
    
    async def get_shop_items(self, item_type: str = None, page: int = 1, items_per_page: int = 8) -> List[Item]:
        """Get items available in shop"""
        async with AsyncSessionLocal() as session:
            query = select(Item).where(Item.is_available_in_shop == True)
            
            if item_type and item_type != "all":
                query = query.where(Item.item_type == item_type)
            
            # Add pagination
            offset = (page - 1) * items_per_page
            query = query.offset(offset).limit(items_per_page)
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def get_shop_categories(self) -> dict:
        """Get shop categories with item counts"""
        async with AsyncSessionLocal() as session:
            categories = {}
            
            for item_type in ItemTypeEnum:
                count = await session.scalar(
                    select(func.count(Item.id)).where(
                        and_(
                            Item.is_available_in_shop == True,
                            Item.item_type == item_type
                        )
                    )
                )
                categories[item_type.value] = count or 0
            
            return categories
    
    async def buy_item(self, user_id: int, item_id: int, quantity: int = 1) -> tuple[bool, str]:
        """Buy item from shop"""
        async with AsyncSessionLocal() as session:
            # Get user and item
            user = await session.get(User, user_id)
            item = await session.get(Item, item_id)
            
            if not user:
                return False, "Пользователь не найден"
            
            if not item:
                return False, "Предмет не найден"
            
            if not item.is_available_in_shop:
                return False, "Предмет недоступен для покупки"
            
            # Check level requirement
            if user.level < item.level_required:
                return False, f"Требуемый уровень: {item.level_required}"
            
            # Calculate total cost
            total_cost = item.price * quantity
            
            if user.money < total_cost:
                return False, f"Недостаточно денег. Нужно: {total_cost}, есть: {user.money}"
            
            # Check inventory space for non-stackable items
            if item.item_type in [ItemTypeEnum.weapon, ItemTypeEnum.armor]:
                inventory_count = await session.scalar(
                    select(func.count(UserItem.id)).where(UserItem.user_id == user_id)
                )
                if inventory_count + quantity > user.inventory_size:
                    return False, f"Недостаточно места в инвентаре"
            
            # Check if user already has this item (for stackable items)
            existing_item = await session.scalar(
                select(UserItem).where(
                    and_(
                        UserItem.user_id == user_id,
                        UserItem.item_id == item_id
                    )
                )
            )
            
            # Add item to inventory
            if existing_item and item.item_type in [ItemTypeEnum.consumable, ItemTypeEnum.material]:
                # Stack with existing item
                existing_item.quantity += quantity
            else:
                # Create new inventory entry
                user_item = UserItem(
                    user_id=user_id,
                    item_id=item_id,
                    quantity=quantity,
                    current_durability=item.durability
                )
                session.add(user_item)
            
            # Deduct money
            user.money -= total_cost
            
            await session.commit()
            
            logger.info(f"User {user.name} bought {quantity}x {item.name} for {total_cost} gold")
            return True, f"Куплено: {quantity}x {item.name}"
    
    async def get_item_info(self, item_id: int) -> Optional[Item]:
        """Get detailed item information"""
        async with AsyncSessionLocal() as session:
            return await session.get(Item, item_id)