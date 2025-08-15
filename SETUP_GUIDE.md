# 🤖 Telegram Scheduler Bot - Complete Setup Guide

This guide will walk you through setting up your own Telegram bot that can send scheduled messages and countdowns in group chats.

## 📋 Prerequisites

- Python 3.8 or higher
- A Telegram account
- Basic command line knowledge

## 🚀 Step-by-Step Setup

### Step 1: Create Your Telegram Bot

1. **Open Telegram** and search for `@BotFather`
2. **Start a chat** with BotFather and send `/start`
3. **Create a new bot** by sending `/newbot`
4. **Choose a name** for your bot (e.g., "My Scheduler Bot")
5. **Choose a username** for your bot (must end with 'bot', e.g., "myscheduler_bot")
6. **Save the bot token** - BotFather will give you a token like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

### Step 2: Download and Setup the Bot Code

1. **Download the bot files** to your computer
2. **Open a terminal/command prompt** and navigate to the bot folder:
   ```bash
   cd telegram_scheduler_bot
   ```

### Step 3: Install Dependencies

```bash
# Install required Python packages
pip install -r requirements.txt
```

### Step 4: Configure Your Bot

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit the .env file** with your favorite text editor and add your bot token:
   ```
   BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   DATABASE_PATH=bot_data.db
   DEFAULT_TIMEZONE=UTC
   LOG_LEVEL=INFO
   ```

### Step 5: Test Your Bot

```bash
# Run the test script to make sure everything works
python test_bot.py
```

You should see all tests pass with green checkmarks ✅

### Step 6: Start Your Bot

```bash
# Start the bot
python bot.py
```

You should see:
```
INFO - Starting Telegram Scheduler Bot...
INFO - Message scheduler started
INFO - Bot is running! Press Ctrl+C to stop.
```

## 📱 Using Your Bot

### Adding Bot to Groups

1. **Add your bot** to a Telegram group
2. **Make sure the bot has permission** to send messages
3. **Send `/start`** in the group to activate the bot

### Available Commands

#### For Group Admins:

- **`/setschedule HH:MM message`** - Set daily message
  ```
  /setschedule 09:00 Good morning team! Today is {day}, {date} 🌅
  ```

- **`/setcountdown HH:MM YYYY-MM-DD title`** - Set countdown
  ```
  /setcountdown 10:00 2024-12-31 New Year Celebration
  ```

- **`/status`** - View all scheduled messages
- **`/removeschedule ID`** - Remove a schedule by ID
- **`/settimezone TIMEZONE`** - Set group timezone
  ```
  /settimezone America/New_York
  ```

#### For Everyone:

- **`/help`** - Show help message
- **`/status`** - View current schedules

### Message Templates

You can use these placeholders in daily messages:

- `{date}` - Current date (2024-08-14)
- `{time}` - Current time (09:00)
- `{day}` - Day of week (Monday)
- `{month}` - Month name (August)
- `{year}` - Current year (2024)

**Example:**
```
/setschedule 08:00 📅 Good morning! Today is {day}, {date}. Have a productive day! 💪
```

## 🌍 Timezone Support

The bot supports all standard timezones. Common examples:

- `UTC` - Coordinated Universal Time
- `America/New_York` - Eastern Time
- `America/Los_Angeles` - Pacific Time
- `Europe/London` - British Time
- `Europe/Paris` - Central European Time
- `Asia/Tokyo` - Japan Time
- `Asia/Kolkata` - India Time
- `Australia/Sydney` - Australian Eastern Time

## 🔧 Advanced Configuration

### Running as a Service (Linux)

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/telegram-scheduler.service
```

Add this content (adjust paths as needed):

```ini
[Unit]
Description=Telegram Scheduler Bot
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/telegram_scheduler_bot
ExecStart=/usr/bin/python3 /path/to/telegram_scheduler_bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable telegram-scheduler.service
sudo systemctl start telegram-scheduler.service
sudo systemctl status telegram-scheduler.service
```

### Running with Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
```

Build and run:

```bash
docker build -t telegram-scheduler-bot .
docker run -d --name scheduler-bot -v $(pwd)/.env:/app/.env telegram-scheduler-bot
```

## 🐛 Troubleshooting

### Common Issues

1. **"BOT_TOKEN not found"**
   - Make sure you created the `.env` file
   - Check that your bot token is correct

2. **"Module not found"**
   - Run `pip install -r requirements.txt` again
   - Make sure you're in the right directory

3. **Bot doesn't respond in groups**
   - Make sure the bot is added to the group
   - Check that the bot has permission to send messages
   - Try `/start` command in the group

4. **Scheduled messages not sending**
   - Check the timezone settings
   - Verify the time format (24-hour: HH:MM)
   - Make sure the bot is running continuously

### Checking Logs

The bot logs important information. Check the console output for error messages.

To enable debug logging, change in `.env`:
```
LOG_LEVEL=DEBUG
```

## 📊 Database

The bot uses SQLite database (`bot_data.db`) to store:
- Group configurations
- Scheduled messages
- Admin permissions
- Timezone settings

**Backup your database regularly** if you have important scheduled messages!

## 🔒 Security Notes

- Keep your bot token secret
- Only group admins can configure schedules
- The bot only works in groups where it's explicitly added
- Database is stored locally and not shared

## 🆘 Support

If you encounter issues:

1. Check this guide again
2. Run the test script: `python test_bot.py`
3. Check the console logs for error messages
4. Make sure all dependencies are installed
5. Verify your bot token is correct

## 🎉 You're All Set!

Your Telegram Scheduler Bot is now ready to send automated messages and countdowns to your groups. Enjoy your automated messaging system!

---

**Happy Scheduling! 🤖✨**