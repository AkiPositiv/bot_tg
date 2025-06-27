from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from services.user_service import UserService

class AuthMiddleware(BaseMiddleware):
    def __init__(self, user_service: UserService):
        self.user_service = user_service
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Get user_id from event
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id
            
            # Get user from database
            user = await self.user_service.get_user(user_id)
            
            # Add user data to handler context
            data['user'] = user
            data['is_registered'] = user is not None
            
            # Update last active timestamp if user exists
            if user:
                await self.user_service.update_last_active(user_id)
        
        return await handler(event, data)