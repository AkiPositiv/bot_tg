from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.user_service import UserService
from keyboards.main_menu import main_menu_keyboard, kingdom_selection_keyboard, gender_selection_keyboard
from config.settings import GameConstants
import re

router = Router()

class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_gender = State()
    waiting_for_kingdom = State()
    confirmation = State()

@router.message(Command("start"))
async def cmd_start(message: Message, user, is_registered: bool):
    """Handle /start command"""
    if is_registered:
        await message.answer(
            f"🎮 Добро пожаловать обратно, <b>{user.name}</b>!\n\n"
            f"👤 Уровень: {user.level}\n"
            f"💰 Деньги: {user.money}\n"
            f"⚡ Опыт: {user.experience}\n\n"
            f"Выберите действие:",
            reply_markup=main_menu_keyboard()
        )
    else:
        await message.answer(
            "🏰 <b>Добро пожаловать в RPG Королевства!</b>\n\n"
            "🎯 В этой игре вы сможете:\n"
            "⚔️ Сражаться с другими игроками\n"
            "🏰 Исследовать подземелья\n"
            "💪 Развивать своего персонажа\n"
            "🛒 Покупать снаряжение\n"
            "🏆 Участвовать в турнирах\n\n"
            "Для начала игры нужно создать персонажа!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Создать персонажа", callback_data="register")]
            ])
        )

@router.callback_query(F.data == "register")
async def start_registration(callback: CallbackQuery, state: FSMContext, is_registered: bool):
    """Start registration process"""
    if is_registered:
        await callback.answer("Вы уже зарегистрированы!")
        return
    
    await state.set_state(RegistrationStates.waiting_for_name)
    await callback.message.edit_text(
        "✏️ <b>Создание персонажа</b>\n\n"
        "Введите имя вашего персонажа:\n"
        "• От 3 до 20 символов\n"
        "• Только буквы, цифры и символы _ -\n"
        "• Без пробелов"
    )
    await callback.answer()

@router.message(StateFilter(RegistrationStates.waiting_for_name))
async def process_name(message: Message, state: FSMContext):
    """Process character name"""
    name = message.text.strip()
    
    # Validate name
    if len(name) < 3:
        await message.answer("❌ Имя слишком короткое (минимум 3 символа)")
        return
    
    if len(name) > 20:
        await message.answer("❌ Имя слишком длинное (максимум 20 символов)")
        return
    
    if not re.match(r'^[a-zA-Zа-яА-Я0-9_-]+$', name):
        await message.answer("❌ Имя содержит недопустимые символы")
        return
    
    # Save name and move to gender selection
    await state.update_data(name=name)
    await state.set_state(RegistrationStates.waiting_for_gender)
    
    await message.answer(
        f"✅ Отлично! Имя <b>{name}</b> принято.\n\n"
        "👤 Теперь выберите пол персонажа:",
        reply_markup=gender_selection_keyboard()
    )

@router.callback_query(StateFilter(RegistrationStates.waiting_for_gender))
async def process_gender(callback: CallbackQuery, state: FSMContext):
    """Process gender selection"""
    gender = callback.data.replace("gender_", "")
    
    if gender not in ["male", "female"]:
        await callback.answer("Неверный выбор!")
        return
    
    # Save gender and move to kingdom selection
    await state.update_data(gender=gender)
    await state.set_state(RegistrationStates.waiting_for_kingdom)
    
    gender_text = "👨 Мужской" if gender == "male" else "👩 Женский"
    
    await callback.message.edit_text(
        f"✅ Пол: <b>{gender_text}</b>\n\n"
        "🏰 Теперь выберите королевство:\n\n"
        "❄️ <b>Северное</b> - сила и выносливость\n"
        "🌅 <b>Западное</b> - мудрость и магия\n"
        "🌸 <b>Восточное</b> - скорость и ловкость\n"
        "🔥 <b>Южное</b> - страсть и боевая ярость",
        reply_markup=kingdom_selection_keyboard()
    )
    await callback.answer()

@router.callback_query(StateFilter(RegistrationStates.waiting_for_kingdom))
async def process_kingdom(callback: CallbackQuery, state: FSMContext):
    """Process kingdom selection"""
    kingdom = callback.data.replace("kingdom_", "")
    
    if kingdom not in ["north", "west", "east", "south"]:
        await callback.answer("Неверный выбор!")
        return
    
    # Save kingdom and show confirmation
    await state.update_data(kingdom=kingdom)
    await state.set_state(RegistrationStates.confirmation)
    
    data = await state.get_data()
    kingdom_info = GameConstants.KINGDOMS[kingdom]
    gender_text = "👨 Мужской" if data['gender'] == "male" else "👩 Женский"
    
    confirmation_text = (
        "🎯 <b>Подтверждение создания персонажа</b>\n\n"
        f"📝 Имя: <b>{data['name']}</b>\n"
        f"👤 Пол: <b>{gender_text}</b>\n"
        f"🏰 Королевство: <b>{kingdom_info['emoji']} {kingdom_info['name']}</b>\n\n"
        f"💪 Стартовые характеристики:\n"
        f"⚔️ Сила: 10\n"
        f"🛡️ Броня: 10\n"
        f"❤️ Здоровье: 100\n"
        f"💨 Проворность: 10\n"
        f"🔮 Мана: 50\n\n"
        f"💰 Стартовые деньги: 100 золота\n\n"
        f"Всё верно?"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Создать персонажа", callback_data="confirm_registration")],
        [InlineKeyboardButton(text="❌ Начать заново", callback_data="register")]
    ])
    
    await callback.message.edit_text(confirmation_text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(StateFilter(RegistrationStates.confirmation), F.data == "confirm_registration")
async def confirm_registration(callback: CallbackQuery, state: FSMContext):
    """Confirm and create character"""
    data = await state.get_data()
    user_service = UserService()
    
    try:
        # Create user
        user = await user_service.create_user(
            telegram_id=callback.from_user.id,
            name=data['name'],
            gender=data['gender'],
            kingdom=data['kingdom']
        )
        
        await state.clear()
        
        kingdom_info = GameConstants.KINGDOMS[data['kingdom']]
        
        await callback.message.edit_text(
            f"🎉 <b>Персонаж создан!</b>\n\n"
            f"Добро пожаловать в мир RPG, <b>{user.name}</b>!\n"
            f"Вы представитель {kingdom_info['emoji']} <b>{kingdom_info['name']}</b>\n\n"
            f"🎮 Теперь вы можете начать своё приключение!",
            reply_markup=main_menu_keyboard()
        )
        
    except Exception as e:
        await callback.message.edit_text(
            "❌ Произошла ошибка при создании персонажа. Попробуйте ещё раз.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="register")]
            ])
        )
    
    await callback.answer()

@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery, user, is_registered: bool):
    """Show main menu"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    await callback.message.edit_text(
        f"🎮 <b>Главное меню</b>\n\n"
        f"👤 {user.name} | Уровень {user.level}\n"
        f"💰 Деньги: {user.money}\n"
        f"⚡ Опыт: {user.experience}\n\n"
        f"Выберите действие:",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()