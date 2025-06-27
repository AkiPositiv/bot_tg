from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.enhanced_battle_service import EnhancedBattleService
from models.interactive_battle import BattlePhaseEnum
import asyncio

router = Router()

@router.callback_query(F.data == "enhanced_pve_encounter")
async def start_enhanced_pve_encounter(callback: CallbackQuery, user, is_registered: bool):
    """Start enhanced PvE encounter with full TS compliance"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    if user.current_hp < user.hp * 0.3:
        await callback.answer("❤️ Недостаточно здоровья для боя! Нужно минимум 30% HP", show_alert=True)
        return
    
    battle_service = EnhancedBattleService()
    battle = await battle_service.start_pve_encounter(user.id)
    
    if not battle:
        await callback.answer("❌ Не удалось найти противника!", show_alert=True)
        return
    
    monster_data = battle.get_monster_data()
    
    # Enhanced monster card with flee chance info
    level_diff = user.level - monster_data['level']
    base_chance = 0.6
    agility_bonus = (user.agility - 10) * 0.02
    level_bonus = level_diff * 0.05
    flee_chance = max(0.1, min(0.9, base_chance + agility_bonus + level_bonus))
    
    monster_card = (
        f"🎯 <b>Встреча с монстром!</b>\n\n"
        f"{monster_data['type_emoji']} <b>{monster_data['name']}</b>\n"
        f"⭐ Уровень: <b>{monster_data['level']}</b>\n"
        f"{monster_data['difficulty_color']} Сложность: <b>{monster_data['type_emoji']}</b>\n\n"
        
        f"📊 <b>Характеристики монстра:</b>\n"
        f"⚔️ Сила: <b>{monster_data['strength']}</b>\n"
        f"🛡️ Броня: <b>{monster_data['armor']}</b>\n"
        f"❤️ Здоровье: <b>{monster_data['hp']}</b>\n"
        f"💨 Проворность: <b>{monster_data['agility']}</b>\n\n"
        
        f"🎁 <b>Награды за победу:</b>\n"
        f"⚡ Опыт: <b>+{monster_data['exp_reward']}</b>\n"
        f"💰 Деньги: <b>+{monster_data['money_reward']}</b> золота\n\n"
        
        f"👤 <b>Ваше состояние:</b>\n"
        f"❤️ HP: <b>{user.current_hp}/{user.hp}</b>\n"
        f"🔮 Мана: <b>{user.current_mana}/{user.mana}</b>\n"
        f"💨 Проворность: <b>{user.agility}</b>\n\n"
        
        f"🏃‍♂️ <b>Шанс побега: {flee_chance:.1%}</b>\n"
        f"⚠️ При неудачном побеге монстр нанесёт удар!\n\n"
        
        f"Что будете делать?"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Сражаться!", callback_data=f"accept_enhanced_pve_{battle.id}")],
        [InlineKeyboardButton(text="🏃‍♂️ Сбежать", callback_data=f"flee_enhanced_pve_{battle.id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="battle_menu")]
    ])
    
    await callback.message.edit_text(monster_card, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("accept_enhanced_pve_"))
async def accept_enhanced_pve_battle(callback: CallbackQuery, user, is_registered: bool):
    """Accept enhanced PvE battle"""
    battle_id = int(callback.data.replace("accept_enhanced_pve_", ""))
    
    battle_service = EnhancedBattleService()
    battle = await battle_service.get_battle(battle_id)
    
    if not battle:
        await callback.answer("❌ Битва не найдена!", show_alert=True)
        return
    
    # Start with attack type selection
    await show_attack_type_selection(callback, battle_id, user)

@router.callback_query(F.data.startswith("flee_enhanced_pve_"))
async def flee_enhanced_pve_battle(callback: CallbackQuery, user, is_registered: bool):
    """Attempt to flee with chance calculation"""
    battle_id = int(callback.data.replace("flee_enhanced_pve_", ""))
    
    battle_service = EnhancedBattleService()
    success, message, damage = await battle_service.attempt_flee(battle_id, user.id)
    
    if success:
        await callback.message.edit_text(
            f"🏃‍♂️ <b>Успешный побег!</b>\n\n"
            f"{message}\n\n"
            f"Иногда отступление - лучшая стратегия.\n"
            f"Восстановите здоровье и возвращайтесь сильнее!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 В меню битв", callback_data="battle_menu")]
            ])
        )
    else:
        await callback.message.edit_text(
            f"❌ <b>Побег не удался!</b>\n\n"
            f"{message}\n\n"
            f"Теперь вам придётся сражаться!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚔️ В бой!", callback_data=f"accept_enhanced_pve_{battle_id}")]
            ])
        )
    
    await callback.answer()

async def show_attack_type_selection(callback: CallbackQuery, battle_id: int, user):
    """Show attack type selection with 3 options"""
    battle_service = EnhancedBattleService()
    battle = await battle_service.get_battle(battle_id)
    
    if not battle:
        return
    
    monster_data = battle.get_monster_data()
    
    attack_text = (
        f"⚔️ <b>Раунд {battle.current_round} - Выбор атаки</b>\n\n"
        f"👤 <b>Ваше состояние:</b>\n"
        f"❤️ HP: <b>{battle.player1_hp}/{user.hp}</b>\n"
        f"🔮 Мана: <b>{battle.player1_mana}/{user.mana}</b>\n\n"
        
        f"{monster_data['type_emoji']} <b>{monster_data['name']}:</b>\n"
        f"❤️ HP: <b>{battle.monster_hp}/{monster_data['hp']}</b>\n\n"
        
        f"🎯 <b>Выберите тип атаки:</b>\n\n"
        
        f"🎯 <b>Точный удар:</b>\n"
        f"• 90% шанс попадания\n"
        f"• +50% шанс критического удара\n"
        f"• +10% урона\n\n"
        
        f"💥 <b>Мощный удар:</b>\n"
        f"• 70% шанс попадания\n"
        f"• +30% урона\n"
        f"• Высокий урон при попадании\n\n"
        
        f"⚔️ <b>Обычная атака:</b>\n"
        f"• 80% шанс попадания\n"
        f"• Сбалансированный урон\n"
        f"• Стандартные эффекты\n\n"
        
        f"⏱️ Время на выбор: <b>50 секунд</b>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Точный удар", callback_data=f"attack_type_precise_{battle_id}")],
        [InlineKeyboardButton(text="💥 Мощный удар", callback_data=f"attack_type_power_{battle_id}")],
        [InlineKeyboardButton(text="⚔️ Обычная атака", callback_data=f"attack_type_normal_{battle_id}")]
    ])
    
    await callback.message.edit_text(attack_text, reply_markup=keyboard)
    
    # Start timeout checker
    asyncio.create_task(check_attack_timeout(battle_id, 50))

@router.callback_query(F.data.startswith("attack_type_"))
async def handle_attack_type_choice(callback: CallbackQuery, user, is_registered: bool):
    """Handle attack type choice"""
    parts = callback.data.split("_")
    attack_type = parts[2]  # precise, power, normal
    battle_id = int(parts[3])
    
    battle_service = EnhancedBattleService()
    success = await battle_service.make_attack_choice(battle_id, user.id, attack_type)
    
    if not success:
        await callback.answer("❌ Ошибка при выборе атаки!", show_alert=True)
        return
    
    attack_names = {
        'precise': 'Точный удар',
        'power': 'Мощный удар', 
        'normal': 'Обычная атака'
    }
    
    await callback.answer(f"✅ Выбран: {attack_names[attack_type]}")
    await show_dodge_direction_selection(callback, battle_id, user)

async def show_dodge_direction_selection(callback: CallbackQuery, battle_id: int, user):
    """Show dodge direction selection"""
    battle_service = EnhancedBattleService()
    battle = await battle_service.get_battle(battle_id)
    
    if not battle:
        return
    
    monster_data = battle.get_monster_data()
    
    # Calculate perfect dodge chance
    perfect_dodge_chance = min(user.agility / 500.0, 0.07) * 100
    
    dodge_text = (
        f"🛡️ <b>Раунд {battle.current_round} - Уклонение</b>\n\n"
        f"👤 <b>Ваше состояние:</b>\n"
        f"❤️ HP: <b>{battle.player1_hp}/{user.hp}</b>\n"
        f"💨 Проворность: <b>{user.agility}</b>\n\n"
        
        f"{monster_data['type_emoji']} <b>{monster_data['name']}:</b>\n"
        f"❤️ HP: <b>{battle.monster_hp}/{monster_data['hp']}</b>\n\n"
        
        f"🛡️ <b>Выберите направление уклонения:</b>\n"
        f"Монстр атакует! Уклонитесь в нужную сторону.\n\n"
        
        f"💫 <b>Мастерское уклонение:</b>\n"
        f"Даже при попадании есть <b>{perfect_dodge_chance:.1f}%</b> шанс\n"
        f"полностью избежать урона!\n\n"
        
        f"⏱️ Время на выбор: <b>50 секунд</b>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️ Влево", callback_data=f"dodge_dir_left_{battle_id}"),
            InlineKeyboardButton(text="🛡️ Блок", callback_data=f"dodge_dir_center_{battle_id}"),
            InlineKeyboardButton(text="➡️ Вправо", callback_data=f"dodge_dir_right_{battle_id}")
        ]
    ])
    
    await callback.message.edit_text(dodge_text, reply_markup=keyboard)
    
    # Start timeout checker
    asyncio.create_task(check_dodge_timeout(battle_id, 50))

@router.callback_query(F.data.startswith("dodge_dir_"))
async def handle_dodge_direction_choice(callback: CallbackQuery, user, is_registered: bool):
    """Handle dodge direction choice"""
    parts = callback.data.split("_")
    direction = parts[2]  # left, center, right
    battle_id = int(parts[3])
    
    battle_service = EnhancedBattleService()
    success = await battle_service.make_direction_choice(battle_id, user.id, direction)
    
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
        f"⏳ Автоматическое применение навыков...\n"
        f"⚔️ Расчёт атак и уклонений...\n"
        f"📊 Обработка результатов...",
        reply_markup=None
    )
    
    # Wait for dramatic effect
    await asyncio.sleep(3)
    
    # Show round results
    await show_enhanced_round_results(callback, battle_id, user)

async def show_enhanced_round_results(callback: CallbackQuery, battle_id: int, user):
    """Show enhanced results of the round"""
    battle_service = EnhancedBattleService()
    battle = await battle_service.get_battle(battle_id)
    
    if not battle:
        return
    
    battle_log = battle.get_battle_log()
    if not battle_log:
        return
    
    last_round = battle_log[-1]
    
    # Build enhanced results text
    results_text = f"📊 <b>Результаты раунда {last_round['round']}</b>\n\n"
    
    # Show skills used
    if last_round.get('skills_used'):
        results_text += f"✨ <b>Автоматически применённые навыки:</b>\n"
        for skill in last_round['skills_used']:
            results_text += f"• {skill['name']}: {skill['effect']}\n"
        results_text += "\n"
    
    results_text += f"🎯 <b>Ваши действия:</b>\n"
    attack_type_names = {
        'precise': 'Точный удар',
        'power': 'Мощный удар',
        'normal': 'Обычная атака'
    }
    results_text += f"⚔️ Атака: {attack_type_names.get(last_round['player_attack_type'], 'Неизвестно')}\n"
    results_text += f"🛡️ Уклонение: {last_round['player_dodge']}\n\n"
    
    results_text += f"👹 <b>Действия монстра:</b>\n"
    results_text += f"⚔️ Атака: {last_round['monster_attack']}\n"
    results_text += f"🛡️ Уклонение: {last_round['monster_dodge']}\n\n"
    
    results_text += f"📋 <b>События раунда:</b>\n"
    for event in last_round['events']:
        results_text += f"• {event}\n"
    
    # Check battle status
    if battle.phase.value == "finished":
        await show_enhanced_battle_finished(callback, battle, user)
        return
    
    # Continue to next round
    results_text += f"\n⏭️ Переход к раунду {battle.current_round}..."
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Продолжить бой", callback_data=f"continue_enhanced_battle_{battle_id}")]
    ])
    
    await callback.message.edit_text(results_text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("continue_enhanced_battle_"))
async def continue_enhanced_battle(callback: CallbackQuery, user, is_registered: bool):
    """Continue to next round"""
    battle_id = int(callback.data.replace("continue_enhanced_battle_", ""))
    await show_attack_type_selection(callback, battle_id, user)

async def show_enhanced_battle_finished(callback: CallbackQuery, battle, user):
    """Show enhanced battle finished results"""
    battle_log = battle.get_battle_log()
    final_result = battle_log[-1] if battle_log else {}
    
    if battle.winner_id == user.id:
        # Victory
        result_text = (
            f"🏆 <b>ВЕЛИКОЛЕПНАЯ ПОБЕДА!</b>\n\n"
            f"🎉 Вы одержали победу в бою!\n\n"
            f"📊 <b>Статистика боя:</b>\n"
            f"⏱️ Раундов: <b>{battle.current_round}</b>\n"
            f"💪 Использовано навыков: <b>{len([r for r in battle_log if r.get('skills_used')])}</b>\n\n"
            
            f"🎁 <b>Награды:</b>\n"
            f"⚡ Опыт: <b>+{battle.exp_gained}</b>\n"
            f"💰 Деньги: <b>+{battle.money_gained}</b> золота\n\n"
            
            f"🔥 Продолжайте сражаться, чтобы стать ещё сильнее!\n"
            f"🎯 Навыки автоматически улучшаются с использованием!"
        )
    else:
        # Defeat or flee
        result_type = final_result.get('result', 'defeat')
        if result_type == 'timeout':
            result_text = (
                f"⏰ <b>ВРЕМЯ ВЫШЛО!</b>\n\n"
                f"Бой затянулся слишком долго.\n"
                f"В следующий раз действуйте быстрее!"
            )
        else:
            result_text = (
                f"💀 <b>ПОРАЖЕНИЕ!</b>\n\n"
                f"Вы потерпели поражение в бою.\n"
                f"💡 Советы для улучшения:\n"
                f"• Прокачайте характеристики\n"
                f"• Изучите новые навыки\n"
                f"• Купите лучшее снаряжение\n"
                f"• Попробуйте другую тактику атак!"
            )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Новый бой", callback_data="enhanced_pve_encounter")],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="battle_menu")]
    ])
    
    await callback.message.edit_text(result_text, reply_markup=keyboard)

async def check_attack_timeout(battle_id: int, timeout_seconds: int):
    """Check for attack selection timeout"""
    await asyncio.sleep(timeout_seconds)
    
    battle_service = EnhancedBattleService()
    battle = await battle_service.get_battle(battle_id)
    
    if battle and battle.phase == BattlePhaseEnum.attack_selection:
        # Auto-select normal attack
        await battle_service.make_attack_choice(battle_id, battle.player1_id, 'normal')

async def check_dodge_timeout(battle_id: int, timeout_seconds: int):
    """Check for dodge selection timeout"""
    await asyncio.sleep(timeout_seconds)
    
    battle_service = EnhancedBattleService()
    battle = await battle_service.get_battle(battle_id)
    
    if battle and battle.phase == BattlePhaseEnum.dodge_selection:
        # Auto-select center (no dodge)
        await battle_service.make_direction_choice(battle_id, battle.player1_id, 'center')