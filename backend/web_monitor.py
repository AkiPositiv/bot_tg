#!/usr/bin/env python3
"""
Web Monitor for RPG Telegram Bot
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from config.database import AsyncSessionLocal
from models.user import User
from models.battle import Battle
import os
import subprocess

app = FastAPI(title="RPG Bot Monitor")

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Bot dashboard"""
    
    # Get bot stats
    async with AsyncSessionLocal() as session:
        # User stats
        total_users = await session.scalar(select(func.count(User.id)))
        active_users = await session.scalar(
            select(func.count(User.id)).where(User.is_active == True)
        )
        
        # Battle stats
        total_battles = await session.scalar(select(func.count(Battle.id)))
        active_battles = await session.scalar(
            select(func.count(Battle.id)).where(Battle.status == 'active')
        )
        
        # Top players
        top_players = await session.execute(
            select(User).order_by(User.level.desc(), User.experience.desc()).limit(5)
        )
        top_players_list = top_players.scalars().all()
    
    # Check if bot process is running
    try:
        result = subprocess.run(['pgrep', '-f', 'bot_main.py'], capture_output=True)
        bot_running = len(result.stdout.decode().strip()) > 0
    except:
        bot_running = False
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>RPG Bot Monitor</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .card {{ background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .status {{ padding: 10px; border-radius: 4px; text-align: center; font-weight: bold; }}
            .status.online {{ background: #d4edda; color: #155724; }}
            .status.offline {{ background: #f8d7da; color: #721c24; }}
            .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
            .stat-item {{ text-align: center; }}
            .stat-value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
            .stat-label {{ color: #666; }}
            .player-list {{ list-style: none; padding: 0; }}
            .player-item {{ padding: 10px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; }}
            h1, h2 {{ color: #333; }}
            .emoji {{ font-size: 1.2em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎮 RPG Telegram Bot Monitor</h1>
            
            <div class="card">
                <h2>🤖 Bot Status</h2>
                <div class="status {'online' if bot_running else 'offline'}">
                    {'🟢 ONLINE' if bot_running else '🔴 OFFLINE'}
                </div>
            </div>
            
            <div class="card">
                <h2>📊 Statistics</h2>
                <div class="stats">
                    <div class="stat-item">
                        <div class="stat-value">{total_users or 0}</div>
                        <div class="stat-label">👤 Total Users</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{active_users or 0}</div>
                        <div class="stat-label">✅ Active Users</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{total_battles or 0}</div>
                        <div class="stat-label">⚔️ Total Battles</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{active_battles or 0}</div>
                        <div class="stat-label">🔥 Active Battles</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>🏆 Top Players</h2>
                <ul class="player-list">
    """
    
    for i, player in enumerate(top_players_list, 1):
        kingdoms = {
            'north': '❄️',
            'west': '🌅', 
            'east': '🌸',
            'south': '🔥'
        }
        kingdom_emoji = kingdoms.get(player.kingdom.value, '🏰')
        
        html_content += f"""
                    <li class="player-item">
                        <span>#{i} {kingdom_emoji} {player.name}</span>
                        <span>Lv.{player.level} | {player.pvp_wins}W/{player.pvp_losses}L</span>
                    </li>
        """
    
    html_content += """
                </ul>
            </div>
            
            <div class="card">
                <h2>📋 Quick Actions</h2>
                <p>Bot management can be done via command line:</p>
                <ul>
                    <li><code>pkill -f bot_main.py</code> - Stop bot</li>
                    <li><code>cd /app/backend && python bot_main.py</code> - Start bot</li>
                    <li><code>tail -f /app/backend/bot.log</code> - View logs</li>
                </ul>
            </div>
            
            <div class="card">
                <h2>🔗 Bot Information</h2>
                <p><strong>Bot Username:</strong> @Aki_Test_tttttttBot</p>
                <p><strong>Database:</strong> SQLite (rpg_game.db)</p>
                <p><strong>Status:</strong> Production Ready</p>
            </div>
        </div>
        
        <script>
            // Auto-refresh every 30 seconds
            setTimeout(() => location.reload(), 30000);
        </script>
    </body>
    </html>
    """
    
    return html_content

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)