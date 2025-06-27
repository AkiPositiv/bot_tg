#!/usr/bin/env python3
import sqlite3
import json
from datetime import datetime, timedelta
import pytz
import asyncio
import sys

# Connect to the database
conn = sqlite3.connect('/app/backend/rpg_game.db')
cursor = conn.cursor()

async def simulate_war_registration():
    """Simulate a user registering for a war"""
    print("Simulating war registration...")
    
    # Get a test user
    cursor.execute("SELECT id, name, kingdom FROM users LIMIT 1")
    test_user = cursor.fetchone()
    if not test_user:
        print("No users found in database")
        return False
    
    test_user_id = test_user[0]
    test_user_name = test_user[1]
    test_user_kingdom = test_user[2]
    
    print(f"Using test user: {test_user_name} (ID: {test_user_id}, Kingdom: {test_user_kingdom})")
    
    # Get a target kingdom different from user's kingdom
    kingdoms = ['north', 'south', 'east', 'west']
    target_kingdoms = [k for k in kingdoms if k != test_user_kingdom]
    if not target_kingdoms:
        print("Could not find a target kingdom for attack")
        return False
    
    target_kingdom = target_kingdoms[0]
    print(f"Target kingdom for attack: {target_kingdom}")
    
    # Find a scheduled war for the target kingdom
    cursor.execute(
        "SELECT id, scheduled_time FROM kingdom_wars WHERE defending_kingdom = ? AND status = 'scheduled' LIMIT 1",
        (target_kingdom,)
    )
    war = cursor.fetchone()
    if not war:
        print(f"No scheduled wars found for kingdom {target_kingdom}")
        return False
    
    war_id = war[0]
    war_time = war[1]
    
    print(f"Selected war ID: {war_id}, scheduled at: {war_time}")
    
    # Simulate joining attack squad
    try:
        # Create attack squad entry
        cursor.execute(
            "SELECT attack_squads FROM kingdom_wars WHERE id = ?",
            (war_id,)
        )
        attack_squads_json = cursor.fetchone()[0]
        attack_squads = json.loads(attack_squads_json) if attack_squads_json else {}
        
        if test_user_kingdom not in attack_squads:
            attack_squads[test_user_kingdom] = []
        
        if test_user_id not in attack_squads[test_user_kingdom]:
            attack_squads[test_user_kingdom].append(test_user_id)
        
        # Update attack squads
        cursor.execute(
            "UPDATE kingdom_wars SET attack_squads = ? WHERE id = ?",
            (json.dumps(attack_squads), war_id)
        )
        
        # Update attacking kingdoms
        cursor.execute(
            "SELECT attacking_kingdoms FROM kingdom_wars WHERE id = ?",
            (war_id,)
        )
        attacking_kingdoms_json = cursor.fetchone()[0]
        attacking_kingdoms = json.loads(attacking_kingdoms_json) if attacking_kingdoms_json else []
        
        if test_user_kingdom not in attacking_kingdoms:
            attacking_kingdoms.append(test_user_kingdom)
        
        cursor.execute(
            "UPDATE kingdom_wars SET attacking_kingdoms = ? WHERE id = ?",
            (json.dumps(attacking_kingdoms), war_id)
        )
        
        # Create participation record
        cursor.execute(
            "SELECT * FROM users WHERE id = ?",
            (test_user_id,)
        )
        user = cursor.fetchone()
        
        # Get user stats (assuming column order from the schema)
        player_stats = {
            'strength': user[11],
            'armor': user[12],
            'hp': user[13],
            'agility': user[15],
            'mana': user[16],
            'level': user[7]
        }
        
        # Insert participation record
        cursor.execute(
            """
            INSERT INTO war_participations 
            (war_id, user_id, kingdom, role, player_stats) 
            VALUES (?, ?, ?, ?, ?)
            """,
            (war_id, test_user_id, test_user_kingdom, 'attacker', json.dumps(player_stats))
        )
        
        conn.commit()
        print(f"✅ Successfully registered user {test_user_name} for attack on {target_kingdom}")
        return True
    
    except Exception as e:
        print(f"❌ Error simulating war registration: {e}")
        conn.rollback()
        return False

async def main():
    success = await simulate_war_registration()
    
    # Check if registration was successful
    if success:
        print("\nVerifying war participation...")
        cursor.execute("SELECT COUNT(*) FROM war_participations")
        participation_count = cursor.fetchone()[0]
        print(f"Total participations after registration: {participation_count}")
        
        if participation_count > 0:
            cursor.execute(
                "SELECT war_id, user_id, kingdom, role FROM war_participations LIMIT 1"
            )
            participation = cursor.fetchone()
            print(f"Participation: War ID {participation[0]}, User ID {participation[1]}, Kingdom {participation[2]}, Role {participation[3]}")
    
    # Close connection
    conn.close()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))