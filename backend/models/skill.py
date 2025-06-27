from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from config.database import Base
import enum

class SkillRankEnum(enum.Enum):
    E = "E"
    D = "D"
    C = "C"
    B = "B"
    A = "A"
    AA = "AA"
    S = "S"
    SS = "SS"
    SSS = "SSS"

class SkillTypeEnum(enum.Enum):
    attack = "attack"
    defense = "defense"
    buff = "buff"
    debuff = "debuff"
    heal = "heal"

class TargetTypeEnum(enum.Enum):
    self_target = "self"
    enemy = "enemy"
    all_enemies = "all_enemies"
    all_allies = "all_allies"

class Skill(Base):
    __tablename__ = "skills"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    rank = Column(Enum(SkillRankEnum), default=SkillRankEnum.E)
    skill_type = Column(Enum(SkillTypeEnum), nullable=False)
    target_type = Column(Enum(TargetTypeEnum), default=TargetTypeEnum.enemy)
    
    # Requirements and costs
    mana_cost = Column(Integer, default=10)
    cooldown = Column(Integer, default=0)  # turns
    level_required = Column(Integer, default=1)
    
    # Effects
    damage_multiplier = Column(Float, default=1.0)
    defense_multiplier = Column(Float, default=1.0)
    heal_amount = Column(Integer, default=0)
    status_effect = Column(String(200))
    effect_duration = Column(Integer, default=0)
    
    # Availability
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Skill(id={self.id}, name='{self.name}', rank={self.rank})>"
    
    @property
    def priority(self):
        """Get skill priority for auto-casting"""
        priorities = {
            'heal': 1,      # Highest priority
            'buff': 2,
            'debuff': 3,
            'defense': 4,
            'attack': 5     # Lowest priority
        }
        return priorities.get(self.skill_type.value, 5)

class UserSkill(Base):
    __tablename__ = "user_skills"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    skill_id = Column(Integer, ForeignKey('skills.id'), nullable=False)
    
    # Skill mastery
    learned_at = Column(DateTime(timezone=True), server_default=func.now())
    times_used = Column(Integer, default=0)
    mastery_level = Column(Integer, default=1)  # 1-10
    last_used = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    skill = relationship("Skill")
    
    def __repr__(self):
        return f"<UserSkill(user_id={self.user_id}, skill_id={self.skill_id}, mastery={self.mastery_level})>"
    
    @property
    def cooldown_reduction(self):
        """Calculate cooldown reduction based on mastery"""
        return min(self.mastery_level * 0.1, 0.5)  # Max 50% reduction
    
    @property
    def effective_cooldown(self):
        """Get effective cooldown with mastery reduction"""
        base_cooldown = self.skill.cooldown
        return max(1, int(base_cooldown * (1 - self.cooldown_reduction)))