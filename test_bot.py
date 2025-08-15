#!/usr/bin/env python3
"""
Test script for Telegram Scheduler Bot
This script tests the core functionality without requiring a real Telegram bot token
"""

import os
import sys
import sqlite3
import tempfile
from datetime import datetime, timedelta
import pytz

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import BotDatabase
from scheduler import MessageScheduler

class MockBot:
    """Mock bot for testing"""
    def __init__(self):
        self.sent_messages = []
    
    async def send_message(self, chat_id, text, parse_mode=None):
        """Mock send message function"""
        self.sent_messages.append({
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'timestamp': datetime.now()
        })
        print(f"[MOCK] Sent to {chat_id}: {text[:50]}...")

def test_database():
    """Test database functionality"""
    print("🧪 Testing Database Functionality...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db = BotDatabase(db_path)
        
        # Test adding group
        assert db.add_group(-123456, "Test Group", "America/New_York")
        print("✅ Group addition works")
        
        # Test adding admin
        assert db.add_group_admin(-123456, 789, "testuser")
        print("✅ Admin addition works")
        
        # Test checking admin
        assert db.is_group_admin(-123456, 789)
        print("✅ Admin checking works")
        
        # Test adding scheduled message
        assert db.add_scheduled_message(
            chat_id=-123456,
            message_type='daily',
            schedule_time='09:00',
            message_template='Good morning! Today is {day}, {date}'
        )
        print("✅ Scheduled message addition works")
        
        # Test getting scheduled messages
        messages = db.get_scheduled_messages(-123456)
        assert len(messages) == 1
        assert messages[0]['message_type'] == 'daily'
        print("✅ Message retrieval works")
        
        # Test timezone functions
        assert db.get_group_timezone(-123456) == "America/New_York"
        assert db.update_group_timezone(-123456, "UTC")
        assert db.get_group_timezone(-123456) == "UTC"
        print("✅ Timezone functions work")
        
        print("✅ All database tests passed!")
        
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

def test_scheduler():
    """Test scheduler functionality"""
    print("\n🧪 Testing Scheduler Functionality...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db = BotDatabase(db_path)
        mock_bot = MockBot()
        scheduler = MessageScheduler(mock_bot, db)
        
        # Add test group
        db.add_group(-123456, "Test Group", "UTC")
        
        # Test adding daily message
        assert scheduler.add_daily_message(-123456, "10:00", "Daily test message: {date}")
        print("✅ Daily message scheduling works")
        
        # Test adding countdown message
        future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        assert scheduler.add_countdown_message(-123456, "11:00", future_date, "Test Event")
        print("✅ Countdown message scheduling works")
        
        # Test getting schedules
        schedules = scheduler.get_group_schedules(-123456)
        assert len(schedules) == 2
        print("✅ Schedule retrieval works")
        
        # Test message formatting
        daily_config = {
            'message_template': 'Today is {day}, {date} at {time}',
            'timezone': 'UTC'
        }
        formatted = scheduler._format_daily_message(daily_config)
        assert '{day}' not in formatted  # Should be replaced
        assert '{date}' not in formatted  # Should be replaced
        print("✅ Daily message formatting works")
        
        # Test countdown formatting
        countdown_config = {
            'target_date': future_date,
            'title': 'Test Event',
            'timezone': 'UTC'
        }
        formatted = scheduler._format_countdown_message(countdown_config)
        assert 'Test Event' in formatted
        assert 'days remaining' in formatted
        print("✅ Countdown message formatting works")
        
        print("✅ All scheduler tests passed!")
        
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

def test_timezone_handling():
    """Test timezone functionality"""
    print("\n🧪 Testing Timezone Handling...")
    
    # Test timezone validation
    try:
        tz = pytz.timezone('America/New_York')
        current_time = datetime.now(tz)
        print(f"✅ Timezone handling works: {current_time.strftime('%H:%M %Z')}")
    except Exception as e:
        print(f"❌ Timezone test failed: {e}")
        return False
    
    # Test common timezones
    common_timezones = ['UTC', 'America/New_York', 'Europe/London', 'Asia/Tokyo']
    for tz_name in common_timezones:
        try:
            tz = pytz.timezone(tz_name)
            current_time = datetime.now(tz)
            print(f"✅ {tz_name}: {current_time.strftime('%H:%M')}")
        except Exception as e:
            print(f"❌ {tz_name} failed: {e}")
            return False
    
    print("✅ All timezone tests passed!")
    return True

def test_message_templates():
    """Test message template functionality"""
    print("\n🧪 Testing Message Templates...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db = BotDatabase(db_path)
        mock_bot = MockBot()
        scheduler = MessageScheduler(mock_bot, db)
        
        # Test template with all placeholders
        template_config = {
            'message_template': 'Date: {date}, Time: {time}, Day: {day}, Month: {month}, Year: {year}',
            'timezone': 'UTC'
        }
        
        formatted = scheduler._format_daily_message(template_config)
        
        # Check that all placeholders were replaced
        placeholders = ['{date}', '{time}', '{day}', '{month}', '{year}']
        for placeholder in placeholders:
            assert placeholder not in formatted, f"Placeholder {placeholder} not replaced"
        
        print(f"✅ Template formatting works: {formatted}")
        print("✅ All template tests passed!")
        
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

def main():
    """Run all tests"""
    print("🚀 Starting Telegram Scheduler Bot Tests\n")
    
    try:
        test_database()
        test_scheduler()
        test_timezone_handling()
        test_message_templates()
        
        print("\n🎉 All tests passed! The bot is ready to use.")
        print("\nNext steps:")
        print("1. Get a bot token from @BotFather on Telegram")
        print("2. Copy .env.example to .env and add your bot token")
        print("3. Install dependencies: pip install -r requirements.txt")
        print("4. Run the bot: python bot.py")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()