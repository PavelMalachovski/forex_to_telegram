# Forex News Telegram Bot

A comprehensive Telegram bot that delivers personalized Forex news from ForexFactory with AI-powered analysis and daily digest scheduling.

## 🌟 Features

### Core Features
- **Real-time News Scraping**: Fetches economic news from ForexFactory
- **AI-Powered Analysis**: Optional ChatGPT integration for news analysis
- **Database Storage**: PostgreSQL backend for efficient news storage and retrieval
- **Personalized Filtering**: User-specific currency and impact preferences
- **Daily Digest**: Automated daily news delivery at custom times
- **Interactive UI**: Inline keyboards for easy navigation

### New User Features (v2.0)
- **User Preferences**: Store individual user settings in database
- **Currency Filtering**: Choose specific currencies of interest
- **Impact Level Selection**: Filter by High/Medium/Low impact events
- **Custom Digest Times**: Choose any specific time for daily digest
- **Settings Management**: Interactive `/settings` command
- **Personalized News**: News filtered based on user preferences

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
```

4. **Set up database**
```bash
python setup_database.py
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
**NEW: Custom Time Picker**
- Choose **any specific time** (00:00 to 23:59)
- **Hour picker**: Select from 0-23 hours
- **Minute picker**: Select from 0-59 minutes (5-minute intervals)
- **Quick presets**: 06:00, 08:00, 12:00, 18:00, 20:00, 22:00
- **Dynamic scheduling**: Scheduler automatically adjusts to user preferences

#### How to Set Custom Time:
1. Use `/settings` command
2. Click "⏰ Digest Time"
3. Choose from:
   - **🕐 Hour** - Select specific hour (0-23)
   - **🕐 Minute** - Select specific minute (0-59, 5-min intervals)
   - **Quick presets** - Choose from common times
   - **Current time display** - Shows your current setting

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | Yes |
| `TELEGRAM_CHAT_ID` | Default chat ID for messages | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `CHATGPT_API_KEY` | OpenAI API key for analysis | No |
| `WEBHOOK_URL` | Webhook URL for production | No |

### Database Schema

#### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    preferred_currencies TEXT DEFAULT '',
    impact_levels TEXT DEFAULT 'high,medium',
    analysis_required BOOLEAN DEFAULT TRUE,
    digest_time TIME DEFAULT '08:00:00',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Forex News Table
```sql
CREATE TABLE forex_news (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    time VARCHAR(10),
    currency VARCHAR(10),
    event TEXT,
    actual VARCHAR(50),
    forecast VARCHAR(50),
    previous VARCHAR(50),
    impact VARCHAR(10),
    analysis TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

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

## 🧪 Testing

### Offline Tests
```bash
# Test user features without database
python test_user_features_offline.py

# Test message formatting
python test_bot_message.py

# Test custom time picker
python test_custom_time_picker.py
```

### Online Tests
```bash
# Test with live database
python test_user_features.py
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

### Technical Improvements
- **Database Integration**: User preferences stored in PostgreSQL
- **Modular Design**: Separate modules for different features
- **Error Handling**: Robust error handling and logging
- **Testing Suite**: Comprehensive test coverage
- **Documentation**: Updated README and inline docs

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

**🎯 Ready to get personalized Forex news delivered to your Telegram at your preferred time!**
