import asyncio
import schedule
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import pytz
from database import BotDatabase

class MessageScheduler:
    def __init__(self, bot, database: BotDatabase):
        self.bot = bot
        self.db = database
        self.running = False
        self.scheduler_thread = None
    
    def start(self):
        """Start the scheduler in a separate thread"""
        if not self.running:
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()
            logging.info("Message scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
        logging.info("Message scheduler stopped")
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        # Clear any existing jobs
        schedule.clear()
        
        # Schedule the job checker to run every minute
        schedule.every().minute.do(self._check_and_send_messages)
        
        while self.running:
            schedule.run_pending()
            threading.Event().wait(1)  # Sleep for 1 second
    
    def _check_and_send_messages(self):
        """Check for messages that need to be sent and send them"""
        try:
            scheduled_messages = self.db.get_scheduled_messages()
            current_time = datetime.now()
            
            for msg_config in scheduled_messages:
                if self._should_send_message(msg_config, current_time):
                    asyncio.create_task(self._send_scheduled_message(msg_config))
                    
        except Exception as e:
            logging.error(f"Error in scheduler check: {e}")
    
    def _should_send_message(self, msg_config: Dict, current_time: datetime) -> bool:
        """Check if a message should be sent now"""
        try:
            # Get the timezone for this group
            group_timezone = pytz.timezone(msg_config.get('timezone', 'UTC'))
            local_time = current_time.astimezone(group_timezone)
            
            # Parse the scheduled time
            schedule_time_str = msg_config['schedule_time']  # Format: "HH:MM"
            schedule_hour, schedule_minute = map(int, schedule_time_str.split(':'))
            
            # Check if current time matches scheduled time (within 1 minute window)
            if (local_time.hour == schedule_hour and 
                local_time.minute == schedule_minute):
                return True
                
            return False
            
        except Exception as e:
            logging.error(f"Error checking message schedule: {e}")
            return False
    
    async def _send_scheduled_message(self, msg_config: Dict):
        """Send a scheduled message"""
        try:
            chat_id = msg_config['chat_id']
            message_type = msg_config['message_type']
            
            if message_type == 'daily':
                message = self._format_daily_message(msg_config)
            elif message_type == 'countdown':
                message = self._format_countdown_message(msg_config)
            else:
                message = msg_config['message_template']
            
            if message:
                await self.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
                logging.info(f"Sent scheduled message to group {chat_id}")
            
        except Exception as e:
            logging.error(f"Error sending scheduled message: {e}")
    
    def _format_daily_message(self, msg_config: Dict) -> str:
        """Format a daily message with current date/time info"""
        try:
            group_timezone = pytz.timezone(msg_config.get('timezone', 'UTC'))
            local_time = datetime.now(group_timezone)
            
            template = msg_config['message_template']
            
            # Replace common placeholders
            message = template.replace('{date}', local_time.strftime('%Y-%m-%d'))
            message = message.replace('{time}', local_time.strftime('%H:%M'))
            message = message.replace('{day}', local_time.strftime('%A'))
            message = message.replace('{month}', local_time.strftime('%B'))
            message = message.replace('{year}', str(local_time.year))
            
            return message
            
        except Exception as e:
            logging.error(f"Error formatting daily message: {e}")
            return msg_config['message_template']
    
    def _format_countdown_message(self, msg_config: Dict) -> str:
        """Format a countdown message"""
        try:
            target_date_str = msg_config['target_date']
            title = msg_config.get('title', 'Event')
            
            # Parse target date
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
            
            # Get timezone-aware current time
            group_timezone = pytz.timezone(msg_config.get('timezone', 'UTC'))
            current_time = datetime.now(group_timezone).replace(tzinfo=None)
            
            # Calculate days remaining
            days_remaining = (target_date - current_time).days
            
            if days_remaining > 0:
                message = f"🗓️ <b>{title}</b>\n\n⏰ <b>{days_remaining} days remaining!</b>\n\nTarget Date: {target_date.strftime('%B %d, %Y')}"
            elif days_remaining == 0:
                message = f"🎉 <b>{title}</b>\n\n🚀 <b>TODAY IS THE DAY!</b>\n\nThe wait is over! 🎊"
            else:
                # Event has passed
                days_passed = abs(days_remaining)
                message = f"📅 <b>{title}</b>\n\n✅ Event completed {days_passed} days ago\n\nDate: {target_date.strftime('%B %d, %Y')}"
            
            return message
            
        except Exception as e:
            logging.error(f"Error formatting countdown message: {e}")
            return f"⏰ Countdown: {msg_config.get('title', 'Event')}"
    
    def add_daily_message(self, chat_id: int, time_str: str, message: str) -> bool:
        """Add a daily scheduled message"""
        try:
            # Validate time format
            datetime.strptime(time_str, '%H:%M')
            
            return self.db.add_scheduled_message(
                chat_id=chat_id,
                message_type='daily',
                schedule_time=time_str,
                message_template=message
            )
        except ValueError:
            logging.error(f"Invalid time format: {time_str}")
            return False
        except Exception as e:
            logging.error(f"Error adding daily message: {e}")
            return False
    
    def add_countdown_message(self, chat_id: int, time_str: str, target_date: str, title: str) -> bool:
        """Add a countdown message"""
        try:
            # Validate time format
            datetime.strptime(time_str, '%H:%M')
            # Validate date format
            datetime.strptime(target_date, '%Y-%m-%d')
            
            return self.db.add_scheduled_message(
                chat_id=chat_id,
                message_type='countdown',
                schedule_time=time_str,
                message_template='',  # Template is generated dynamically
                target_date=target_date,
                title=title
            )
        except ValueError as e:
            logging.error(f"Invalid date/time format: {e}")
            return False
        except Exception as e:
            logging.error(f"Error adding countdown message: {e}")
            return False
    
    def get_group_schedules(self, chat_id: int) -> List[Dict]:
        """Get all scheduled messages for a group"""
        return self.db.get_scheduled_messages(chat_id)
    
    def remove_schedule(self, message_id: int, chat_id: int) -> bool:
        """Remove a scheduled message"""
        return self.db.remove_scheduled_message(message_id, chat_id)