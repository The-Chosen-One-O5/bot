import os
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatType
import pytz

from database import BotDatabase
from scheduler import MessageScheduler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO'))
)
logger = logging.getLogger(__name__)

class TelegramSchedulerBot:
    def __init__(self):
        self.token = os.getenv('BOT_TOKEN')
        if not self.token:
            raise ValueError("BOT_TOKEN not found in environment variables")
        
        self.db = BotDatabase(os.getenv('DATABASE_PATH', 'bot_data.db'))
        self.application = Application.builder().token(self.token).build()
        self.scheduler = MessageScheduler(self.application.bot, self.db)
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("setschedule", self.set_schedule_command))
        self.application.add_handler(CommandHandler("setcountdown", self.set_countdown_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("removeschedule", self.remove_schedule_command))
        self.application.add_handler(CommandHandler("settimezone", self.set_timezone_command))
        
        # Message handler for group messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        chat = update.effective_chat
        user = update.effective_user
        
        if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            # Add group to database
            group_name = chat.title or f"Group {chat.id}"
            self.db.add_group(chat.id, group_name)
            
            # Check if user is admin
            try:
                chat_member = await context.bot.get_chat_member(chat.id, user.id)
                if chat_member.status in ['administrator', 'creator']:
                    self.db.add_group_admin(chat.id, user.id, user.username)
                    
                    welcome_message = (
                        f"🤖 <b>Scheduler Bot Activated!</b>\n\n"
                        f"Hello {user.first_name}! I'm now ready to send scheduled messages in this group.\n\n"
                        f"<b>Available Commands:</b>\n"
                        f"• /setschedule - Set daily messages\n"
                        f"• /setcountdown - Set countdown messages\n"
                        f"• /status - View current schedules\n"
                        f"• /help - Show detailed help\n\n"
                        f"<i>Note: Only group admins can configure schedules.</i>"
                    )
                else:
                    welcome_message = (
                        f"🤖 <b>Scheduler Bot Added!</b>\n\n"
                        f"Hello! I'm ready to send scheduled messages, but only group admins can configure me.\n\n"
                        f"Use /help to see available commands."
                    )
                    
            except Exception as e:
                logger.error(f"Error checking admin status: {e}")
                welcome_message = "🤖 Scheduler Bot activated! Use /help for available commands."
            
            await update.message.reply_text(welcome_message, parse_mode='HTML')
            
        else:
            # Private chat
            await update.message.reply_text(
                "👋 Hello! I'm a group scheduler bot.\n\n"
                "Add me to a group and use /start there to begin scheduling messages!\n\n"
                "Use /help for more information."
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "🤖 <b>Telegram Scheduler Bot Help</b>\n\n"
            "<b>Commands for Group Admins:</b>\n"
            "• <code>/setschedule HH:MM message</code> - Set daily message\n"
            "  Example: <code>/setschedule 09:00 Good morning team! 🌅</code>\n\n"
            "• <code>/setcountdown HH:MM YYYY-MM-DD title</code> - Set countdown\n"
            "  Example: <code>/setcountdown 10:00 2024-12-31 New Year</code>\n\n"
            "• <code>/status</code> - View all scheduled messages\n"
            "• <code>/removeschedule ID</code> - Remove schedule by ID\n"
            "• <code>/settimezone TIMEZONE</code> - Set group timezone\n"
            "  Example: <code>/settimezone America/New_York</code>\n\n"
            "<b>Message Templates (for daily messages):</b>\n"
            "• <code>{date}</code> - Current date (YYYY-MM-DD)\n"
            "• <code>{time}</code> - Current time (HH:MM)\n"
            "• <code>{day}</code> - Day of week (Monday, Tuesday...)\n"
            "• <code>{month}</code> - Month name (January, February...)\n"
            "• <code>{year}</code> - Current year\n\n"
            "<b>Example with templates:</b>\n"
            "<code>/setschedule 08:00 📅 Today is {day}, {date}. Have a great day!</code>\n\n"
            "<b>Commands for Everyone:</b>\n"
            "• <code>/help</code> - Show this help message\n"
            "• <code>/status</code> - View current schedules\n\n"
            "<i>Note: Time format is 24-hour (HH:MM). All times are in the group's timezone.</i>"
        )
        
        await update.message.reply_text(help_text, parse_mode='HTML')
    
    async def set_schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /setschedule command"""
        chat = update.effective_chat
        user = update.effective_user
        
        # Check if it's a group
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("❌ This command only works in groups!")
            return
        
        # Check if user is admin
        if not await self._is_user_admin(context, chat.id, user.id):
            await update.message.reply_text("❌ Only group admins can set schedules!")
            return
        
        # Parse arguments
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Usage: <code>/setschedule HH:MM message</code>\n"
                "Example: <code>/setschedule 09:00 Good morning team! 🌅</code>",
                parse_mode='HTML'
            )
            return
        
        time_str = context.args[0]
        message = ' '.join(context.args[1:])
        
        # Validate time format
        try:
            datetime.strptime(time_str, '%H:%M')
        except ValueError:
            await update.message.reply_text("❌ Invalid time format! Use HH:MM (24-hour format)")
            return
        
        # Add to scheduler
        if self.scheduler.add_daily_message(chat.id, time_str, message):
            timezone = self.db.get_group_timezone(chat.id)
            await update.message.reply_text(
                f"✅ <b>Daily message scheduled!</b>\n\n"
                f"⏰ Time: {time_str} ({timezone})\n"
                f"💬 Message: {message}\n\n"
                f"<i>This message will be sent daily at the specified time.</i>",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text("❌ Failed to schedule message. Please try again.")
    
    async def set_countdown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /setcountdown command"""
        chat = update.effective_chat
        user = update.effective_user
        
        # Check if it's a group
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("❌ This command only works in groups!")
            return
        
        # Check if user is admin
        if not await self._is_user_admin(context, chat.id, user.id):
            await update.message.reply_text("❌ Only group admins can set countdowns!")
            return
        
        # Parse arguments
        if len(context.args) < 3:
            await update.message.reply_text(
                "❌ Usage: <code>/setcountdown HH:MM YYYY-MM-DD title</code>\n"
                "Example: <code>/setcountdown 10:00 2024-12-31 New Year Celebration</code>",
                parse_mode='HTML'
            )
            return
        
        time_str = context.args[0]
        date_str = context.args[1]
        title = ' '.join(context.args[2:])
        
        # Validate formats
        try:
            datetime.strptime(time_str, '%H:%M')
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid format!\n"
                "Time: HH:MM (24-hour)\n"
                "Date: YYYY-MM-DD"
            )
            return
        
        # Add to scheduler
        if self.scheduler.add_countdown_message(chat.id, time_str, date_str, title):
            timezone = self.db.get_group_timezone(chat.id)
            days_until = (target_date - datetime.now()).days
            
            await update.message.reply_text(
                f"✅ <b>Countdown scheduled!</b>\n\n"
                f"🎯 Event: {title}\n"
                f"📅 Target Date: {target_date.strftime('%B %d, %Y')}\n"
                f"⏰ Daily Update: {time_str} ({timezone})\n"
                f"⏳ Days Remaining: {days_until}\n\n"
                f"<i>Daily countdown updates will be sent at the specified time.</i>",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text("❌ Failed to schedule countdown. Please try again.")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        chat = update.effective_chat
        
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("❌ This command only works in groups!")
            return
        
        schedules = self.scheduler.get_group_schedules(chat.id)
        
        if not schedules:
            await update.message.reply_text("📭 No scheduled messages found for this group.")
            return
        
        timezone = self.db.get_group_timezone(chat.id)
        status_text = f"📋 <b>Scheduled Messages ({timezone})</b>\n\n"
        
        for i, schedule in enumerate(schedules, 1):
            msg_type = schedule['message_type']
            time = schedule['schedule_time']
            
            if msg_type == 'daily':
                message_preview = schedule['message_template'][:50]
                if len(schedule['message_template']) > 50:
                    message_preview += "..."
                status_text += f"<b>{i}.</b> Daily Message (ID: {schedule['id']})\n"
                status_text += f"   ⏰ {time}\n"
                status_text += f"   💬 {message_preview}\n\n"
                
            elif msg_type == 'countdown':
                title = schedule['title']
                target_date = schedule['target_date']
                try:
                    target = datetime.strptime(target_date, '%Y-%m-%d')
                    days_left = (target - datetime.now()).days
                    status_text += f"<b>{i}.</b> Countdown (ID: {schedule['id']})\n"
                    status_text += f"   🎯 {title}\n"
                    status_text += f"   ⏰ {time}\n"
                    status_text += f"   📅 {target.strftime('%B %d, %Y')}\n"
                    status_text += f"   ⏳ {days_left} days remaining\n\n"
                except:
                    status_text += f"<b>{i}.</b> Countdown (ID: {schedule['id']})\n"
                    status_text += f"   🎯 {title}\n"
                    status_text += f"   ⏰ {time}\n\n"
        
        status_text += f"<i>Use /removeschedule ID to remove a schedule</i>"
        
        await update.message.reply_text(status_text, parse_mode='HTML')
    
    async def remove_schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /removeschedule command"""
        chat = update.effective_chat
        user = update.effective_user
        
        # Check if it's a group
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("❌ This command only works in groups!")
            return
        
        # Check if user is admin
        if not await self._is_user_admin(context, chat.id, user.id):
            await update.message.reply_text("❌ Only group admins can remove schedules!")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Usage: <code>/removeschedule ID</code>\n"
                "Use /status to see schedule IDs",
                parse_mode='HTML'
            )
            return
        
        try:
            schedule_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid schedule ID! Must be a number.")
            return
        
        if self.scheduler.remove_schedule(schedule_id, chat.id):
            await update.message.reply_text(f"✅ Schedule {schedule_id} removed successfully!")
        else:
            await update.message.reply_text(f"❌ Schedule {schedule_id} not found or couldn't be removed.")
    
    async def set_timezone_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settimezone command"""
        chat = update.effective_chat
        user = update.effective_user
        
        # Check if it's a group
        if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await update.message.reply_text("❌ This command only works in groups!")
            return
        
        # Check if user is admin
        if not await self._is_user_admin(context, chat.id, user.id):
            await update.message.reply_text("❌ Only group admins can set timezone!")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Usage: <code>/settimezone TIMEZONE</code>\n\n"
                "Examples:\n"
                "• <code>/settimezone UTC</code>\n"
                "• <code>/settimezone America/New_York</code>\n"
                "• <code>/settimezone Europe/London</code>\n"
                "• <code>/settimezone Asia/Tokyo</code>",
                parse_mode='HTML'
            )
            return
        
        timezone_str = context.args[0]
        
        # Validate timezone
        try:
            pytz.timezone(timezone_str)
        except pytz.exceptions.UnknownTimeZoneError:
            await update.message.reply_text(
                f"❌ Unknown timezone: {timezone_str}\n\n"
                "Please use a valid timezone like:\n"
                "• UTC\n"
                "• America/New_York\n"
                "• Europe/London\n"
                "• Asia/Tokyo"
            )
            return
        
        if self.db.update_group_timezone(chat.id, timezone_str):
            current_time = datetime.now(pytz.timezone(timezone_str))
            await update.message.reply_text(
                f"✅ <b>Timezone updated!</b>\n\n"
                f"🌍 New timezone: {timezone_str}\n"
                f"🕐 Current time: {current_time.strftime('%H:%M on %B %d, %Y')}\n\n"
                f"<i>All scheduled messages will now use this timezone.</i>",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text("❌ Failed to update timezone. Please try again.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages (for logging/monitoring)"""
        # This can be used for additional features like message analytics
        pass
    
    async def _is_user_admin(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> bool:
        """Check if user is admin in the group"""
        try:
            # Check with Telegram API
            chat_member = await context.bot.get_chat_member(chat_id, user_id)
            is_telegram_admin = chat_member.status in ['administrator', 'creator']
            
            # Update database if user is admin
            if is_telegram_admin:
                user = chat_member.user
                self.db.add_group_admin(chat_id, user_id, user.username)
            
            return is_telegram_admin
            
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            # Fallback to database check
            return self.db.is_group_admin(chat_id, user_id)
    
    async def run(self):
        """Start the bot"""
        logger.info("Starting Telegram Scheduler Bot...")
        
        # Start the message scheduler
        self.scheduler.start()
        
        # Start the bot
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("Bot is running! Press Ctrl+C to stop.")
        
        try:
            # Keep the bot running
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Stopping bot...")
        finally:
            # Cleanup
            self.scheduler.stop()
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

def main():
    """Main function"""
    try:
        bot = TelegramSchedulerBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == '__main__':
    main()