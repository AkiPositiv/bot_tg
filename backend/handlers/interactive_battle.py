from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.interactive_battle_service import InteractiveBattleService
from models.interactive_battle import BattlePhaseEnum
import asyncio

router = Router()

@router.callback_query(F.data == "pve_encounter")
async def start_pve_encounter(callback: CallbackQuery, user, is_registered: bool):
    """Start PvE encounter"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    # Check if user has enough HP
    if user.current_hp < user.hp * 0.3:
        await callback.answer("❤️ Недостаточно здоровья для боя! Нужно минимум 30% HP", show_alert=True)
        return
    
    battle_service = InteractiveBattleService()
    battle = await battle_service.start_pve_encounter(user.id)
    
    if not battle:
        await callback.answer("❌ Не удалось найти противника!", show_alert=True)
        return
    
    monster_data = battle.get_monster_data()
    
    # Create monster card
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
        f"🔮 Мана: <b>{user.current_mana}/{user.mana}</b>\n\n"
        
        f"Что будете делать?"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Сражаться!", callback_data=f"accept_pve_{battle.id}")],
        [InlineKeyboardButton(text="🏃‍♂️ Сбежать", callback_data=f"flee_pve_{battle.id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="battle_menu")]
    ])
    
    await callback.message.edit_text(monster_card, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("accept_pve_"))
async def accept_pve_battle(callback: CallbackQuery, user, is_registered: bool):
    """Accept PvE battle"""
    battle_id = int(callback.data.replace("accept_pve_", ""))
    
    battle_service = InteractiveBattleService()
    success = await battle_service.accept_pve_battle(battle_id)
    
    if not success:
        await callback.answer("❌ Не удалось начать бой!", show_alert=True)
        return
    
    await show_attack_selection(callback, battle_id, user)

@router.callback_query(F.data.startswith("flee_pve_"))
async def flee_pve_battle(callback: CallbackQuery, user, is_registered: bool):
    """Flee from PvE battle"""
    battle_id = int(callback.data.replace("flee_pve_", ""))
    
    battle_service = InteractiveBattleService()
    success = await battle_service.flee_from_battle(battle_id, user.id)
    
    if success:
        await callback.message.edit_text(
            "🏃‍♂️ <b>Вы сбежали с поля боя!</b>\n\n"
            "Иногда отступление - лучшая стратегия.\n"
            "Восстановите здоровье и возвращайтесь сильнее!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 В меню битв", callback_data="battle_menu")]
            ])
        )
    else:
        await callback.answer("❌ Не удалось сбежать!", show_alert=True)
    
    await callback.answer()

async def show_attack_selection(callback: CallbackQuery, battle_id: int, user):
    """Show attack direction selection"""
    battle_service = InteractiveBattleService()
    battle = await battle_service.get_battle(battle_id)
    
    if not battle:
        return
    
    monster_data = battle.get_monster_data()
    
    attack_text = (
        f"⚔️ <b>Раунд {battle.current_round}</b>\n\n"
        f"👤 <b>Ваше состояние:</b>\n"
        f"❤️ HP: <b>{battle.player1_hp}/{user.hp}</b>\n"
        f"🔮 Мана: <b>{battle.player1_mana}/{user.mana}</b>\n\n"
        
        f"{monster_data['type_emoji']} <b>{monster_data['name']}:</b>\n"
        f"❤️ HP: <b>{battle.monster_hp}/{monster_data['hp']}</b>\n\n"
        
        f"🎯 <b>Выберите направление атаки:</b>\n"
        f"Монстр попытается уклониться в одну из сторон.\n"
        f"Угадайте направление для точного попадания!\n\n"
        f"⏱️ Время на выбор: <b>50 секунд</b>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️ Левая", callback_data=f"attack_left_{battle_id}"),
            InlineKeyboardButton(text="🎯 Центр", callback_data=f"attack_center_{battle_id}"),
            InlineKeyboardButton(text="➡️ Правая", callback_data=f"attack_right_{battle_id}")
        ]
    ])
    
    await callback.message.edit_text(attack_text, reply_markup=keyboard)
    
    # Start timeout checker
    asyncio.create_task(check_round_timeout(battle_id, 50))

@router.callback_query(F.data.startswith("attack_"))
async def handle_attack_choice(callback: CallbackQuery, user, is_registered: bool):
    """Handle attack direction choice"""
    parts = callback.data.split("_")
    direction = parts[1]
    battle_id = int(parts[2])
    
    battle_service = InteractiveBattleService()
    success = await battle_service.make_attack_choice(battle_id, user.id, direction)
    
    if not success:
        await callback.answer("❌ Ошибка при выборе атаки!", show_alert=True)
        return
    
    await callback.answer(f"✅ Выбрана атака: {direction}")
    await show_dodge_selection(callback, battle_id, user)

async def show_dodge_selection(callback: CallbackQuery, battle_id: int, user):
    """Show dodge direction selection"""
    battle_service = InteractiveBattleService()
    battle = await battle_service.get_battle(battle_id)
    
    if not battle:
        return
    
    monster_data = battle.get_monster_data()
    
    dodge_text = (
        f"🛡️ <b>Раунд {battle.current_round} - Уклонение</b>\n\n"
        f"👤 <b>Ваше состояние:</b>\n"
        f"❤️ HP: <b>{battle.player1_hp}/{user.hp}</b>\n\n"
        
        f"{monster_data['type_emoji']} <b>{monster_data['name']}:</b>\n"
        f"❤️ HP: <b>{battle.monster_hp}/{monster_data['hp']}</b>\n\n"
        
        f"🛡️ <b>Выберите направление уклонения:</b>\n"
        f"Монстр атакует! Уклонитесь в нужную сторону,\n"
        f"чтобы избежать урона.\n\n"
        f"⏱️ Время на выбор: <b>50 секунд</b>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️ Влево", callback_data=f"dodge_left_{battle_id}"),
            InlineKeyboardButton(text="🛡️ Блок", callback_data=f"dodge_center_{battle_id}"),
            InlineKeyboardButton(text="➡️ Вправо", callback_data=f"dodge_right_{battle_id}")
        ]
    ])
    
    await callback.message.edit_text(dodge_text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("dodge_"))
async def handle_dodge_choice(callback: CallbackQuery, user, is_registered: bool):
    """Handle dodge direction choice"""
    parts = callback.data.split("_")
    direction = parts[1]
    battle_id = int(parts[2])
    
    battle_service = InteractiveBattleService()
    success = await battle_service.make_dodge_choice(battle_id, user.id, direction)
    
    if not success:
        await callback.answer("❌ Ошибка при выборе уклонения!", show_alert=True)
        return
    
    await callback.answer(f"✅ Выбрано уклонение: {direction}")
    
    # Show calculating message
    await callback.message.edit_text(
        f"⚙️ <b>Расчёт результатов раунда...</b>\n\n"
        f"⏳ Подождите, идёт обработка ваших действий...",
        reply_markup=None
    )
    
    # Wait a bit for dramatic effect
    await asyncio.sleep(2)
    
    # Show round results
    await show_round_results(callback, battle_id, user)

async def show_round_results(callback: CallbackQuery, battle_id: int, user):
    """Show results of the round"""
    battle_service = InteractiveBattleService()
    battle = await battle_service.get_battle(battle_id)
    
    if not battle:
        return
    
    battle_log = battle.get_battle_log()
    if not battle_log:
        return
    
    last_round = battle_log[-1]
    
    # Build results text
    results_text = f"📊 <b>Результаты раунда {last_round['round']}</b>\n\n"
    
    results_text += f"🎯 <b>Ваши действия:</b>\n"
    results_text += f"⚔️ Атака: {last_round['player_attack']}\n"
    results_text += f"🛡️ Уклонение: {last_round['player_dodge']}\n\n"
    
    results_text += f"👹 <b>Действия монстра:</b>\n"
    results_text += f"⚔️ Атака: {last_round['monster_attack']}\n"
    results_text += f"🛡️ Уклонение: {last_round['monster_dodge']}\n\n"
    
    results_text += f"📋 <b>События раунда:</b>\n"
    for event in last_round['events']:
        results_text += f"• {event}\n"
    
    # Check battle status
    if battle.phase.value == "finished":
        await show_battle_finished(callback, battle, user)
        return
    
    # Continue to next round
    results_text += f"\n⏭️ Переход к раунду {battle.current_round}..."
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Продолжить бой", callback_data=f"continue_battle_{battle_id}")]
    ])
    
    await callback.message.edit_text(results_text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("continue_battle_"))
async def continue_battle(callback: CallbackQuery, user, is_registered: bool):
    """Continue to next round"""
    battle_id = int(callback.data.replace("continue_battle_", ""))
    await show_attack_selection(callback, battle_id, user)

async def show_battle_finished(callback: CallbackQuery, battle, user):
    """Show battle finished results"""
    battle_log = battle.get_battle_log()
    final_result = battle_log[-1] if battle_log else {}
    
    if battle.winner_id == user.id:
        # Victory
        result_text = (
            f"🏆 <b>ПОБЕДА!</b>\n\n"
            f"🎉 Вы одержали победу в бою!\n\n"
            f"🎁 <b>Награды:</b>\n"
            f"⚡ Опыт: <b>+{battle.exp_gained}</b>\n"
            f"💰 Деньги: <b>+{battle.money_gained}</b> золота\n\n"
            f"🔥 Продолжайте сражаться, чтобы стать сильнее!"
        )
        result_emoji = "🏆"
    else:
        # Defeat or flee
        result_type = final_result.get('result', 'defeat')
        if result_type == 'timeout':
            result_text = (
                f"⏰ <b>ВРЕМЯ ВЫШЛО!</b>\n\n"
                f"Бой затянулся, и монстр сбежал.\n"
                f"В следующий раз будьте быстрее!"
            )
        else:
            result_text = (
                f"💀 <b>ПОРАЖЕНИЕ!</b>\n\n"
                f"Вы потерпели поражение в бою.\n"
                f"Не отчаивайтесь! Прокачайтесь и возвращайтесь!"
            )
        result_emoji = "💀"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Новый бой", callback_data="pve_encounter")],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="battle_menu")]
    ])
    
    await callback.message.edit_text(result_text, reply_markup=keyboard)

async def check_round_timeout(battle_id: int, timeout_seconds: int):
    """Check for round timeout"""
    await asyncio.sleep(timeout_seconds)
    
    battle_service = InteractiveBattleService()
    timed_out = await battle_service.check_battle_timeout(battle_id)
    
    if timed_out:
        # Battle timed out - would need to notify players
        # This is simplified for now
        pass