#!/usr/bin/env python3
import sqlite3
import json
from datetime import datetime, timedelta
import pytz
import asyncio
import sys
import random

async def simulate_war_start():
    """Simulate starting a war"""
    print("Simulating war start...")
    
    # Connect to the database
    conn = sqlite3.connect('/app/backend/rpg_game.db')
    cursor = conn.cursor()
    
    # Get a scheduled war with participants
    cursor.execute(
        """
        SELECT kw.id, kw.defending_kingdom, kw.scheduled_time, kw.attacking_kingdoms
        FROM kingdom_wars kw
        JOIN war_participations wp ON kw.id = wp.war_id
        WHERE kw.status = 'scheduled'
        GROUP BY kw.id
        LIMIT 1
        """
    )
    war = cursor.fetchone()
    
    if not war:
        print("No scheduled wars with participants found")
        return False
    
    war_id = war[0]
    defending_kingdom = war[1]
    scheduled_time = war[2]
    attacking_kingdoms_json = war[3]
    
    print(f"Found war ID: {war_id}, defending kingdom: {defending_kingdom}, scheduled at: {scheduled_time}")
    
    # Parse attacking kingdoms
    attacking_kingdoms = json.loads(attacking_kingdoms_json) if attacking_kingdoms_json else []
    print(f"Attacking kingdoms: {attacking_kingdoms}")
    
    # Get attack squads
    cursor.execute(
        "SELECT attack_squads FROM kingdom_wars WHERE id = ?",
        (war_id,)
    )
    attack_squads_json = cursor.fetchone()[0]
    attack_squads = json.loads(attack_squads_json) if attack_squads_json else {}
    
    # Get defense squad
    cursor.execute(
        "SELECT defense_squad FROM kingdom_wars WHERE id = ?",
        (war_id,)
    )
    defense_squad_json = cursor.fetchone()[0]
    defense_squad = json.loads(defense_squad_json) if defense_squad_json else []
    
    print(f"Attack squads: {attack_squads}")
    print(f"Defense squad: {defense_squad}")
    
    # Simulate war start
    try:
        # Update war status to active
        cursor.execute(
            "UPDATE kingdom_wars SET status = 'active', started_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), war_id)
        )
        
        # Calculate attack and defense stats
        total_attack_stats = {}
        for kingdom, player_ids in attack_squads.items():
            kingdom_stats = {
                'total_strength': random.randint(50, 100) * len(player_ids),
                'total_armor': random.randint(40, 80) * len(player_ids),
                'total_hp': random.randint(500, 1000) * len(player_ids),
                'total_agility': random.randint(30, 70) * len(player_ids),
                'total_mana': random.randint(200, 400) * len(player_ids),
                'player_count': len(player_ids)
            }
            total_attack_stats[kingdom] = kingdom_stats
        
        defense_stats = {
            'total_strength': random.randint(60, 120) * len(defense_squad) if defense_squad else 0,
            'total_armor': random.randint(50, 100) * len(defense_squad) if defense_squad else 0,
            'total_hp': random.randint(600, 1200) * len(defense_squad) if defense_squad else 0,
            'total_agility': random.randint(40, 80) * len(defense_squad) if defense_squad else 0,
            'total_mana': random.randint(250, 500) * len(defense_squad) if defense_squad else 0,
            'player_count': len(defense_squad),
            'voluntary_defenders': len(defense_squad),
            'auto_defenders': 0
        }
        
        # Apply defense buff
        defense_buff = 1.3 if len(attacking_kingdoms) > 1 else 1.0
        
        # Update war stats
        cursor.execute(
            "UPDATE kingdom_wars SET total_attack_stats = ?, defense_stats = ?, defense_buff = ? WHERE id = ?",
            (json.dumps(total_attack_stats), json.dumps(defense_stats), defense_buff, war_id)
        )
        
        # Simulate battle results
        battle_results = []
        money_transfers = {}
        successful_attacker = None
        
        # Process attacks
        for kingdom in attacking_kingdoms:
            if not successful_attacker:
                # Attacker breaks through defense
                successful_attacker = kingdom
                battle_results.append({
                    'attacker': kingdom,
                    'defender': defending_kingdom,
                    'result': 'victory',
                    'damage_dealt': random.randint(500, 1000),
                    'message': f'{kingdom} сломало защиту {defending_kingdom}!'
                })
                
                # Calculate money transfer (40% of defenders' money)
                money_transfers[kingdom] = random.randint(1000, 5000)
            else:
                # Too late, defense already broken
                battle_results.append({
                    'attacker': kingdom,
                    'defender': defending_kingdom,
                    'result': 'too_late',
                    'message': f'{kingdom} опоздало - город уже разграблен!'
                })
        
        # Update battle results and money transfers
        cursor.execute(
            "UPDATE kingdom_wars SET battle_results = ?, money_transferred = ? WHERE id = ?",
            (json.dumps(battle_results), json.dumps(money_transfers), war_id)
        )
        
        # Finish war
        cursor.execute(
            "UPDATE kingdom_wars SET status = 'finished', finished_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), war_id)
        )
        
        # Update participants
        if successful_attacker:
            # Reward attackers
            cursor.execute(
                """
                UPDATE war_participations 
                SET money_gained = ?, exp_gained = ?
                WHERE war_id = ? AND kingdom = ? AND role = 'attacker'
                """,
                (random.randint(100, 500), random.randint(50, 200), war_id, successful_attacker)
            )
            
            # Penalize defenders
            cursor.execute(
                """
                UPDATE war_participations 
                SET money_lost = ?
                WHERE war_id = ? AND role = 'defender'
                """,
                (random.randint(100, 300), war_id)
            )
        
        conn.commit()
        print(f"✅ Successfully simulated war {war_id} with result: {successful_attacker} won")
        return True
    
    except Exception as e:
        print(f"❌ Error simulating war start: {e}")
        conn.rollback()
        return False

async def main():
    success = await simulate_war_start()
    
    # Check war status after simulation
    if success:
        conn = sqlite3.connect('/app/backend/rpg_game.db')
        cursor = conn.cursor()
        
        print("\nVerifying war status...")
        cursor.execute(
            "SELECT id, status, started_at, finished_at FROM kingdom_wars WHERE status = 'finished' LIMIT 1"
        )
        war = cursor.fetchone()
        if war:
            print(f"War ID {war[0]} is now {war[1]}")
            print(f"Started at: {war[2]}")
            print(f"Finished at: {war[3]}")
            
            # Check battle results
            cursor.execute(
                "SELECT battle_results, money_transferred FROM kingdom_wars WHERE id = ?",
                (war[0],)
            )
            results = cursor.fetchone()
            battle_results = json.loads(results[0]) if results[0] else []
            money_transfers = json.loads(results[1]) if results[1] else {}
            
            print("\nBattle Results:")
            for result in battle_results:
                print(f"- {result['attacker']} vs {result['defender']}: {result['result']}")
            
            print("\nMoney Transfers:")
            for kingdom, amount in money_transfers.items():
                print(f"- {kingdom}: +{amount} gold")
            
            # Check participant rewards
            cursor.execute(
                """
                SELECT user_id, role, money_gained, money_lost, exp_gained 
                FROM war_participations 
                WHERE war_id = ?
                """,
                (war[0],)
            )
            participants = cursor.fetchall()
            
            print("\nParticipant Rewards:")
            for participant in participants:
                user_id, role, money_gained, money_lost, exp_gained = participant
                print(f"- User {user_id} ({role}): +{money_gained} gold, -{money_lost} gold, +{exp_gained} exp")
        
        conn.close()
    
    return 0 if success else 1

if __name__ == "__main__":
    asyncio.run(main())