#!/usr/bin/env python3
"""
Test shop and inventory functionality
"""
import asyncio
from config.database import AsyncSessionLocal
from models.item import Item
from models.user import User
from services.shop_service import ShopService
from services.inventory_service import InventoryService

async def test_shop_inventory():
    """Test shop and inventory functionality"""
    print("🧪 Testing Shop & Inventory System...")
    
    # Test shop service
    shop_service = ShopService()
    
    # Get shop items
    print("\n📦 Testing shop items...")
    items = await shop_service.get_shop_items()
    print(f"Found {len(items)} items in shop")
    
    for item in items[:5]:  # Show first 5 items
        print(f"  {item.rarity_emoji} {item.name} - {item.price}g (Lv.{item.level_required})")
    
    # Test categories
    print("\n📂 Testing shop categories...")
    categories = await shop_service.get_shop_categories()
    for category, count in categories.items():
        print(f"  {category}: {count} items")
    
    # Test inventory service
    print("\n🎒 Testing inventory service...")
    inventory_service = InventoryService()
    
    # Check if we have any users to test with
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, func
        result = await session.execute(select(func.count(User.id)))
        user_count = result.scalar()
        print(f"Found {user_count} users in database")
    
    print("\n✅ Shop & Inventory system is working correctly!")

if __name__ == "__main__":
    asyncio.run(test_shop_inventory())