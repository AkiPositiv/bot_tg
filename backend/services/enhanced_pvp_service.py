from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import AsyncSessionLocal
from models.interactive_battle import InteractiveBattle, BattleModeEnum, BattlePhaseEnum
from models.user import User
from models.skill import UserSkill, SkillTypeEnum
from utils.formulas import GameFormulas
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, List
import random
import logging
import asyncio

logger = logging.getLogger(__name__)

class EnhancedPvPService:
    def __init__(self):
        pass
    
    async def create_interactive_pvp_battle(self, challenger_id: int, defender_id: int) -> Optional[InteractiveBattle]:
        """Create interactive PvP battle"""
        async with AsyncSessionLocal() as session:
            # Get both players
            challenger = await session.get(User, challenger_id)
            defender = await session.get(User, defender_id)
            
            if not challenger or not defender:
                return None
            
            # Check HP requirements
            if challenger.current_hp < challenger.hp * 0.3 or defender.current_hp < defender.hp * 0.3:
                return None
            
            # Create interactive battle
            battle = InteractiveBattle(
                mode=BattleModeEnum.pvp_interactive,
                phase=BattlePhaseEnum.monster_encounter,  # Waiting for acceptance
                player1_id=challenger_id,
                player2_id=defender_id,
                player1_hp=challenger.current_hp,
                player1_mana=challenger.current_mana,
                player2_hp=defender.current_hp,
                player2_mana=defender.current_mana
            )
            
            session.add(battle)
            await session.commit()
            await session.refresh(battle)
            
            logger.info(f"Interactive PvP created: {challenger_id} vs {defender_id}")
            return battle
    
    async def accept_interactive_pvp_battle(self, battle_id: int, defender_id: int) -> bool:
        """Accept interactive PvP battle"""
        async with AsyncSessionLocal() as session:
            battle = await session.get(InteractiveBattle, battle_id)
            if not battle or battle.player2_id != defender_id:
                return False
            
            if battle.phase != BattlePhaseEnum.monster_encounter:
                return False
            
            # Start first round
            battle.phase = BattlePhaseEnum.attack_selection
            battle.reset_round_choices()
            
            await session.commit()
            return True
    
    async def make_pvp_attack_choice(self, battle_id: int, player_id: int, attack_type: str) -> bool:
        """Make attack choice in PvP"""
        async with AsyncSessionLocal() as session:
            battle = await session.get(InteractiveBattle, battle_id)
            if not battle or battle.phase != BattlePhaseEnum.attack_selection:
                return False
            
            if attack_type not in ['precise', 'power', 'normal']:
                return False
            
            # Set choice based on player
            if battle.player1_id == player_id:
                battle.player1_attack_choice = attack_type
            elif battle.player2_id == player_id:
                battle.player2_attack_choice = attack_type
            else:
                return False
            
            # Check if both players made attack choice
            if battle.player1_attack_choice and battle.player2_attack_choice:
                battle.phase = BattlePhaseEnum.dodge_selection
            
            await session.commit()
            return True
    
    async def make_pvp_dodge_choice(self, battle_id: int, player_id: int, direction: str) -> bool:
        """Make dodge choice in PvP"""
        async with AsyncSessionLocal() as session:
            battle = await session.get(InteractiveBattle, battle_id)
            if not battle or battle.phase != BattlePhaseEnum.dodge_selection:
                return False
            
            if direction not in ['left', 'center', 'right']:
                return False
            
            # Set choice based on player
            if battle.player1_id == player_id:
                battle.player1_dodge_choice = direction
            elif battle.player2_id == player_id:
                battle.player2_dodge_choice = direction
            else:
                return False
            
            # Check if both players are ready
            if battle.both_players_ready():
                await self._calculate_pvp_round(battle, session)
            
            await session.commit()
            return True
    
    async def _calculate_pvp_round(self, battle: InteractiveBattle, session: AsyncSession):
        """Calculate PvP round with full mechanics"""
        battle.phase = BattlePhaseEnum.calculating
        
        # Get both players
        player1 = await session.get(User, battle.player1_id)
        player2 = await session.get(User, battle.player2_id)
        
        round_log = {
            'round': battle.current_round,
            'player1_attack_type': battle.player1_attack_choice,
            'player1_dodge': battle.player1_dodge_choice,
            'player2_attack_type': battle.player2_attack_choice,
            'player2_dodge': battle.player2_dodge_choice,
            'events': [],
            'skills_used': []
        }
        
        # Auto-cast skills for both players
        p1_skills = await self._auto_cast_pvp_skills(player1, battle, 'player1', session)
        p2_skills = await self._auto_cast_pvp_skills(player2, battle, 'player2', session)
        
        round_log['skills_used'] = {
            'player1': p1_skills,
            'player2': p2_skills
        }
        
        # Calculate attacks for both players
        # Player 1 attacks Player 2
        p1_damage = await self._calculate_pvp_attack(
            player1, player2, battle.player1_attack_choice, 
            battle.player2_dodge_choice, p1_skills
        )
        
        # Player 2 attacks Player 1
        p2_damage = await self._calculate_pvp_attack(
            player2, player1, battle.player2_attack_choice, 
            battle.player1_dodge_choice, p2_skills
        )
        
        # Apply damage and log results
        if p1_damage['damage'] > 0:
            battle.player2_hp = max(0, battle.player2_hp - p1_damage['damage'])
            round_log['events'].extend([f"[{player1.name}] " + event for event in p1_damage['events']])
        else:
            round_log['events'].append(f"[{player1.name}] Атака промахнулась!")
        
        if p2_damage['damage'] > 0:
            battle.player1_hp = max(0, battle.player1_hp - p2_damage['damage'])
            round_log['events'].extend([f"[{player2.name}] " + event for event in p2_damage['events']])
        else:
            round_log['events'].append(f"[{player2.name}] Атака промахнулась!")
        
        # Add round to log
        battle.add_to_battle_log(round_log)
        
        # Check for battle end
        if battle.player1_hp <= 0 or battle.player2_hp <= 0:
            await self._finish_pvp_battle(battle, player1, player2, session)
            return
        
        # Continue to next round
        battle.current_round += 1
        if battle.current_round > battle.max_rounds:
            # Timeout - higher HP wins
            await self._finish_pvp_battle_timeout(battle, player1, player2, session)
        else:
            # Start next round
            battle.phase = BattlePhaseEnum.attack_selection
            battle.reset_round_choices()
    
    async def _auto_cast_pvp_skills(self, player: User, battle: InteractiveBattle, 
                                   player_key: str, session: AsyncSession) -> List[dict]:
        """Auto-cast skills for PvP player"""
        # Get player's skills
        user_skills_result = await session.execute(
            select(UserSkill).where(UserSkill.user_id == player.id)
        )
        user_skills = user_skills_result.scalars().all()
        
        if not user_skills:
            return []
        
        skills_used = []
        current_mana = battle.player1_mana if player_key == 'player1' else battle.player2_mana
        current_hp = battle.player1_hp if player_key == 'player1' else battle.player2_hp
        
        # Sort skills by priority
        sorted_skills = sorted(user_skills, key=lambda x: x.skill.priority)
        
        for user_skill in sorted_skills:
            skill = user_skill.skill
            
            if current_mana < skill.mana_cost:
                continue
            
            should_use = False
            
            if skill.skill_type == SkillTypeEnum.heal and current_hp < player.hp * 0.5:
                should_use = True
            elif skill.skill_type == SkillTypeEnum.buff and battle.current_round <= 2:
                should_use = True
            elif skill.skill_type == SkillTypeEnum.attack and random.random() < 0.25:
                should_use = True
            
            if should_use:
                current_mana -= skill.mana_cost
                
                if player_key == 'player1':
                    battle.player1_mana = current_mana
                else:
                    battle.player2_mana = current_mana
                
                # Apply skill effects
                if skill.skill_type == SkillTypeEnum.heal:
                    heal_amount = skill.heal_amount
                    old_hp = current_hp
                    current_hp = min(current_hp + heal_amount, player.hp)
                    actual_heal = current_hp - old_hp
                    
                    if player_key == 'player1':
                        battle.player1_hp = current_hp
                    else:
                        battle.player2_hp = current_hp
                    
                    skills_used.append({
                        'name': skill.name,
                        'type': 'heal',
                        'effect': f'Восстановлено {actual_heal} HP'
                    })
                
                # Update usage stats
                user_skill.times_used += 1
                user_skill.last_used = datetime.utcnow()
        
        return skills_used
    
    async def _calculate_pvp_attack(self, attacker: User, defender: User, 
                                   attack_type: str, defender_dodge: str, skills_effects: List[dict]) -> dict:
        """Calculate PvP attack damage"""
        result = {'damage': 0, 'events': []}
        
        # Hit chance based on attack type
        hit_chance = {
            'precise': 0.9,
            'power': 0.7,
            'normal': 0.8
        }.get(attack_type, 0.8)
        
        # Random direction for attack
        attacker_direction = random.choice(['left', 'center', 'right'])
        
        # Check if attack hits
        direction_hit = (attacker_direction == defender_dodge)
        
        if direction_hit and random.random() < hit_chance:
            # Calculate damage
            base_damage = attacker.strength + int(attacker.agility * 0.5)
            
            # Apply attack type modifiers
            if attack_type == 'power':
                base_damage = int(base_damage * 1.3)
            elif attack_type == 'precise':
                base_damage = int(base_damage * 1.1)
            
            defense = int(defender.armor * 0.8)
            damage = max(base_damage - defense, int(base_damage * 0.1))
            
            # Check for critical hit
            crit_chance = GameFormulas.critical_hit_chance(attacker.agility)
            if attack_type == 'precise':
                crit_chance *= 1.5
            
            if random.random() < crit_chance:
                damage = int(damage * 1.5)
                result['events'].append(f"🔥 Критический {attack_type} удар!")
            
            # Check for perfect dodge (defender's last chance)
            perfect_dodge_chance = min(defender.agility / 500.0, 0.07)
            if random.random() < perfect_dodge_chance:
                damage = 0
                result['events'].append("💨 Мастерское уклонение!")
            else:
                result['damage'] = damage
                result['events'].append(f"⚔️ {attack_type.title()} удар нанёс {damage} урона")
        
        else:
            # Missed, check for glancing hit
            if GameFormulas.is_critical_hit(attacker.agility) and random.random() < 0.15:
                result['damage'] = 2
                result['events'].append("✨ Промах, но мастерство позволило нанести 2 урона!")
            else:
                result['events'].append(f"💨 {attack_type.title()} удар промахнулся!")
        
        return result
    
    async def _finish_pvp_battle(self, battle: InteractiveBattle, player1: User, 
                                player2: User, session: AsyncSession):
        """Finish PvP battle with winner determination"""
        battle.phase = BattlePhaseEnum.finished
        battle.finished_at = datetime.utcnow()
        
        # Determine winner
        if battle.player1_hp <= 0:
            winner = player2
            loser = player1
        else:
            winner = player1
            loser = player2
        
        battle.winner_id = winner.id
        
        # Calculate rewards
        winner_stats = {
            'strength': winner.strength,
            'armor': winner.armor,
            'agility': winner.agility,
            'hp': winner.hp,
            'mana': winner.mana
        }
        loser_stats = {
            'strength': loser.strength,
            'armor': loser.armor,
            'agility': loser.agility,
            'hp': loser.hp,
            'mana': loser.mana
        }
        
        rewards = GameFormulas.calculate_battle_rewards(winner_stats, loser_stats)
        battle.exp_gained = rewards['experience']
        battle.money_gained = rewards['money']
        
        # Update player stats
        winner.money += battle.money_gained
        if winner.id == player1.id:
            player1.current_hp = battle.player1_hp
            player1.current_mana = battle.player1_mana
            player1.pvp_wins += 1
            player2.current_hp = max(1, battle.player2_hp)
            player2.current_mana = battle.player2_mana
            player2.pvp_losses += 1
        else:
            player2.current_hp = battle.player2_hp
            player2.current_mana = battle.player2_mana
            player2.pvp_wins += 1
            player1.current_hp = max(1, battle.player1_hp)
            player1.current_mana = battle.player1_mana
            player1.pvp_losses += 1
        
        # Add experience
        from services.user_service import UserService
        user_service = UserService()
        await user_service.add_experience(winner.id, battle.exp_gained)
        
        battle.add_to_battle_log({
            'round': battle.current_round,
            'result': 'victory',
            'winner': winner.name,
            'message': f"Победа {winner.name}! Получено {battle.exp_gained} опыта и {battle.money_gained} золота"
        })
    
    async def _finish_pvp_battle_timeout(self, battle: InteractiveBattle, player1: User, 
                                        player2: User, session: AsyncSession):
        """Finish PvP battle due to timeout"""
        battle.phase = BattlePhaseEnum.finished
        battle.finished_at = datetime.utcnow()
        
        # Winner is player with higher HP
        if battle.player1_hp > battle.player2_hp:
            winner = player1
            loser = player2
        elif battle.player2_hp > battle.player1_hp:
            winner = player2
            loser = player1
        else:
            # Tie - no winner
            battle.add_to_battle_log({
                'round': battle.current_round,
                'result': 'draw',
                'message': 'Время истекло! Ничья - оба игрока остались с равным HP!'
            })
            return
        
        battle.winner_id = winner.id
        
        # Reduced rewards for timeout victory
        battle.exp_gained = 15
        battle.money_gained = 5
        
        winner.money += battle.money_gained
        
        # Update stats
        if winner.id == player1.id:
            player1.pvp_wins += 1
            player2.pvp_losses += 1
        else:
            player2.pvp_wins += 1
            player1.pvp_losses += 1
        
        from services.user_service import UserService
        user_service = UserService()
        await user_service.add_experience(winner.id, battle.exp_gained)
        
        battle.add_to_battle_log({
            'round': battle.current_round,
            'result': 'timeout_victory',
            'winner': winner.name,
            'message': f"Победа по таймауту: {winner.name}! Получено {battle.exp_gained} опыта"
        })
    
    async def check_pvp_timeout(self, battle_id: int) -> bool:
        """Check and handle PvP battle timeout"""
        async with AsyncSessionLocal() as session:
            battle = await session.get(InteractiveBattle, battle_id)
            if not battle or not battle.round_start_time:
                return False
            
            timeout_time = battle.round_start_time + timedelta(seconds=battle.round_timeout)
            if datetime.utcnow() > timeout_time:
                # Handle timeout - auto-select normal attack and center dodge
                if battle.phase == BattlePhaseEnum.attack_selection:
                    if not battle.player1_attack_choice:
                        battle.player1_attack_choice = 'normal'
                    if not battle.player2_attack_choice:
                        battle.player2_attack_choice = 'normal'
                    battle.phase = BattlePhaseEnum.dodge_selection
                
                elif battle.phase == BattlePhaseEnum.dodge_selection:
                    if not battle.player1_dodge_choice:
                        battle.player1_dodge_choice = 'center'
                    if not battle.player2_dodge_choice:
                        battle.player2_dodge_choice = 'center'
                    
                    # Calculate round with timeout choices
                    await self._calculate_pvp_round(battle, session)
                
                await session.commit()
                return True
            
            return False
    
    async def get_battle(self, battle_id: int) -> Optional[InteractiveBattle]:
        """Get PvP battle by ID"""
        async with AsyncSessionLocal() as session:
            return await session.get(InteractiveBattle, battle_id)