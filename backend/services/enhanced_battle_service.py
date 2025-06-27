from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import AsyncSessionLocal
from models.interactive_battle import InteractiveBattle, BattleModeEnum, BattlePhaseEnum
from models.monster import Monster
from models.user import User
from models.skill import UserSkill, SkillTypeEnum
from utils.formulas import GameFormulas
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, List
import random
import logging
import json

logger = logging.getLogger(__name__)

class EnhancedBattleService:
    def __init__(self):
        pass
    
    async def start_pve_encounter(self, player_id: int) -> Optional[InteractiveBattle]:
        """Start enhanced PvE encounter with flee chance calculation"""
        async with AsyncSessionLocal() as session:
            player = await session.get(User, player_id)
            if not player:
                return None
            
            if player.current_hp < player.hp * 0.3:
                return None
            
            # Generate random monster
            monster = Monster.generate_random_monster(player.level)
            
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
            
            logger.info(f"Enhanced PvE encounter: Player {player_id} vs {monster.name}")
            return battle
    
    async def attempt_flee(self, battle_id: int, player_id: int) -> Tuple[bool, str, int]:
        """
        Attempt to flee from battle with chance calculation
        Returns: (success, message, damage_taken)
        """
        async with AsyncSessionLocal() as session:
            battle = await session.get(InteractiveBattle, battle_id)
            if not battle or battle.player1_id != player_id:
                return False, "Битва не найдена", 0
            
            player = await session.get(User, battle.player1_id)
            monster_data = battle.get_monster_data()
            
            # Calculate flee chance based on agility and level difference
            level_diff = player.level - monster_data['level']
            base_chance = 0.6  # 60% base chance
            agility_bonus = (player.agility - 10) * 0.02  # 2% per agility point above 10
            level_bonus = level_diff * 0.05  # 5% per level difference
            
            flee_chance = max(0.1, min(0.9, base_chance + agility_bonus + level_bonus))
            
            if random.random() < flee_chance:
                # Successful flee
                battle.phase = BattlePhaseEnum.finished
                battle.finished_at = datetime.utcnow()
                battle.add_to_battle_log({
                    'round': battle.current_round,
                    'action': 'flee_success',
                    'player': 'player1',
                    'message': f'Успешный побег! (Шанс: {flee_chance:.1%})'
                })
                
                await session.commit()
                return True, f"🏃‍♂️ Успешный побег! (Шанс был {flee_chance:.1%})", 0
            
            else:
                # Failed flee - monster gets one free attack
                monster_damage = self._calculate_monster_attack(monster_data, player)
                
                battle.player1_hp = max(0, battle.player1_hp - monster_damage)
                player.current_hp = battle.player1_hp
                
                battle.add_to_battle_log({
                    'round': battle.current_round,
                    'action': 'flee_failed',
                    'player': 'player1',
                    'damage_taken': monster_damage,
                    'message': f'Неудачный побег! Монстр нанёс {monster_damage} урона'
                })
                
                # Can't flee again from this monster
                battle.phase = BattlePhaseEnum.attack_selection
                battle.reset_round_choices()
                
                await session.commit()
                return False, f"❌ Побег не удался! Монстр нанёс {monster_damage} урона. Больше нельзя убежать от этого врага!", monster_damage
    
    def _calculate_monster_attack(self, monster_data: dict, player: User) -> int:
        """Calculate monster's free attack damage"""
        base_damage = monster_data['strength'] + int(monster_data['agility'] * 0.5)
        defense = int(player.armor * 0.8)
        return max(base_damage - defense, int(base_damage * 0.1))
    
    async def make_attack_choice(self, battle_id: int, player_id: int, attack_type: str) -> bool:
        """
        Make attack type choice with new options:
        - precise: точный удар (normal damage, higher crit chance)
        - power: мощный удар (higher damage, lower accuracy)
        - normal: обычная атака (balanced)
        """
        async with AsyncSessionLocal() as session:
            battle = await session.get(InteractiveBattle, battle_id)
            if not battle or battle.phase != BattlePhaseEnum.attack_selection:
                return False
            
            if attack_type not in ['precise', 'power', 'normal']:
                return False
            
            if battle.player1_id == player_id:
                battle.player1_attack_choice = attack_type
            elif battle.player2_id == player_id:
                battle.player2_attack_choice = attack_type
            else:
                return False
            
            # For PvE, auto-proceed to direction selection
            if battle.mode == BattleModeEnum.pve_interactive:
                battle.phase = BattlePhaseEnum.dodge_selection
            
            await session.commit()
            return True
    
    async def make_direction_choice(self, battle_id: int, player_id: int, direction: str) -> bool:
        """Make direction choice for dodge"""
        async with AsyncSessionLocal() as session:
            battle = await session.get(InteractiveBattle, battle_id)
            if not battle or battle.phase != BattlePhaseEnum.dodge_selection:
                return False
            
            if direction not in ['left', 'center', 'right']:
                return False
            
            if battle.player1_id == player_id:
                battle.player1_dodge_choice = direction
            elif battle.player2_id == player_id:
                battle.player2_dodge_choice = direction
            else:
                return False
            
            # Check if ready to calculate
            if battle.both_players_ready():
                await self._calculate_enhanced_round(battle, session)
            
            await session.commit()
            return True
    
    async def _calculate_enhanced_round(self, battle: InteractiveBattle, session: AsyncSession):
        """Enhanced round calculation with skills and improved mechanics"""
        battle.phase = BattlePhaseEnum.calculating
        
        player = await session.get(User, battle.player1_id)
        
        if battle.mode == BattleModeEnum.pve_interactive:
            await self._calculate_enhanced_pve_round(battle, player, session)
    
    async def _calculate_enhanced_pve_round(self, battle: InteractiveBattle, player: User, session: AsyncSession):
        """Enhanced PvE round with skills and improved mechanics"""
        monster_data = battle.get_monster_data()
        if not monster_data:
            return
        
        round_log = {
            'round': battle.current_round,
            'player_attack_type': battle.player1_attack_choice,
            'player_dodge': battle.player1_dodge_choice,
            'events': [],
            'skills_used': []
        }
        
        # Auto-cast skills before combat
        skills_effects = await self._auto_cast_skills(player, battle, session)
        round_log['skills_used'] = skills_effects
        
        # Generate monster choices
        monster_attack_direction = random.choice(['left', 'center', 'right'])
        monster_dodge_direction = random.choice(['left', 'center', 'right'])
        
        round_log['monster_attack'] = monster_attack_direction
        round_log['monster_dodge'] = monster_dodge_direction
        
        # Calculate player attack based on type
        player_damage = await self._calculate_enhanced_player_attack(
            player, monster_data, battle.player1_attack_choice, 
            monster_dodge_direction, skills_effects
        )
        
        # Log player attack results
        if player_damage > 0:
            round_log['events'].extend(player_damage['events'])
        else:
            round_log['events'].append("💨 Игрок промахнулся!")
        
        # Apply damage to monster
        actual_damage = player_damage.get('damage', 0)
        battle.monster_hp = max(0, battle.monster_hp - actual_damage)
        
        # Check if monster is dead
        if battle.monster_hp <= 0:
            await self._finish_enhanced_battle(battle, player, monster_data, session, round_log)
            return
        
        # Calculate monster attack with perfect dodge chance
        monster_damage = await self._calculate_enhanced_monster_attack(
            monster_data, player, monster_attack_direction, battle.player1_dodge_choice
        )
        
        if monster_damage > 0:
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
            player.current_hp = 1
            return
        
        # Continue to next round
        battle.current_round += 1
        if battle.current_round > battle.max_rounds:
            battle.phase = BattlePhaseEnum.finished
            battle.finished_at = datetime.utcnow()
            battle.add_to_battle_log({
                'round': battle.current_round,
                'result': 'timeout',
                'message': 'Время боя истекло!'
            })
        else:
            battle.phase = BattlePhaseEnum.attack_selection
            battle.reset_round_choices()
    
    async def _auto_cast_skills(self, player: User, battle: InteractiveBattle, session: AsyncSession) -> List[dict]:
        """Auto-cast skills based on priority system"""
        # Get player's skills
        user_skills_result = await session.execute(
            select(UserSkill).where(UserSkill.user_id == player.id)
        )
        user_skills = user_skills_result.scalars().all()
        
        if not user_skills:
            return []
        
        skills_used = []
        current_mana = battle.player1_mana
        
        # Sort skills by priority (heal > buff > debuff > defense > attack)
        sorted_skills = sorted(user_skills, key=lambda x: x.skill.priority)
        
        for user_skill in sorted_skills:
            skill = user_skill.skill
            
            # Check if skill can be used
            if current_mana < skill.mana_cost:
                continue
            
            # Check skill conditions
            should_use = False
            
            if skill.skill_type == SkillTypeEnum.heal and battle.player1_hp < player.hp * 0.5:
                should_use = True
            elif skill.skill_type == SkillTypeEnum.buff and battle.current_round <= 2:
                should_use = True
            elif skill.skill_type == SkillTypeEnum.attack and random.random() < 0.3:
                should_use = True
            
            if should_use:
                # Use skill
                current_mana -= skill.mana_cost
                battle.player1_mana = current_mana
                
                # Apply skill effects
                if skill.skill_type == SkillTypeEnum.heal:
                    heal_amount = skill.heal_amount
                    old_hp = battle.player1_hp
                    battle.player1_hp = min(battle.player1_hp + heal_amount, player.hp)
                    actual_heal = battle.player1_hp - old_hp
                    
                    skills_used.append({
                        'name': skill.name,
                        'type': 'heal',
                        'effect': f'Восстановлено {actual_heal} HP'
                    })
                
                elif skill.skill_type == SkillTypeEnum.buff:
                    skills_used.append({
                        'name': skill.name,
                        'type': 'buff',
                        'effect': f'Наложен бафф: {skill.status_effect or "Усиление"}'
                    })
                
                # Update usage stats
                user_skill.times_used += 1
                user_skill.last_used = datetime.utcnow()
        
        return skills_used
    
    async def _calculate_enhanced_player_attack(self, player: User, monster_data: dict, 
                                               attack_type: str, monster_dodge: str, skills_effects: List[dict]) -> dict:
        """Calculate enhanced player attack with different attack types"""
        result = {'damage': 0, 'events': []}
        
        # Determine if attack hits based on type
        hit_chance = {
            'precise': 0.9,   # 90% hit chance
            'power': 0.7,     # 70% hit chance  
            'normal': 0.8     # 80% hit chance
        }.get(attack_type, 0.8)
        
        # Random direction for attack
        player_attack_dir = random.choice(['left', 'center', 'right'])
        
        # Check if attack hits direction-wise
        direction_hit = (player_attack_dir == monster_dodge)
        
        if direction_hit and random.random() < hit_chance:
            # Direct hit
            base_damage = player.strength + int(player.agility * 0.5)
            
            # Apply attack type modifiers
            if attack_type == 'power':
                base_damage = int(base_damage * 1.3)  # 30% more damage
            elif attack_type == 'precise':
                base_damage = int(base_damage * 1.1)  # 10% more damage
            
            defense = int(monster_data['armor'] * 0.8)
            damage = max(base_damage - defense, int(base_damage * 0.1))
            
            # Check for critical hit (enhanced chance for precise attacks)
            crit_chance = GameFormulas.critical_hit_chance(player.agility)
            if attack_type == 'precise':
                crit_chance *= 1.5  # 50% higher crit chance for precise attacks
            
            if random.random() < crit_chance:
                damage = int(damage * 1.5)
                result['events'].append(f"🔥 Критический {attack_type} удар!")
            
            result['damage'] = damage
            result['events'].append(f"⚔️ {attack_type.title()} удар нанёс {damage} урона")
            
        else:
            # Missed, but check for glancing hit
            if GameFormulas.is_critical_hit(player.agility) and random.random() < 0.15:
                result['damage'] = 2
                result['events'].append("✨ Промах, но мастерство позволило нанести 2 урона!")
            else:
                result['events'].append(f"💨 {attack_type.title()} удар промахнулся!")
        
        return result
    
    async def _calculate_enhanced_monster_attack(self, monster_data: dict, player: User, 
                                               monster_direction: str, player_dodge: str) -> int:
        """Calculate enhanced monster attack with perfect dodge"""
        # Check direction hit
        if monster_direction != player_dodge:
            return 0  # Monster missed
        
        # Monster hit, calculate damage
        base_damage = monster_data['strength'] + int(monster_data['agility'] * 0.5)
        defense = int(player.armor * 0.8)
        damage = max(base_damage - defense, int(base_damage * 0.1))
        
        # Check for perfect dodge (very low chance)
        perfect_dodge_chance = min(player.agility / 500.0, 0.07)  # Max 7%
        if random.random() < perfect_dodge_chance:
            return 0  # Perfect dodge
        
        return damage
    
    async def _finish_enhanced_battle(self, battle: InteractiveBattle, player: User, 
                                    monster_data: dict, session: AsyncSession, round_log: dict):
        """Finish enhanced battle with proper rewards"""
        battle.phase = BattlePhaseEnum.finished
        battle.finished_at = datetime.utcnow()
        battle.winner_id = player.id
        battle.exp_gained = monster_data['exp_reward']
        battle.money_gained = monster_data['money_reward']
        
        round_log['events'].append(f"🏆 {monster_data['name']} повержен!")
        battle.add_to_battle_log(round_log)
        
        battle.add_to_battle_log({
            'round': battle.current_round,
            'result': 'victory',
            'message': f"Победа! Получено {battle.exp_gained} опыта и {battle.money_gained} золота"
        })
        
        # Update player stats
        player.current_hp = battle.player1_hp
        player.current_mana = battle.player1_mana
        player.money += battle.money_gained
        player.pve_wins += 1
        
        # Add experience
        from services.user_service import UserService
        user_service = UserService()
        await user_service.add_experience(player.id, battle.exp_gained)
    
    async def get_battle(self, battle_id: int) -> Optional[InteractiveBattle]:
        """Get battle by ID"""
        async with AsyncSessionLocal() as session:
            return await session.get(InteractiveBattle, battle_id)