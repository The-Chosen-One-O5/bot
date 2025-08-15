#!/usr/bin/env python3
"""
Example script showing how to run the Telegram Scheduler Bot
This demonstrates the proper way to start the bot with error handling
"""

import os
import sys
import logging
from pathlib import Path

def main():
    """Main function to run the bot with proper error handling"""
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    # Check if .env file exists
    env_file = Path('.env')
    if not env_file.exists():
        logger.error("❌ .env file not found!")
        logger.info("📝 Please copy .env.example to .env and add your bot token")
        logger.info("💡 Run: cp .env.example .env")
        sys.exit(1)
    
    # Check if bot token is configured
    from dotenv import load_dotenv
    load_dotenv()
    
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token or bot_token == 'your_bot_token_here':
        logger.error("❌ BOT_TOKEN not configured!")
        logger.info("📝 Please edit .env file and add your bot token from @BotFather")
        sys.exit(1)
    
    # Import and run the bot
    try:
        logger.info("🚀 Starting Telegram Scheduler Bot...")
        from bot import main as bot_main
        bot_main()
        
    except KeyboardInterrupt:
        logger.info("⏹️  Bot stopped by user")
        
    except ImportError as e:
        logger.error(f"❌ Missing dependencies: {e}")
        logger.info("📦 Please install dependencies: pip install -r requirements.txt")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        logger.info("🔍 Check the logs above for more details")
        sys.exit(1)

if __name__ == '__main__':
    main()