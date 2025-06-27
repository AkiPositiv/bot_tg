#!/usr/bin/env python3
"""
Update handlers to include new shop and inventory handlers
"""

# Update handlers/__init__.py to include new handlers
handlers_init_content = '''from aiogram import Dispatcher
from handlers.start import router as start_router
from handlers.profile import router as profile_router
from handlers.battle import router as battle_router
from handlers.shop import router as shop_router
from handlers.inventory import router as inventory_router

def setup_handlers(dp: Dispatcher):
    """Setup all handlers"""
    dp.include_router(start_router)
    dp.include_router(profile_router)
    dp.include_router(battle_router)
    dp.include_router(shop_router)
    dp.include_router(inventory_router)
'''

# Write the updated handlers init file
with open('/app/backend/handlers/__init__.py', 'w') as f:
    f.write(handlers_init_content)

print("Updated handlers/__init__.py to include shop and inventory handlers")