import asyncio
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, date, time as dt_time, timedelta
from typing import Optional, Dict, Any

import pytz
from telegram import Update, Chat, ChatMember, ChatMemberUpdated
from telegram.ext import (
    Application,
    ContextTypes,
    CommandHandler,
    CallbackContext,
    PicklePersistence,
    JobQueue,
    Job,
)


logger = logging.getLogger(__name__)


def parse_hhmm(hhmm: str) -> Optional[dt_time]:
    """Parse a ``HH:MM`` 24‑hour time string into a ``datetime.time``.

    Returns ``None`` if the string cannot be parsed.
    """
    try:
        hour_str, minute_str = hhmm.split(":", 1)
        hour = int(hour_str)
        minute = int(minute_str)
        if not (0 <= hour < 24 and 0 <= minute < 60):
            return None
        return dt_time(hour, minute)
    except Exception:
        return None


def parse_date(datestr: str) -> Optional[date]:
    """Parse a ``YYYY‑MM‑DD`` string into a ``datetime.date``.

    Returns ``None`` if the string cannot be parsed.
    """
    try:
        return datetime.strptime(datestr, "%Y-%m-%d").date()
    except Exception:
        return None


@dataclass
class ScheduleRecord:
    """Represents a row in the schedules database."""
    id: int
    chat_id: int
    schedule_type: str
    time_str: str
    end_date_str: Optional[str]
    message: str
    timezone: str


class SchedulerBot:
    """Bot that implements scheduling commands for Telegram groups.

    The bot uses a SQLite database to store schedules.  Each schedule
    corresponds to a job in the ``JobQueue``.  When the bot starts up it
    restores all persisted schedules and re‑schedules their jobs.
    """

    def __init__(self, token: str, db_path: str = "schedule.db") -> None:
        self.token = token
        self.db_path = db_path
        # Create the event loop early so that database initialisation can run
        # synchronously when ``__init__`` completes.
        self.loop = asyncio.get_event_loop()
        # Connect to the database and ensure the schedules table exists.
        self._init_db()
        # The application builder will create the job queue internally.
        self.app: Application = Application.builder().token(self.token).build()
        # A mapping from schedule id to job instance so we can cancel jobs
        self.active_jobs: Dict[int, Job] = {}
        # Register command handlers
        self._register_handlers()
        # Restore schedules from disk
        self.loop.run_until_complete(self._restore_schedules())

    def _init_db(self) -> None:
        """Initialise the SQLite database and create tables if needed."""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    schedule_type TEXT NOT NULL,
                    time_str TEXT NOT NULL,
                    end_date_str TEXT,
                    message TEXT NOT NULL,
                    timezone TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_timezones (
                    chat_id INTEGER PRIMARY KEY,
                    timezone TEXT NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _get_chat_timezone(self, chat_id: int) -> str:
        """Fetch the timezone string for a chat, defaulting to UTC."""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT timezone FROM chat_timezones WHERE chat_id = ?", (chat_id,)
            )
            row = cur.fetchone()
            if row:
                return row[0]
            return "UTC"
        finally:
            conn.close()

    async def _restore_schedules(self) -> None:
        """Load all schedules from the database and recreate their jobs."""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, chat_id, schedule_type, time_str, end_date_str, message, timezone FROM schedules")
            rows = cur.fetchall()
            for row in rows:
                rec = ScheduleRecord(*row)
                await self._schedule_job(rec)
        finally:
            conn.close()

    def _register_handlers(self) -> None:
        """Register all command handlers with the application."""
        self.app.add_handler(CommandHandler("setschedule", self.setschedule))
        self.app.add_handler(CommandHandler("setcountdown", self.setcountdown))
        self.app.add_handler(CommandHandler("setrepeating", self.setrepeating))
        self.app.add_handler(CommandHandler("status", self.status))
        self.app.add_handler(CommandHandler("removeschedule", self.removeschedule))
        self.app.add_handler(CommandHandler("settimezone", self.settimezone))

    async def _schedule_job(self, rec: ScheduleRecord) -> None:
        """Create a ``Job`` in the job queue for the given schedule record."""
        tz = pytz.timezone(rec.timezone)
        # Convert time string to time object
        t = parse_hhmm(rec.time_str)
        if t is None:
            logger.error("Invalid time string stored in DB: %s", rec.time_str)
            return
        # Determine callback function based on schedule type
        if rec.schedule_type == "daily":
            callback = self._daily_callback
        elif rec.schedule_type == "countdown":
            callback = self._countdown_callback
        elif rec.schedule_type == "repeating":
            callback = self._repeating_callback
        else:
            logger.error("Unknown schedule type: %s", rec.schedule_type)
            return
        # Compute time-of-day for scheduling
        hour = t.hour
        minute = t.minute
        # Unique name for the job to avoid duplicates
        job_name = f"schedule_{rec.id}"
        job: Job = self.app.job_queue.run_daily(
            callback=callback,
            time=dt_time(hour, minute, tzinfo=tz),
            name=job_name,
            data={"schedule_id": rec.id},
        )
        self.active_jobs[rec.id] = job
        logger.info("Scheduled job %s of type %s for chat %s", rec.id, rec.schedule_type, rec.chat_id)

    async def setschedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the ``/setschedule`` command.  Syntax: /setschedule HH:MM message"""
        if update.effective_chat is None:
            return
        chat_id = update.effective_chat.id
        # The user must provide at least 2 arguments: time and message
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("Usage: /setschedule HH:MM message")
            return
        time_str = args[0]
        message = " ".join(args[1:])
        t = parse_hhmm(time_str)
        if t is None:
            await update.message.reply_text("Invalid time format. Use HH:MM (24h).")
            return
        timezone_name = self._get_chat_timezone(chat_id)
        # Insert schedule into DB
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO schedules (chat_id, schedule_type, time_str, end_date_str, message, timezone) VALUES (?, ?, ?, ?, ?, ?)",
                (chat_id, "daily", time_str, None, message, timezone_name),
            )
            conn.commit()
            schedule_id = cur.lastrowid
        finally:
            conn.close()
        rec = ScheduleRecord(schedule_id, chat_id, "daily", time_str, None, message, timezone_name)
        await self._schedule_job(rec)
        await update.message.reply_text(f"Scheduled daily message (ID {schedule_id}) at {time_str}.")

    async def setcountdown(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the ``/setcountdown`` command.

        Syntax: /setcountdown HH:MM YYYY‑MM‑DD title

        Sends a daily countdown message that reports the number of days
        remaining until the target date.  Once the date is passed the job
        automatically removes itself.
        """
        if update.effective_chat is None:
            return
        chat_id = update.effective_chat.id
        args = context.args
        if len(args) < 3:
            await update.message.reply_text(
                "Usage: /setcountdown HH:MM YYYY-MM-DD title"
            )
            return
        time_str, date_str = args[0], args[1]
        title = " ".join(args[2:])
        t = parse_hhmm(time_str)
        target_date = parse_date(date_str)
        if t is None or target_date is None:
            await update.message.reply_text(
                "Invalid time or date. Time format: HH:MM, date format: YYYY-MM-DD."
            )
            return
        timezone_name = self._get_chat_timezone(chat_id)
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO schedules (chat_id, schedule_type, time_str, end_date_str, message, timezone) VALUES (?, ?, ?, ?, ?, ?)",
                (chat_id, "countdown", time_str, date_str, title, timezone_name),
            )
            conn.commit()
            schedule_id = cur.lastrowid
        finally:
            conn.close()
        rec = ScheduleRecord(schedule_id, chat_id, "countdown", time_str, date_str, title, timezone_name)
        await self._schedule_job(rec)
        await update.message.reply_text(
            f"Scheduled daily countdown (ID {schedule_id}) for {title} on {date_str} at {time_str}."
        )

    async def setrepeating(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the ``/setrepeating`` command.

        Syntax: /setrepeating HH:MM YYYY‑MM‑DD message

        Sends the given message every day at the specified time until the end
        date.  After the date has passed, the schedule automatically deletes
        itself.
        """
        if update.effective_chat is None:
            return
        chat_id = update.effective_chat.id
        args = context.args
        if len(args) < 3:
            await update.message.reply_text(
                "Usage: /setrepeating HH:MM YYYY-MM-DD message"
            )
            return
        time_str, end_date_str = args[0], args[1]
        message = " ".join(args[2:])
        t = parse_hhmm(time_str)
        end_date = parse_date(end_date_str)
        if t is None or end_date is None:
            await update.message.reply_text(
                "Invalid time or date. Time format: HH:MM, date format: YYYY-MM-DD."
            )
            return
        timezone_name = self._get_chat_timezone(chat_id)
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO schedules (chat_id, schedule_type, time_str, end_date_str, message, timezone) VALUES (?, ?, ?, ?, ?, ?)",
                (chat_id, "repeating", time_str, end_date_str, message, timezone_name),
            )
            conn.commit()
            schedule_id = cur.lastrowid
        finally:
            conn.close()
        rec = ScheduleRecord(schedule_id, chat_id, "repeating", time_str, end_date_str, message, timezone_name)
        await self._schedule_job(rec)
        await update.message.reply_text(
            f"Scheduled repeating message (ID {schedule_id}) every day at {time_str} until {end_date_str}."
        )

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """List all active schedules for the chat."""
        if update.effective_chat is None:
            return
        chat_id = update.effective_chat.id
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, schedule_type, time_str, end_date_str, message, timezone FROM schedules WHERE chat_id = ?",
                (chat_id,),
            )
            rows = cur.fetchall()
        finally:
            conn.close()
        if not rows:
            await update.message.reply_text("No schedules found for this chat.")
            return
        lines = ["Schedules:"]
        for row in rows:
            schedule_id, schedule_type, time_str, end_date_str, message, tz_name = row
            if schedule_type == "daily":
                lines.append(f"ID {schedule_id}: Daily at {time_str} ({tz_name}) – '{message[:30]}…'")
            elif schedule_type == "countdown":
                lines.append(
                    f"ID {schedule_id}: Countdown at {time_str} to {end_date_str} – {message[:30]}…"
                )
            elif schedule_type == "repeating":
                lines.append(
                    f"ID {schedule_id}: Repeating at {time_str} until {end_date_str} – '{message[:30]}…'"
                )
        await update.message.reply_text("\n".join(lines))

    async def removeschedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Remove a schedule by ID and cancel its job."""
        if update.effective_chat is None:
            return
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("Usage: /removeschedule ID")
            return
        try:
            schedule_id = int(args[0])
        except ValueError:
            await update.message.reply_text("ID must be a number.")
            return
        # Remove from DB
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
            deleted = cur.rowcount
            conn.commit()
        finally:
            conn.close()
        # Cancel job if exists
        job = self.active_jobs.pop(schedule_id, None)
        if job:
            job.schedule_removal()
        if deleted:
            await update.message.reply_text(f"Removed schedule {schedule_id}.")
        else:
            await update.message.reply_text(f"Schedule {schedule_id} not found.")

    async def settimezone(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Set the timezone for this chat.  Syntax: /settimezone America/Los_Angeles"""
        if update.effective_chat is None:
            return
        chat_id = update.effective_chat.id
        args = context.args
        if len(args) != 1:
            await update.message.reply_text(
                "Usage: /settimezone TIMEZONE (e.g. America/Los_Angeles)"
            )
            return
        tz_name = args[0]
        if tz_name not in pytz.all_timezones:
            await update.message.reply_text("Invalid timezone name.")
            return
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO chat_timezones (chat_id, timezone) VALUES (?, ?)",
                (chat_id, tz_name),
            )
            conn.commit()
        finally:
            conn.close()
        await update.message.reply_text(f"Timezone updated to {tz_name}.")

    # Callback functions for jobs
    async def _daily_callback(self, context: CallbackContext) -> None:
        """Send the scheduled message each day."""
        job_data = context.job.data or {}
        schedule_id = job_data.get("schedule_id")
        if schedule_id is None:
            return
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT chat_id, message FROM schedules WHERE id = ? AND schedule_type = 'daily'",
                (schedule_id,),
            )
            row = cur.fetchone()
            if not row:
                return
            chat_id, message = row
        finally:
            conn.close()
        # Replace template placeholders
        now = datetime.now(pytz.timezone(self._get_chat_timezone(chat_id)))
        formatted_msg = self._apply_templates(message, now)
        try:
            await context.bot.send_message(chat_id=chat_id, text=formatted_msg)
        except Exception as exc:
            logger.warning("Failed to send daily message: %s", exc)

    async def _countdown_callback(self, context: CallbackContext) -> None:
        """Send a countdown message each day until the target date."""
        job_data = context.job.data or {}
        schedule_id = job_data.get("schedule_id")
        if schedule_id is None:
            return
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT chat_id, time_str, end_date_str, message, timezone FROM schedules WHERE id = ? AND schedule_type = 'countdown'",
                (schedule_id,),
            )
            row = cur.fetchone()
            if not row:
                return
            chat_id, time_str, end_date_str, title, tz_name = row
        finally:
            conn.close()
        tz = pytz.timezone(tz_name)
        now = datetime.now(tz).date()
        end_date = parse_date(end_date_str)
        if end_date is None:
            return
        # If date has passed, remove schedule
        if now > end_date:
            await self._cancel_schedule(schedule_id)
            await context.bot.send_message(chat_id=chat_id, text=f"Countdown for {title} has ended.")
            return
        delta = end_date - now
        days = delta.days
        # Compose countdown message
        msg = f"{days} day{'s' if days != 1 else ''} remaining until {title}!"
        try:
            await context.bot.send_message(chat_id=chat_id, text=msg)
        except Exception as exc:
            logger.warning("Failed to send countdown message: %s", exc)

    async def _repeating_callback(self, context: CallbackContext) -> None:
        """Send a repeating message until the end date."""
        job_data = context.job.data or {}
        schedule_id = job_data.get("schedule_id")
        if schedule_id is None:
            return
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT chat_id, end_date_str, message, timezone FROM schedules WHERE id = ? AND schedule_type = 'repeating'",
                (schedule_id,),
            )
            row = cur.fetchone()
            if not row:
                return
            chat_id, end_date_str, message, tz_name = row
        finally:
            conn.close()
        tz = pytz.timezone(tz_name)
        now = datetime.now(tz).date()
        end_date = parse_date(end_date_str)
        if end_date is None:
            return
        # If date has passed, cancel schedule
        if now > end_date:
            await self._cancel_schedule(schedule_id)
            return
        now_dt = datetime.now(tz)
        formatted_msg = self._apply_templates(message, now_dt)
        try:
            await context.bot.send_message(chat_id=chat_id, text=formatted_msg)
        except Exception as exc:
            logger.warning("Failed to send repeating message: %s", exc)

    def _apply_templates(self, message: str, dt: datetime) -> str:
        """Replace template placeholders in messages with current values."""
        # Support {date}, {time}, {day}, {month}, {year}
        replacements = {
            "{date}": dt.strftime("%Y-%m-%d"),
            "{time}": dt.strftime("%H:%M"),
            "{day}": dt.strftime("%A"),
            "{month}": dt.strftime("%B"),
            "{year}": dt.strftime("%Y"),
        }
        result = message
        for key, value in replacements.items():
            result = result.replace(key, value)
        return result

    async def _cancel_schedule(self, schedule_id: int) -> None:
        """Remove a schedule from the DB and cancel its job."""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
            conn.commit()
        finally:
            conn.close()
        job = self.active_jobs.pop(schedule_id, None)
        if job:
            job.schedule_removal()
        logger.info("Schedule %s completed and removed.", schedule_id)

    def run(self) -> None:
        """Start the bot.  This method blocks until the bot is shut down."""
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO,
        )
        logger.info("Starting scheduler bot")
        self.app.run_polling()


if __name__ == "__main__":
    import os
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise RuntimeError(
            "No Telegram bot token found. Set the TELEGRAM_BOT_TOKEN environment variable."
        )
    bot = SchedulerBot(token=bot_token)
    bot.run()
