from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
        InlineKeyboardButton(text="⚔️ Сражение", callback_data="battle_menu")
    )
    builder.row(
        InlineKeyboardButton(text="🏰 Подземелья", callback_data="dungeon_menu"),
        InlineKeyboardButton(text="🛒 Магазин", callback_data="shop_menu")
    )
    builder.row(
        InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory"),
        InlineKeyboardButton(text="📚 Навыки", callback_data="skills_menu")
    )
    builder.row(
        InlineKeyboardButton(text="🏆 События", callback_data="events"),
        InlineKeyboardButton(text="📊 Рейтинги", callback_data="leaderboards")
    )
    
    return builder.as_markup()

def kingdom_selection_keyboard() -> InlineKeyboardMarkup:
    """Kingdom selection keyboard"""
    builder = InlineKeyboardBuilder()
    
    kingdoms = [
        ("❄️ Северное", "kingdom_north"),
        ("🌅 Западное", "kingdom_west"),
        ("🌸 Восточное", "kingdom_east"),
        ("🔥 Южное", "kingdom_south")
    ]
    
    for name, callback in kingdoms:
        builder.row(InlineKeyboardButton(text=name, callback_data=callback))
    
    return builder.as_markup()

def gender_selection_keyboard() -> InlineKeyboardMarkup:
    """Gender selection keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="👨 Мужской", callback_data="gender_male"),
        InlineKeyboardButton(text="👩 Женский", callback_data="gender_female")
    )
    
    return builder.as_markup()

def battle_menu_keyboard() -> InlineKeyboardMarkup:
    """Battle menu keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="⚔️ PvP битва", callback_data="pvp_battle"),
        InlineKeyboardButton(text="🤖 Тренировка", callback_data="training_battle")
    )
    builder.row(
        InlineKeyboardButton(text="🎯 Интерактивный PvE", callback_data="enhanced_pve_encounter"),
        InlineKeyboardButton(text="⚔️ Интерактивный PvP", callback_data="interactive_pvp")
    )
    builder.row(
        InlineKeyboardButton(text="🏰 Атака королевства", callback_data="kingdom_attack"),
        InlineKeyboardButton(text="🛡️ Защита", callback_data="kingdom_defense")
    )
    builder.row(
        InlineKeyboardButton(text="👑 Королевские битвы", callback_data="kingdom_wars")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика боев", callback_data="battle_stats"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    )
    
    return builder.as_markup()

def kingdom_attack_keyboard(user_kingdom: str) -> InlineKeyboardMarkup:
    """Kingdom attack selection keyboard"""
    builder = InlineKeyboardBuilder()
    
    kingdoms = {
        'north': '❄️ Северное',
        'west': '🌅 Западное', 
        'east': '🌸 Восточное',
        'south': '🔥 Южное'
    }
    
    for kingdom_id, kingdom_name in kingdoms.items():
        if kingdom_id != user_kingdom:  # Can't attack own kingdom
            builder.row(InlineKeyboardButton(
                text=kingdom_name, 
                callback_data=f"attack_{kingdom_id}"
            ))
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="battle_menu"))
    return builder.as_markup()

def battle_accept_keyboard(battle_id: int) -> InlineKeyboardMarkup:
    """Battle accept/decline keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_battle_{battle_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline_battle_{battle_id}")
    )
    
    return builder.as_markup()

def profile_menu_keyboard(has_free_points: bool = False) -> InlineKeyboardMarkup:
    """Profile menu keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📊 Характеристики", callback_data="view_stats"),
        InlineKeyboardButton(text="🏆 Достижения", callback_data="achievements")
    )
    
    if has_free_points:
        builder.row(InlineKeyboardButton(
            text="⭐ Распределить очки", 
            callback_data="distribute_stats"
        ))
    
    builder.row(
        InlineKeyboardButton(text="⚖️ Статистика боев", callback_data="battle_statistics"),
        InlineKeyboardButton(text="🎯 Квесты", callback_data="quests")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    )
    
    return builder.as_markup()