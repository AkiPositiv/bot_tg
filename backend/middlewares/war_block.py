from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, CallbackQuery, Message
from typing import Callable, Dict, Any, Awaitable
from services.enhanced_kingdom_war_service import EnhancedKingdomWarService
import logging

logger = logging.getLogger(__name__)

class WarBlockMiddleware(BaseMiddleware):
    """Middleware to block user actions during war participation"""
    
    def __init__(self):
        self.war_service = EnhancedKingdomWarService()
        # Actions that should be blocked during war
        self.blocked_actions = {
            'pvp_battle', 'pve_encounter', 'quick_training', 'training_battle',
            'shop_menu', 'buy_', 'sell_', 'equip_', 'use_item_',
            'dungeon_menu', 'interactive_battle'
        }
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        
        # Skip blocking for certain handlers
        user = data.get('user')
        if not user:
            return await handler(event, data)
        
        # Check if this is a callback query with blocked action
        if isinstance(event, CallbackQuery):
            callback_data = event.data
            
            # Skip war-related actions and main navigation
            if (callback_data and (
                callback_data.startswith('kingdom_war') or
                callback_data.startswith('attack_kingdom_') or
                callback_data.startswith('defend_kingdom_') or
                callback_data in ['main_menu', 'battle_menu', 'profile', 'kingdom_wars', 'war_results']
            )):
                return await handler(event, data)
            
            # Check if action should be blocked
            if callback_data and any(action in callback_data for action in self.blocked_actions):
                try:
                    is_blocked, block_message = await self.war_service.check_user_war_block(user.id)
                    if is_blocked:
                        await event.answer(block_message, show_alert=True)
                        return  # Block the action
                except Exception as e:
                    logger.error(f"Error checking war block for user {user.id}: {e}")
        
        # For text commands, check specific ones
        elif isinstance(event, Message) and event.text:
            blocked_commands = ['/shop', '/inventory', '/battle', '/dungeon']
            if any(event.text.startswith(cmd) for cmd in blocked_commands):
                try:
                    is_blocked, block_message = await self.war_service.check_user_war_block(user.id)
                    if is_blocked:
                        await event.reply(block_message)
                        return  # Block the action
                except Exception as e:
                    logger.error(f"Error checking war block for user {user.id}: {e}")
        
        return await handler(event, data)