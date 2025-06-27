from sqlalchemy import Column, Integer, String, Text, Enum
from config.database import Base
import enum
import random

class MonsterTypeEnum(enum.Enum):
    weak = "weak"
    normal = "normal"
    strong = "strong"
    boss = "boss"

class Monster(Base):
    __tablename__ = "monsters"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    monster_type = Column(Enum(MonsterTypeEnum), default=MonsterTypeEnum.normal)
    
    # Level and stats
    level = Column(Integer, default=1)
    strength = Column(Integer, default=10)
    armor = Column(Integer, default=8)
    hp = Column(Integer, default=80)
    agility = Column(Integer, default=8)
    
    # Rewards
    exp_reward = Column(Integer, default=25)
    money_reward = Column(Integer, default=15)
    
    def __repr__(self):
        return f"<Monster(id={self.id}, name='{self.name}', level={self.level})>"
    
    @classmethod
    def generate_random_monster(cls, player_level: int):
        """Generate a random monster based on player level"""
        # Monster templates
        templates = {
            'weak': {
                'names': ['Гоблин-разбойник', 'Крыса-мутант', 'Слабый скелет', 'Дикий волк'],
                'stat_modifier': 0.7,
                'reward_modifier': 0.8
            },
            'normal': {
                'names': ['Орк-воин', 'Лесной тролль', 'Зомби-солдат', 'Каменный голем'],
                'stat_modifier': 1.0,
                'reward_modifier': 1.0
            },
            'strong': {
                'names': ['Огненный элементаль', 'Ледяной великан', 'Тёмный рыцарь', 'Древний дракон'],
                'stat_modifier': 1.3,
                'reward_modifier': 1.5
            }
        }
        
        # Choose monster type based on random chance
        rand = random.random()
        if rand < 0.5:
            monster_type = 'weak'
        elif rand < 0.85:
            monster_type = 'normal'
        else:
            monster_type = 'strong'
        
        template = templates[monster_type]
        name = random.choice(template['names'])
        
        # Calculate level (±2 from player level)
        level_variance = random.randint(-2, 2)
        monster_level = max(1, player_level + level_variance)
        
        # Calculate stats based on level and type
        base_stats = {
            'strength': 8 + monster_level * 2,
            'armor': 6 + monster_level * 1.5,
            'hp': 60 + monster_level * 15,
            'agility': 5 + monster_level * 1.2
        }
        
        # Apply type modifier
        modifier = template['stat_modifier']
        stats = {k: int(v * modifier) for k, v in base_stats.items()}
        
        # Calculate rewards
        exp_reward = int((20 + monster_level * 3) * template['reward_modifier'])
        money_reward = int((10 + monster_level * 2) * template['reward_modifier'])
        
        return cls(
            name=name,
            monster_type=MonsterTypeEnum(monster_type),
            level=monster_level,
            strength=stats['strength'],
            armor=int(stats['armor']),
            hp=stats['hp'],
            agility=int(stats['agility']),
            exp_reward=exp_reward,
            money_reward=money_reward
        )
    
    @property
    def type_emoji(self):
        """Get monster type emoji"""
        emojis = {
            'weak': '😈',
            'normal': '👹',
            'strong': '👺',
            'boss': '🐉'
        }
        return emojis.get(self.monster_type.value, '👹')
    
    @property
    def difficulty_color(self):
        """Get difficulty color indicator"""
        colors = {
            'weak': '🟢',
            'normal': '🟡',
            'strong': '🔴',
            'boss': '🟣'
        }
        return colors.get(self.monster_type.value, '🟡')