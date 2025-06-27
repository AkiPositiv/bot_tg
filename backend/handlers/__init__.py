from aiogram import Dispatcher
from handlers.start import router as start_router
from handlers.profile import router as profile_router
from handlers.battle import router as battle_router
from handlers.shop import router as shop_router
from handlers.inventory import router as inventory_router
from handlers.interactive_battle import router as interactive_battle_router
from handlers.kingdom_war import router as kingdom_war_router
from handlers.enhanced_interactive_battle import router as enhanced_interactive_battle_router
from handlers.enhanced_pvp_battle import router as enhanced_pvp_battle_router
from handlers.enhanced_main_battle import router as enhanced_main_battle_router

def setup_handlers(dp: Dispatcher):
    """Setup all handlers"""
    dp.include_router(start_router)
    dp.include_router(profile_router)
    dp.include_router(battle_router)
    dp.include_router(shop_router)
    dp.include_router(inventory_router)
    dp.include_router(interactive_battle_router)
    dp.include_router(kingdom_war_router)
    dp.include_router(enhanced_interactive_battle_router)
    dp.include_router(enhanced_pvp_battle_router)
    dp.include_router(enhanced_main_battle_router)
