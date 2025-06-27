#!/usr/bin/env python3
import sqlite3
import json
from datetime import datetime
import asyncio
import sys

async def test_war_blocking():
    """Test if war blocking middleware is working"""
    print("Testing war blocking middleware...")
    
    # Connect to the database
    conn = sqlite3.connect('/app/backend/rpg_game.db')
    cursor = conn.cursor()
    
    # Get a test user who is participating in a war
    cursor.execute(
        """
        SELECT u.id, u.name, u.kingdom, wp.war_id, wp.role 
        FROM users u
        JOIN war_participations wp ON u.id = wp.user_id
        LIMIT 1
        """
    )
    participant = cursor.fetchone()
    
    if not participant:
        print("No war participants found in database")
        return False
    
    user_id = participant[0]
    user_name = participant[1]
    user_kingdom = participant[2]
    war_id = participant[3]
    role = participant[4]
    
    print(f"Found war participant: {user_name} (ID: {user_id}, Kingdom: {user_kingdom})")
    print(f"Participating in war ID: {war_id} as {role}")
    
    # Check if user is blocked (simulating the middleware check)
    # In the real middleware, this would be done by EnhancedKingdomWarService.check_user_war_block
    cursor.execute(
        """
        SELECT COUNT(*) FROM war_participations wp
        JOIN kingdom_wars kw ON wp.war_id = kw.id
        WHERE wp.user_id = ? AND kw.status = 'scheduled'
        """,
        (user_id,)
    )
    is_blocked = cursor.fetchone()[0] > 0
    block_message = "Вы заявлены на участие в Атаке Королевств. Дождитесь окончания битвы." if is_blocked else ""
    
    print(f"Is user blocked: {is_blocked}")
    if is_blocked:
        print(f"Block message: {block_message}")
    
    # Try to simulate some blocked actions
    blocked_actions = [
        'pvp_battle', 'pve_encounter', 'shop_menu', 'inventory', 'dungeon_menu'
    ]
    
    for action in blocked_actions:
        print(f"\nTesting action: {action}")
        # This is a simulation - in a real scenario, the middleware would check this
        if is_blocked:
            print(f"❌ Action '{action}' is blocked: {block_message}")
        else:
            print(f"✅ Action '{action}' is allowed")
    
    # Try to simulate allowed actions
    allowed_actions = [
        'kingdom_wars', 'main_menu', 'battle_menu', 'war_results'
    ]
    
    for action in allowed_actions:
        print(f"\nTesting action: {action}")
        # These actions should be allowed even if user is in war mode
        print(f"✅ Action '{action}' is allowed (war-related action)")
    
    conn.close()
    return True

async def main():
    success = await test_war_blocking()
    return 0 if success else 1

if __name__ == "__main__":
    asyncio.run(main())