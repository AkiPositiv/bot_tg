import random
import math

class GameFormulas:
    @staticmethod
    def experience_for_level(level: int) -> int:
        """Calculate experience needed for a specific level"""
        return int(100 * (level ** 1.5))
    
    @staticmethod
    def total_experience_for_level(level: int) -> int:
        """Calculate total experience needed to reach level"""
        return sum(GameFormulas.experience_for_level(i) for i in range(1, level))
    
    @staticmethod
    def calculate_damage(attacker_stats: dict, defender_stats: dict, skill_multiplier: float = 1.0) -> int:
        """Calculate damage in battle"""
        # Base damage calculation
        base_damage = (attacker_stats['strength'] + attacker_stats['agility'] * 0.5) * skill_multiplier
        
        # Defense calculation
        defense = defender_stats['armor'] * 0.8
        
        # Final damage (minimum 10% of base damage)
        final_damage = max(base_damage - defense, base_damage * 0.1)
        
        return int(final_damage)
    
    @staticmethod
    def critical_hit_chance(agility: int) -> float:
        """Calculate critical hit chance based on agility"""
        return min(agility / 200.0, 0.3)  # Max 30%
    
    @staticmethod
    def dodge_chance(agility: int) -> float:
        """Calculate dodge chance based on agility"""
        return min(agility / 300.0, 0.2)  # Max 20%
    
    @staticmethod
    def is_critical_hit(agility: int) -> bool:
        """Check if attack is critical"""
        return random.random() < GameFormulas.critical_hit_chance(agility)
    
    @staticmethod
    def is_dodge(agility: int) -> bool:
        """Check if attack is dodged"""
        return random.random() < GameFormulas.dodge_chance(agility)
    
    @staticmethod
    def calculate_battle_rewards(winner_stats: dict, loser_stats: dict) -> dict:
        """Calculate rewards for battle winner"""
        # Calculate stats ratio for reward scaling
        winner_total = sum(winner_stats.values())
        loser_total = sum(loser_stats.values())
        
        if winner_total == 0:
            stats_ratio = 1.0
        else:
            stats_ratio = loser_total / winner_total
        
        # Base rewards
        base_exp = 50
        base_money = 25
        
        # Scale rewards based on opponent strength
        exp_reward = int(base_exp * stats_ratio)
        money_reward = int(base_money * stats_ratio)
        
        return {
            'experience': max(exp_reward, 10),  # Minimum 10 exp
            'money': max(money_reward, 5)       # Minimum 5 money
        }
    
    @staticmethod
    def stat_points_for_level(level: int) -> int:
        """Calculate total stat points available at level"""
        from config.settings import settings
        return (level - 1) * settings.STAT_POINTS_PER_LEVEL