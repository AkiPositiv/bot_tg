from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from config.database import Base
import enum

class ItemTypeEnum(enum.Enum):
    weapon = "weapon"
    armor = "armor"
    consumable = "consumable"
    material = "material"
    scroll = "scroll"

class RarityEnum(enum.Enum):
    common = "common"
    rare = "rare"
    legendary = "legendary"
    mythical = "mythical"

class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    item_type = Column(Enum(ItemTypeEnum), nullable=False)
    rarity = Column(Enum(RarityEnum), default=RarityEnum.common)
    
    # Basic properties
    weight = Column(Integer, default=1)
    price = Column(Integer, default=10)
    level_required = Column(Integer, default=1)
    
    # Stat bonuses
    strength_bonus = Column(Integer, default=0)
    armor_bonus = Column(Integer, default=0)
    hp_bonus = Column(Integer, default=0)
    agility_bonus = Column(Integer, default=0)
    mana_bonus = Column(Integer, default=0)
    
    # Equipment properties
    durability = Column(Integer, default=100)
    max_durability = Column(Integer, default=100)
    
    # Special effects
    special_effect = Column(String(200))
    
    # Availability
    is_available_in_shop = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Item(id={self.id}, name='{self.name}', type={self.item_type})>"
    
    @property
    def total_stats(self):
        """Calculate total stat bonus"""
        return (self.strength_bonus + self.armor_bonus + 
                self.hp_bonus // 10 + self.agility_bonus + self.mana_bonus // 5)
    
    @property
    def rarity_emoji(self):
        """Get rarity emoji"""
        emojis = {
            'common': '⚪',
            'rare': '🔵',
            'legendary': '🟡',
            'mythical': '🔴'
        }
        return emojis.get(self.rarity.value, '⚪')

class UserItem(Base):
    __tablename__ = "user_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)
    
    # Item instance properties
    quantity = Column(Integer, default=1)
    is_equipped = Column(Boolean, default=False)
    current_durability = Column(Integer, default=100)
    
    # Timestamps
    obtained_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    item = relationship("Item")
    
    def __repr__(self):
        return f"<UserItem(user_id={self.user_id}, item_id={self.item_id}, qty={self.quantity})>"