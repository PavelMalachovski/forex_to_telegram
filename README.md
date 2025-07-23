# Forex Factory to Telegram Bot

An advanced Telegram bot that scrapes the Forex Factory economic calendar and sends news updates to Telegram channels with intelligent time handling, sorting, and impact filtering.

## 🚀 Latest Features

- **Enhanced Time Management**: All news items have proper times with fallback to previous available times
- **Smart Sorting**: News sorted by currency alphabetically, then chronologically by time
- **Advanced Anti-Bot Bypass**: Multiple strategies to bypass Cloudflare and other anti-bot protections
- **Multi-Strategy Scraping**: Includes undetected-chromedriver with human-like behavior
- **Intelligent Fallbacks**: Automatic fallback to alternative methods if primary fails
- **ChatGPT Integration**: Optional AI-powered analysis of news events
- **Flexible Scheduling**: Configurable news fetching intervals
- **Impact Level Filtering**: All news is scraped and stored; filtering is done at output (Telegram or API)
- **Telegram Integration**: Clean, formatted messages sent to Telegram channels
- **Robust Error Handling**: Comprehensive timeout mechanisms and graceful degradation

## ✨ Major Improvements

- **All news is scraped and stored for each date, regardless of impact.**
- **Impact is now robustly detected and stored per news item (high, medium, low, tentative, none).**
- **Filtering by impact is done only at output (Telegram, API, etc).**
- **Database logic and API endpoints updated for new impact handling.**

## 🛠️ Installation

### Prerequisites
- Python 3.11+
- Google Chrome (for undetected-chromedriver)
- Telegram Bot Token
- Optional: OpenAI API Key for ChatGPT analysis

### Quick Start

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/forex_to_telegram.git
cd forex_to_telegram
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Install Playwright browsers** (optional, for enhanced scraping):
```bash
playwright install chromium
```

4. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## ⚙️ Configuration

Create a `.env` file with the following variables:

```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
DATABASE_URL=postgresql://username:password@hostname:5432/database_name
API_KEY=your_api_key_here

# Optional
CHATGPT_API_KEY=your_openai_api_key_here  # For AI analysis
TIMEZONE=Europe/Prague  # Your preferred timezone
```

> **Never commit your real credentials or secrets to version control.**

### Environment Variables Explained

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Your Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Yes | Target chat/channel ID for news messages |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `API_KEY` | Yes | API key for protected endpoints |
| `CHATGPT_API_KEY` | No | OpenAI API key for AI-powered news analysis |
| `TIMEZONE` | No | Timezone for date handling (default: Europe/Prague) |

## 🚀 Usage

### Running the Bot

```bash
python app.py
```

### Manual News Fetching (Python)

```python
from bot.scraper import ForexNewsScraper, ChatGPTAnalyzer
from bot.config import Config
from datetime import datetime

config = Config()
analyzer = ChatGPTAnalyzer(config.chatgpt_api_key)
scraper = ForexNewsScraper(config, analyzer)

# Fetch news for today (all impacts)
news = await scraper.scrape_news()

# Fetch news for a specific date (all impacts)
target_date = datetime(2025, 7, 17)
news = await scraper.scrape_news(target_date)
```

### Impact Levels

- All news is scraped and stored for each date.
- Impact is detected per item: `high`, `medium`, `low`, `tentative`, `none`.
- Filtering by impact is done at output (Telegram, API, etc).

## 🌐 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/webhook` | POST | Telegram webhook endpoint |
| `/db/stats` | GET | Database statistics |
| `/db/check/<date>` | GET | Check if data exists for a date |
| `/db/import` | POST | Bulk import data (requires API key) |

## 🐳 Deployment

### Docker Deployment

```bash
# Build the Docker image
docker build -t forex-telegram-bot .

# Run with environment variables
docker run -d \
  --env-file .env \
  -p 10000:10000 \
  forex-telegram-bot
```

### Render.com Deployment

1. **Connect your GitHub repository**
2. **Set environment variables** in Render dashboard
3. **Deploy using the provided `Dockerfile`**

## 🧑‍💻 Technical Details

- **All news is scraped and stored for each date.**
- **Impact is detected and stored per item.**
- **Filtering by impact is done at output.**
- **Database schema includes per-item impact.**
- **Bulk import script supports historical data import.**

## 🛡️ Security

- All sensitive data is managed via environment variables.
- Never commit real credentials to version control.
- API endpoints requiring modification use API key authentication.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This bot is for educational and personal use only. Please respect ForexFactory's terms of service and implement appropriate rate limiting. The authors are not responsible for any misuse of this software.

---

**Made with ❤️ for the Forex trading community**
