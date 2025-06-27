from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum, Boolean
from sqlalchemy.sql import func
from config.database import Base
import enum
import json

class BattleModeEnum(enum.Enum):
    pvp_interactive = "pvp_interactive"
    pve_interactive = "pve_interactive"
    auto = "auto"

class BattlePhaseEnum(enum.Enum):
    monster_encounter = "monster_encounter"
    attack_selection = "attack_selection"
    dodge_selection = "dodge_selection"
    calculating = "calculating"
    finished = "finished"

class InteractiveBattle(Base):
    __tablename__ = "interactive_battles"
    
    id = Column(Integer, primary_key=True, index=True)
    mode = Column(Enum(BattleModeEnum), nullable=False)
    phase = Column(Enum(BattlePhaseEnum), default=BattlePhaseEnum.monster_encounter)
    
    # Participants
    player1_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    player2_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Null for PvE
    monster_data = Column(Text, nullable=True)  # JSON for PvE monsters
    
    # Battle state
    current_round = Column(Integer, default=1)
    max_rounds = Column(Integer, default=10)
    
    # Player states
    player1_hp = Column(Integer, nullable=False)
    player1_mana = Column(Integer, nullable=False)
    player2_hp = Column(Integer, nullable=True)
    player2_mana = Column(Integer, nullable=True)
    monster_hp = Column(Integer, nullable=True)
    
    # Round choices
    player1_attack_choice = Column(String(20), nullable=True)  # left, center, right
    player1_dodge_choice = Column(String(20), nullable=True)   # left, center, right
    player2_attack_choice = Column(String(20), nullable=True)
    player2_dodge_choice = Column(String(20), nullable=True)
    
    # Round timer
    round_start_time = Column(DateTime(timezone=True), nullable=True)
    round_timeout = Column(Integer, default=50)  # seconds
    
    # Battle log
    battle_log = Column(Text, default="[]")  # JSON array
    
    # Results
    winner_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    exp_gained = Column(Integer, default=0)
    money_gained = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<InteractiveBattle(id={self.id}, mode={self.mode}, phase={self.phase})>"
    
    def get_monster_data(self):
        """Parse monster data from JSON"""
        try:
            return json.loads(self.monster_data) if self.monster_data else None
        except:
            return None
    
    def set_monster_data(self, monster):
        """Set monster data as JSON"""
        monster_dict = {
            'name': monster.name,
            'level': monster.level,
            'strength': monster.strength,
            'armor': monster.armor,
            'hp': monster.hp,
            'agility': monster.agility,
            'exp_reward': monster.exp_reward,
            'money_reward': monster.money_reward,
            'type_emoji': monster.type_emoji,
            'difficulty_color': monster.difficulty_color
        }
        self.monster_data = json.dumps(monster_dict)
        self.monster_hp = monster.hp
    
    def get_battle_log(self):
        """Parse battle log from JSON"""
        try:
            return json.loads(self.battle_log) if self.battle_log else []
        except:
            return []
    
    def add_to_battle_log(self, entry):
        """Add entry to battle log"""
        log = self.get_battle_log()
        log.append(entry)
        self.battle_log = json.dumps(log)
    
    def reset_round_choices(self):
        """Reset choices for new round"""
        self.player1_attack_choice = None
        self.player1_dodge_choice = None
        self.player2_attack_choice = None
        self.player2_dodge_choice = None
        self.round_start_time = func.now()
    
    def both_players_ready(self):
        """Check if both players have made their choices"""
        if self.mode == BattleModeEnum.pve_interactive:
            return (self.player1_attack_choice is not None and 
                    self.player1_dodge_choice is not None)
        else:
            return (self.player1_attack_choice is not None and 
                    self.player1_dodge_choice is not None and
                    self.player2_attack_choice is not None and 
                    self.player2_dodge_choice is not None)