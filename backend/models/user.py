from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum
from sqlalchemy.sql import func
from config.database import Base
import enum

class GenderEnum(enum.Enum):
    male = "male"
    female = "female"

class KingdomEnum(enum.Enum):
    north = "north"
    west = "west"
    east = "east"
    south = "south"

class User(Base):
    __tablename__ = "users"
    
    # Primary key - Telegram ID
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic info
    name = Column(String(50), nullable=False)
    gender = Column(Enum(GenderEnum), nullable=False)
    kingdom = Column(Enum(KingdomEnum), nullable=False)
    
    # Level and progression
    level = Column(Integer, default=1)
    experience = Column(Integer, default=0)
    free_stat_points = Column(Integer, default=0)
    
    # Resources
    money = Column(Integer, default=100)
    stones = Column(Integer, default=0)
    
    # Base stats
    strength = Column(Integer, default=10)
    armor = Column(Integer, default=10)
    hp = Column(Integer, default=100)
    current_hp = Column(Integer, default=100)
    agility = Column(Integer, default=10)
    mana = Column(Integer, default=50)
    current_mana = Column(Integer, default=50)
    
    # Additional fields
    inventory_size = Column(Integer, default=20)
    
    # Battle statistics
    pvp_wins = Column(Integer, default=0)
    pvp_losses = Column(Integer, default=0)
    pve_wins = Column(Integer, default=0)
    total_damage_dealt = Column(Integer, default=0)
    total_damage_received = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', level={self.level})>"
    
    @property
    def max_hp(self):
        """Calculate max HP including bonuses"""
        return self.hp
    
    @property
    def max_mana(self):
        """Calculate max mana including bonuses"""
        return self.mana
    
    @property
    def total_stats(self):
        """Calculate total stats"""
        return self.strength + self.armor + self.agility + (self.hp // 10) + (self.mana // 5)