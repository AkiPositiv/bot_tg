from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.shop_service import ShopService
from models.item import ItemTypeEnum
import math

router = Router()

@router.callback_query(F.data == "shop_menu")
async def show_shop_menu(callback: CallbackQuery, user, is_registered: bool):
    """Show shop main menu"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    shop_service = ShopService()
    categories = await shop_service.get_shop_categories()
    
    builder = InlineKeyboardBuilder()
    
    # Shop categories
    category_names = {
        'weapon': '⚔️ Оружие',
        'armor': '🛡️ Броня',
        'consumable': '🧪 Зелья',
        'material': '🔩 Материалы',
        'scroll': '📜 Свитки'
    }
    
    for category, count in categories.items():
        if count > 0:
            text = f"{category_names.get(category, category)} ({count})"
            builder.row(InlineKeyboardButton(
                text=text,
                callback_data=f"shop_category_{category}_1"
            ))
    
    builder.row(
        InlineKeyboardButton(text="🛒 Все товары", callback_data="shop_category_all_1")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    )
    
    await callback.message.edit_text(
        f"🛒 <b>Магазин</b>\n\n"
        f"💰 Ваши деньги: <b>{user.money}</b> золота\n\n"
        f"Выберите категорию товаров:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("shop_category_"))
async def show_shop_category(callback: CallbackQuery, user, is_registered: bool):
    """Show items in category"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    # Parse callback data: shop_category_{category}_{page}
    parts = callback.data.split("_")
    category = parts[2]
    page = int(parts[3])
    
    shop_service = ShopService()
    items = await shop_service.get_shop_items(category, page, 6)
    
    if not items:
        await callback.answer("В этой категории нет товаров!", show_alert=True)
        return
    
    category_names = {
        'weapon': '⚔️ Оружие',
        'armor': '🛡️ Броня', 
        'consumable': '🧪 Зелья',
        'material': '🔩 Материалы',
        'scroll': '📜 Свитки',
        'all': '🛒 Все товары'
    }
    
    category_name = category_names.get(category, category)
    
    # Build items text
    items_text = f"🛒 <b>{category_name}</b>\n\n"
    items_text += f"💰 Ваши деньги: <b>{user.money}</b> золота\n\n"
    
    builder = InlineKeyboardBuilder()
    
    for i, item in enumerate(items, 1):
        # Item description
        stats_text = ""
        if item.strength_bonus > 0:
            stats_text += f"⚔️+{item.strength_bonus} "
        if item.armor_bonus > 0:
            stats_text += f"🛡️+{item.armor_bonus} "
        if item.hp_bonus > 0:
            stats_text += f"❤️+{item.hp_bonus} "
        if item.agility_bonus > 0:
            stats_text += f"💨+{item.agility_bonus} "
        if item.mana_bonus > 0:
            stats_text += f"🔮+{item.mana_bonus} "
        
        level_req = f" (Ур.{item.level_required})" if item.level_required > 1 else ""
        
        items_text += (
            f"{item.rarity_emoji} <b>{item.name}</b>{level_req}\n"
            f"💰 {item.price} золота | {stats_text}\n"
        )
        if item.description:
            items_text += f"📝 {item.description}\n"
        items_text += "\n"
        
        # Buy button
        can_afford = user.money >= item.price
        can_use = user.level >= item.level_required
        
        if can_afford and can_use:
            builder.row(InlineKeyboardButton(
                text=f"💰 Купить {item.name}",
                callback_data=f"buy_item_{item.id}"
            ))
        else:
            reason = "Недостаточно денег" if not can_afford else "Низкий уровень"
            builder.row(InlineKeyboardButton(
                text=f"❌ {item.name} ({reason})",
                callback_data="shop_unavailable"
            ))
    
    # Pagination (simplified)
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"shop_category_{category}_{page-1}"
        ))
    
    # Check if there are more items
    more_items = await shop_service.get_shop_items(category, page + 1, 6)
    if more_items:
        nav_buttons.append(InlineKeyboardButton(
            text="➡️ Далее",
            callback_data=f"shop_category_{category}_{page+1}"
        ))
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(
        InlineKeyboardButton(text="🔙 К категориям", callback_data="shop_menu")
    )
    
    await callback.message.edit_text(
        items_text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("buy_item_"))
async def buy_item(callback: CallbackQuery, user, is_registered: bool):
    """Buy an item"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    item_id = int(callback.data.replace("buy_item_", ""))
    
    shop_service = ShopService()
    success, message = await shop_service.buy_item(user.id, item_id, 1)
    
    if success:
        await callback.answer(f"✅ {message}", show_alert=True)
        # Refresh the user money display
        await show_shop_menu(callback, user, is_registered)
    else:
        await callback.answer(f"❌ {message}", show_alert=True)

@router.callback_query(F.data == "shop_unavailable")
async def shop_unavailable(callback: CallbackQuery):
    """Handle unavailable item clicks"""
    await callback.answer("Этот товар недоступен для покупки", show_alert=True)