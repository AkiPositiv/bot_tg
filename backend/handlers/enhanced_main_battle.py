from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from services.enhanced_kingdom_war_service import EnhancedKingdomWarService
from keyboards.main_menu import battle_menu_keyboard

router = Router()

@router.callback_query(F.data == "enhanced_battle_menu")
async def show_enhanced_battle_menu(callback: CallbackQuery, user, is_registered: bool):
    """Show enhanced battle menu with war blocking check"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    # Check if user is blocked due to war participation
    war_service = EnhancedKingdomWarService()
    is_blocked, block_message = await war_service.check_user_war_block(user.id)
    
    if is_blocked:
        await callback.message.edit_text(
            f"⚔️ <b>Заблокировано</b>\n\n"
            f"🚫 {block_message}\n\n"
            f"Вы не можете выполнять другие действия, пока идёт война королевств.\n"
            f"Дождитесь окончания сражения.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Проверить статус", callback_data="enhanced_battle_menu")],
                [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
            ])
        )
        await callback.answer()
        return
    
    # Show enhanced battle menu
    battle_text = (
        f"⚔️ <b>Меню сражений v3.0</b>\n\n"
        f"👤 {user.name} | Уровень {user.level}\n"
        f"💪 Сила: {user.strength} | 🛡️ Броня: {user.armor}\n"
        f"❤️ HP: {user.current_hp}/{user.hp} | 🔮 Мана: {user.current_mana}/{user.mana}\n\n"
        
        f"🆕 <b>Новые возможности:</b>\n"
        f"🎯 Интерактивные PvE бои с выбором действий\n"
        f"⚔️ Интерактивные PvP битвы между игроками\n"
        f"🏰 Участие в войнах королевств\n"
        f"✨ Автоматическое применение навыков\n\n"
        
        f"Выберите тип сражения:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎯 Интерактивный PvE", callback_data="enhanced_pve_encounter"),
            InlineKeyboardButton(text="⚔️ Интерактивный PvP", callback_data="interactive_pvp")
        ],
        [
            InlineKeyboardButton(text="🤖 Быстрая тренировка", callback_data="quick_training"),
            InlineKeyboardButton(text="🏰 Атака королевства", callback_data="kingdom_attack")
        ],
        [
            InlineKeyboardButton(text="🛡️ Защита королевства", callback_data="kingdom_defense"),
            InlineKeyboardButton(text="⚔️ Войны королевств", callback_data="kingdom_wars_menu")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика боев", callback_data="battle_stats"),
            InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
        ]
    ])
    
    await callback.message.edit_text(battle_text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "kingdom_wars_menu")
async def show_kingdom_wars_menu(callback: CallbackQuery, user, is_registered: bool):
    """Show kingdom wars menu with schedule"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    from datetime import datetime
    import pytz
    
    # Get current time in Tashkent timezone
    tashkent_tz = pytz.timezone('Asia/Tashkent')
    current_time = datetime.now(tashkent_tz)
    
    # Calculate next war times
    war_times = [8, 13, 18]
    next_wars = []
    
    for hour in war_times:
        war_time = current_time.replace(hour=hour, minute=0, second=0, microsecond=0)
        if war_time <= current_time:
            # Add one day if time has passed
            war_time = war_time.replace(day=war_time.day + 1)
        next_wars.append(war_time)
    
    # Sort by time
    next_wars.sort()
    next_war = next_wars[0]
    
    wars_text = (
        f"🏰 <b>Войны Королевств</b>\n\n"
        f"⏰ <b>Расписание войн:</b>\n"
        f"🌅 8:00 - Утренняя атака\n"
        f"🌞 13:00 - Дневное сражение\n"
        f"🌆 18:00 - Вечерняя битва\n"
        f"<i>Время: Ташкентское (UTC+5)</i>\n\n"
        
        f"🔥 <b>Следующая война:</b>\n"
        f"📅 {next_war.strftime('%d.%m.%Y в %H:%M')}\n"
        f"⏳ Осталось: <b>{format_time_until(next_war, current_time)}</b>\n\n"
        
        f"👤 <b>Ваше королевство:</b>\n"
        f"🏰 {get_kingdom_emoji(user.kingdom.value)} {get_kingdom_name(user.kingdom.value)}\n\n"
        
        f"💡 <b>Как участвовать:</b>\n"
        f"🗡️ Атакуйте вражеские королевства\n"
        f"🛡️ Защищайте своё королевство\n"
        f"💰 Получайте 40% денег побеждённых\n"
        f"⚡ Зарабатывайте опыт за участие"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗡️ Присоединиться к атаке", callback_data="join_attack_menu"),
            InlineKeyboardButton(text="🛡️ Защищать королевство", callback_data="join_defense")
        ],
        [
            InlineKeyboardButton(text="📊 Мои результаты войн", callback_data="my_war_results"),
            InlineKeyboardButton(text="🏆 Статистика королевств", callback_data="kingdom_stats")
        ],
        [
            InlineKeyboardButton(text="❓ Правила войн", callback_data="war_rules"),
            InlineKeyboardButton(text="🔙 Назад", callback_data="enhanced_battle_menu")
        ]
    ])
    
    await callback.message.edit_text(wars_text, reply_markup=keyboard)
    await callback.answer()

def get_kingdom_emoji(kingdom: str) -> str:
    """Get kingdom emoji"""
    emojis = {
        'north': '❄️',
        'west': '🌅',
        'east': '🌸',
        'south': '🔥'
    }
    return emojis.get(kingdom, '🏰')

def get_kingdom_name(kingdom: str) -> str:
    """Get kingdom name"""
    names = {
        'north': 'Северное королевство',
        'west': 'Западное королевство',
        'east': 'Восточное королевство',
        'south': 'Южное королевство'
    }
    return names.get(kingdom, 'Неизвестное королевство')

def format_time_until(target_time, current_time):
    """Format time until target"""
    delta = target_time - current_time
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    if delta.days > 0:
        return f"{delta.days}д {hours}ч {minutes}м"
    elif hours > 0:
        return f"{hours}ч {minutes}м"
    else:
        return f"{minutes}м"

@router.callback_query(F.data == "join_attack_menu")
async def show_join_attack_menu(callback: CallbackQuery, user, is_registered: bool):
    """Show menu to join attack on kingdoms"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    from config.settings import GameConstants
    
    attack_text = (
        f"🗡️ <b>Присоединиться к атаке</b>\n\n"
        f"👤 Ваше королевство: {get_kingdom_emoji(user.kingdom.value)} {get_kingdom_name(user.kingdom.value)}\n\n"
        f"⚔️ Выберите цель для атаки:\n"
        f"<i>Вы не можете атаковать своё королевство</i>\n\n"
        
        f"⚠️ <b>Внимание!</b>\n"
        f"После присоединения к атаке все остальные\n"
        f"действия будут заблокированы до окончания войны."
    )
    
    builder = InlineKeyboardBuilder()
    
    # Show other kingdoms for attack
    kingdoms = {
        'north': '❄️ Северное',
        'west': '🌅 Западное',
        'east': '🌸 Восточное', 
        'south': '🔥 Южное'
    }
    
    for kingdom_id, kingdom_name in kingdoms.items():
        if kingdom_id != user.kingdom.value:
            builder.row(InlineKeyboardButton(
                text=f"🗡️ Атаковать {kingdom_name}",
                callback_data=f"join_attack_{kingdom_id}"
            ))
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="kingdom_wars_menu"))
    
    await callback.message.edit_text(attack_text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("join_attack_"))
async def join_attack_squad(callback: CallbackQuery, user, is_registered: bool):
    """Join attack squad for specific kingdom"""
    target_kingdom = callback.data.replace("join_attack_", "")
    
    # Get next war time
    from datetime import datetime
    import pytz
    
    tashkent_tz = pytz.timezone('Asia/Tashkent')
    current_time = datetime.now(tashkent_tz)
    
    # Find next war time
    war_times = [8, 13, 18]
    next_war_time = None
    
    for hour in war_times:
        war_time = current_time.replace(hour=hour, minute=0, second=0, microsecond=0)
        if war_time > current_time:
            next_war_time = war_time
            break
    
    if not next_war_time:
        # Tomorrow's first war
        tomorrow = current_time.replace(day=current_time.day + 1, hour=8, minute=0, second=0, microsecond=0)
        next_war_time = tomorrow
    
    # Convert to UTC for storage
    next_war_time_utc = next_war_time.astimezone(pytz.UTC)
    
    war_service = EnhancedKingdomWarService()
    success, message = await war_service.join_attack_squad(user.id, target_kingdom, next_war_time_utc)
    
    if success:
        result_text = (
            f"✅ <b>Присоединение к атаке!</b>\n\n"
            f"{message}\n\n"
            f"🎯 Цель: {get_kingdom_emoji(target_kingdom)} {get_kingdom_name(target_kingdom)}\n"
            f"⏰ Время войны: {next_war_time.strftime('%d.%m.%Y в %H:%M')}\n\n"
            
            f"🚫 <b>Внимание:</b>\n"
            f"Теперь все остальные действия заблокированы\n"
            f"до окончания войны королевств.\n\n"
            
            f"Дождитесь начала сражения!"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏰 Статус войны", callback_data="kingdom_wars_menu")],
            [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
        ])
    else:
        result_text = (
            f"❌ <b>Ошибка присоединения</b>\n\n"
            f"{message}\n\n"
            f"Попробуйте ещё раз или выберите другую цель."
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="join_attack_menu")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="kingdom_wars_menu")]
        ])
    
    await callback.message.edit_text(result_text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "join_defense")
async def join_defense_squad(callback: CallbackQuery, user, is_registered: bool):
    """Join defense squad for own kingdom"""
    # Get next war time
    from datetime import datetime
    import pytz
    
    tashkent_tz = pytz.timezone('Asia/Tashkent')
    current_time = datetime.now(tashkent_tz)
    
    # Find next war time
    war_times = [8, 13, 18]
    next_war_time = None
    
    for hour in war_times:
        war_time = current_time.replace(hour=hour, minute=0, second=0, microsecond=0)
        if war_time > current_time:
            next_war_time = war_time
            break
    
    if not next_war_time:
        # Tomorrow's first war
        tomorrow = current_time.replace(day=current_time.day + 1, hour=8, minute=0, second=0, microsecond=0)
        next_war_time = tomorrow
    
    # Convert to UTC for storage
    next_war_time_utc = next_war_time.astimezone(pytz.UTC)
    
    war_service = EnhancedKingdomWarService()
    success, message = await war_service.join_defense_squad(user.id, next_war_time_utc)
    
    if success:
        result_text = (
            f"🛡️ <b>Присоединение к защите!</b>\n\n"
            f"{message}\n\n"
            f"🏰 Защищаете: {get_kingdom_emoji(user.kingdom.value)} {get_kingdom_name(user.kingdom.value)}\n"
            f"⏰ Время войны: {next_war_time.strftime('%d.%m.%Y в %H:%M')}\n\n"
            
            f"💪 <b>Преимущества защитников:</b>\n"
            f"• +30% к броне при атаке нескольких королевств\n"
            f"• Восстановление после каждой волны атаки\n"
            f"• Получение денег при успешной защите\n\n"
            
            f"🚫 <b>Внимание:</b>\n"
            f"Все остальные действия заблокированы\n"
            f"до окончания войны."
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏰 Статус войны", callback_data="kingdom_wars_menu")],
            [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
        ])
    else:
        result_text = (
            f"❌ <b>Ошибка присоединения</b>\n\n"
            f"{message}\n\n"
            f"Попробуйте ещё раз."
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="join_defense")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="kingdom_wars_menu")]
        ])
    
    await callback.message.edit_text(result_text, reply_markup=keyboard)
    await callback.answer()

# Placeholder handlers for other war-related functions
@router.callback_query(F.data.in_(["my_war_results", "kingdom_stats", "war_rules"]))
async def war_placeholder_handlers(callback: CallbackQuery):
    """Placeholder handlers for war features"""
    feature_names = {
        "my_war_results": "Результаты войн",
        "kingdom_stats": "Статистика королевств",
        "war_rules": "Правила войн"
    }
    
    feature_name = feature_names.get(callback.data, "Эта функция")
    await callback.answer(f"{feature_name} будут добавлены в следующих обновлениях!", show_alert=True)

from aiogram.utils.keyboard import InlineKeyboardBuilder