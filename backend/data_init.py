#!/usr/bin/env python3
"""
Initialize game data - items, equipment, etc.
"""
import asyncio
from sqlalchemy import select, func, text
from config.database import AsyncSessionLocal
from models.item import Item, ItemTypeEnum, RarityEnum

async def init_game_data():
    """Initialize basic game items"""
    async with AsyncSessionLocal() as session:
        # Check if items already exist
        existing_items = await session.execute(select(func.count(Item.id)))
        if existing_items.scalar() > 0:
            print("Items already exist, skipping initialization")
            return
        
        # Weapons
        weapons = [
            Item(
                name="Ржавый меч",
                description="Старый меч начинающего воина",
                item_type=ItemTypeEnum.weapon,
                rarity=RarityEnum.common,
                price=50,
                level_required=1,
                strength_bonus=5,
                durability=80,
                max_durability=80
            ),
            Item(
                name="Железный меч",
                description="Надежное оружие из качественного железа",
                item_type=ItemTypeEnum.weapon,
                rarity=RarityEnum.common,
                price=150,
                level_required=3,
                strength_bonus=12,
                durability=100,
                max_durability=100
            ),
            Item(
                name="Серебряный клинок",
                description="Элегантный меч из серебра",
                item_type=ItemTypeEnum.weapon,
                rarity=RarityEnum.rare,
                price=400,
                level_required=7,
                strength_bonus=20,
                agility_bonus=5,
                durability=120,
                max_durability=120
            ),
            Item(
                name="Огненный меч",
                description="Легендарный клинок, пылающий магическим огнем",
                item_type=ItemTypeEnum.weapon,
                rarity=RarityEnum.legendary,
                price=1000,
                level_required=15,
                strength_bonus=35,
                agility_bonus=10,
                special_effect="Поджигает противника",
                durability=150,
                max_durability=150
            )
        ]
        
        # Armor
        armor_items = [
            Item(
                name="Кожаная куртка",
                description="Простая защита из кожи",
                item_type=ItemTypeEnum.armor,
                rarity=RarityEnum.common,
                price=40,
                level_required=1,
                armor_bonus=8,
                durability=60,
                max_durability=60
            ),
            Item(
                name="Кольчуга",
                description="Металлическая кольчужная рубаха",
                item_type=ItemTypeEnum.armor,
                rarity=RarityEnum.common,
                price=120,
                level_required=3,
                armor_bonus=18,
                durability=100,
                max_durability=100
            ),
            Item(
                name="Стальные доспехи",
                description="Тяжелые доспехи из закаленной стали",
                item_type=ItemTypeEnum.armor,
                rarity=RarityEnum.rare,
                price=350,
                level_required=6,
                armor_bonus=30,
                hp_bonus=25,
                durability=120,
                max_durability=120
            ),
            Item(
                name="Драконья чешуя",
                description="Магические доспехи из чешуи древнего дракона",
                item_type=ItemTypeEnum.armor,
                rarity=RarityEnum.legendary,
                price=800,
                level_required=12,
                armor_bonus=45,
                hp_bonus=50,
                special_effect="Сопротивление магии",
                durability=180,
                max_durability=180
            )
        ]
        
        # Consumables
        consumables = [
            Item(
                name="Малое зелье здоровья",
                description="Восстанавливает небольшое количество HP",
                item_type=ItemTypeEnum.consumable,
                rarity=RarityEnum.common,
                price=25,
                level_required=1,
                hp_bonus=30,
                weight=1
            ),
            Item(
                name="Зелье здоровья",
                description="Восстанавливает умеренное количество HP",
                item_type=ItemTypeEnum.consumable,
                rarity=RarityEnum.common,
                price=50,
                level_required=1,
                hp_bonus=60,
                weight=1
            ),
            Item(
                name="Большое зелье здоровья",
                description="Восстанавливает много HP",
                item_type=ItemTypeEnum.consumable,
                rarity=RarityEnum.rare,
                price=100,
                level_required=5,
                hp_bonus=120,
                weight=1
            ),
            Item(
                name="Зелье маны",
                description="Восстанавливает магическую энергию",
                item_type=ItemTypeEnum.consumable,
                rarity=RarityEnum.common,
                price=40,
                level_required=1,
                mana_bonus=25,
                weight=1
            ),
            Item(
                name="Большое зелье маны",
                description="Восстанавливает много магической энергии",
                item_type=ItemTypeEnum.consumable,
                rarity=RarityEnum.rare,
                price=80,
                level_required=3,
                mana_bonus=50,
                weight=1
            )
        ]
        
        # Materials
        materials = [
            Item(
                name="Железная руда",
                description="Сырье для изготовления оружия",
                item_type=ItemTypeEnum.material,
                rarity=RarityEnum.common,
                price=10,
                level_required=1,
                weight=2
            ),
            Item(
                name="Серебряная руда",
                description="Редкий металл для качественного снаряжения",
                item_type=ItemTypeEnum.material,
                rarity=RarityEnum.rare,
                price=30,
                level_required=1,
                weight=2
            )
        ]
        
        # Add all items
        all_items = weapons + armor_items + consumables + materials
        
        for item in all_items:
            session.add(item)
        
        await session.commit()
        print(f"Added {len(all_items)} items to the database")

if __name__ == "__main__":
    asyncio.run(init_game_data())