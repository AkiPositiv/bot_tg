import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: int = 30):
        self.rate_limit = rate_limit  # requests per minute
        self.user_requests = {}  # {user_id: [timestamps]}
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id
            current_time = time.time()
            
            # Initialize user request list
            if user_id not in self.user_requests:
                self.user_requests[user_id] = []
            
            # Remove old requests (older than 1 minute)
            self.user_requests[user_id] = [
                timestamp for timestamp in self.user_requests[user_id]
                if current_time - timestamp < 60
            ]
            
            # Check rate limit
            if len(self.user_requests[user_id]) >= self.rate_limit:
                if isinstance(event, Message):
                    await event.answer("⚠️ Слишком много запросов. Подождите немного.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⚠️ Слишком много запросов!", show_alert=True)
                return
            
            # Add current request
            self.user_requests[user_id].append(current_time)
        
        return await handler(event, data)