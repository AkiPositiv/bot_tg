from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import AsyncSessionLocal
from models.kingdom_war import KingdomWar, WarParticipation, WarStatusEnum, WarTypeEnum
from models.user import User, KingdomEnum
from services.user_service import UserService
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
import pytz
import json

logger = logging.getLogger(__name__)

class KingdomWarService:
    def __init__(self):
        self.user_service = UserService()
        # Ташкентский timezone
        self.tashkent_tz = pytz.timezone('Asia/Tashkent')
        # Время войн: 8:00, 13:00, 18:00 по Ташкентскому времени
        self.war_times = [8, 13, 18]
    
    async def schedule_daily_wars(self, date: datetime):
        """Schedule wars for a specific date"""
        async with AsyncSessionLocal() as session:
            for hour in self.war_times:
                # Create war time in Tashkent timezone
                war_time = self.tashkent_tz.localize(
                    datetime.combine(date.date(), datetime.min.time().replace(hour=hour))
                )
                
                # Convert to UTC for storage
                war_time_utc = war_time.astimezone(pytz.UTC)
                
                # Check if war already scheduled for this time
                existing = await session.scalar(
                    select(KingdomWar).where(
                        KingdomWar.scheduled_time == war_time_utc,
                        KingdomWar.status == WarStatusEnum.scheduled
                    )
                )
                
                if not existing:
                    # Create wars for each kingdom as potential defender
                    for kingdom in KingdomEnum:
                        war = KingdomWar(
                            scheduled_time=war_time_utc,
                            defending_kingdom=kingdom.value,
                            status=WarStatusEnum.scheduled
                        )
                        session.add(war)
            
            await session.commit()
            logger.info(f"Scheduled wars for {date.date()}")
    
    async def join_attack_squad(self, user_id: int, target_kingdom: str, war_time: datetime) -> Tuple[bool, str]:
        """Join attack squad for specific war"""
        async with AsyncSessionLocal() as session:
            # Get user
            user = await session.get(User, user_id)
            if not user:
                return False, "Пользователь не найден"
            
            # Can't attack own kingdom
            if user.kingdom.value == target_kingdom:
                return False, "Нельзя атаковать своё королевство"
            
            # Find the war
            war = await session.scalar(
                select(KingdomWar).where(
                    and_(
                        KingdomWar.defending_kingdom == target_kingdom,
                        KingdomWar.scheduled_time == war_time,
                        KingdomWar.status == WarStatusEnum.scheduled
                    )
                )
            )
            
            if not war:
                return False, "Война не найдена"
            
            # Check if already participating
            existing = await session.scalar(
                select(WarParticipation).where(
                    and_(
                        WarParticipation.war_id == war.id,
                        WarParticipation.user_id == user_id
                    )
                )
            )
            
            if existing:
                return False, "Вы уже участвуете в этой войне"
            
            # Add to attack squad
            attack_squads = war.get_attack_squads()
            user_kingdom = user.kingdom.value
            
            if user_kingdom not in attack_squads:
                attack_squads[user_kingdom] = []
            
            attack_squads[user_kingdom].append(user_id)
            war.set_attack_squads(attack_squads)
            
            # Add attacking kingdom to list
            attacking_kingdoms = war.get_attacking_kingdoms()
            if user_kingdom not in attacking_kingdoms:
                attacking_kingdoms.append(user_kingdom)
                war.set_attacking_kingdoms(attacking_kingdoms)
            
            # Create participation record
            participation = WarParticipation(
                war_id=war.id,
                user_id=user_id,
                kingdom=user_kingdom,
                role='attacker'
            )
            
            # Store player stats
            player_stats = {
                'strength': user.strength,
                'armor': user.armor,
                'hp': user.hp,
                'agility': user.agility,
                'mana': user.mana,
                'level': user.level
            }
            participation.set_player_stats(player_stats)
            
            session.add(participation)
            await session.commit()
            
            logger.info(f"User {user_id} joined attack on {target_kingdom}")
            return True, f"Вы присоединились к атаке на {target_kingdom}"
    
    async def join_defense_squad(self, user_id: int, war_time: datetime) -> Tuple[bool, str]:
        """Join defense squad for own kingdom"""
        async with AsyncSessionLocal() as session:
            # Get user
            user = await session.get(User, user_id)
            if not user:
                return False, "Пользователь не найден"
            
            # Find the war for user's kingdom
            war = await session.scalar(
                select(KingdomWar).where(
                    and_(
                        KingdomWar.defending_kingdom == user.kingdom.value,
                        KingdomWar.scheduled_time == war_time,
                        KingdomWar.status == WarStatusEnum.scheduled
                    )
                )
            )
            
            if not war:
                return False, "Война не найдена"
            
            # Check if already participating
            existing = await session.scalar(
                select(WarParticipation).where(
                    and_(
                        WarParticipation.war_id == war.id,
                        WarParticipation.user_id == user_id
                    )
                )
            )
            
            if existing:
                return False, "Вы уже участвуете в защите"
            
            # Add to defense squad
            defense_squad = war.get_defense_squad()
            defense_squad.append(user_id)
            war.set_defense_squad(defense_squad)
            
            # Create participation record
            participation = WarParticipation(
                war_id=war.id,
                user_id=user_id,
                kingdom=user.kingdom.value,
                role='defender'
            )
            
            # Store player stats
            player_stats = {
                'strength': user.strength,
                'armor': user.armor,
                'hp': user.hp,
                'agility': user.agility,
                'mana': user.mana,
                'level': user.level
            }
            participation.set_player_stats(player_stats)
            
            session.add(participation)
            await session.commit()
            
            logger.info(f"User {user_id} joined defense of {user.kingdom.value}")
            return True, "Вы присоединились к защите своего королевства"
    
    async def start_war(self, war_id: int) -> bool:
        """Start a scheduled war"""
        async with AsyncSessionLocal() as session:
            war = await session.get(KingdomWar, war_id)
            if not war or war.status != WarStatusEnum.scheduled:
                return False
            
            # Check if there are attackers
            attacking_kingdoms = war.get_attacking_kingdoms()
            if not attacking_kingdoms:
                # No attackers, cancel war
                war.status = WarStatusEnum.finished
                war.finished_at = datetime.utcnow()
                await session.commit()
                return False
            
            war.status = WarStatusEnum.active
            war.started_at = datetime.utcnow()
            
            # Calculate total stats for each attacking kingdom
            await self._calculate_kingdom_stats(war, session)
            
            # Calculate defense buff based on number of attacking kingdoms
            num_attacking = len(attacking_kingdoms)
            if num_attacking > 1:
                war.defense_buff = 1.3  # 30% defense buff
            else:
                war.defense_buff = 1.0
            
            await session.commit()
            
            # Process the war
            await self._process_war_battles(war, session)
            
            return True
    
    async def _calculate_kingdom_stats(self, war: KingdomWar, session: AsyncSession):
        """Calculate total stats for each kingdom"""
        attack_squads = war.get_attack_squads()
        total_attack_stats = {}
        
        # Calculate attack stats for each kingdom
        for kingdom, player_ids in attack_squads.items():
            kingdom_stats = {
                'total_strength': 0,
                'total_armor': 0,
                'total_hp': 0,
                'total_agility': 0,
                'total_mana': 0,
                'player_count': len(player_ids)
            }
            
            # Get stats from participation records
            participations = await session.execute(
                select(WarParticipation).where(
                    and_(
                        WarParticipation.war_id == war.id,
                        WarParticipation.user_id.in_(player_ids),
                        WarParticipation.role == 'attacker'
                    )
                )
            )
            
            for participation in participations.scalars():
                stats = participation.get_player_stats()
                kingdom_stats['total_strength'] += stats.get('strength', 0)
                kingdom_stats['total_armor'] += stats.get('armor', 0)
                kingdom_stats['total_hp'] += stats.get('hp', 0)
                kingdom_stats['total_agility'] += stats.get('agility', 0)
                kingdom_stats['total_mana'] += stats.get('mana', 0)
            
            total_attack_stats[kingdom] = kingdom_stats
        
        war.set_total_attack_stats(total_attack_stats)
        
        # Calculate defense stats
        defense_squad = war.get_defense_squad()
        defense_stats = {
            'total_strength': 0,
            'total_armor': 0,
            'total_hp': 0,
            'total_agility': 0,
            'total_mana': 0,
            'player_count': len(defense_squad)
        }
        
        if defense_squad:
            defense_participations = await session.execute(
                select(WarParticipation).where(
                    and_(
                        WarParticipation.war_id == war.id,
                        WarParticipation.user_id.in_(defense_squad),
                        WarParticipation.role == 'defender'
                    )
                )
            )
            
            for participation in defense_participations.scalars():
                stats = participation.get_player_stats()
                defense_stats['total_strength'] += stats.get('strength', 0)
                defense_stats['total_armor'] += stats.get('armor', 0)
                defense_stats['total_hp'] += stats.get('hp', 0)
                defense_stats['total_agility'] += stats.get('agility', 0)
                defense_stats['total_mana'] += stats.get('mana', 0)
        
        war.set_defense_stats(defense_stats)
    
    async def _process_war_battles(self, war: KingdomWar, session: AsyncSession):
        """Process all battles in the war"""
        attack_stats = war.get_total_attack_stats()
        defense_stats = war.get_defense_stats()
        
        # Sort attacking kingdoms by total stats (weakest first)
        sorted_attackers = sorted(
            attack_stats.items(),
            key=lambda x: x[1]['total_strength'] + x[1]['total_armor'] + x[1]['total_agility']
        )
        
        # Apply defense buff
        buffed_defense_stats = defense_stats.copy()
        buffed_defense_stats['total_armor'] = int(defense_stats['total_armor'] * war.defense_buff)
        
        money_transfers = {}
        battle_results = []
        current_defense_hp = buffed_defense_stats['total_hp']
        
        # Process attacks in order (weakest to strongest)
        for kingdom, kingdom_stats in sorted_attackers:
            if current_defense_hp <= 0:
                # Defense already broken, this kingdom gets nothing
                battle_results.append({
                    'attacker': kingdom,
                    'defender': war.defending_kingdom,
                    'result': 'too_late',
                    'message': f'{kingdom} опоздало - город уже разграблен!'
                })
                continue
            
            # Calculate battle outcome
            attack_power = kingdom_stats['total_strength'] + kingdom_stats['total_agility']
            defense_power = buffed_defense_stats['total_strength'] + buffed_defense_stats['total_agility']
            
            # Damage calculation
            damage_to_defense = max(attack_power - buffed_defense_stats['total_armor'], attack_power * 0.1)
            damage_to_attacker = max(defense_power - kingdom_stats['total_armor'], defense_power * 0.1)
            
            current_defense_hp -= damage_to_defense
            
            if current_defense_hp <= 0:
                # Attacker breaks through defense
                battle_results.append({
                    'attacker': kingdom,
                    'defender': war.defending_kingdom,
                    'result': 'victory',
                    'damage_dealt': damage_to_defense,
                    'message': f'{kingdom} сломало защиту {war.defending_kingdom}!'
                })
                
                # Calculate money transfer (40% of defenders' money)
                money_to_transfer = await self._calculate_money_transfer(war, kingdom, session)
                money_transfers[kingdom] = money_to_transfer
                
            else:
                # Defense holds
                battle_results.append({
                    'attacker': kingdom,
                    'defender': war.defending_kingdom,
                    'result': 'defeat',
                    'damage_dealt': damage_to_defense,
                    'damage_received': damage_to_attacker,
                    'message': f'{kingdom} не смогло сломать защиту {war.defending_kingdom}'
                })
            
            # Restore defense HP to full for next wave
            current_defense_hp = buffed_defense_stats['total_hp']
        
        # Store results
        war.battle_results = json.dumps(battle_results)
        war.set_money_transferred(money_transfers)
        
        # Apply money transfers and experience
        await self._apply_war_rewards(war, session)
        
        # Finish war
        war.status = WarStatusEnum.finished
        war.finished_at = datetime.utcnow()
        await session.commit()
        
        logger.info(f"War {war.id} finished with results: {len(battle_results)} battles")
    
    async def _calculate_money_transfer(self, war: KingdomWar, winning_kingdom: str, session: AsyncSession) -> int:
        """Calculate money to transfer from defenders to attackers"""
        # Get all defenders
        defense_squad = war.get_defense_squad()
        
        if not defense_squad:
            return 0
        
        # Calculate 40% of total money from all defenders
        total_money_taken = 0
        
        for user_id in defense_squad:
            user = await session.get(User, user_id)
            if user:
                money_lost = int(user.money * 0.4)
                user.money -= money_lost
                total_money_taken += money_lost
        
        return total_money_taken
    
    async def _apply_war_rewards(self, war: KingdomWar, session: AsyncSession):
        """Apply money and experience rewards to participants"""
        money_transfers = war.get_money_transferred()
        attack_stats = war.get_total_attack_stats()
        
        exp_distribution = {}
        
        for kingdom, money_gained in money_transfers.items():
            if kingdom not in attack_stats:
                continue
            
            kingdom_stats = attack_stats[kingdom]
            squad = war.get_attack_squads().get(kingdom, [])
            
            if not squad:
                continue
            
            # Calculate total stats for distribution
            total_kingdom_stats = (kingdom_stats['total_strength'] + 
                                 kingdom_stats['total_armor'] + 
                                 kingdom_stats['total_agility'])
            
            # Distribute money and exp based on individual stats
            for user_id in squad:
                participation = await session.scalar(
                    select(WarParticipation).where(
                        and_(
                            WarParticipation.war_id == war.id,
                            WarParticipation.user_id == user_id,
                            WarParticipation.role == 'attacker'
                        )
                    )
                )
                
                if not participation:
                    continue
                
                user_stats = participation.get_player_stats()
                user_total_stats = (user_stats['strength'] + 
                                   user_stats['armor'] + 
                                   user_stats['agility'])
                
                # Calculate share based on stats
                if total_kingdom_stats > 0:
                    share = user_total_stats / total_kingdom_stats
                else:
                    share = 1.0 / len(squad)
                
                # Calculate rewards
                money_reward = int(money_gained * share)
                exp_reward = int(50 * share * user_stats['level'])  # Base 50 exp * level
                
                # Apply rewards to user
                user = await session.get(User, user_id)
                if user:
                    user.money += money_reward
                    await self.user_service.add_experience(user_id, exp_reward)
                
                # Store in participation record
                participation.money_gained = money_reward
                participation.exp_gained = exp_reward
                
                exp_distribution[str(user_id)] = exp_reward
        
        war.set_exp_distributed(exp_distribution)
    
    async def get_user_war_results(self, user_id: int, war_id: int) -> Optional[Dict]:
        """Get war results for specific user"""
        async with AsyncSessionLocal() as session:
            participation = await session.scalar(
                select(WarParticipation).where(
                    and_(
                        WarParticipation.war_id == war_id,
                        WarParticipation.user_id == user_id
                    )
                )
            )
            
            if not participation:
                return None
            
            war = await session.get(KingdomWar, war_id)
            if not war:
                return None
            
            return {
                'role': participation.role.value,
                'kingdom': participation.kingdom,
                'money_gained': participation.money_gained,
                'money_lost': participation.money_lost,
                'exp_gained': participation.exp_gained,
                'war_status': war.status.value,
                'battle_results': war.get_battle_results()
            }
    
    async def get_scheduled_wars(self, date: datetime = None) -> List[KingdomWar]:
        """Get scheduled wars for a date"""
        if date is None:
            date = datetime.utcnow()
        
        # Get wars for the date
        start_of_day = datetime.combine(date.date(), datetime.min.time())
        end_of_day = start_of_day + timedelta(days=1)
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(KingdomWar).where(
                    and_(
                        KingdomWar.scheduled_time >= start_of_day,
                        KingdomWar.scheduled_time < end_of_day,
                        KingdomWar.status == WarStatusEnum.scheduled
                    )
                ).order_by(KingdomWar.scheduled_time)
            )
            
            return result.scalars().all()