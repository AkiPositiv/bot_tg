from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.main_menu import profile_menu_keyboard
from config.settings import GameConstants
from services.user_service import UserService

router = Router()

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery, user, is_registered: bool):
    """Show user profile"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    kingdom_info = GameConstants.KINGDOMS[user.kingdom.value]
    gender_text = "👨 Мужской" if user.gender.value == "male" else "👩 Женский"
    
    # Calculate experience needed for next level
    from utils.formulas import GameFormulas
    exp_needed = GameFormulas.experience_for_level(user.level + 1)
    
    profile_text = (
        f"👤 <b>Профиль игрока</b>\n\n"
        f"📝 Имя: <b>{user.name}</b>\n"
        f"👤 Пол: <b>{gender_text}</b>\n"
        f"🏰 Королевство: <b>{kingdom_info['emoji']} {kingdom_info['name']}</b>\n"
        f"⭐ Уровень: <b>{user.level}</b>\n"
        f"⚡ Опыт: <b>{user.experience}/{exp_needed}</b>\n\n"
        
        f"💪 <b>Характеристики:</b>\n"
        f"⚔️ Сила: <b>{user.strength}</b>\n"
        f"🛡️ Броня: <b>{user.armor}</b>\n"
        f"❤️ Здоровье: <b>{user.current_hp}/{user.hp}</b>\n"
        f"💨 Проворность: <b>{user.agility}</b>\n"
        f"🔮 Мана: <b>{user.current_mana}/{user.mana}</b>\n\n"
        
        f"💰 <b>Ресурсы:</b>\n"
        f"🪙 Деньги: <b>{user.money}</b> золота\n"
        f"💎 Камни: <b>{user.stones}</b>\n\n"
        
        f"⚔️ <b>Статистика боев:</b>\n"
        f"🏆 PvP побед: <b>{user.pvp_wins}</b>\n"
        f"💀 PvP поражений: <b>{user.pvp_losses}</b>\n"
        f"🤖 PvE побед: <b>{user.pve_wins}</b>\n"
        f"⚡ Всего урона: <b>{user.total_damage_dealt}</b>\n"
    )
    
    if user.free_stat_points > 0:
        profile_text += f"\n⭐ <b>Свободных очков характеристик: {user.free_stat_points}</b>"
    
    await callback.message.edit_text(
        profile_text,
        reply_markup=profile_menu_keyboard(user.free_stat_points > 0)
    )
    await callback.answer()

@router.callback_query(F.data == "view_stats")
async def view_detailed_stats(callback: CallbackQuery, user, is_registered: bool):
    """Show detailed character stats"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    # Calculate derived stats
    crit_chance = min(user.agility / 200.0, 0.3) * 100
    dodge_chance = min(user.agility / 300.0, 0.2) * 100
    
    stats_text = (
        f"📊 <b>Подробная статистика</b>\n\n"
        f"💪 <b>Базовые характеристики:</b>\n"
        f"⚔️ Сила: <b>{user.strength}</b>\n"
        f"   └ Урон в бою: <b>+{user.strength}</b>\n"
        f"🛡️ Броня: <b>{user.armor}</b>\n"
        f"   └ Поглощение урона: <b>{int(user.armor * 0.8)}</b>\n"
        f"❤️ Здоровье: <b>{user.hp}</b>\n"
        f"   └ Текущее: <b>{user.current_hp}/{user.hp}</b>\n"
        f"💨 Проворность: <b>{user.agility}</b>\n"
        f"   └ Шанс крита: <b>{crit_chance:.1f}%</b>\n"
        f"   └ Шанс уклонения: <b>{dodge_chance:.1f}%</b>\n"
        f"🔮 Мана: <b>{user.mana}</b>\n"
        f"   └ Текущая: <b>{user.current_mana}/{user.mana}</b>\n\n"
        
        f"📈 <b>Производные характеристики:</b>\n"
        f"⚡ Общая сила: <b>{user.total_stats}</b>\n"
        f"🎯 Базовый урон: <b>{user.strength + int(user.agility * 0.5)}</b>\n"
        f"🛡️ Физическая защита: <b>{int(user.armor * 0.8)}</b>\n"
    )
    
    if user.free_stat_points > 0:
        stats_text += f"\n⭐ <b>Свободных очков: {user.free_stat_points}</b>"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад к профилю", callback_data="profile")]
    ])
    
    await callback.message.edit_text(stats_text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "battle_statistics")
async def show_battle_stats(callback: CallbackQuery, user, is_registered: bool):
    """Show battle statistics"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    total_battles = user.pvp_wins + user.pvp_losses
    winrate = (user.pvp_wins / total_battles * 100) if total_battles > 0 else 0
    
    stats_text = (
        f"⚔️ <b>Статистика сражений</b>\n\n"
        f"🏆 <b>PvP сражения:</b>\n"
        f"✅ Победы: <b>{user.pvp_wins}</b>\n"
        f"❌ Поражения: <b>{user.pvp_losses}</b>\n"
        f"📊 Винрейт: <b>{winrate:.1f}%</b>\n\n"
        
        f"🤖 <b>PvE сражения:</b>\n"
        f"✅ Победы: <b>{user.pve_wins}</b>\n\n"
        
        f"⚡ <b>Урон:</b>\n"
        f"⚔️ Нанесено: <b>{user.total_damage_dealt}</b>\n"
        f"🛡️ Получено: <b>{user.total_damage_received}</b>\n"
    )
    
    if total_battles > 0:
        avg_damage = user.total_damage_dealt // total_battles
        stats_text += f"📈 Средний урон за бой: <b>{avg_damage}</b>\n"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад к профилю", callback_data="profile")]
    ])
    
    await callback.message.edit_text(stats_text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.in_(["achievements", "quests"]))
async def placeholder_handlers(callback: CallbackQuery):
    """Placeholder for future features"""
    feature_name = "Достижения" if callback.data == "achievements" else "Квесты"
    await callback.answer(f"{feature_name} будут добавлены в следующих обновлениях!", show_alert=True)