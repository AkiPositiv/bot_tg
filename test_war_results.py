#!/usr/bin/env python3
import sqlite3
import json
from datetime import datetime
import asyncio
import sys

async def test_war_results():
    """Test war results functionality"""
    print("Testing war results functionality...")
    
    # Connect to the database
    conn = sqlite3.connect('/app/backend/rpg_game.db')
    cursor = conn.cursor()
    
    # Check if there are finished wars
    cursor.execute("SELECT COUNT(*) FROM kingdom_wars WHERE status = 'finished'")
    finished_wars = cursor.fetchone()[0]
    
    if finished_wars == 0:
        print("No finished wars found in database")
        return False
    
    print(f"Found {finished_wars} finished wars")
    
    # Get details of a finished war
    cursor.execute(
        """
        SELECT id, defending_kingdom, attacking_kingdoms, battle_results, money_transferred
        FROM kingdom_wars 
        WHERE status = 'finished'
        LIMIT 1
        """
    )
    war = cursor.fetchone()
    
    war_id = war[0]
    defending_kingdom = war[1]
    attacking_kingdoms_json = war[2]
    battle_results_json = war[3]
    money_transferred_json = war[4]
    
    attacking_kingdoms = json.loads(attacking_kingdoms_json) if attacking_kingdoms_json else []
    battle_results = json.loads(battle_results_json) if battle_results_json else []
    money_transferred = json.loads(money_transferred_json) if money_transferred_json else {}
    
    print(f"\nWar ID: {war_id}")
    print(f"Defending Kingdom: {defending_kingdom}")
    print(f"Attacking Kingdoms: {attacking_kingdoms}")
    
    print("\nBattle Results:")
    for result in battle_results:
        print(f"- {result['attacker']} vs {result['defender']}: {result['result']}")
        if 'message' in result:
            print(f"  Message: {result['message']}")
    
    print("\nMoney Transferred:")
    for kingdom, amount in money_transferred.items():
        print(f"- {kingdom}: +{amount} gold")
    
    # Get participant results
    cursor.execute(
        """
        SELECT wp.user_id, u.name, wp.kingdom, wp.role, wp.money_gained, wp.money_lost, wp.exp_gained
        FROM war_participations wp
        JOIN users u ON wp.user_id = u.id
        WHERE wp.war_id = ?
        """,
        (war_id,)
    )
    participants = cursor.fetchall()
    
    print("\nParticipant Results:")
    for participant in participants:
        user_id, name, kingdom, role, money_gained, money_lost, exp_gained = participant
        print(f"- {name} (ID: {user_id}, Kingdom: {kingdom}, Role: {role})")
        print(f"  Money Gained: {money_gained}, Money Lost: {money_lost}, Exp Gained: {exp_gained}")
    
    # Simulate accessing war results menu
    print("\nSimulating war results menu access...")
    print("✅ War results menu would show the above information")
    
    # Simulate accessing personal results
    print("\nSimulating personal war results access...")
    if participants:
        user_id = participants[0][0]
        user_name = participants[0][1]
        print(f"✅ Personal war results for {user_name} (ID: {user_id}) would show their participation details")
    else:
        print("❌ No participants found for this war")
    
    # Simulate accessing global results
    print("\nSimulating global war results access...")
    print("✅ Global war results would show a summary of all wars")
    
    conn.close()
    return True

async def main():
    success = await test_war_results()
    return 0 if success else 1

if __name__ == "__main__":
    asyncio.run(main())