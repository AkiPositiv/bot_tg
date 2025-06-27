from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import AsyncSessionLocal
from models.battle import Battle, BattleTypeEnum, BattleStatusEnum
from models.user import User
from utils.formulas import GameFormulas
from typing import Dict, List, Optional
import logging
import random
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class BattleService:
    def __init__(self):
        pass
    
    async def create_pvp_battle(self, challenger_id: int, defender_id: int) -> Battle:
        """Create PvP battle"""
        async with AsyncSessionLocal() as session:
            battle = Battle(
                battle_type=BattleTypeEnum.pvp,
                challenger_id=challenger_id,
                defender_id=defender_id,
                status=BattleStatusEnum.pending
            )
            session.add(battle)
            await session.commit()
            await session.refresh(battle)
            return battle
    
    async def accept_battle(self, battle_id: int) -> bool:
        """Accept battle challenge"""
        async with AsyncSessionLocal() as session:
            battle = await session.get(Battle, battle_id)
            if not battle or battle.status != BattleStatusEnum.pending:
                return False
            
            battle.status = BattleStatusEnum.active
            battle.started_at = datetime.utcnow()
            await session.commit()
            
            # Process battle in background
            asyncio.create_task(self.process_battle(battle_id))
            return True
    
    async def process_battle(self, battle_id: int) -> Battle:
        """Process entire battle"""
        async with AsyncSessionLocal() as session:
            battle = await session.get(Battle, battle_id)
            if not battle:
                return None
            
            # Get participants
            challenger = await session.get(User, battle.challenger_id)
            defender = await session.get(User, battle.defender_id)
            
            if not challenger or not defender:
                battle.status = BattleStatusEnum.cancelled
                await session.commit()
                return battle
            
            # Battle simulation
            battle_log = []
            turn = 1
            
            # Create battle snapshots
            challenger_hp = challenger.current_hp
            defender_hp = defender.current_hp
            challenger_mana = challenger.current_mana
            defender_mana = defender.current_mana
            
            while turn <= 50 and challenger_hp > 0 and defender_hp > 0:
                # Determine who attacks first based on agility
                if challenger.agility >= defender.agility:
                    attacker, defender_target = challenger, defender
                    attacker_hp, defender_hp_ref = challenger_hp, 'defender_hp'
                else:
                    attacker, defender_target = defender, challenger
                    attacker_hp, defender_hp_ref = defender_hp, 'challenger_hp'
                
                # Calculate damage
                attacker_stats = {
                    'strength': attacker.strength,
                    'agility': attacker.agility
                }
                defender_stats = {
                    'armor': defender_target.armor,
                    'agility': defender_target.agility
                }
                
                # Check for dodge
                if GameFormulas.is_dodge(defender_target.agility):
                    battle_log.append({
                        'turn': turn,
                        'attacker': attacker.name,
                        'action': 'attack',
                        'result': 'dodged',
                        'damage': 0
                    })
                else:
                    # Calculate damage
                    damage = GameFormulas.calculate_damage(attacker_stats, defender_stats)
                    
                    # Check for critical hit
                    if GameFormulas.is_critical_hit(attacker.agility):
                        damage = int(damage * 1.5)
                        result = 'critical'
                    else:
                        result = 'hit'
                    
                    # Apply damage
                    if attacker == challenger:
                        defender_hp = max(0, defender_hp - damage)
                    else:
                        challenger_hp = max(0, challenger_hp - damage)
                    
                    battle_log.append({
                        'turn': turn,
                        'attacker': attacker.name,
                        'action': 'attack',
                        'result': result,
                        'damage': damage,
                        'challenger_hp': challenger_hp,
                        'defender_hp': defender_hp
                    })
                
                turn += 1
            
            # Determine winner
            if challenger_hp <= 0:
                winner = defender
                loser = challenger
            elif defender_hp <= 0:
                winner = challenger
                loser = defender
            else:
                # Timeout - higher HP wins
                if challenger_hp > defender_hp:
                    winner = challenger
                    loser = defender
                else:
                    winner = defender
                    loser = challenger
            
            # Update battle result
            battle.winner_id = winner.id
            battle.total_turns = turn - 1
            battle.set_damage_log(battle_log)
            battle.status = BattleStatusEnum.finished
            battle.finished_at = datetime.utcnow()
            
            # Calculate and apply rewards
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
            
            # Update winner stats
            winner.experience += rewards['experience']
            winner.money += rewards['money']
            
            # Update battle statistics
            if winner == challenger:
                challenger.pvp_wins += 1
                defender.pvp_losses += 1
            else:
                defender.pvp_wins += 1
                challenger.pvp_losses += 1
            
            await session.commit()
            
            logger.info(f"Battle {battle_id} finished. Winner: {winner.name}")
            return battle
    
    async def get_battle(self, battle_id: int) -> Optional[Battle]:
        """Get battle by ID"""
        async with AsyncSessionLocal() as session:
            return await session.get(Battle, battle_id)
    
    async def get_pending_battles(self, user_id: int) -> List[Battle]:
        """Get pending battles for user"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Battle).where(
                    Battle.defender_id == user_id,
                    Battle.status == BattleStatusEnum.pending
                )
            )
            return result.scalars().all()