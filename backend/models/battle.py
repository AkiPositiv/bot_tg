from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.sql import func
from config.database import Base
import enum
import json

class BattleTypeEnum(enum.Enum):
    pvp = "pvp"
    pve = "pve"

class BattleStatusEnum(enum.Enum):
    pending = "pending"
    active = "active"
    finished = "finished"
    cancelled = "cancelled"

class Battle(Base):
    __tablename__ = "battles"
    
    id = Column(Integer, primary_key=True, index=True)
    battle_type = Column(Enum(BattleTypeEnum), nullable=False)
    status = Column(Enum(BattleStatusEnum), default=BattleStatusEnum.pending)
    
    # Participants
    challenger_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    defender_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    winner_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Battle data
    total_turns = Column(Integer, default=0)
    damage_log = Column(Text, default="[]")  # JSON string
    
    # Rewards
    exp_gained = Column(Integer, default=0)
    money_gained = Column(Integer, default=0)
    items_dropped = Column(Text, default="[]")  # JSON string
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<Battle(id={self.id}, type={self.battle_type}, status={self.status})>"
    
    def get_damage_log(self):
        """Parse damage log from JSON"""
        try:
            return json.loads(self.damage_log) if self.damage_log else []
        except:
            return []
    
    def set_damage_log(self, log_data):
        """Set damage log as JSON"""
        self.damage_log = json.dumps(log_data)
    
    def get_items_dropped(self):
        """Parse items dropped from JSON"""
        try:
            return json.loads(self.items_dropped) if self.items_dropped else []
        except:
            return []
    
    def set_items_dropped(self, items):
        """Set items dropped as JSON"""
        self.items_dropped = json.dumps(items)