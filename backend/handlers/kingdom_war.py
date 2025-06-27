from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.enhanced_kingdom_war_service import EnhancedKingdomWarService
from services.user_service import UserService
from config.settings import GameConstants
from datetime import datetime, timedelta
import pytz
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "kingdom_wars")
async def show_kingdom_wars_menu(callback: CallbackQuery, user, is_registered: bool):
    """Show kingdom wars main menu"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    war_service = EnhancedKingdomWarService()
    
    # Check if user is blocked due to war participation
    is_blocked, block_message = await war_service.check_user_war_block(user.id)
    
    tashkent_tz = pytz.timezone('Asia/Tashkent')
    now = datetime.now(tashkent_tz)
    
    # Get next war times
    next_wars = []
    war_times = [8, 13, 18]
    
    for hour in war_times:
        next_war = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if next_war <= now:
            next_war += timedelta(days=1)
        next_wars.append(next_war)
    
    next_war_text = "⏰ **Следующие войны:**\n"
    for war_time in next_wars[:3]:  # Show next 3 wars
        time_str = war_time.strftime("%H:%M")
        if war_time.date() == now.date():
            next_war_text += f"• Сегодня в {time_str}\n"
        else:
            next_war_text += f"• Завтра в {time_str}\n"
    
    kingdom_info = GameConstants.KINGDOMS[user.kingdom.value]
    
    menu_text = (
        f"🏰 **Королевские Битвы**\n\n"
        f"Вы представитель {kingdom_info['emoji']} **{kingdom_info['name']}**\n\n"
        f"{next_war_text}\n"
    )
    
    if is_blocked:
        menu_text += f"⚠️ **{block_message}**\n\n"
    
    menu_text += (
        f"**Правила войн:**\n"
        f"• Войны проходят 3 раза в день\n" 
        f"• За 30 минут до войны - объявление\n"
        f"• Можно атаковать любое королевство или защищать своё\n"
        f"• При атаке нескольких королевств защитники получают +30% к защите\n"
        f"• Неучаствующие защитники теряют 40% золота дополнительно\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Атаковать королевство", callback_data="kingdom_war_attack")],
        [InlineKeyboardButton(text="🛡️ Защищать своё королевство", callback_data="kingdom_war_defend")],
        [InlineKeyboardButton(text="📊 Результаты войн", callback_data="war_results")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="battle_menu")]
    ])
    
    await callback.message.edit_text(menu_text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "kingdom_war_attack")
async def show_attack_kingdoms(callback: CallbackQuery, user, is_registered: bool):
    """Show kingdoms available for attack"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    war_service = EnhancedKingdomWarService()
    
    # Check if user is blocked
    is_blocked, block_message = await war_service.check_user_war_block(user.id)
    if is_blocked:
        await callback.answer(block_message, show_alert=True)
        return
    
    # Get next war times
    tashkent_tz = pytz.timezone('Asia/Tashkent')
    now = datetime.now(tashkent_tz)
    war_times = [8, 13, 18]
    
    # Find next available war time
    next_wars = []
    for hour in war_times:
        next_war = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if next_war <= now:
            next_war += timedelta(days=1)
        next_wars.append(next_war)
    
    builder = InlineKeyboardBuilder()
    
    # Add kingdom attack buttons for each time slot
    for war_time in next_wars[:2]:  # Show next 2 wars
        time_str = war_time.strftime("%H:%M")
        date_str = "сегодня" if war_time.date() == now.date() else "завтра"
        
        # Add kingdoms to attack (except user's own)
        for kingdom_key, kingdom_info in GameConstants.KINGDOMS.items():
            if kingdom_key != user.kingdom.value:
                builder.row(InlineKeyboardButton(
                    text=f"⚔️ {kingdom_info['emoji']} {kingdom_info['name']} [{date_str} {time_str}]",
                    callback_data=f"attack_kingdom_{kingdom_key}_{war_time.strftime('%Y%m%d_%H')}"
                ))
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="kingdom_wars"))
    
    await callback.message.edit_text(
        f"⚔️ **Выберите цель для атаки**\n\n"
        f"Доступные войны:\n"
        f"• Можно записаться на участие в ближайших войнах\n"
        f"• После записи другие действия будут заблокированы\n"
        f"• Выберите королевство и время войны:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("attack_kingdom_"))
async def join_attack_squad(callback: CallbackQuery, user, is_registered: bool):
    """Join attack squad for specific kingdom and time"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    # Parse callback data: attack_kingdom_{kingdom}_{date}_{hour}
    parts = callback.data.split("_")
    target_kingdom = parts[2]
    date_hour = "_".join(parts[3:])  # YYYYMMDD_HH
    
    try:
        war_datetime = datetime.strptime(date_hour, "%Y%m%d_%H")
        tashkent_tz = pytz.timezone('Asia/Tashkent')
        war_time = tashkent_tz.localize(war_datetime)
        war_time_utc = war_time.astimezone(pytz.UTC)
    except ValueError:
        await callback.answer("Неверный формат времени!", show_alert=True)
        return
    
    war_service = EnhancedKingdomWarService()
    success, message = await war_service.join_attack_squad(user.id, target_kingdom, war_time_utc)
    
    if success:
        kingdom_info = GameConstants.KINGDOMS[target_kingdom]
        await callback.message.edit_text(
            f"✅ **Записаны на атаку!**\n\n"
            f"🎯 Цель: {kingdom_info['emoji']} **{kingdom_info['name']}**\n"
            f"⏰ Время: {war_time.strftime('%d.%m.%Y в %H:%M')} (Ташкентское время)\n\n"
            f"⚠️ **Внимание:** Все остальные действия заблокированы до окончания войны!\n\n"
            f"За 30 минут до войны будет объявление в канале войн.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
        )
        await callback.answer("✅ Успешно записаны на атаку!")
    else:
        await callback.answer(message, show_alert=True)

@router.callback_query(F.data == "kingdom_war_defend")
async def show_defend_options(callback: CallbackQuery, user, is_registered: bool):
    """Show defense options for user's kingdom"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    war_service = EnhancedKingdomWarService()
    
    # Check if user is blocked
    is_blocked, block_message = await war_service.check_user_war_block(user.id)
    if is_blocked:
        await callback.answer(block_message, show_alert=True)
        return
    
    # Get next war times
    tashkent_tz = pytz.timezone('Asia/Tashkent')
    now = datetime.now(tashkent_tz)
    war_times = [8, 13, 18]
    
    # Find next available war times
    next_wars = []
    for hour in war_times:
        next_war = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if next_war <= now:
            next_war += timedelta(days=1)
        next_wars.append(next_war)
    
    builder = InlineKeyboardBuilder()
    
    # Add defense options for each time slot
    for war_time in next_wars[:2]:  # Show next 2 wars
        time_str = war_time.strftime("%H:%M")
        date_str = "сегодня" if war_time.date() == now.date() else "завтра"
        
        builder.row(InlineKeyboardButton(
            text=f"🛡️ Защищать {date_str} в {time_str}",
            callback_data=f"defend_kingdom_{war_time.strftime('%Y%m%d_%H')}"
        ))
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="kingdom_wars"))
    
    kingdom_info = GameConstants.KINGDOMS[user.kingdom.value]
    
    await callback.message.edit_text(
        f"🛡️ **Защита королевства**\n\n"
        f"Ваше королевство: {kingdom_info['emoji']} **{kingdom_info['name']}**\n\n"
        f"**Важно:**\n"
        f"• Если вы не запишетесь на защиту и ваше королевство атакуют, вы потеряете 40% золота дополнительно\n"
        f"• Защитники получают +30% к защите при атаке нескольких королевств\n"
        f"• После записи все действия будут заблокированы до окончания войны\n\n"
        f"Выберите время для защиты:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("defend_kingdom_"))
async def join_defense_squad(callback: CallbackQuery, user, is_registered: bool):
    """Join defense squad for specific time"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    # Parse callback data: defend_kingdom_{date}_{hour}
    date_hour = callback.data.replace("defend_kingdom_", "")
    
    try:
        war_datetime = datetime.strptime(date_hour, "%Y%m%d_%H")
        tashkent_tz = pytz.timezone('Asia/Tashkent')
        war_time = tashkent_tz.localize(war_datetime)
        war_time_utc = war_time.astimezone(pytz.UTC)
    except ValueError:
        await callback.answer("Неверный формат времени!", show_alert=True)
        return
    
    war_service = EnhancedKingdomWarService()
    success, message = await war_service.join_defense_squad(user.id, war_time_utc)
    
    if success:
        kingdom_info = GameConstants.KINGDOMS[user.kingdom.value]
        await callback.message.edit_text(
            f"🛡️ **Записаны на защиту!**\n\n"
            f"🏰 Защищаем: {kingdom_info['emoji']} **{kingdom_info['name']}**\n"
            f"⏰ Время: {war_time.strftime('%d.%m.%Y в %H:%M')} (Ташкентское время)\n\n"
            f"⚠️ **Внимание:** Все остальные действия заблокированы до окончания войны!\n\n"
            f"За 30 минут до войны будет объявление в канале войн.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
        )
        await callback.answer("✅ Успешно записаны на защиту!")
    else:
        await callback.answer(message, show_alert=True)

@router.callback_query(F.data == "war_results")
async def show_war_results_menu(callback: CallbackQuery, user, is_registered: bool):
    """Show war results menu"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    await callback.message.edit_text(
        f"📊 **Результаты войн**\n\n"
        f"Выберите тип результатов:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📈 Мои результаты", callback_data="my_war_results")],
            [InlineKeyboardButton(text="🌍 Глобальные результаты", callback_data="global_war_results")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="kingdom_wars")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data == "my_war_results")
async def show_my_war_results(callback: CallbackQuery, user, is_registered: bool):
    """Show user's personal war results"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    # This would be implemented to show user's recent war participations
    await callback.message.edit_text(
        f"📈 **Ваши результаты войн**\n\n"
        f"Эта функция будет доступна после первой войны!\n\n"
        f"Здесь будет отображаться:\n"
        f"• История участия в войнах\n"
        f"• Полученные награды и потери\n"
        f"• Статистика по атакам и защите",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="war_results")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data == "global_war_results")
async def show_global_war_results(callback: CallbackQuery, user, is_registered: bool):
    """Show global war results"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    # This would show recent global war results
    await callback.message.edit_text(
        f"🌍 **Глобальные результаты войн**\n\n"
        f"Последние войны королевств будут отображаться здесь!\n\n"
        f"Информация будет включать:\n"
        f"• Результаты каждой войны\n"
        f"• Участвующие королевства\n"
        f"• Переданные суммы золота\n"
        f"• Ключевые участники",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="war_results")]
        ])
    )
    await callback.answer()

@router.message(F.text == "/war_result")
async def cmd_war_result(message, user, is_registered: bool):
    """Command to show latest war result for user"""
    if not is_registered:
        await message.reply("Сначала нужно зарегистрироваться!")
        return
    
    war_service = EnhancedKingdomWarService()
    
    # Get user's latest war result
    from config.database import AsyncSessionLocal
    from models.kingdom_war import WarParticipation, KingdomWar, WarStatusEnum
    from sqlalchemy import select, desc, and_
    
    async with AsyncSessionLocal() as session:
        # Get user's latest war participation
        latest_participation = await session.execute(
            select(WarParticipation)
            .join(KingdomWar)
            .where(
                and_(
                    WarParticipation.user_id == user.id,
                    KingdomWar.status == WarStatusEnum.finished
                )
            )
            .order_by(desc(WarParticipation.joined_at))
            .limit(1)
        )
        
        participation = latest_participation.scalar_one_or_none()
        
        if not participation:
            await message.reply(
                f"📊 **Результат последней войны**\n\n"
                f"У вас пока нет участий в войнах королевств.\n\n"
                f"Чтобы принять участие:\n"
                f"1. Перейдите в меню битв\n"
                f"2. Выберите 'Королевские битвы'\n"
                f"3. Запишитесь на атаку или защиту",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏰 Королевские битвы", callback_data="kingdom_wars")]
                ])
            )
            return
        
        # Get war details
        war = await session.get(KingdomWar, participation.war_id)
        
        if not war:
            await message.reply("Ошибка: война не найдена.")
            return
        
        # Create result message
        from config.settings import GameConstants
        import pytz
        
        war_time = war.started_at.astimezone(pytz.timezone('Asia/Tashkent'))
        kingdom_info = GameConstants.KINGDOMS.get(participation.kingdom, {})
        
        result_text = (
            f"📊 **Результат последней войны**\n\n"
            f"🗓️ **Дата:** {war_time.strftime('%d.%m.%Y в %H:%M')}\n"
            f"🏰 **Ваше королевство:** {kingdom_info.get('emoji', '🏰')} {kingdom_info.get('name', participation.kingdom)}\n"
            f"⚔️ **Роль:** {'Атакующий' if participation.role == 'attacker' else 'Защитник'}\n\n"
        )
        
        # War outcome
        battle_results = war.get_battle_results()
        if battle_results:
            if participation.role == 'attacker':
                # Find result for this user's kingdom
                user_result = None
                for result in battle_results:
                    if result.get('attacker') == participation.kingdom:
                        user_result = result
                        break
                
                if user_result:
                    if user_result['result'] == 'victory':
                        result_text += "🎉 **Результат:** ПОБЕДА!\n"
                    elif user_result['result'] == 'defeat':
                        result_text += "❌ **Результат:** Поражение\n"
                    else:
                        result_text += "⏰ **Результат:** Опоздание\n"
                else:
                    result_text += "❓ **Результат:** Неизвестно\n"
            else:
                # Defender - check if defense held
                defending_kingdom = war.defending_kingdom
                total_damage = 0
                for result in battle_results:
                    total_damage += result.get('damage', 0)
                
                defense_hp = sum([war.get_defense_stats().get('hp', 0)])
                if total_damage >= defense_hp:
                    result_text += "❌ **Результат:** Оборона пробита\n"
                else:
                    result_text += "🛡️ **Результат:** Успешная оборона!\n"
        else:
            result_text += "🕊️ **Результат:** Никто не атаковал\n"
        
        # Personal rewards/losses
        if participation.money_gained > 0:
            result_text += f"💰 **Получено золота:** +{participation.money_gained}\n"
        elif participation.money_lost > 0:
            result_text += f"💸 **Потеряно золота:** -{participation.money_lost}\n"
        
        if participation.exp_gained > 0:
            result_text += f"⭐ **Получено опыта:** +{participation.exp_gained}\n"
        
        # Player stats at time of war
        player_stats = participation.get_player_stats()
        if player_stats:
            result_text += (
                f"\n**Ваши характеристики в войне:**\n"
                f"💪 Сила: {player_stats.get('strength', 0)}\n"
                f"🛡️ Броня: {player_stats.get('armor', 0)}\n"
                f"❤️ Здоровье: {player_stats.get('hp', 0)}\n"
                f"⚡ Ловкость: {player_stats.get('agility', 0)}\n"
                f"🔮 Мана: {player_stats.get('mana', 0)}"
            )
        
        await message.reply(
            result_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏰 Королевские битвы", callback_data="kingdom_wars")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
        )