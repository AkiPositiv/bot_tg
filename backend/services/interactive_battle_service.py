from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import AsyncSessionLocal
from models.interactive_battle import InteractiveBattle, BattleModeEnum, BattlePhaseEnum
from models.monster import Monster
from models.user import User
from utils.formulas import GameFormulas
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
import random
import logging
import asyncio

logger = logging.getLogger(__name__)

class InteractiveBattleService:
    def __init__(self):
        pass
    
    async def start_pve_encounter(self, player_id: int) -> Optional[InteractiveBattle]:
        """Start a PvE encounter with random monster"""
        async with AsyncSessionLocal() as session:
            # Get player
            player = await session.get(User, player_id)
            if not player:
                return None
            
            # Check if player has enough HP
            if player.current_hp < player.hp * 0.3:
                return None
            
            # Generate random monster
            monster = Monster.generate_random_monster(player.level)
            
            # Create interactive battle
            battle = InteractiveBattle(
                mode=BattleModeEnum.pve_interactive,
                phase=BattlePhaseEnum.monster_encounter,
                player1_id=player_id,
                player1_hp=player.current_hp,
                player1_mana=player.current_mana
            )
            
            battle.set_monster_data(monster)
            
            session.add(battle)
            await session.commit()
            await session.refresh(battle)
            
            logger.info(f"PvE encounter started: Player {player_id} vs {monster.name}")
            return battle
    
    async def accept_pve_battle(self, battle_id: int) -> bool:
        """Accept PvE battle and start first round"""
        async with AsyncSessionLocal() as session:
            battle = await session.get(InteractiveBattle, battle_id)
            if not battle or battle.phase != BattlePhaseEnum.monster_encounter:
                return False
            
            # Start first round
            battle.phase = BattlePhaseEnum.attack_selection
            battle.reset_round_choices()
            
            await session.commit()
            return True
    
    async def flee_from_battle(self, battle_id: int, player_id: int) -> bool:
        """Flee from battle"""
        async with AsyncSessionLocal() as session:
            battle = await session.get(InteractiveBattle, battle_id)
            if not battle or battle.player1_id != player_id:
                return False
            
            battle.phase = BattlePhaseEnum.finished
            battle.finished_at = datetime.utcnow()
            battle.add_to_battle_log({
                'round': battle.current_round,
                'action': 'flee',
                'player': 'player1',
                'message': 'Игрок сбежал с поля боя!'
            })
            
            await session.commit()
            logger.info(f"Player {player_id} fled from battle {battle_id}")
            return True
    
    async def make_attack_choice(self, battle_id: int, player_id: int, choice: str) -> bool:
        """Make attack choice (left, center, right)"""
        async with AsyncSessionLocal() as session:
            battle = await session.get(InteractiveBattle, battle_id)
            if not battle or battle.phase != BattlePhaseEnum.attack_selection:
                return False
            
            if choice not in ['left', 'center', 'right']:
                return False
            
            # Set choice based on player
            if battle.player1_id == player_id:
                battle.player1_attack_choice = choice
            elif battle.player2_id == player_id:
                battle.player2_attack_choice = choice
            else:
                return False
            
            # Check if all players made attack choice
            if self._all_attack_choices_made(battle):
                battle.phase = BattlePhaseEnum.dodge_selection
            
            await session.commit()
            return True
    
    async def make_dodge_choice(self, battle_id: int, player_id: int, choice: str) -> bool:
        """Make dodge choice (left, center, right)"""
        async with AsyncSessionLocal() as session:
            battle = await session.get(InteractiveBattle, battle_id)
            if not battle or battle.phase != BattlePhaseEnum.dodge_selection:
                return False
            
            if choice not in ['left', 'center', 'right']:
                return False
            
            # Set choice based on player
            if battle.player1_id == player_id:
                battle.player1_dodge_choice = choice
            elif battle.player2_id == player_id:
                battle.player2_dodge_choice = choice
            else:
                return False
            
            # Check if all players made dodge choice
            if battle.both_players_ready():
                # Calculate round results
                await self._calculate_round_results(battle, session)
            
            await session.commit()
            return True
    
    async def _calculate_round_results(self, battle: InteractiveBattle, session: AsyncSession):
        """Calculate results of the round"""
        battle.phase = BattlePhaseEnum.calculating
        
        # Get players
        player1 = await session.get(User, battle.player1_id)
        
        if battle.mode == BattleModeEnum.pve_interactive:
            await self._calculate_pve_round(battle, player1, session)
        else:
            player2 = await session.get(User, battle.player2_id)
            await self._calculate_pvp_round(battle, player1, player2, session)
    
    async def _calculate_pve_round(self, battle: InteractiveBattle, player: User, session: AsyncSession):
        """Calculate PvE round results"""
        monster_data = battle.get_monster_data()
        if not monster_data:
            return
        
        round_log = {
            'round': battle.current_round,
            'player_attack': battle.player1_attack_choice,
            'player_dodge': battle.player1_dodge_choice,
            'events': []
        }
        
        # Generate monster choices
        monster_attack = random.choice(['left', 'center', 'right'])
        monster_dodge = random.choice(['left', 'center', 'right'])
        
        round_log['monster_attack'] = monster_attack
        round_log['monster_dodge'] = monster_dodge
        
        # Calculate player attack on monster
        player_damage = 0
        if battle.player1_attack_choice == monster_dodge:
            # Direct hit
            base_damage = player.strength + int(player.agility * 0.5)
            defense = int(monster_data['armor'] * 0.8)
            player_damage = max(base_damage - defense, int(base_damage * 0.1))
            
            # Check for critical hit
            if GameFormulas.is_critical_hit(player.agility):
                player_damage = int(player_damage * 1.5)
                round_log['events'].append("🔥 Критический удар игрока!")
            
            round_log['events'].append(f"⚔️ Игрок нанёс {player_damage} урона")
        else:
            # Missed, but check for crit chance to still hit
            if GameFormulas.is_critical_hit(player.agility):
                player_damage = 2  # Minimal damage from crit
                round_log['events'].append("✨ Промах, но критический навык позволил нанести 2 урона!")
            else:
                round_log['events'].append("💨 Игрок промахнулся!")
        
        # Apply damage to monster
        battle.monster_hp = max(0, battle.monster_hp - player_damage)
        
        # Check if monster is dead
        if battle.monster_hp <= 0:
            await self._finish_pve_battle(battle, player, monster_data, session, round_log)
            return
        
        # Calculate monster attack on player
        monster_damage = 0
        if monster_attack == battle.player1_dodge_choice:
            # Monster hit
            base_damage = monster_data['strength'] + int(monster_data['agility'] * 0.5)
            defense = int(player.armor * 0.8)
            monster_damage = max(base_damage - defense, int(base_damage * 0.1))
            
            # Check if player can dodge with agility
            if GameFormulas.is_dodge(player.agility):
                monster_damage = 0
                round_log['events'].append("💨 Игрок уклонился от атаки!")
            else:
                round_log['events'].append(f"🩸 Монстр нанёс {monster_damage} урона")
        else:
            round_log['events'].append("💨 Монстр промахнулся!")
        
        # Apply damage to player
        battle.player1_hp = max(0, battle.player1_hp - monster_damage)
        
        # Add round to log
        battle.add_to_battle_log(round_log)
        
        # Check if player is dead
        if battle.player1_hp <= 0:
            battle.phase = BattlePhaseEnum.finished
            battle.finished_at = datetime.utcnow()
            battle.add_to_battle_log({
                'round': battle.current_round,
                'result': 'defeat',
                'message': 'Игрок погиб в бою!'
            })
            
            # Update player HP
            player.current_hp = 1  # Leave with 1 HP
            return
        
        # Continue to next round
        battle.current_round += 1
        if battle.current_round > battle.max_rounds:
            # Timeout - monster wins
            battle.phase = BattlePhaseEnum.finished
            battle.finished_at = datetime.utcnow()
            battle.add_to_battle_log({
                'round': battle.current_round,
                'result': 'timeout',
                'message': 'Время боя истекло! Монстр сбежал.'
            })
        else:
            # Start next round
            battle.phase = BattlePhaseEnum.attack_selection
            battle.reset_round_choices()
    
    async def _finish_pve_battle(self, battle: InteractiveBattle, player: User, monster_data: dict, session: AsyncSession, round_log: dict):
        """Finish PvE battle with player victory"""
        battle.phase = BattlePhaseEnum.finished
        battle.finished_at = datetime.utcnow()
        battle.winner_id = player.id
        battle.exp_gained = monster_data['exp_reward']
        battle.money_gained = monster_data['money_reward']
        
        # Add victory to log
        round_log['events'].append(f"🏆 {monster_data['name']} повержен!")
        battle.add_to_battle_log(round_log)
        
        battle.add_to_battle_log({
            'round': battle.current_round,
            'result': 'victory',
            'message': f"Победа! Получено {battle.exp_gained} опыта и {battle.money_gained} золота"
        })
        
        # Update player stats
        player.current_hp = battle.player1_hp
        player.money += battle.money_gained
        player.pve_wins += 1
        
        # Add experience
        from services.user_service import UserService
        user_service = UserService()
        await user_service.add_experience(player.id, battle.exp_gained)
    
    def _all_attack_choices_made(self, battle: InteractiveBattle) -> bool:
        """Check if all players made attack choices"""
        if battle.mode == BattleModeEnum.pve_interactive:
            return battle.player1_attack_choice is not None
        else:
            return (battle.player1_attack_choice is not None and 
                    battle.player2_attack_choice is not None)
    
    async def get_battle(self, battle_id: int) -> Optional[InteractiveBattle]:
        """Get battle by ID"""
        async with AsyncSessionLocal() as session:
            return await session.get(InteractiveBattle, battle_id)
    
    async def check_battle_timeout(self, battle_id: int) -> bool:
        """Check if battle has timed out"""
        async with AsyncSessionLocal() as session:
            battle = await session.get(InteractiveBattle, battle_id)
            if not battle or not battle.round_start_time:
                return False
            
            timeout_time = battle.round_start_time + timedelta(seconds=battle.round_timeout)
            if datetime.utcnow() > timeout_time:
                # Handle timeout
                battle.phase = BattlePhaseEnum.finished
                battle.finished_at = datetime.utcnow()
                battle.add_to_battle_log({
                    'round': battle.current_round,
                    'result': 'timeout',
                    'message': 'Время раунда истекло!'
                })
                
                await session.commit()
                return True
            
            return False