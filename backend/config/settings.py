import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Bot Settings
    BOT_TOKEN: str
    
    # Database
    DB_PATH: str = "./rpg_game.db"
    
    # War Settings
    WAR_CHANNEL_ID: str = ""  # ID канала для уведомлений о войнах
    
    # Game Settings
    MAX_LEVEL: int = 100
    BASE_EXPERIENCE: int = 100
    STAT_POINTS_PER_LEVEL: int = 3
    STARTING_MONEY: int = 100
    STARTING_INVENTORY_SIZE: int = 20
    
    # Battle Settings
    BATTLE_TIMEOUT: int = 300
    MAX_BATTLE_TURNS: int = 50
    
    # Dungeon Settings
    MAX_DUNGEON_PARTICIPANTS: int = 5
    DUNGEON_WAIT_TIME: int = 180
    
    # Security
    RATE_LIMIT: int = 30
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"sqlite+aiosqlite:///{self.DB_PATH}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Load settings
ROOT_DIR = Path(__file__).parent.parent
settings = Settings(_env_file=ROOT_DIR / '.env')

# Game Constants
class GameConstants:
    BASE_STATS = {
        'strength': 10,
        'armor': 10,
        'hp': 100,
        'agility': 10,
        'mana': 50
    }
    
    KINGDOMS = {
        'north': {'name': 'Северное королевство', 'emoji': '❄️'},
        'west': {'name': 'Западное королевство', 'emoji': '🌅'},
        'east': {'name': 'Восточное королевство', 'emoji': '🌸'},
        'south': {'name': 'Южное королевство', 'emoji': '🔥'}
    }
    
    RARITY_COLORS = {
        'common': '⚪',
        'rare': '🔵', 
        'legendary': '🟡',
        'mythical': '🔴'
    }