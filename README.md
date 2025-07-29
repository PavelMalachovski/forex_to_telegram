# Forex News Telegram Bot

A comprehensive Telegram bot that delivers personalized Forex news from ForexFactory with AI-powered analysis, daily digest scheduling, and real-time notifications.

## 🌟 Features

### Core Features
- **Real-time News Scraping**: Fetches economic news from ForexFactory
- **AI-Powered Analysis**: Optional ChatGPT integration for news analysis
- **Database Storage**: PostgreSQL backend for efficient news storage and retrieval
- **Personalized Filtering**: User-specific currency and impact preferences
- **Daily Digest**: Automated daily news delivery at custom times
- **Interactive UI**: Inline keyboards for easy navigation

### User Features (v2.0)
- **User Preferences**: Store individual user settings in database
- **Currency Filtering**: Choose specific currencies of interest
- **Impact Level Selection**: Filter by High/Medium/Low impact events
- **Custom Digest Times**: Choose any specific time for daily digest
- **Settings Management**: Interactive `/settings` command
- **Personalized News**: News filtered based on user preferences
- **News Notifications**: Real-time alerts before high-impact events

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL database
- Chrome browser (for web scraping)
- Telegram Bot Token
- ChatGPT API Key (optional)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd forex_to_telegram
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
# Create .env file or set environment variables
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
DATABASE_URL=postgresql://user:password@host:port/database
CHATGPT_API_KEY=your_chatgpt_key  # Optional
API_KEY=your_secure_api_key_here
```

4. **Set up database with timezone support**
```bash
python scripts/setup_with_timezone.py
```

5. **Run the bot**
```bash
python app.py
```

## 📋 Commands

### Basic Commands
- `/start`, `/help` - Show help message
- `/today` - Get today's news
- `/tomorrow` - Get tomorrow's news
- `/calendar` - Select a specific date

### Settings Commands
- `/settings` - Configure your preferences

## ⚙️ User Settings

### Currency Preferences
Choose which currencies you want to receive news for:
- **USD**, **EUR**, **GBP**, **JPY**, **AUD**, **CAD**, **CHF**, **NZD**
- **CNY**, **INR**, **BRL**, **RUB**, **KRW**, **MXN**, **SGD**, **HKD**

### Impact Levels
Select which impact levels interest you:
- **🔴 High Impact** - Major economic events
- **🟠 Medium Impact** - Moderate market movers
- **🟡 Low Impact** - Minor events

### AI Analysis
- **Enable/Disable** ChatGPT-powered news analysis
- Provides insights and market context for each event

### Daily Digest Time ⏰
**Custom Time Picker**
- Choose **any specific time** (00:00 to 23:59)
- **Hour picker**: Select from 0-23 hours
- **Minute picker**: Select from 0-59 minutes (5-minute intervals)
- **Quick presets**: 06:00, 08:00, 12:00, 18:00, 20:00, 22:00
- **Dynamic scheduling**: Scheduler automatically adjusts to user preferences

### Timezone Settings 🌍
**Timezone Support**
- **Default**: Europe/Prague (CET)
- **Available timezones**: Europe, America, Asia, Australia regions
- **Automatic conversion**: Notifications and digest times adjusted to your timezone
- **Popular timezones**: London, New York, Tokyo, Sydney, and more

#### How to Set Custom Time:
1. Use `/settings` command
2. Click "⏰ Digest Time"
3. Choose from:
   - **🕐 Hour** - Select specific hour (0-23)
   - **🕐 Minute** - Select specific minute (0-59, 5-min intervals)
   - **Quick presets** - Choose from common times
   - **Current time display** - Shows your current setting

### News Notifications 🔔
**Real-time News Alerts**
- **Enable/Disable** notifications for upcoming news events
- **Custom Timing**: Choose 15, 30, or 60 minutes before events
- **Impact Filtering**: Get alerts for High/Medium/Low impact events
- **Smart Scheduling**: Automatic checks every 5 minutes

#### How to Configure Notifications:
1. Use `/settings` command
2. Click "🔔 Notifications"
3. Configure:
   - **Enable/Disable** - Turn notifications on/off
   - **⏱️ Alert Timing** - Choose 15, 30, or 60 minutes before
   - **📊 Alert Impact** - Select which impact levels to notify about

#### Example Notification:
```
⚠️ In 30 minutes: high news!
14:30 | USD | Non-Farm Payrolls | 🔴 High Impact
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | Yes |
| `TELEGRAM_CHAT_ID` | Default chat ID for messages | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `API_KEY` | Secure API key for operations | Yes |
| `CHATGPT_API_KEY` | OpenAI API key for analysis | No |
| `WEBHOOK_URL` | Webhook URL for production | No |

### Database Configuration

The bot is configured to work with a PostgreSQL database. Example settings:

```
Hostname: your-db-hostname
Port: 5432
Database: your_db_name
Username: your_db_user
Password: your_db_password
Internal Database URL: postgresql://your_db_user:your_db_password@your-db-hostname/your_db_name
```

> **Never share your real database credentials. Use environment variables for all secrets.**

## 📊 Database Schema

### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    preferred_currencies TEXT DEFAULT '',
    impact_levels TEXT DEFAULT 'high,medium',
    analysis_required BOOLEAN DEFAULT TRUE,
    digest_time TIME DEFAULT '08:00:00',
    notifications_enabled BOOLEAN DEFAULT FALSE,
    notification_minutes INTEGER DEFAULT 30,
    notification_impact_levels TEXT DEFAULT 'high',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Forex News Table
```sql
CREATE TABLE forex_news (
    id SERIAL PRIMARY KEY,
    date TIMESTAMP NOT NULL,
    time VARCHAR(50) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    event TEXT NOT NULL,
    actual VARCHAR(100),
    forecast VARCHAR(100),
    previous VARCHAR(100),
    impact_level VARCHAR(20) NOT NULL, -- high, medium, low, tentative, none
    analysis TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_date_currency_time ON forex_news(date, currency, time);
CREATE INDEX idx_date_impact ON forex_news(date, impact_level);
```

## 🗄️ Database Logic

The bot implements the following database logic:

### 1. Check Database First
- When a user requests news, the bot first checks if data exists in the database
- If data exists, it retrieves and sends it to Telegram
- If no data exists, it scrapes from ForexFactory and stores the results

### 2. Data Storage
- All scraped news is automatically stored in the database
- Data is organized by date, impact (per item), and currency
- Duplicate data is prevented with smart checking

### 3. Bulk Import
- Use the bulk import script to populate historical data
- Perfect for importing data from 1.1.2025 onwards

## 📊 API Endpoints

### Health & Status
- `GET /ping` - Basic health check
- `GET /health` - Detailed health status
- `GET /status` - Application status with user count

### Database Operations
- `GET /db/stats` - Database statistics
- `GET /db/check/<date>` - Check news for specific date
- `POST /db/import` - Bulk import news data

### Manual Operations
- `POST /manual_scrape` - Trigger manual news scraping

### Example Usage
```bash
# Check database health
curl https://your-app-url/health

# Get database statistics
curl https://your-app-url/db/stats

# Check data for specific date
curl https://your-app-url/db/check/2025-01-01

# Import data via API
curl -X POST https://your-app-url/db/import \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "start_date": "2025-01-01",
    "end_date": "2025-01-31",
    "impact_level": "high"
  }'
```

## 🛠️ Setup Instructions

### Local Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export DATABASE_URL="postgresql://your_db_user:your_db_password@your-db-hostname/your_db_name"
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
export API_KEY="your_api_key"

# Run database setup
python setup_database.py
```

### Deployment

1. **Connect your GitHub repository** to your cloud provider
2. **Set environment variables** in the dashboard
3. **Deploy** using the provided Dockerfile
4. **Monitor logs** for database connection status

### Database Setup Options

#### Option 1: Basic Setup (without notifications)
```bash
python scripts/setup_database.py
```

#### Option 2: Complete Setup (with notifications)
```bash
python scripts/setup_with_timezone.py
```

#### Option 3: Add notifications to existing database
```bash
python scripts/setup_with_timezone.py
```

### Bulk Data Import

To import historical data from 1.1.2025:

```bash
# Import data for January 2025
python scripts/bulk_import.py --start-date 2025-01-01 --end-date 2025-01-31 --impact-level high

# Import all impact levels for a date range
python scripts/bulk_import.py --start-date 2025-01-01 --end-date 2025-01-31 --impact-level all

# Dry run to see what would be imported
python scripts/bulk_import.py --start-date 2025-01-01 --end-date 2025-01-31 --impact-level high --dry-run
```

## 🔔 Notification Feature

### Overview

The notification feature allows users to receive real-time alerts before high-impact news events. Users can configure when they want to be notified (15, 30, or 60 minutes before events) and which impact levels they want to be alerted about.

### Features

- **Enable/Disable**: Users can turn notifications on or off
- **Timing Options**: 15, 30, or 60 minutes before events
- **Impact Filtering**: Choose High, Medium, or Low impact events
- **Smart Scheduling**: Automatic checks every 5 minutes

### Deployment Steps

#### Step 1: Deploy the Code
Deploy the updated code to your environment. The bot will start normally, but notifications will be disabled.

#### Step 2: Add Notification Columns
For existing databases, run the setup script:

```bash
python scripts/setup_with_timezone.py
```

This will add the following columns to the `users` table:
- `notifications_enabled` (BOOLEAN, default: FALSE)
- `notification_minutes` (INTEGER, default: 30)
- `notification_impact_levels` (TEXT, default: 'high')

#### Step 3: Verify Migration
After running the script, the notification feature will be automatically enabled. Users can then:

1. Use `/settings` command
2. Click "🔔 Notifications"
3. Configure their notification preferences

### Backward Compatibility

The implementation is designed to be backward compatible:

- **Before Migration**: Notification settings won't appear in `/settings`
- **After Migration**: Full notification functionality will be available

### Testing the Feature

#### Before Migration
- `/settings` will show only currency, impact, analysis, and digest time settings
- No notification-related errors will occur

#### After Migration
- `/settings` will include "🔔 Notifications" option
- Users can configure notification timing and impact levels
- Notifications will be sent automatically

## 🧪 Testing

### Offline Tests
```bash
# Test user features without database
python tests/test_user_features_offline.py

# Test message formatting
python tests/test_bot_message.py

# Test custom time picker
python tests/test_custom_time_picker.py
```

### Online Tests
```bash
# Test with live database
python tests/test_user_features.py
```

### Notification Tests
```bash
# Test notification functionality
python test_notifications.py

# Set up notification feature
python setup_notifications.py
```

## 🚀 Deployment

### Docker Deployment
```bash
# Build and run with Docker
docker build -t forex-bot .
docker run -p 5000:5000 forex-bot
```

### Manual Deployment
```bash
# Install dependencies
pip install -r requirements.txt

# Set up database
python setup_database.py

# Run the application
python app.py
```

## 🔄 Daily Digest System

### How It Works
1. **Dynamic Scheduling**: Creates jobs for each unique user digest time
2. **Personalized Content**: Filters news based on user preferences
3. **Automatic Delivery**: Sends digest at user's chosen time
4. **Smart Filtering**: Only shows news matching user's currency and impact preferences

### Digest Features
- **Custom Times**: Any time from 00:00 to 23:59
- **Personalized Content**: Based on user preferences
- **No Duplicates**: Efficient database storage
- **Error Handling**: Graceful failure handling
- **User Feedback**: Clear messages when no news available

## 🛠️ Troubleshooting

### Common Issues

#### Database Connection Failed
- Check if DATABASE_URL is set correctly
- Verify database credentials
- Ensure database is accessible from your deployment

#### Migration Errors
- Run `python setup_database.py` to create tables
- Check logs for specific error messages

#### Import Failures
- Verify API key is correct
- Check date format (YYYY-MM-DD)
- Monitor logs for scraping errors

#### Notifications Not Sending
1. Check if notifications are enabled for user
2. Verify notification timing settings
3. Check scheduler logs for errors
4. Ensure database connection is working

#### Database Migration Issues
1. Verify database connection string
2. Check table permissions
3. Run migration script manually
4. Verify column existence

### Debug Commands
```bash
# Test notification service
python test_notifications.py

# Check database schema
python -c "from bot.models import DatabaseManager; db = DatabaseManager(); print('Tables:', db.engine.table_names())"

# Verify user preferences
python -c "from bot.database_service import ForexNewsService; from bot.config import Config; db = ForexNewsService(Config().get_database_url()); user = db.get_or_create_user(YOUR_USER_ID); print('Notifications:', user.notifications_enabled)"

# Check application health
curl https://your-app-url/health

# Check database specifically
curl https://your-app-url/db/stats
```

### Health Checks
```bash
# Check application health
curl https://your-app-url/health

# Check database specifically
curl https://your-app-url/db/stats
```

## 🛡️ Security

### API Key Protection
- All database operations require API key authentication
- Environment variables for sensitive data
- Secure database connection strings

### Data Privacy
- No personal data stored
- Only forex news data in database
- Automatic data retention policies

## 📈 Version 2.0 Changes

### New Features
- ✅ **User Database**: Individual user preferences storage
- ✅ **Currency Filtering**: Choose specific currencies
- ✅ **Impact Selection**: Filter by High/Medium/Low impact
- ✅ **Custom Digest Times**: Choose any specific time
- ✅ **Settings Management**: Interactive `/settings` command
- ✅ **Personalized News**: News filtered by user preferences
- ✅ **Dynamic Scheduling**: Automatic job management
- ✅ **Enhanced UI**: Better user experience
- ✅ **News Notifications**: Real-time alerts before high-impact events

### Technical Improvements
- **Database Integration**: User preferences stored in PostgreSQL
- **Modular Design**: Separate modules for different features
- **Error Handling**: Robust error handling and logging
- **Testing Suite**: Comprehensive test coverage
- **Documentation**: Updated README and inline docs

## 🚀 Performance Optimization

### Database Indexes
- Composite indexes for efficient date/currency/time queries
- Separate index for date/impact level filtering
- Automatic cleanup of old data (configurable)

### Caching Strategy
- Database-first approach reduces scraping load
- Smart duplicate detection prevents redundant scraping
- Rate limiting built into bulk import

## 📚 Next Steps

1. **Deploy with the updated environment variables**
2. **Run the bulk import** for historical data from 1.1.2025
3. **Test the API endpoints** to verify functionality
4. **Monitor the application** for any issues
5. **Scale as needed** based on usage patterns

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the documentation
2. Run the test suites
3. Check the logs for error messages
4. Open an issue with detailed information

---

**🎯 Ready to get personalized Forex news delivered to your Telegram at your preferred time with real-time notifications!**
