#!/usr/bin/env python3
import sqlite3
import json
from datetime import datetime
import pytz

# Connect to the database
conn = sqlite3.connect('/app/backend/rpg_game.db')
cursor = conn.cursor()

# Check kingdom_wars table
print("=== Kingdom Wars ===")
cursor.execute("SELECT COUNT(*) FROM kingdom_wars")
war_count = cursor.fetchone()[0]
print(f"Total wars: {war_count}")

cursor.execute("SELECT status, COUNT(*) FROM kingdom_wars GROUP BY status")
statuses = cursor.fetchall()
for status, count in statuses:
    print(f"Status '{status}': {count}")

# Check war_participations table
print("\n=== War Participations ===")
cursor.execute("SELECT COUNT(*) FROM war_participations")
participation_count = cursor.fetchone()[0]
print(f"Total participations: {participation_count}")

if participation_count > 0:
    cursor.execute("SELECT role, COUNT(*) FROM war_participations GROUP BY role")
    roles = cursor.fetchall()
    for role, count in roles:
        print(f"Role '{role}': {count}")

# Check war times
print("\n=== War Times ===")
cursor.execute("SELECT scheduled_time FROM kingdom_wars LIMIT 5")
war_times = cursor.fetchall()
tashkent_tz = pytz.timezone('Asia/Tashkent')

for i, (war_time,) in enumerate(war_times, 1):
    try:
        dt = datetime.fromisoformat(war_time.replace('Z', '+00:00'))
        tashkent_time = dt.astimezone(tashkent_tz)
        print(f"War {i}: {tashkent_time.strftime('%Y-%m-%d %H:%M:%S')} (Tashkent time)")
    except:
        print(f"War {i}: {war_time} (Invalid format)")

# Check users
print("\n=== Users ===")
cursor.execute("SELECT COUNT(*) FROM users")
user_count = cursor.fetchone()[0]
print(f"Total users: {user_count}")

if user_count > 0:
    cursor.execute("SELECT id, name, kingdom FROM users LIMIT 5")
    users = cursor.fetchall()
    for user_id, name, kingdom in users:
        print(f"User {user_id}: {name} (Kingdom: {kingdom})")

# Close connection
conn.close()