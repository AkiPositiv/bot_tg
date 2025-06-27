from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from keyboards.main_menu import battle_menu_keyboard, kingdom_attack_keyboard, battle_accept_keyboard
from services.battle_service import BattleService
from services.user_service import UserService
from config.settings import GameConstants
from sqlalchemy import select
from config.database import AsyncSessionLocal
from models.user import User
import random

router = Router()

@router.callback_query(F.data == "battle_menu")
async def show_battle_menu(callback: CallbackQuery, user, is_registered: bool):
    """Show battle menu"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    await callback.message.edit_text(
        f"⚔️ <b>Меню сражений</b>\n\n"
        f"👤 {user.name} | Уровень {user.level}\n"
        f"💪 Сила: {user.strength} | 🛡️ Броня: {user.armor}\n"
        f"❤️ HP: {user.current_hp}/{user.hp} | 🔮 Мана: {user.current_mana}/{user.mana}\n\n"
        f"Выберите тип сражения:",
        reply_markup=battle_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "kingdom_attack")
async def show_kingdom_attack(callback: CallbackQuery, user, is_registered: bool):
    """Show kingdom attack menu"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    kingdom_info = GameConstants.KINGDOMS[user.kingdom.value]
    
    await callback.message.edit_text(
        f"🏰 <b>Атака королевства</b>\n\n"
        f"Вы представитель {kingdom_info['emoji']} <b>{kingdom_info['name']}</b>\n\n"
        f"Выберите королевство для атаки:\n"
        f"(Игроки вашего королевства не отображаются)",
        reply_markup=kingdom_attack_keyboard(user.kingdom.value)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("attack_"))
async def attack_kingdom(callback: CallbackQuery, user, is_registered: bool):
    """Show players from target kingdom"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    target_kingdom = callback.data.replace("attack_", "")
    kingdom_info = GameConstants.KINGDOMS[target_kingdom]
    
    # Get online players from target kingdom (level range ±5)
    async with AsyncSessionLocal() as session:
        min_level = max(1, user.level - 5)
        max_level = user.level + 5
        
        result = await session.execute(
            select(User).where(
                User.kingdom == target_kingdom,
                User.level >= min_level,
                User.level <= max_level,
                User.id != user.id,
                User.is_active == True
            ).limit(10)
        )
        players = result.scalars().all()
    
    if not players:
        await callback.answer(
            f"В {kingdom_info['name']} нет подходящих противников!\n"
            f"Ищем игроков уровня {min_level}-{max_level}",
            show_alert=True
        )
        return
    
    # Create player selection keyboard
    builder = InlineKeyboardBuilder()
    for player in players:
        player_text = f"⚔️ {player.name} | Ур.{player.level}"
        builder.row(InlineKeyboardButton(
            text=player_text,
            callback_data=f"challenge_{player.id}"
        ))
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="kingdom_attack"))
    
    await callback.message.edit_text(
        f"🏰 <b>Игроки {kingdom_info['emoji']} {kingdom_info['name']}</b>\n\n"
        f"Выберите противника для вызова на бой:\n"
        f"(Показаны игроки уровня {min_level}-{max_level})",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("challenge_"))
async def challenge_player(callback: CallbackQuery, user, is_registered: bool):
    """Challenge player to battle"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    defender_id = int(callback.data.replace("challenge_", ""))
    
    # Check if user has enough HP
    if user.current_hp < user.hp * 0.3:  # Need at least 30% HP
        await callback.answer(
            "❤️ Недостаточно здоровья для боя!\n"
            "Нужно минимум 30% HP",
            show_alert=True
        )
        return
    
    # Get defender info
    async with AsyncSessionLocal() as session:
        defender = await session.get(User, defender_id)
        if not defender:
            await callback.answer("Игрок не найден!", show_alert=True)
            return
    
    # Create battle
    battle_service = BattleService()
    battle = await battle_service.create_pvp_battle(user.id, defender_id)
    
    # Notify challenger
    await callback.message.edit_text(
        f"⚔️ <b>Вызов отправлен!</b>\n\n"
        f"Вы вызвали на бой <b>{defender.name}</b> (Ур.{defender.level})\n"
        f"Ожидаем ответа противника...\n\n"
        f"ID битвы: #{battle.id}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="battle_menu")]
        ])
    )
    
    # Here we would normally send notification to defender via bot
    # For now just show success message
    await callback.answer("✅ Вызов отправлен!")

@router.callback_query(F.data == "pvp_battle")
async def show_pvp_battles(callback: CallbackQuery, user, is_registered: bool):
    """Show pending PvP battles for user"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    battle_service = BattleService()
    pending_battles = await battle_service.get_pending_battles(user.id)
    
    if not pending_battles:
        await callback.message.edit_text(
            f"⚔️ <b>PvP Сражения</b>\n\n"
            f"У вас нет входящих вызовов на бой.\n\n"
            f"Чтобы сразиться с кем-то:\n"
            f"1. Выберите 'Атака королевства'\n"
            f"2. Выберите целевое королевство\n"
            f"3. Вызовите игрока на бой",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏰 Атака королевства", callback_data="kingdom_attack")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="battle_menu")]
            ])
        )
        await callback.answer()
        return
    
    # Show pending battles
    builder = InlineKeyboardBuilder()
    
    for battle in pending_battles:
        # Get challenger info
        async with AsyncSessionLocal() as session:
            challenger = await session.get(User, battle.challenger_id)
        
        if challenger:
            builder.row(InlineKeyboardButton(
                text=f"⚔️ {challenger.name} (Ур.{challenger.level})",
                callback_data=f"view_battle_{battle.id}"
            ))
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="battle_menu"))
    
    await callback.message.edit_text(
        f"⚔️ <b>Входящие вызовы</b>\n\n"
        f"У вас {len(pending_battles)} входящих вызовов на бой:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("view_battle_"))
async def view_battle_challenge(callback: CallbackQuery, user, is_registered: bool):
    """View battle challenge details"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    battle_id = int(callback.data.replace("view_battle_", ""))
    battle_service = BattleService()
    battle = await battle_service.get_battle(battle_id)
    
    if not battle or battle.defender_id != user.id:
        await callback.answer("Битва не найдена!", show_alert=True)
        return
    
    # Get challenger info
    async with AsyncSessionLocal() as session:
        challenger = await session.get(User, battle.challenger_id)
    
    if not challenger:
        await callback.answer("Противник не найден!", show_alert=True)
        return
    
    kingdom_info = GameConstants.KINGDOMS[challenger.kingdom.value]
    
    battle_text = (
        f"⚔️ <b>Вызов на бой</b>\n\n"
        f"🎯 Противник: <b>{challenger.name}</b>\n"
        f"⭐ Уровень: <b>{challenger.level}</b>\n"
        f"🏰 Королевство: <b>{kingdom_info['emoji']} {kingdom_info['name']}</b>\n\n"
        
        f"💪 <b>Характеристики противника:</b>\n"
        f"⚔️ Сила: <b>{challenger.strength}</b>\n"
        f"🛡️ Броня: <b>{challenger.armor}</b>\n"
        f"❤️ Здоровье: <b>{challenger.hp}</b>\n"
        f"💨 Проворность: <b>{challenger.agility}</b>\n\n"
        
        f"🏆 Статистика: {challenger.pvp_wins}W/{challenger.pvp_losses}L\n\n"
        f"Принять вызов?"
    )
    
    await callback.message.edit_text(
        battle_text,
        reply_markup=battle_accept_keyboard(battle_id)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("accept_battle_"))
async def accept_battle(callback: CallbackQuery, user, is_registered: bool):
    """Accept battle challenge"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    battle_id = int(callback.data.replace("accept_battle_", ""))
    
    # Check if user has enough HP
    if user.current_hp < user.hp * 0.3:  # Need at least 30% HP
        await callback.answer(
            "❤️ Недостаточно здоровья для боя!\n"
            "Нужно минимум 30% HP",
            show_alert=True
        )
        return
    
    battle_service = BattleService()
    success = await battle_service.accept_battle(battle_id)
    
    if not success:
        await callback.answer("Не удалось принять вызов!", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"⚔️ <b>Битва началась!</b>\n\n"
        f"⏳ Идёт автоматический расчёт боя...\n"
        f"Результат будет готов через несколько секунд.\n\n"
        f"ID битвы: #{battle_id}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Проверить результат", callback_data=f"check_result_{battle_id}")],
            [InlineKeyboardButton(text="🔙 В меню", callback_data="battle_menu")]
        ])
    )
    await callback.answer("✅ Битва началась!")

@router.callback_query(F.data.startswith("decline_battle_"))
async def decline_battle(callback: CallbackQuery, user, is_registered: bool):
    """Decline battle challenge"""
    battle_id = int(callback.data.replace("decline_battle_", ""))
    
    # Update battle status to cancelled
    # For now just show message
    await callback.message.edit_text(
        f"❌ <b>Вызов отклонён</b>\n\n"
        f"Вы отклонили вызов на бой.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="pvp_battle")]
        ])
    )
    await callback.answer("Вызов отклонён!")

@router.callback_query(F.data.startswith("check_result_"))
async def check_battle_result(callback: CallbackQuery, user, is_registered: bool):
    """Check battle result"""
    battle_id = int(callback.data.replace("check_result_", ""))
    battle_service = BattleService()
    battle = await battle_service.get_battle(battle_id)
    
    if not battle:
        await callback.answer("Битва не найдена!", show_alert=True)
        return
    
    if battle.status.value != "finished":
        await callback.answer("Битва ещё не завершена! Подождите...", show_alert=True)
        return
    
    # Get participants
    async with AsyncSessionLocal() as session:
        challenger = await session.get(User, battle.challenger_id)
        defender = await session.get(User, battle.defender_id)
        winner = await session.get(User, battle.winner_id)
    
    # Determine if user won
    user_won = (battle.winner_id == user.id)
    opponent = challenger if user.id == battle.defender_id else defender
    
    result_emoji = "🏆" if user_won else "💀"
    result_text = "ПОБЕДА" if user_won else "ПОРАЖЕНИЕ"
    
    battle_text = (
        f"{result_emoji} <b>{result_text}!</b>\n\n"
        f"⚔️ <b>Результат битвы #{battle_id}</b>\n\n"
        f"👤 Ваш противник: <b>{opponent.name}</b>\n"
        f"🏆 Победитель: <b>{winner.name}</b>\n"
        f"⏱️ Продолжительность: <b>{battle.total_turns} ходов</b>\n\n"
    )
    
    if user_won:
        battle_text += (
            f"🎁 <b>Награды:</b>\n"
            f"⚡ Опыт: <b>+{battle.exp_gained}</b>\n"
            f"💰 Деньги: <b>+{battle.money_gained}</b> золота\n\n"
        )
    
    # Show some battle log highlights
    damage_log = battle.get_damage_log()
    if damage_log:
        battle_text += f"📊 <b>Ключевые моменты боя:</b>\n"
        for i, log_entry in enumerate(damage_log[-3:]):  # Last 3 actions
            if log_entry['result'] == 'critical':
                battle_text += f"💥 {log_entry['attacker']}: Крит! {log_entry['damage']} урона\n"
            elif log_entry['result'] == 'dodged':
                battle_text += f"💨 Уклонение от атаки {log_entry['attacker']}\n"
    
    await callback.message.edit_text(
        battle_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 В меню битв", callback_data="battle_menu")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data == "battle_stats")
async def show_battle_stats(callback: CallbackQuery, user, is_registered: bool):
    """Show battle statistics"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    total_battles = user.pvp_wins + user.pvp_losses
    winrate = (user.pvp_wins / total_battles * 100) if total_battles > 0 else 0
    
    stats_text = (
        f"📊 <b>Статистика сражений</b>\n\n"
        f"👤 Игрок: <b>{user.name}</b>\n"
        f"⭐ Уровень: <b>{user.level}</b>\n\n"
        
        f"⚔️ <b>PvP битвы:</b>\n"
        f"🏆 Победы: <b>{user.pvp_wins}</b>\n"
        f"💀 Поражения: <b>{user.pvp_losses}</b>\n"
        f"📊 Винрейт: <b>{winrate:.1f}%</b>\n\n"
        
        f"🤖 <b>PvE битвы:</b>\n"
        f"✅ Победы: <b>{user.pve_wins}</b>\n\n"
        
        f"⚡ <b>Урон:</b>\n"
        f"⚔️ Нанесено: <b>{user.total_damage_dealt}</b>\n"
        f"🛡️ Получено: <b>{user.total_damage_received}</b>\n"
    )
    
    if total_battles > 0:
        avg_damage = user.total_damage_dealt // total_battles
        stats_text += f"📈 Средний урон за бой: <b>{avg_damage}</b>\n"
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="battle_menu")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data == "training_battle")
async def show_training_options(callback: CallbackQuery, user, is_registered: bool):
    """Show training battle options"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    training_text = (
        f"🤖 <b>Тренировочные бои</b>\n\n"
        f"Выберите тип тренировки:\n\n"
        f"⚔️ <b>Быстрый бой</b> - автоматический бой против ИИ\n"
        f"🎯 <b>Интерактивный бой</b> - пошаговая битва с выбором действий\n\n"
        f"💡 Интерактивные бои дают больше опыта!"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Быстрый бой", callback_data="quick_training")],
        [InlineKeyboardButton(text="🎯 Интерактивный бой", callback_data="pve_encounter")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="battle_menu")]
    ])
    
    await callback.message.edit_text(training_text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "quick_training")
async def training_battle(callback: CallbackQuery, user, is_registered: bool):
    """Training battle against AI"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    # Generate AI opponent with similar stats
    ai_level = max(1, user.level + random.randint(-2, 2))
    ai_strength = user.strength + random.randint(-3, 3)
    ai_armor = user.armor + random.randint(-3, 3)
    ai_hp = user.hp + random.randint(-20, 20)
    ai_agility = user.agility + random.randint(-3, 3)
    
    # Simple battle simulation
    user_damage = max(1, user.strength + user.agility // 2 - ai_armor // 2)
    ai_damage = max(1, ai_strength + ai_agility // 2 - user.armor // 2)
    
    user_hp = user.current_hp
    ai_hp_current = max(50, ai_hp)
    
    # Quick battle simulation
    turns = 0
    while user_hp > 0 and ai_hp_current > 0 and turns < 20:
        # User attacks
        if random.random() > 0.1:  # 90% hit chance
            damage = user_damage + random.randint(-2, 5)
            ai_hp_current -= damage
        
        if ai_hp_current <= 0:
            break
            
        # AI attacks
        if random.random() > 0.1:  # 90% hit chance
            damage = ai_damage + random.randint(-2, 5)
            user_hp -= damage
            
        turns += 1
    
    # Determine result
    if user_hp > 0:
        result = "🏆 ПОБЕДА!"
        exp_reward = 20 + ai_level * 2
        money_reward = 10 + ai_level
        
        # Update user stats (simplified)
        user_service = UserService()
        await user_service.add_experience(user.id, exp_reward)
        await user_service.update_user(user.id, 
                                     money=user.money + money_reward,
                                     pve_wins=user.pve_wins + 1)
        
        result_text = (
            f"{result}\n\n"
            f"🤖 Противник: ИИ Боец (Ур.{ai_level})\n"
            f"⏱️ Продолжительность: {turns} ходов\n\n"
            f"🎁 Награды:\n"
            f"⚡ Опыт: +{exp_reward}\n"
            f"💰 Деньги: +{money_reward} золота"
        )
    else:
        result_text = (
            f"💀 ПОРАЖЕНИЕ!\n\n"
            f"🤖 Противник: ИИ Боец (Ур.{ai_level})\n"
            f"⏱️ Продолжительность: {turns} ходов\n\n"
            f"Не расстраивайтесь! Попробуйте ещё раз."
        )
    
    await callback.message.edit_text(
        f"🤖 <b>Тренировочный бой</b>\n\n{result_text}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Ещё бой", callback_data="training_battle")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="battle_menu")]
        ])
    )
    await callback.answer()

# Placeholder handlers for future features
@router.callback_query(F.data.in_(["dungeon_menu", "skills_menu", "events", "leaderboards"]))
async def placeholder_features(callback: CallbackQuery):
    """Placeholder for future features"""
    feature_names = {
        "dungeon_menu": "Подземелья",
        "skills_menu": "Навыки", 
        "events": "События",
        "leaderboards": "Таблица лидеров"
    }
    
    feature_name = feature_names.get(callback.data, "Эта функция")
    await callback.answer(f"{feature_name} будут добавлены в следующих обновлениях!", show_alert=True)

@router.callback_query(F.data == "inventory")
async def inventory_from_battle(callback: CallbackQuery, user, is_registered: bool):
    """Redirect to inventory from battle menu"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    # Import and use inventory handler
    from handlers.inventory import show_inventory
    await show_inventory(callback, user, is_registered)

@router.callback_query(F.data == "shop_menu")
async def shop_menu_from_battle(callback: CallbackQuery, user, is_registered: bool):
    """Redirect to shop menu from battle menu"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    # Import and use shop handler
    from handlers.shop import show_shop_menu
    await show_shop_menu(callback, user, is_registered)