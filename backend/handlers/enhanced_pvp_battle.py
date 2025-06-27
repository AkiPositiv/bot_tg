from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.enhanced_pvp_service import EnhancedPvPService
from models.interactive_battle import BattlePhaseEnum
from config.settings import GameConstants
import asyncio

router = Router()

@router.callback_query(F.data == "interactive_pvp")
async def show_interactive_pvp_menu(callback: CallbackQuery, user, is_registered: bool):
    """Show interactive PvP menu"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    if user.current_hp < user.hp * 0.3:
        await callback.answer("❤️ Недостаточно здоровья для боя! Нужно минимум 30% HP", show_alert=True)
        return
    
    menu_text = (
        f"⚔️ <b>Интерактивные PvP битвы</b>\n\n"
        f"🎯 <b>Новый формат сражений!</b>\n"
        f"• Пошаговые битвы с выбором действий\n"
        f"• 3 типа атак: Точный, Мощный, Обычный\n"
        f"• 3 направления уклонения\n"
        f"• Автоматическое применение навыков\n"
        f"• 50 секунд на каждый ход\n\n"
        
        f"👤 <b>Ваше состояние:</b>\n"
        f"❤️ HP: <b>{user.current_hp}/{user.hp}</b>\n"
        f"🔮 Мана: <b>{user.current_mana}/{user.mana}</b>\n"
        f"⚡ Уровень: <b>{user.level}</b>\n\n"
        
        f"Выберите королевство для поиска противников:"
    )
    
    builder = InlineKeyboardBuilder()
    
    # Kingdom selection for attack
    kingdoms = {
        'north': '❄️ Северное',
        'west': '🌅 Западное', 
        'east': '🌸 Восточное',
        'south': '🔥 Южное'
    }
    
    for kingdom_id, kingdom_name in kingdoms.items():
        if kingdom_id != user.kingdom.value:  # Can't attack own kingdom
            builder.row(InlineKeyboardButton(
                text=kingdom_name, 
                callback_data=f"pvp_select_{kingdom_id}"
            ))
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="battle_menu"))
    
    await callback.message.edit_text(menu_text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("pvp_select_"))
async def select_pvp_opponent(callback: CallbackQuery, user, is_registered: bool):
    """Select PvP opponent from kingdom"""
    target_kingdom = callback.data.replace("pvp_select_", "")
    
    # Get online players from target kingdom (simplified)
    from config.database import AsyncSessionLocal
    from models.user import User
    from sqlalchemy import select, and_
    
    async with AsyncSessionLocal() as session:
        min_level = max(1, user.level - 5)
        max_level = user.level + 5
        
        result = await session.execute(
            select(User).where(
                and_(
                    User.kingdom == target_kingdom,
                    User.level >= min_level,
                    User.level <= max_level,
                    User.id != user.id,
                    User.is_active == True,
                    User.current_hp >= User.hp * 0.3  # Must have enough HP
                )
            ).limit(10)
        )
        players = result.scalars().all()
    
    if not players:
        kingdom_info = GameConstants.KINGDOMS[target_kingdom]
        await callback.answer(
            f"В {kingdom_info['name']} нет подходящих противников для интерактивного PvP!\n"
            f"Ищем игроков уровня {min_level}-{max_level} с достаточным HP",
            show_alert=True
        )
        return
    
    # Create player selection menu
    builder = InlineKeyboardBuilder()
    kingdom_info = GameConstants.KINGDOMS[target_kingdom]
    
    menu_text = (
        f"⚔️ <b>Выбор противника</b>\n\n"
        f"🏰 {kingdom_info['emoji']} <b>{kingdom_info['name']}</b>\n"
        f"Игроки уровня {min_level}-{max_level}:\n\n"
    )
    
    for player in players[:8]:  # Show max 8 players
        # Calculate relative strength
        player_total = player.strength + player.armor + player.agility
        user_total = user.strength + user.armor + user.agility
        
        if player_total > user_total * 1.2:
            strength_indicator = "🔴 Сильнее"
        elif player_total < user_total * 0.8:
            strength_indicator = "🟢 Слабее"
        else:
            strength_indicator = "🟡 Равный"
        
        menu_text += (
            f"👤 <b>{player.name}</b> (Ур.{player.level})\n"
            f"📊 {strength_indicator} | "
            f"❤️ {player.current_hp}/{player.hp} | "
            f"🏆 {player.pvp_wins}W/{player.pvp_losses}L\n\n"
        )
        
        builder.row(InlineKeyboardButton(
            text=f"⚔️ Вызвать {player.name}",
            callback_data=f"challenge_interactive_{player.id}"
        ))
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="interactive_pvp"))
    
    await callback.message.edit_text(menu_text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("challenge_interactive_"))
async def challenge_interactive_pvp(callback: CallbackQuery, user, is_registered: bool):
    """Challenge player to interactive PvP"""
    defender_id = int(callback.data.replace("challenge_interactive_", ""))
    
    pvp_service = EnhancedPvPService()
    battle = await pvp_service.create_interactive_pvp_battle(user.id, defender_id)
    
    if not battle:
        await callback.answer("❌ Не удалось создать битву!", show_alert=True)
        return
    
    # Get defender info for display
    from config.database import AsyncSessionLocal
    from models.user import User
    
    async with AsyncSessionLocal() as session:
        defender = await session.get(User, defender_id)
    
    if not defender:
        await callback.answer("❌ Противник не найден!", show_alert=True)
        return
    
    # Notify challenger
    challenge_text = (
        f"⚔️ <b>Интерактивный вызов отправлен!</b>\n\n"
        f"🎯 Противник: <b>{defender.name}</b> (Ур.{defender.level})\n"
        f"🏰 Королевство: {GameConstants.KINGDOMS[defender.kingdom.value]['emoji']} {GameConstants.KINGDOMS[defender.kingdom.value]['name']}\n\n"
        
        f"📊 <b>Характеристики противника:</b>\n"
        f"⚔️ Сила: <b>{defender.strength}</b>\n"
        f"🛡️ Броня: <b>{defender.armor}</b>\n"
        f"❤️ HP: <b>{defender.hp}</b>\n"
        f"💨 Проворность: <b>{defender.agility}</b>\n\n"
        
        f"🏆 Статистика: <b>{defender.pvp_wins}W/{defender.pvp_losses}L</b>\n\n"
        
        f"⏳ Ожидаем ответа противника...\n"
        f"ID битвы: #{battle.id}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Проверить статус", callback_data=f"check_pvp_status_{battle.id}")],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="battle_menu")]
    ])
    
    await callback.message.edit_text(challenge_text, reply_markup=keyboard)
    
    # Here would normally send notification to defender
    # For now just show success
    await callback.answer("✅ Интерактивный вызов отправлен!")

@router.callback_query(F.data.startswith("check_pvp_status_"))
async def check_pvp_battle_status(callback: CallbackQuery, user, is_registered: bool):
    """Check status of PvP battle"""
    battle_id = int(callback.data.replace("check_pvp_status_", ""))
    
    pvp_service = EnhancedPvPService()
    battle = await pvp_service.get_battle(battle_id)
    
    if not battle:
        await callback.answer("❌ Битва не найдена!", show_alert=True)
        return
    
    if battle.phase.value == "monster_encounter":  # Still waiting for acceptance
        await callback.answer("⏳ Противник ещё не принял вызов", show_alert=True)
        return
    elif battle.phase.value == "finished":
        await show_interactive_pvp_results(callback, battle, user)
        return
    else:
        # Battle is active - show current state
        await show_interactive_pvp_battle_state(callback, battle, user)

async def show_interactive_pvp_battle_state(callback: CallbackQuery, battle, user):
    """Show current state of active PvP battle"""
    # Get opponent info
    from config.database import AsyncSessionLocal
    from models.user import User
    
    async with AsyncSessionLocal() as session:
        if battle.player1_id == user.id:
            opponent = await session.get(User, battle.player2_id)
            user_hp = battle.player1_hp
            user_mana = battle.player1_mana
            opponent_hp = battle.player2_hp
            user_attack = battle.player1_attack_choice
            user_dodge = battle.player1_dodge_choice
        else:
            opponent = await session.get(User, battle.player1_id)
            user_hp = battle.player2_hp
            user_mana = battle.player2_mana
            opponent_hp = battle.player1_hp
            user_attack = battle.player2_attack_choice
            user_dodge = battle.player2_dodge_choice
    
    phase_names = {
        'attack_selection': 'Выбор атаки',
        'dodge_selection': 'Выбор уклонения',
        'calculating': 'Расчёт результатов'
    }
    
    status_text = (
        f"⚔️ <b>Интерактивная битва #{battle.id}</b>\n\n"
        f"🔄 Раунд: <b>{battle.current_round}</b>\n"
        f"📍 Фаза: <b>{phase_names.get(battle.phase.value, battle.phase.value)}</b>\n\n"
        
        f"👤 <b>Вы:</b> ❤️ {user_hp}/{user.hp} | 🔮 {user_mana}/{user.mana}\n"
        f"👤 <b>{opponent.name}:</b> ❤️ {opponent_hp}/{opponent.hp}\n\n"
        
        f"🎯 Ваш выбор атаки: <b>{user_attack or 'Не выбран'}</b>\n"
        f"🛡️ Ваш выбор уклонения: <b>{user_dodge or 'Не выбран'}</b>\n\n"
    )
    
    if battle.phase.value == "attack_selection":
        status_text += "⏳ Выберите тип атаки..."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Точный удар", callback_data=f"pvp_attack_precise_{battle.id}")],
            [InlineKeyboardButton(text="💥 Мощный удар", callback_data=f"pvp_attack_power_{battle.id}")],
            [InlineKeyboardButton(text="⚔️ Обычная атака", callback_data=f"pvp_attack_normal_{battle.id}")]
        ])
    elif battle.phase.value == "dodge_selection":
        status_text += "⏳ Выберите направление уклонения..."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Влево", callback_data=f"pvp_dodge_left_{battle.id}")],
            [InlineKeyboardButton(text="🛡️ Блок", callback_data=f"pvp_dodge_center_{battle.id}")],
            [InlineKeyboardButton(text="➡️ Вправо", callback_data=f"pvp_dodge_right_{battle.id}")]
        ])
    else:
        status_text += "⏳ Ожидание расчёта..."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"check_pvp_status_{battle.id}")]
        ])
    
    await callback.message.edit_text(status_text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("pvp_attack_"))
async def handle_pvp_attack_choice(callback: CallbackQuery, user, is_registered: bool):
    """Handle PvP attack choice"""
    parts = callback.data.split("_")
    attack_type = parts[2]  # precise, power, normal
    battle_id = int(parts[3])
    
    pvp_service = EnhancedPvPService()
    success = await pvp_service.make_pvp_attack_choice(battle_id, user.id, attack_type)
    
    if not success:
        await callback.answer("❌ Ошибка при выборе атаки!", show_alert=True)
        return
    
    attack_names = {
        'precise': 'Точный удар',
        'power': 'Мощный удар',
        'normal': 'Обычная атака'
    }
    
    await callback.answer(f"✅ Выбран: {attack_names[attack_type]}")
    
    # Update battle state
    await show_interactive_pvp_battle_state(callback, await pvp_service.get_battle(battle_id), user)

@router.callback_query(F.data.startswith("pvp_dodge_"))
async def handle_pvp_dodge_choice(callback: CallbackQuery, user, is_registered: bool):
    """Handle PvP dodge choice"""
    parts = callback.data.split("_")
    direction = parts[2]  # left, center, right
    battle_id = int(parts[3])
    
    pvp_service = EnhancedPvPService()
    success = await pvp_service.make_pvp_dodge_choice(battle_id, user.id, direction)
    
    if not success:
        await callback.answer("❌ Ошибка при выборе уклонения!", show_alert=True)
        return
    
    direction_names = {
        'left': 'Влево',
        'center': 'Блок',
        'right': 'Вправо'
    }
    
    await callback.answer(f"✅ Выбрано: {direction_names[direction]}")
    
    # Show calculating message
    await callback.message.edit_text(
        f"⚙️ <b>Расчёт результатов раунда...</b>\n\n"
        f"⏳ Применение навыков обоих игроков...\n"
        f"⚔️ Расчёт атак и защиты...\n"
        f"📊 Определение результатов...",
        reply_markup=None
    )
    
    # Wait and check results
    await asyncio.sleep(3)
    battle = await pvp_service.get_battle(battle_id)
    
    if battle.phase.value == "finished":
        await show_interactive_pvp_results(callback, battle, user)
    else:
        await show_interactive_pvp_round_results(callback, battle, user)

async def show_interactive_pvp_round_results(callback: CallbackQuery, battle, user):
    """Show PvP round results"""
    battle_log = battle.get_battle_log()
    if not battle_log:
        return
    
    last_round = battle_log[-1]
    
    # Get opponent info
    from config.database import AsyncSessionLocal
    from models.user import User
    
    async with AsyncSessionLocal() as session:
        if battle.player1_id == user.id:
            opponent = await session.get(User, battle.player2_id)
        else:
            opponent = await session.get(User, battle.player1_id)
    
    results_text = f"📊 <b>Результаты раунда {last_round['round']}</b>\n\n"
    
    # Show skills used
    if last_round.get('skills_used'):
        results_text += f"✨ <b>Автоматически применённые навыки:</b>\n"
        for player_key, skills in last_round['skills_used'].items():
            player_name = user.name if (player_key == 'player1' and battle.player1_id == user.id) or (player_key == 'player2' and battle.player2_id == user.id) else opponent.name
            if skills:
                results_text += f"[{player_name}]:\n"
                for skill in skills:
                    results_text += f"  • {skill['name']}: {skill['effect']}\n"
        results_text += "\n"
    
    # Show actions
    results_text += f"🎯 <b>Действия игроков:</b>\n"
    results_text += f"[{user.name}] Атака: {last_round.get('player1_attack_type' if battle.player1_id == user.id else 'player2_attack_type')}\n"
    results_text += f"[{user.name}] Уклонение: {last_round.get('player1_dodge' if battle.player1_id == user.id else 'player2_dodge')}\n"
    results_text += f"[{opponent.name}] Атака: {last_round.get('player2_attack_type' if battle.player1_id == user.id else 'player1_attack_type')}\n"
    results_text += f"[{opponent.name}] Уклонение: {last_round.get('player2_dodge' if battle.player1_id == user.id else 'player1_dodge')}\n\n"
    
    # Show events
    results_text += f"📋 <b>События раунда:</b>\n"
    for event in last_round['events']:
        results_text += f"• {event}\n"
    
    results_text += f"\n⏭️ Переход к раунду {battle.current_round}..."
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Продолжить бой", callback_data=f"check_pvp_status_{battle.id}")]
    ])
    
    await callback.message.edit_text(results_text, reply_markup=keyboard)

async def show_interactive_pvp_results(callback: CallbackQuery, battle, user):
    """Show final PvP battle results"""
    battle_log = battle.get_battle_log()
    final_result = battle_log[-1] if battle_log else {}
    
    # Get opponent info
    from config.database import AsyncSessionLocal
    from models.user import User
    
    async with AsyncSessionLocal() as session:
        if battle.player1_id == user.id:
            opponent = await session.get(User, battle.player2_id)
        else:
            opponent = await session.get(User, battle.player1_id)
    
    user_won = (battle.winner_id == user.id)
    result_type = final_result.get('result', 'unknown')
    
    if user_won:
        result_text = (
            f"🏆 <b>ПОБЕДА В PvP!</b>\n\n"
            f"🎉 Вы одержали победу над <b>{opponent.name}</b>!\n\n"
            
            f"📊 <b>Статистика боя:</b>\n"
            f"⏱️ Раундов: <b>{battle.current_round}</b>\n"
            f"🎯 Тип победы: <b>{'По таймауту' if 'timeout' in result_type else 'Боевая'}</b>\n\n"
            
            f"🎁 <b>Награды:</b>\n"
            f"⚡ Опыт: <b>+{battle.exp_gained}</b>\n"
            f"💰 Деньги: <b>+{battle.money_gained}</b> золота\n\n"
            
            f"🔥 Отличная работа! Ваши навыки в PvP растут!"
        )
    elif result_type == 'draw':
        result_text = (
            f"🤝 <b>НИЧЬЯ!</b>\n\n"
            f"Равный бой с <b>{opponent.name}</b>!\n"
            f"Оба игрока показали отличные навыки.\n\n"
            f"⏱️ Раундов: <b>{battle.current_round}</b>\n"
            f"🎯 Результат: Время истекло при равном HP"
        )
    else:
        result_text = (
            f"💀 <b>ПОРАЖЕНИЕ</b>\n\n"
            f"Вы проиграли <b>{opponent.name}</b>\n\n"
            
            f"📊 <b>Статистика боя:</b>\n"
            f"⏱️ Раундов: <b>{battle.current_round}</b>\n"
            f"🎯 Тип поражения: <b>{'По таймауту' if 'timeout' in result_type else 'Боевое'}</b>\n\n"
            
            f"💡 <b>Советы для улучшения:</b>\n"
            f"• Изучите новые навыки\n"
            f"• Улучшите снаряжение\n"
            f"• Экспериментируйте с тактикой атак\n"
            f"• Тренируйтесь против ИИ"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Новый PvP", callback_data="interactive_pvp")],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="battle_menu")]
    ])
    
    await callback.message.edit_text(result_text, reply_markup=keyboard)