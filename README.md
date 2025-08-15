# Telegram Scheduler Bot

A powerful, feature-rich Telegram bot that can be added to groups to send scheduled messages like daily countdowns, reminders, and announcements with full timezone support.

## ✨ Features

- 📅 **Daily Scheduled Messages** - Send recurring messages at specific times
- ⏰ **Countdown Functionality** - Automatic countdowns to important dates
- 👥 **Group Chat Support** - Works seamlessly in Telegram groups
- 🌍 **Full Timezone Support** - Accurate scheduling across all timezones
- 🎨 **Customizable Message Templates** - Dynamic placeholders for dates, times, etc.
- 📊 **SQLite Database Storage** - Persistent configuration storage
- 🔒 **Admin-Only Controls** - Only group admins can configure schedules
- 🐳 **Docker Support** - Easy deployment with Docker/Docker Compose
- 🧪 **Comprehensive Testing** - Built-in test suite for reliability
- 📝 **Rich Logging** - Detailed logging for monitoring and debugging

## 🚀 Quick Start

### 1. Create Your Bot
1. Message `@BotFather` on Telegram
2. Send `/newbot` and follow the prompts
3. Save your bot token

### 2. Setup and Run
```bash
# Clone/download the bot files
cd telegram_scheduler_bot

# Install dependencies
pip install -r requirements.txt

# Configure your bot
cp .env.example .env
# Edit .env and add your BOT_TOKEN

# Test the bot
python test_bot.py

# Start the bot
python bot.py
```

### 3. Add to Groups
1. Add your bot to a Telegram group
2. Send `/start` in the group
3. Use `/help` to see available commands

## 📱 Commands

### For Group Admins:

- **`/setschedule HH:MM message`** - Set daily scheduled message
  ```
  /setschedule 09:00 Good morning team! Today is {day}, {date} 🌅
  ```

- **`/setcountdown HH:MM YYYY-MM-DD title`** - Set countdown to specific date
  ```
  /setcountdown 10:00 2024-12-31 New Year Celebration
  ```

- **`/status`** - View all scheduled messages for the group
- **`/removeschedule ID`** - Remove a scheduled message by ID
- **`/settimezone TIMEZONE`** - Set group timezone
  ```
  /settimezone America/New_York
  ```

### For Everyone:

- **`/help`** - Show detailed help message
- **`/status`** - View current schedules

## 🎨 Message Templates

Use these dynamic placeholders in your daily messages:

- `{date}` - Current date (2024-08-14)
- `{time}` - Current time (09:00)
- `{day}` - Day of week (Thursday)
- `{month}` - Month name (August)
- `{year}` - Current year (2024)

**Example:**
```
/setschedule 08:00 📅 Good morning! Today is {day}, {date}. Have a productive day! 💪
```

## 🌍 Timezone Support

The bot supports all standard timezones:

- `UTC` - Coordinated Universal Time
- `America/New_York` - Eastern Time
- `America/Los_Angeles` - Pacific Time
- `Europe/London` - British Time
- `Europe/Paris` - Central European Time
- `Asia/Tokyo` - Japan Time
- `Asia/Kolkata` - India Time
- `Australia/Sydney` - Australian Eastern Time

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)
```bash
# Create .env file with your bot token
cp .env.example .env

# Start the bot
docker-compose up -d

# View logs
docker-compose logs -f
```

### Using Docker
```bash
# Build the image
docker build -t telegram-scheduler-bot .

# Run the container
docker run -d --name scheduler-bot \
  -v $(pwd)/.env:/app/.env \
  -v $(pwd)/bot_data.db:/app/data/bot_data.db \
  telegram-scheduler-bot
```

## 🔧 Advanced Setup

### Running as a System Service (Linux)

1. Create service file:
```bash
sudo nano /etc/systemd/system/telegram-scheduler.service
```

2. Add configuration:
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

3. Enable and start:
```bash
sudo systemctl enable telegram-scheduler.service
sudo systemctl start telegram-scheduler.service
```

## 📁 Project Structure

```
telegram_scheduler_bot/
├── bot.py              # Main bot application
├── database.py         # Database operations
├── scheduler.py        # Message scheduling logic
├── test_bot.py         # Test suite
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template
├── Dockerfile          # Docker configuration
├── docker-compose.yml  # Docker Compose setup
├── README.md           # This file
└── SETUP_GUIDE.md      # Detailed setup instructions
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_bot.py
```

This tests:
- Database functionality
- Message scheduling
- Timezone handling
- Template formatting
- Error handling

## 🐛 Troubleshooting

### Common Issues:

1. **Bot doesn't respond**
   - Check bot token in `.env`
   - Ensure bot is added to group
   - Verify bot has message permissions

2. **Scheduled messages not sending**
   - Check timezone configuration
   - Verify time format (24-hour HH:MM)
   - Ensure bot is running continuously

3. **Permission errors**
   - Only group admins can configure schedules
   - Check admin status with `/status`

### Debug Mode:
Set `LOG_LEVEL=DEBUG` in `.env` for detailed logging.

## 📊 Database

The bot uses SQLite to store:
- Group configurations and timezones
- Scheduled message templates and times
- Admin permissions
- Countdown targets and titles

**Important:** Backup `bot_data.db` regularly!

## 🔒 Security

- Bot token is kept secure in environment variables
- Only group admins can configure schedules
- Database is stored locally
- No external data transmission except to Telegram API

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests: `python test_bot.py`
4. Submit a pull request

## 📄 License

This project is open source. Feel free to use, modify, and distribute.

## 🆘 Support

For detailed setup instructions, see [SETUP_GUIDE.md](SETUP_GUIDE.md)

For issues:
1. Check the setup guide
2. Run the test suite
3. Check logs for error messages
4. Verify configuration

---

**Happy Scheduling! 🤖✨**

Made with ❤️ for the Telegram community