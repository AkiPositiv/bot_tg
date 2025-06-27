from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.inventory_service import InventoryService
from models.item import ItemTypeEnum

router = Router()

@router.callback_query(F.data == "inventory")
async def show_inventory(callback: CallbackQuery, user, is_registered: bool):
    """Show user inventory"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    inventory_service = InventoryService()
    inventory = await inventory_service.get_user_inventory(user.id)
    stats = await inventory_service.get_inventory_stats(user.id)
    
    if not inventory:
        await callback.message.edit_text(
            f"🎒 <b>Инвентарь пуст</b>\n\n"
            f"📦 Использовано: 0/{user.inventory_size}\n\n"
            f"Отправляйтесь в магазин, чтобы купить предметы!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Магазин", callback_data="shop_menu")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
            ])
        )
        await callback.answer()
        return
    
    # Group items by type
    equipped_items = []
    weapons = []
    armor = []
    consumables = []
    other_items = []
    
    for user_item in inventory:
        if user_item.is_equipped:
            equipped_items.append(user_item)
        elif user_item.item.item_type == ItemTypeEnum.weapon:
            weapons.append(user_item)
        elif user_item.item.item_type == ItemTypeEnum.armor:
            armor.append(user_item)
        elif user_item.item.item_type == ItemTypeEnum.consumable:
            consumables.append(user_item)
        else:
            other_items.append(user_item)
    
    inventory_text = f"🎒 <b>Инвентарь</b>\n\n"
    inventory_text += f"📦 Использовано: {stats['total_items']}/{user.inventory_size}\n\n"
    
    # Show equipped items
    if equipped_items:
        inventory_text += "⚡ <b>Экипировано:</b>\n"
        for user_item in equipped_items:
            durability_text = f" ({user_item.current_durability}/{user_item.item.max_durability})" if user_item.item.max_durability > 0 else ""
            inventory_text += f"✅ {user_item.item.rarity_emoji} {user_item.item.name}{durability_text}\n"
        inventory_text += "\n"
    
    builder = InlineKeyboardBuilder()
    
    # Show inventory categories
    if weapons:
        builder.row(InlineKeyboardButton(
            text=f"⚔️ Оружие ({len(weapons)})",
            callback_data="inventory_weapons"
        ))
    
    if armor:
        builder.row(InlineKeyboardButton(
            text=f"🛡️ Броня ({len(armor)})",
            callback_data="inventory_armor"
        ))
    
    if consumables:
        builder.row(InlineKeyboardButton(
            text=f"🧪 Зелья ({len(consumables)})",
            callback_data="inventory_consumables"
        ))
    
    if other_items:
        builder.row(InlineKeyboardButton(
            text=f"📦 Прочее ({len(other_items)})",
            callback_data="inventory_other"
        ))
    
    if equipped_items:
        builder.row(InlineKeyboardButton(
            text="⚡ Управление экипировкой",
            callback_data="inventory_equipped"
        ))
    
    builder.row(
        InlineKeyboardButton(text="🛒 Магазин", callback_data="shop_menu"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    )
    
    await callback.message.edit_text(
        inventory_text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("inventory_"))
async def show_inventory_category(callback: CallbackQuery, user, is_registered: bool):
    """Show specific inventory category"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    category = callback.data.replace("inventory_", "")
    
    inventory_service = InventoryService()
    inventory = await inventory_service.get_user_inventory(user.id)
    
    # Filter items by category
    filtered_items = []
    category_name = ""
    
    if category == "weapons":
        filtered_items = [item for item in inventory if item.item.item_type == ItemTypeEnum.weapon and not item.is_equipped]
        category_name = "⚔️ Оружие"
    elif category == "armor":
        filtered_items = [item for item in inventory if item.item.item_type == ItemTypeEnum.armor and not item.is_equipped]
        category_name = "🛡️ Броня"
    elif category == "consumables":
        filtered_items = [item for item in inventory if item.item.item_type == ItemTypeEnum.consumable]
        category_name = "🧪 Зелья"
    elif category == "other":
        filtered_items = [item for item in inventory if item.item.item_type not in [ItemTypeEnum.weapon, ItemTypeEnum.armor, ItemTypeEnum.consumable] and not item.is_equipped]
        category_name = "📦 Прочее"
    elif category == "equipped":
        filtered_items = [item for item in inventory if item.is_equipped]
        category_name = "⚡ Экипированные предметы"
    
    if not filtered_items:
        await callback.answer(f"В категории '{category_name}' нет предметов!", show_alert=True)
        return
    
    inventory_text = f"{category_name}\n\n"
    
    builder = InlineKeyboardBuilder()
    
    for user_item in filtered_items[:10]:  # Show max 10 items
        # Item info
        item = user_item.item
        quantity_text = f" x{user_item.quantity}" if user_item.quantity > 1 else ""
        durability_text = f" ({user_item.current_durability}/{item.max_durability})" if item.max_durability > 0 else ""
        
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
        
        inventory_text += (
            f"{item.rarity_emoji} <b>{item.name}</b>{quantity_text}{durability_text}\n"
        )
        if stats_text:
            inventory_text += f"📊 {stats_text}\n"
        inventory_text += "\n"
        
        # Action buttons
        if item.item_type in [ItemTypeEnum.weapon, ItemTypeEnum.armor]:
            if user_item.is_equipped:
                builder.row(InlineKeyboardButton(
                    text=f"📤 Снять {item.name}",
                    callback_data=f"unequip_{user_item.id}"
                ))
            else:
                builder.row(InlineKeyboardButton(
                    text=f"📥 Экипировать {item.name}",
                    callback_data=f"equip_{user_item.id}"
                ))
        elif item.item_type == ItemTypeEnum.consumable:
            builder.row(InlineKeyboardButton(
                text=f"🧪 Использовать {item.name}",
                callback_data=f"use_item_{user_item.id}"
            ))
        
        # Sell button
        if not user_item.is_equipped:
            sell_price = int(item.price * 0.5)
            builder.row(InlineKeyboardButton(
                text=f"💰 Продать за {sell_price}г",
                callback_data=f"sell_item_{user_item.id}"
            ))
    
    builder.row(
        InlineKeyboardButton(text="🔙 К инвентарю", callback_data="inventory")
    )
    
    await callback.message.edit_text(
        inventory_text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("equip_"))
async def equip_item(callback: CallbackQuery, user, is_registered: bool):
    """Equip an item"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    user_item_id = int(callback.data.replace("equip_", ""))
    
    inventory_service = InventoryService()
    success, message = await inventory_service.equip_item(user.id, user_item_id)
    
    if success:
        await callback.answer(f"✅ {message}", show_alert=True)
        # Refresh inventory
        await show_inventory(callback, user, is_registered)
    else:
        await callback.answer(f"❌ {message}", show_alert=True)

@router.callback_query(F.data.startswith("unequip_"))
async def unequip_item(callback: CallbackQuery, user, is_registered: bool):
    """Unequip an item"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    user_item_id = int(callback.data.replace("unequip_", ""))
    
    inventory_service = InventoryService()
    success, message = await inventory_service.unequip_item(user.id, user_item_id)
    
    if success:
        await callback.answer(f"✅ {message}", show_alert=True)
        # Refresh inventory
        await show_inventory(callback, user, is_registered)
    else:
        await callback.answer(f"❌ {message}", show_alert=True)

@router.callback_query(F.data.startswith("use_item_"))
async def use_item(callback: CallbackQuery, user, is_registered: bool):
    """Use a consumable item"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    user_item_id = int(callback.data.replace("use_item_", ""))
    
    inventory_service = InventoryService()
    success, message = await inventory_service.use_item(user.id, user_item_id)
    
    if success:
        await callback.answer(f"✅ {message}", show_alert=True)
        # Refresh inventory to show updated quantities
        await show_inventory(callback, user, is_registered)
    else:
        await callback.answer(f"❌ {message}", show_alert=True)

@router.callback_query(F.data.startswith("sell_item_"))
async def sell_item(callback: CallbackQuery, user, is_registered: bool):
    """Sell an item"""
    if not is_registered:
        await callback.answer("Сначала нужно зарегистрироваться!")
        return
    
    user_item_id = int(callback.data.replace("sell_item_", ""))
    
    inventory_service = InventoryService()
    success, message = await inventory_service.sell_item(user.id, user_item_id, 1)
    
    if success:
        await callback.answer(f"✅ {message}", show_alert=True)
        # Refresh inventory
        await show_inventory(callback, user, is_registered)
    else:
        await callback.answer(f"❌ {message}", show_alert=True)