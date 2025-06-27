from sqlalchemy import select, and_, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import AsyncSessionLocal
from config.settings import settings
from models.kingdom_war import KingdomWar, WarParticipation, WarStatusEnum, WarTypeEnum
from models.user import User, KingdomEnum
from services.user_service import UserService
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
import pytz
import json

logger = logging.getLogger(__name__)

class EnhancedKingdomWarService:
    def __init__(self):
        self.user_service = UserService()
        self.tashkent_tz = pytz.timezone('Asia/Tashkent')
        self.war_times = [8, 13, 18]
        self.war_channel_id = settings.WAR_CHANNEL_ID
    
    async def schedule_daily_wars(self, date: datetime):
        """Schedule wars with 30-minute advance notifications"""
        async with AsyncSessionLocal() as session:
            for hour in self.war_times:
                # Create war time in Tashkent timezone
                war_time = self.tashkent_tz.localize(
                    datetime.combine(date.date(), datetime.min.time().replace(hour=hour))
                )
                
                # Convert to UTC for storage
                war_time_utc = war_time.astimezone(pytz.UTC)
                
                # Check if war already scheduled
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
            logger.info(f"Scheduled enhanced wars for {date.date()}")
    
    async def join_attack_squad(self, user_id: int, target_kingdom: str, war_time: datetime) -> Tuple[bool, str]:
        """Join attack squad with action blocking"""
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                return False, "Пользователь не найден"
            
            if user.kingdom.value == target_kingdom:
                return False, "Нельзя атаковать своё королевство"
            
            # Check if user is already in war mode
            if await self._is_user_in_war_mode(user_id, session):
                return False, "Вы уже заявлены на участие в войне королевств!"
            
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
            
            # Block user from other actions
            await self._set_user_war_mode(user_id, war.id, 'attacker', session)
            
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
            
            logger.info(f"User {user_id} joined enhanced attack on {target_kingdom}")
            return True, f"Вы заявлены на атаку {target_kingdom}! Дождитесь начала войны. Другие действия заблокированы."
    
    async def join_defense_squad(self, user_id: int, war_time: datetime) -> Tuple[bool, str]:
        """Join defense squad with action blocking"""
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                return False, "Пользователь не найден"
            
            # Check if user is already in war mode
            if await self._is_user_in_war_mode(user_id, session):
                return False, "Вы уже заявлены на участие в войне королевств!"
            
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
            
            # Block user from other actions
            await self._set_user_war_mode(user_id, war.id, 'defender', session)
            
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
            
            logger.info(f"User {user_id} joined enhanced defense of {user.kingdom.value}")
            return True, "Вы заявлены на защиту королевства! Дождитесь начала войны. Другие действия заблокированы."
    
    async def _set_user_war_mode(self, user_id: int, war_id: int, role: str, session: AsyncSession):
        """Set user in war mode (block other actions)"""
        # This could be implemented as a separate table or user field
        # For now, we'll use the participation record as the indicator
        pass
    
    async def _is_user_in_war_mode(self, user_id: int, session: AsyncSession) -> bool:
        """Check if user is currently in war mode"""
        # Check if user has any pending war participations
        result = await session.scalar(
            select(WarParticipation).where(
                and_(
                    WarParticipation.user_id == user_id,
                    WarParticipation.war_id.in_(
                        select(KingdomWar.id).where(
                            KingdomWar.status == WarStatusEnum.scheduled
                        )
                    )
                )
            )
        )
        return result is not None
    
    async def check_user_war_block(self, user_id: int) -> Tuple[bool, str]:
        """Check if user is blocked from actions due to war participation"""
        async with AsyncSessionLocal() as session:
            if await self._is_user_in_war_mode(user_id, session):
                return True, "Вы заявлены на участие в Атаке Королевств. Дождитесь окончания битвы."
            return False, ""
    
    async def start_enhanced_war(self, war_id: int) -> bool:
        """Start enhanced war with full mechanics"""
        async with AsyncSessionLocal() as session:
            war = await session.get(KingdomWar, war_id)
            if not war or war.status != WarStatusEnum.scheduled:
                return False
            
            attacking_kingdoms = war.get_attacking_kingdoms()
            defense_squad = war.get_defense_squad()
            
            # Include online non-participating players in defense
            await self._add_online_defenders(war, session)
            
            if not attacking_kingdoms:
                # No attackers, cancel war
                war.status = WarStatusEnum.finished
                war.finished_at = datetime.utcnow()
                await self._release_war_participants(war, session)
                await session.commit()
                return False
            
            war.status = WarStatusEnum.active
            war.started_at = datetime.utcnow()
            
            # Calculate stats with online defenders
            await self._calculate_enhanced_kingdom_stats(war, session)
            
            # Calculate defense buff
            num_attacking = len(attacking_kingdoms)
            if num_attacking > 1:
                war.defense_buff = 1.3  # 30% defense buff
            else:
                war.defense_buff = 1.0
            
            await session.commit()
            
            # Process the war
            await self._process_enhanced_war_battles(war, session)
            
            return True
    
    async def _add_online_defenders(self, war: KingdomWar, session: AsyncSession):
        """Add online non-participating players to defense"""
        # Get online players from defending kingdom who aren't already participating
        current_time = datetime.utcnow()
        online_threshold = current_time - timedelta(minutes=30)  # Active in last 30 minutes
        
        online_players = await session.execute(
            select(User).where(
                and_(
                    User.kingdom == war.defending_kingdom,
                    User.last_active >= online_threshold,
                    User.id.not_in(
                        select(WarParticipation.user_id).where(
                            WarParticipation.war_id == war.id
                        )
                    )
                )
            )
        )
        
        defense_squad = war.get_defense_squad()
        
        for player in online_players.scalars():
            defense_squad.append(player.id)
            
            # Create participation record for auto-defenders
            participation = WarParticipation(
                war_id=war.id,
                user_id=player.id,
                kingdom=player.kingdom.value,
                role='defender'
            )
            
            player_stats = {
                'strength': player.strength,
                'armor': player.armor,
                'hp': player.hp,
                'agility': player.agility,
                'mana': player.mana,
                'level': player.level
            }
            participation.set_player_stats(player_stats)
            session.add(participation)
        
        war.set_defense_squad(defense_squad)
    
    async def _calculate_enhanced_kingdom_stats(self, war: KingdomWar, session: AsyncSession):
        """Calculate enhanced kingdom stats including all defenders"""
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
        
        # Calculate defense stats (including online auto-defenders)
        defense_squad = war.get_defense_squad()
        defense_stats = {
            'total_strength': 0,
            'total_armor': 0,
            'total_hp': 0,
            'total_agility': 0,
            'total_mana': 0,
            'player_count': len(defense_squad),
            'voluntary_defenders': 0,
            'auto_defenders': 0
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
    
    async def _process_enhanced_war_battles(self, war: KingdomWar, session: AsyncSession):
        """Process enhanced war battles with full mechanics"""
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
        successful_attacker = None
        
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
            
            # Enhanced damage calculation
            damage_to_defense = max(attack_power - buffed_defense_stats['total_armor'], attack_power * 0.1)
            damage_to_attacker = max(defense_power - kingdom_stats['total_armor'], defense_power * 0.1)
            
            current_defense_hp -= damage_to_defense
            
            if current_defense_hp <= 0:
                # Attacker breaks through defense
                successful_attacker = kingdom
                battle_results.append({
                    'attacker': kingdom,
                    'defender': war.defending_kingdom,
                    'result': 'victory',
                    'damage_dealt': damage_to_defense,
                    'message': f'{kingdom} сломало защиту {war.defending_kingdom}!'
                })
                
                # Calculate money transfer (40% of defenders' money)
                money_to_transfer = await self._calculate_enhanced_money_transfer(war, kingdom, session)
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
        
        # Apply enhanced penalties and rewards
        await self._apply_enhanced_war_consequences(war, successful_attacker, session)
        
        # Store results
        war.battle_results = json.dumps(battle_results)
        war.set_money_transferred(money_transfers)
        
        # Apply money transfers and experience
        await self._apply_enhanced_war_rewards(war, session)
        
        # Finish war and restore participants
        war.status = WarStatusEnum.finished
        war.finished_at = datetime.utcnow()
        await self._release_war_participants(war, session)
        await self._restore_participants_after_war(war, session)
        
        await session.commit()
        
        logger.info(f"Enhanced war {war.id} finished with results: {len(battle_results)} battles")
    
    async def _calculate_enhanced_money_transfer(self, war: KingdomWar, winning_kingdom: str, session: AsyncSession) -> int:
        """Calculate enhanced money transfer from all kingdom players"""
        # Get ALL players from defending kingdom (participating and non-participating)
        defending_players = await session.execute(
            select(User).where(User.kingdom == war.defending_kingdom)
        )
        
        total_money_taken = 0
        
        for user in defending_players.scalars():
            money_lost = int(user.money * 0.4)
            user.money = max(0, user.money - money_lost)
            total_money_taken += money_lost
            
            # Mark money loss in participation if exists
            participation = await session.scalar(
                select(WarParticipation).where(
                    and_(
                        WarParticipation.war_id == war.id,
                        WarParticipation.user_id == user.id
                    )
                )
            )
            if participation:
                participation.money_lost = money_lost
        
        return total_money_taken
    
    async def _apply_enhanced_war_consequences(self, war: KingdomWar, successful_attacker: str, session: AsyncSession):
        """Apply enhanced consequences including penalties for non-participants"""
        if successful_attacker:
            # Defense was broken - apply penalties to non-participating defenders
            defense_squad = war.get_defense_squad()
            
            # Get all players from defending kingdom
            all_defenders = await session.execute(
                select(User).where(User.kingdom == war.defending_kingdom)
            )
            
            for user in all_defenders.scalars():
                if user.id not in defense_squad:
                    # Non-participant penalty: additional 40% loss (total 80% loss)
                    additional_penalty = int(user.money * 0.4)
                    user.money = max(0, user.money - additional_penalty)
                    logger.info(f"Non-participant penalty applied to user {user.id}: -{additional_penalty}")
    
    async def _apply_enhanced_war_rewards(self, war: KingdomWar, session: AsyncSession):
        """Apply enhanced money and experience rewards"""
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
                
                # Calculate enhanced rewards
                money_reward = int(money_gained * share)
                exp_reward = int(75 * share * user_stats['level'])  # Increased base exp
                
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
    
    async def _release_war_participants(self, war: KingdomWar, session: AsyncSession):
        """Release participants from war mode"""
        # This would remove the war mode block from all participants
        # Implementation depends on how war mode blocking is implemented
        pass
    
    async def _restore_participants_after_war(self, war: KingdomWar, session: AsyncSession):
        """Restore HP/MP of all participants after 5 minutes"""
        # This could be implemented as a scheduled task
        # For now, we'll just log it
        logger.info(f"War {war.id} participants will be restored in 5 minutes")
    
    async def get_enhanced_user_war_results(self, user_id: int, war_id: int) -> Optional[Dict]:
        """Get enhanced war results for specific user"""
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
                'battle_results': war.get_battle_results(),
                'total_participants': len(war.get_defense_squad()) + sum(
                    len(squad) for squad in war.get_attack_squads().values()
                ),
                'defense_buff_applied': war.defense_buff > 1.0
            }
    
    async def get_war_summary_for_channel(self, war_ids: List[int]) -> str:
        """Generate war summary for war channel"""
        async with AsyncSessionLocal() as session:
            summaries = []
            
            for war_id in war_ids:
                war = await session.get(KingdomWar, war_id)
                if not war:
                    continue
                
                battle_results = war.get_battle_results()
                money_transfers = war.get_money_transferred()
                
                summary = f"🏰 **{war.defending_kingdom.upper()}** - Война завершена\n"
                
                if battle_results:
                    for result in battle_results:
                        if result['result'] == 'victory':
                            money = money_transfers.get(result['attacker'], 0)
                            summary += f"✅ {result['attacker']} → ПОБЕДА (захвачено {money} золота)\n"
                        elif result['result'] == 'defeat':
                            summary += f"❌ {result['attacker']} → Поражение\n"
                        elif result['result'] == 'too_late':
                            summary += f"⏰ {result['attacker']} → Опоздало\n"
                else:
                    summary += "🕊️ Никто не атаковал\n"
                
                summaries.append(summary)
            
            return "\n".join(summaries)
    
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