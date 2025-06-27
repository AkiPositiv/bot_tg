from sqlalchemy import Column, Integer, String, DateTime, Text, Enum, Boolean, Float
from sqlalchemy.sql import func
from config.database import Base
import enum
import json
from datetime import datetime

class WarStatusEnum(enum.Enum):
    scheduled = "scheduled"
    active = "active"
    finished = "finished"

class WarTypeEnum(enum.Enum):
    kingdom_attack = "kingdom_attack"
    siege = "siege"

class KingdomWar(Base):
    __tablename__ = "kingdom_wars"
    
    id = Column(Integer, primary_key=True, index=True)
    war_type = Column(Enum(WarTypeEnum), default=WarTypeEnum.kingdom_attack)
    status = Column(Enum(WarStatusEnum), default=WarStatusEnum.scheduled)
    
    # War timing
    scheduled_time = Column(DateTime(timezone=True), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    
    # Participating kingdoms
    attacking_kingdoms = Column(Text, default="[]")  # JSON array of kingdom names
    defending_kingdom = Column(String(20), nullable=False)
    
    # Battle data
    attack_squads = Column(Text, default="{}")  # JSON dict: kingdom -> [player_ids]
    defense_squad = Column(Text, default="[]")  # JSON array of player_ids
    
    # Stats
    total_attack_stats = Column(Text, default="{}")  # JSON dict: kingdom -> stats
    defense_stats = Column(Text, default="{}")  # JSON dict with defense stats
    defense_buff = Column(Float, default=1.0)  # Defense multiplier
    
    # Results
    battle_results = Column(Text, default="[]")  # JSON array of battle results
    money_transferred = Column(Text, default="{}")  # JSON dict: kingdom -> amount
    exp_distributed = Column(Text, default="{}")  # JSON dict: player_id -> exp
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<KingdomWar(id={self.id}, defending={self.defending_kingdom}, status={self.status})>"
    
    def get_attacking_kingdoms(self):
        """Parse attacking kingdoms from JSON"""
        try:
            return json.loads(self.attacking_kingdoms) if self.attacking_kingdoms else []
        except:
            return []
    
    def set_attacking_kingdoms(self, kingdoms):
        """Set attacking kingdoms as JSON"""
        self.attacking_kingdoms = json.dumps(kingdoms)
    
    def get_attack_squads(self):
        """Parse attack squads from JSON"""
        try:
            return json.loads(self.attack_squads) if self.attack_squads else {}
        except:
            return {}
    
    def set_attack_squads(self, squads):
        """Set attack squads as JSON"""
        self.attack_squads = json.dumps(squads)
    
    def get_defense_squad(self):
        """Parse defense squad from JSON"""
        try:
            return json.loads(self.defense_squad) if self.defense_squad else []
        except:
            return []
    
    def set_defense_squad(self, squad):
        """Set defense squad as JSON"""
        self.defense_squad = json.dumps(squad)
    
    def get_total_attack_stats(self):
        """Parse total attack stats from JSON"""
        try:
            return json.loads(self.total_attack_stats) if self.total_attack_stats else {}
        except:
            return {}
    
    def set_total_attack_stats(self, stats):
        """Set total attack stats as JSON"""
        self.total_attack_stats = json.dumps(stats)
    
    def get_defense_stats(self):
        """Parse defense stats from JSON"""
        try:
            return json.loads(self.defense_stats) if self.defense_stats else {}
        except:
            return {}
    
    def set_defense_stats(self, stats):
        """Set defense stats as JSON"""
        self.defense_stats = json.dumps(stats)
    
    def get_battle_results(self):
        """Parse battle results from JSON"""
        try:
            return json.loads(self.battle_results) if self.battle_results else []
        except:
            return []
    
    def add_battle_result(self, result):
        """Add battle result to log"""
        results = self.get_battle_results()
        results.append(result)
        self.battle_results = json.dumps(results)
    
    def get_money_transferred(self):
        """Parse money transferred from JSON"""
        try:
            return json.loads(self.money_transferred) if self.money_transferred else {}
        except:
            return {}
    
    def set_money_transferred(self, transfers):
        """Set money transferred as JSON"""
        self.money_transferred = json.dumps(transfers)
    
    def get_exp_distributed(self):
        """Parse exp distributed from JSON"""
        try:
            return json.loads(self.exp_distributed) if self.exp_distributed else {}
        except:
            return {}
    
    def set_exp_distributed(self, exp_dist):
        """Set exp distributed as JSON"""
        self.exp_distributed = json.dumps(exp_dist)

class WarParticipation(Base):
    __tablename__ = "war_participations"
    
    id = Column(Integer, primary_key=True, index=True)
    war_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    kingdom = Column(String(20), nullable=False)
    role = Column(Enum(enum.Enum('Role', ['attacker', 'defender'])), nullable=False)
    
    # Player stats at time of war
    player_stats = Column(Text, default="{}")  # JSON with player stats
    
    # Results
    money_gained = Column(Integer, default=0)
    money_lost = Column(Integer, default=0)
    exp_gained = Column(Integer, default=0)
    
    # Timestamps
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<WarParticipation(war_id={self.war_id}, user_id={self.user_id}, role={self.role})>"
    
    def get_player_stats(self):
        """Parse player stats from JSON"""
        try:
            return json.loads(self.player_stats) if self.player_stats else {}
        except:
            return {}
    
    def set_player_stats(self, stats):
        """Set player stats as JSON"""
        self.player_stats = json.dumps(stats)