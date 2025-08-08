# 📊 Forex News & Chart Visualization Bot

**A comprehensive Telegram bot for personalized forex news, real-time notifications, and advanced chart analysis with AI-powered insights.**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-blue.svg)](https://postgresql.org)
[![Telegram](https://img.shields.io/badge/Platform-Telegram-blue.svg)](https://telegram.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🚀 **Key Features**

### 📈 **Advanced Chart Visualization**
- **Interactive Chart Generation**: Professional TradingView-style charts
- **Cross-Rate Analysis**: Compare any two currencies (EUR/USD, JPY/GBP, etc.)
- **Asymmetric Time Windows**: Flexible pre/post event analysis
  - `30m before → 3h after` - Focus on market reaction
  - `3h before → 1h after` - Analyze market setup
  - `2h before → 2h after` - Balanced analysis
- **Real-Time Data**: Yahoo Finance integration with fallback mechanisms
- **Event Impact Visualization**: Color-coded impact zones on charts
- **Robust Fallback System**: Mock data generation when APIs fail

### 📰 **Smart News Delivery**
- **Real-Time Scraping**: Economic news from ForexFactory
- **AI-Powered Analysis**: Optional ChatGPT integration
- **Personalized Filtering**: Currency and impact preferences
- **Custom Notifications**: 15/30/60 minutes before events
- **Daily Digest**: Automated delivery at your chosen time

### ⚙️ **User Management**
- **Individual Preferences**: Database-stored user settings
- **Multi-Currency Support**: 16+ major currencies
- **Impact Level Filtering**: High/Medium/Low events
- **Timezone Support**: Global timezone conversion
- **Interactive Settings**: Easy preference management

## 📊 **Chart Features Showcase**

### **Single Currency Charts**
```
📊 EUR News Event: CPI Flash Estimate y/y
2025-08-01

Time window: ±2h around event
Impact level: High (red shading)
Price change: +0.0015 (+0.14%)
```

### **Cross-Rate Charts**
```
📈 JPY/USD Cross-Rate Chart
2025-08-01

Pair: JPY/USD
Time window: 30m before → 3h after
Accurate pricing: ~0.0067 (not 1.0000)
Real market data with fallbacks
```

### **Time Window Options**
- **Pre-Event Focus**: `3h before → 1h after`
- **Post-Event Focus**: `30m before → 3h after`
- **Balanced Analysis**: `2h before → 2h after`
- **Quick Scalping**: `1h before → 30m after`

## 🎯 **Quick Start**

### **Prerequisites**
- Python 3.8+
- PostgreSQL database
- Telegram Bot Token
- Chrome browser (for scraping)

### **Installation**

```bash
# 1. Clone repository
git clone <repository-url>
cd forex_to_telegram

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env
# Edit .env with your credentials

# 4. Initialize database
python scripts/setup_with_timezone.py

# 5. Run the bot
python app.py
```

### **Environment Variables**
```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token
DATABASE_URL=postgresql://user:pass@host:port/db
API_KEY=your_secure_api_key

# Optional
CHATGPT_API_KEY=your_openai_key
ALPHA_VANTAGE_API_KEY=your_av_key
WEBHOOK_URL=your_webhook_url
```

## 📋 **Bot Commands**

### **Core Commands**
- `/start` - Welcome message and setup
- `/help` - Comprehensive help guide
- `/today` - Today's economic news
- `/tomorrow` - Tomorrow's events
- `/calendar` - Interactive date picker
- `/visualize` - **📊 Chart generation interface**
- `/settings` - Configure preferences

### **Chart Commands**
```
/visualize
├── Select Currency (EUR, USD, GBP, JPY...)
├── Choose Event (CPI, NFP, PMI...)
├── Pick Chart Type:
│   ├── 📊 Single Currency (30min, 1h, 2h, 3h)
│   └── 📈 Cross-Rate Charts:
│       ├── 30m before → 1h after
│       ├── 30m before → 2h after
│       ├── 1h before → 3h after
│       └── ...10 total options
└── Select Secondary Currency → Generate Chart
```

## ⚙️ **User Settings**

### **Currency Preferences** 🌍
**Major Currencies**: USD, EUR, GBP, JPY, AUD, CAD, CHF, NZD
**Additional**: CNY, INR, BRL, RUB, KRW, MXN, SGD, HKD

### **Impact Levels** 📊
- **🔴 High Impact** - Major market movers (NFP, FOMC, CPI)
- **🟠 Medium Impact** - Moderate events (PMI, retail sales)
- **🟡 Low Impact** - Minor announcements

### **Notification Settings** 🔔
- **Timing**: 15, 30, or 60 minutes before events
- **Impact Filter**: Choose which levels to get alerts for
- **Smart Alerts**: Contextual notifications with event details

### **Digest & Timezone** ⏰
- **Custom Time**: Any time from 00:00 to 23:59
- **Timezone Support**: Global timezone conversion
- **Personalized Content**: Based on your preferences

## 🏗️ **Project Structure**

```
forex_to_telegram/
├── 📂 bot/                     # Core application
│   ├── chart_service.py        # 📊 Chart generation & data fetching
│   ├── visualize_handler.py    # 🎨 Chart UI & user interaction
│   ├── telegram_handlers.py    # 🤖 Bot message handling
│   ├── database_service.py     # 💾 Database operations
│   ├── notification_service.py # 🔔 Real-time notifications
│   ├── scraper.py             # 🌐 News scraping & AI analysis
│   └── user_settings.py       # ⚙️ User preference management
├── 📂 tests/                   # Test suite (32 test files)
│   ├── test_chart_service.py   # Chart generation tests
│   ├── test_asymmetric_*.py    # Time window tests
│   └── test_*.py              # Comprehensive coverage
├── 📂 scripts/                 # Utility scripts (6 utilities)
│   ├── setup_database.py      # Database initialization
│   ├── bulk_import.py         # Historical data import
│   └── organize_tests.py      # Test organization
├── 📂 migrations/             # Database migrations
├── app.py                     # 🚀 Main application entry
├── requirements.txt           # 📦 Dependencies
└── README.md                  # 📖 This file
```

## 📊 **Database Schema**

### **Users Table**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    preferred_currencies TEXT DEFAULT '',
    impact_levels TEXT DEFAULT 'high,medium',
    analysis_required BOOLEAN DEFAULT TRUE,
    digest_time TIME DEFAULT '08:00:00',
    timezone VARCHAR(50) DEFAULT 'Europe/Prague',
    notifications_enabled BOOLEAN DEFAULT FALSE,
    notification_minutes INTEGER DEFAULT 30,
    notification_impact_levels TEXT DEFAULT 'high',
    chart_settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **Forex News Table**
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
    impact_level VARCHAR(20) NOT NULL,
    analysis TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes
CREATE INDEX idx_date_currency_time ON forex_news(date, currency, time);
CREATE INDEX idx_date_impact ON forex_news(date, impact_level);
CREATE INDEX idx_currency_impact ON forex_news(currency, impact_level);
```

## 🔧 **Technical Implementation**

### **Chart Service Architecture**
```python
# Multi-layered data fetching strategy
1. Yahoo Finance (Primary) → Real market data
2. Alternative symbols → Backup symbols
3. Alpha Vantage API → External fallback
4. Mock data generation → Final fallback

# Asymmetric time windows
before_hours = 0.5  # 30 minutes before event
after_hours = 3.0   # 3 hours after event
start_time = event_time - timedelta(hours=before_hours)
end_time = event_time + timedelta(hours=after_hours)
```

### **Error Handling & Reliability**
- **Retry Mechanisms**: 3 attempts with exponential backoff
- **Multiple Data Sources**: Yahoo Finance, Alpha Vantage, mock data
- **Telegram Timeout Prevention**: Immediate callback responses
- **Graceful Degradation**: Quality charts even with API failures

### **Performance Optimizations**
- **Data Caching**: Intelligent caching for repeated requests
- **Parallel Processing**: Multiple tool calls for efficiency
- **Database Indexes**: Optimized queries for large datasets
- **Connection Pooling**: Efficient database connections

## 🧪 **Testing Suite**

### **Comprehensive Coverage** (32 Test Files)
```bash
# Chart functionality
python tests/test_chart_service.py
python tests/test_asymmetric_time_windows.py
python tests/test_fallback_chart.py

# User features
python tests/test_user_features.py
python tests/test_notifications.py
python tests/test_timezone.py

# Integration tests
python tests/test_bot_commands.py
python tests/test_webhook.py
```

### **Test Organization**
```bash
python scripts/organize_tests.py
# Outputs organized list of all 32 tests
# Covers: Charts, Bot, Database, Webhooks, Timezones
```

## 🚀 **Deployment**

### **Docker Deployment**
```dockerfile
FROM python:3.8-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

### **Environment Setup**
```bash
# Production deployment
docker build -t forex-bot .
docker run -d -p 5000:5000 \
  -e TELEGRAM_BOT_TOKEN=your_token \
  -e DATABASE_URL=your_db_url \
  forex-bot
```

### **Health Monitoring**
```bash
# Health checks
curl https://your-app-url/health
curl https://your-app-url/db/stats
curl https://your-app-url/ping

# API endpoints
curl https://your-app-url/status
```

## 📈 **API Endpoints**

### **Health & Monitoring**
- `GET /ping` - Basic health check
- `GET /health` - Detailed health status
- `GET /status` - Application status with metrics
- `GET /db/stats` - Database statistics

### **Data Operations**
- `GET /db/check/<date>` - Check news for date
- `POST /db/import` - Bulk import with API key
- `POST /manual_scrape` - Trigger scraping

### **Chart Operations** (Internal)
- Chart generation via Telegram bot interface
- Real-time data fetching with fallbacks
- Asymmetric time window calculations

## 🔐 **Security & Privacy**

### **API Security**
- **API Key Authentication**: All sensitive endpoints protected
- **Environment Variables**: Secure credential storage
- **Input Validation**: Sanitized user inputs
- **Rate Limiting**: Built-in request throttling

### **Data Privacy**
- **Minimal Data Storage**: Only necessary user preferences
- **No Personal Information**: No names, emails, or sensitive data
- **Secure Database**: PostgreSQL with encrypted connections
- **Automatic Cleanup**: Configurable data retention

## 🆕 **Latest Updates (v3.0)**

### **New Chart Features** ✨
- ✅ **Asymmetric Time Windows**: 10+ flexible analysis options
- ✅ **Cross-Rate Charts**: Any currency pair combinations
- ✅ **JPY/USD Fix**: Correct pricing (~0.0067, not 1.0000)
- ✅ **Enhanced Fallbacks**: Robust data fetching with mock generation
- ✅ **Date Display**: Charts now show event dates clearly
- ✅ **Improved UI**: Better button organization and feedback

### **Technical Improvements** 🔧
- ✅ **Project Refactoring**: Tests moved to `tests/` folder
- ✅ **Enhanced .gitignore**: PNG files and comprehensive exclusions
- ✅ **32 Test Files**: Complete test coverage
- ✅ **Error Handling**: Better logging and user feedback
- ✅ **Performance**: Parallel processing and caching

### **User Experience** 🎨
- ✅ **Immediate Feedback**: No more timeout errors
- ✅ **Professional Charts**: TradingView-style visualizations
- ✅ **Flexible Analysis**: Pre/post event timing options
- ✅ **Reliable Delivery**: Charts always generate successfully

## 🛠️ **Troubleshooting**

### **Common Issues**

#### **Chart Generation Fails**
```bash
# Check data sources
2025-08-04 [INFO] Using asymmetric time window: 0.5h before, 3h after
2025-08-04 [INFO] Successfully fetched 207 data points for EURUSD=X
2025-08-04 [INFO] Successfully generated direct pair chart
```

#### **Callback Timeouts**
```bash
# Should see immediate response
2025-08-04 [INFO] Processing visualize callback: viz_multi_EUR_13_0.5_3
2025-08-04 [INFO] Handling multi-currency selection
```

#### **Database Connection**
```bash
# Test database connectivity
python -c "from bot.database_service import ForexNewsService; from bot.config import Config; db = ForexNewsService(Config().get_database_url()); print('✅ Database connected')"
```

### **Debug Commands**
```bash
# Test chart generation
python tests/test_chart_service.py

# Test asymmetric windows
python tests/test_asymmetric_time_windows.py

# Verify callback handling
python tests/test_callback_fixes.py
```

## 📚 **Development Guide**

### **Adding New Features**
```python
# 1. Add to appropriate module (bot/)
# 2. Create tests (tests/)
# 3. Update README.md
# 4. Test thoroughly
# 5. Submit PR
```

### **Code Organization**
- **`bot/`**: Core application logic
- **`tests/`**: All test files (32 total)
- **`scripts/`**: Utility scripts (6 utilities)
- **`migrations/`**: Database schema changes

### **Testing Standards**
- **Unit Tests**: Individual component testing
- **Integration Tests**: Full workflow testing
- **Mock Data**: Fallback testing without APIs
- **Error Scenarios**: Timeout and failure handling

## 🤝 **Contributing**

1. **Fork** the repository
2. **Create** feature branch: `git checkout -b feature/amazing-feature`
3. **Add tests** for new functionality
4. **Test thoroughly**: `python -m pytest tests/`
5. **Submit** pull request with detailed description

## 📄 **License**

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

## 🆘 **Support**

### **Getting Help**
1. **📖 Documentation**: Check this README first
2. **🧪 Test Suite**: Run relevant tests
3. **📋 Logs**: Check application logs for errors
4. **🐛 Issues**: Open GitHub issue with details

### **Useful Resources**
- **Test Organization**: `python scripts/organize_tests.py`
- **Health Check**: `curl https://your-app-url/health`
- **Database Stats**: `curl https://your-app-url/db/stats`

---

## 🎯 **Ready to Get Started?**

**🚀 Deploy your personalized forex news bot with professional chart analysis!**

**📊 Generate beautiful charts • 🔔 Get real-time alerts • 📰 Stay informed • 🎨 Analyze market moves**

[⭐ Star this repo](https://github.com/your-repo) | [🐛 Report issues](https://github.com/your-repo/issues) | [💡 Request features](https://github.com/your-repo/discussions)
