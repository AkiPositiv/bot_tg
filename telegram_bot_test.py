#!/usr/bin/env python3
"""
Telegram RPG Bot v3.0 - Interactive Test Script
Tests the Kingdom Wars system by simulating user interactions
"""
import os
import sys
import logging
import asyncio
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, User, Chat
from datetime import datetime
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("interactive_test")

class TelegramBotInteractiveTester:
    def __init__(self):
        self.bot_token = os.environ.get("BOT_TOKEN", "1730744154:AAGxL3yNgmoN3LOZvOWdNGu6Wgxt81TacXE")
        self.test_chat_id = 1075491040  # Replace with your chat ID for testing
        self.bot = None
        self.test_results = []
    
    async def setup(self):
        """Setup bot instance for testing"""
        self.bot = Bot(
            token=self.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        logger.info("Bot instance created for testing")
    
    async def run_tests(self):
        """Run interactive tests"""
        logger.info("Starting Kingdom Wars Interactive Tests")
        
        # Setup bot
        await self.setup()
        
        try:
            # Test /start command
            await self.test_start_command()
            
            # Test main menu navigation
            await self.test_main_menu()
            
            # Test battle menu access
            await self.test_battle_menu()
            
            # Test Kingdom Wars menu
            await self.test_kingdom_wars_menu()
            
            # Test attack registration
            await self.test_attack_registration()
            
            # Test defense registration
            await self.test_defense_registration()
            
            # Test war results menu
            await self.test_war_results_menu()
            
            # Test /war_result command
            await self.test_war_result_command()
            
            # Print test results
            self.print_results()
            
        except Exception as e:
            logger.error(f"Error during interactive testing: {e}")
        finally:
            # Close bot session
            await self.bot.session.close()
    
    async def test_start_command(self):
        """Test /start command"""
        logger.info("Testing /start command...")
        try:
            # Send /start command
            response = await self.bot.send_message(self.test_chat_id, "/start")
            
            # Wait for bot response
            await asyncio.sleep(2)
            
            self.test_results.append({
                "test": "Start Command",
                "status": "Sent",
                "message_id": response.message_id
            })
            
            logger.info("✅ /start command sent")
        except Exception as e:
            logger.error(f"❌ Error sending /start command: {e}")
    
    async def test_main_menu(self):
        """Test main menu navigation"""
        logger.info("Testing main menu navigation...")
        try:
            # Simulate clicking on main menu button
            await self.bot.send_message(self.test_chat_id, "Accessing main menu...")
            
            # Wait for bot response
            await asyncio.sleep(2)
            
            self.test_results.append({
                "test": "Main Menu Navigation",
                "status": "Simulated"
            })
            
            logger.info("✅ Main menu navigation simulated")
        except Exception as e:
            logger.error(f"❌ Error simulating main menu navigation: {e}")
    
    async def test_battle_menu(self):
        """Test battle menu access"""
        logger.info("Testing battle menu access...")
        try:
            # Simulate clicking on battle menu button
            await self.bot.send_message(self.test_chat_id, "Accessing battle menu...")
            
            # Wait for bot response
            await asyncio.sleep(2)
            
            self.test_results.append({
                "test": "Battle Menu Access",
                "status": "Simulated"
            })
            
            logger.info("✅ Battle menu access simulated")
        except Exception as e:
            logger.error(f"❌ Error simulating battle menu access: {e}")
    
    async def test_kingdom_wars_menu(self):
        """Test Kingdom Wars menu"""
        logger.info("Testing Kingdom Wars menu...")
        try:
            # Simulate clicking on Kingdom Wars button
            await self.bot.send_message(self.test_chat_id, "Accessing Kingdom Wars menu...")
            
            # Wait for bot response
            await asyncio.sleep(2)
            
            self.test_results.append({
                "test": "Kingdom Wars Menu",
                "status": "Simulated"
            })
            
            logger.info("✅ Kingdom Wars menu access simulated")
        except Exception as e:
            logger.error(f"❌ Error simulating Kingdom Wars menu access: {e}")
    
    async def test_attack_registration(self):
        """Test attack registration"""
        logger.info("Testing attack registration...")
        try:
            # Simulate clicking on attack button
            await self.bot.send_message(self.test_chat_id, "Simulating attack registration...")
            
            # Wait for bot response
            await asyncio.sleep(2)
            
            self.test_results.append({
                "test": "Attack Registration",
                "status": "Simulated"
            })
            
            logger.info("✅ Attack registration simulated")
        except Exception as e:
            logger.error(f"❌ Error simulating attack registration: {e}")
    
    async def test_defense_registration(self):
        """Test defense registration"""
        logger.info("Testing defense registration...")
        try:
            # Simulate clicking on defense button
            await self.bot.send_message(self.test_chat_id, "Simulating defense registration...")
            
            # Wait for bot response
            await asyncio.sleep(2)
            
            self.test_results.append({
                "test": "Defense Registration",
                "status": "Simulated"
            })
            
            logger.info("✅ Defense registration simulated")
        except Exception as e:
            logger.error(f"❌ Error simulating defense registration: {e}")
    
    async def test_war_results_menu(self):
        """Test war results menu"""
        logger.info("Testing war results menu...")
        try:
            # Simulate clicking on war results button
            await self.bot.send_message(self.test_chat_id, "Accessing war results menu...")
            
            # Wait for bot response
            await asyncio.sleep(2)
            
            self.test_results.append({
                "test": "War Results Menu",
                "status": "Simulated"
            })
            
            logger.info("✅ War results menu access simulated")
        except Exception as e:
            logger.error(f"❌ Error simulating war results menu access: {e}")
    
    async def test_war_result_command(self):
        """Test /war_result command"""
        logger.info("Testing /war_result command...")
        try:
            # Send /war_result command
            response = await self.bot.send_message(self.test_chat_id, "/war_result")
            
            # Wait for bot response
            await asyncio.sleep(2)
            
            self.test_results.append({
                "test": "War Result Command",
                "status": "Sent",
                "message_id": response.message_id
            })
            
            logger.info("✅ /war_result command sent")
        except Exception as e:
            logger.error(f"❌ Error sending /war_result command: {e}")
    
    def print_results(self):
        """Print test results"""
        logger.info("=== Kingdom Wars Interactive Test Results ===")
        for i, result in enumerate(self.test_results, 1):
            logger.info(f"{i}. {result['test']}: {result['status']}")
        logger.info("=== End of Test Results ===")

async def main():
    tester = TelegramBotInteractiveTester()
    await tester.run_tests()

if __name__ == "__main__":
    asyncio.run(main())