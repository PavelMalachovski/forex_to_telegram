# Forex Factory to Telegram Bot

An advanced Telegram bot that scrapes Forex Factory economic calendar and sends high-impact news updates to Telegram channels with intelligent time handling and sorting.

## 🚀 Latest Features

- **Enhanced Time Management**: All news items now have proper times with intelligent fallback to previous available times
- **Smart Sorting**: News sorted by currency alphabetically, then chronologically by time
- **Advanced Anti-Bot Bypass**: Multiple strategies to bypass Cloudflare and other anti-bot protections
- **Multi-Strategy Scraping**:
  - Advanced curl-based scraping with browser simulation
  - Enhanced HTTP requests with session management
  - Playwright with comprehensive stealth and Turnstile bypass
  - Undetected-chromedriver with human-like behavior
- **Intelligent Fallbacks**: Automatic fallback to alternative methods if primary fails
- **ChatGPT Integration**: Optional AI-powered analysis of news events
- **Flexible Scheduling**: Configurable news fetching intervals
- **Impact Level Filtering**: Filter news by impact level (high, medium, low, all)
- **Telegram Integration**: Clean, formatted messages sent to Telegram channels
- **Robust Error Handling**: Comprehensive timeout mechanisms and graceful degradation

## ✨ Recent Major Improvements

### Enhanced Time Handling & Sorting (Latest)
- **Complete Time Assignment**: All news items now have valid times - no more "N/A" times
- **Intelligent Time Fallback**: Missing times automatically use the previous available time
- **Smart Sorting**: News sorted by currency first, then by time within each currency
- **Robust Time Parsing**: Handles various time formats (12-hour, 24-hour, AM/PM)
- **Clean Output**: Better organized messages with clear currency sections

### Advanced Anti-Bot Detection Bypass

The scraper now implements sophisticated techniques to bypass ForexFactory's Cloudflare protection:

1. **Multiple Curl Strategies**:
   - Browser simulation with full headers
   - Mobile browser emulation
   - Minimal headers approach

2. **Enhanced Playwright Integration**:
   - Comprehensive stealth mode with fingerprint masking
   - Automatic Cloudflare Turnstile detection and bypass
   - Human-like behavior simulation
   - Advanced WebDriver detection removal

3. **Undetected-Chromedriver Support**:
   - Human-like mouse movements and scrolling
   - Random delays and behavior patterns
   - Advanced browser fingerprint masking
   - Automatic Cloudflare challenge handling

4. **Session Management**:
   - Intelligent session establishment
   - Cookie management and persistence
   - Rate limiting and delay mechanisms

5. **Robust Error Handling**:
   - Timeout mechanisms to prevent hanging
   - Detailed logging and debugging
   - Automatic retry with different strategies

### Fixed Telegram MarkdownV2 Escaping
- **Corrected double escaping issue** in `escape_markdown_v2()` function
- **Proper character escaping order** (backslash first to prevent double escaping)
- **Comprehensive error handling** with fallback to plain text
- **Validation functions** for MarkdownV2 format
- **Safe fallback mechanisms** for problematic text

## 🛠️ Installation

### Prerequisites
- Python 3.11+
- Google Chrome (for undetected-chromedriver)
- Telegram Bot Token
- Optional: OpenAI API Key for ChatGPT analysis

### Quick Start

1. **Clone the repository**:
```bash
git clone https://github.com/PavelMalachovski/forex_to_telegram.git
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

# Optional
CHATGPT_API_KEY=your_openai_api_key_here  # For AI analysis
TIMEZONE=Europe/Prague  # Your preferred timezone
```

### Environment Variables Explained

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Your Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Yes | Target chat/channel ID for news messages |
| `CHATGPT_API_KEY` | No | OpenAI API key for AI-powered news analysis |
| `TIMEZONE` | No | Timezone for date handling (default: Europe/Prague) |

## 🚀 Usage

### Running the Bot

```bash
python app.py
```

### Manual News Fetching

```python
from bot.scraper import ForexNewsScraper, ChatGPTAnalyzer
from bot.config import Config
from datetime import datetime

config = Config()
analyzer = ChatGPTAnalyzer(config.chatgpt_api_key)
scraper = ForexNewsScraper(config, analyzer)

# Fetch news for today (high impact)
news = await scraper.scrape_news(impact_level="high")

# Fetch news for specific date
target_date = datetime(2025, 7, 17)
news = await scraper.scrape_news(target_date, impact_level="high")

# Fetch all impact levels
news = await scraper.scrape_news(impact_level="all")
```

### Impact Levels

- `"high"`: Only high-impact (red) news events
- `"medium"`: High and medium-impact events
- `"low"`: Only low-impact (yellow) events
- `"all"`: All impact levels

## 🌐 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/webhook` | POST | Telegram webhook endpoint |
| `/fetch-news` | GET | Manual news fetch trigger |
| `/fetch-news/<date>` | GET | Fetch news for specific date (YYYY-MM-DD) |

## 🐳 Deployment

### Docker Deployment

The project includes a comprehensive Dockerfile with Google Chrome support:

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

The bot is optimized for Render.com deployment:

1. **Connect your GitHub repository**
2. **Set environment variables** in Render dashboard
3. **Deploy using the provided `Dockerfile`**

#### Render.com Configuration

```yaml
services:
  - type: web
    name: forex-scraper
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1 --threads 2
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
```

### Other Platforms

The bot can be deployed on any platform that supports Python 3.11+ and Docker:

- **Heroku**: Use the provided `Procfile`
- **Railway**: Direct deployment from GitHub
- **DigitalOcean App Platform**: Docker deployment
- **AWS ECS**: Container deployment
- **Google Cloud Run**: Serverless container deployment

## 🔧 Technical Details

### Enhanced Time Handling

The scraper now ensures all news items have proper times:

```python
# Before: Some items had "N/A" times
# After: All items have valid times with intelligent fallback
```

**Features:**
- Automatic time assignment for missing times
- Fallback to previous available time
- Default time (09:00) if no times available
- Robust time parsing for various formats

### Smart Sorting Algorithm

News is sorted by:
1. **Currency** (alphabetically)
2. **Time** (chronologically within each currency)

```python
# Sort key: (currency, time_minutes)
# Example: ("EUR", 540) for 09:00, ("USD", 630) for 10:30
```

### Anti-Bot Bypass Strategies

1. **Curl-based Scraping**:
   - Uses system curl with various header configurations
   - Simulates different browser types and mobile devices
   - Handles compressed responses and redirects

2. **HTTP Session Management**:
   - Establishes sessions with main site before accessing calendar
   - Manages cookies and maintains session state
   - Implements realistic delays between requests

3. **Playwright Stealth Mode**:
   - Removes WebDriver detection signatures
   - Masks automation indicators
   - Simulates human-like mouse movements and interactions
   - Handles Cloudflare Turnstile challenges automatically

4. **Undetected-Chromedriver**:
   - Human-like behavior simulation
   - Random delays and mouse movements
   - Advanced browser fingerprint masking
   - Automatic Cloudflare challenge handling

### Error Handling

- **Comprehensive timeout mechanisms**
- **Automatic fallback between strategies**
- **Detailed logging for debugging**
- **Graceful degradation when services are unavailable**
- **Exponential backoff for retry attempts**

### Message Formatting

The bot sends well-formatted messages with:
- **Currency grouping** with clear headers
- **Time-based sorting** within each currency
- **Comprehensive news details** (actual, forecast, previous)
- **AI analysis** (if ChatGPT API is configured)
- **Proper MarkdownV2 escaping** with fallback to HTML/plain text

## 📊 Monitoring and Debugging

### Key Log Messages

| Message | Meaning |
|---------|---------|
| `"Successfully loaded content"` | Page loaded successfully |
| `"Bot blocking detected"` | Anti-bot measures triggered |
| `"MarkdownV2 validation failed"` | Formatting issues detected |
| `"Successfully sent after fixing"` | Recovery successful |

### Common Issues and Solutions

#### Issue: Still getting selector timeouts
**Solution**: The improved version tries multiple selectors and has longer timeouts. Check logs for which selectors are being attempted.

#### Issue: MarkdownV2 errors persist
**Solution**: The new version has comprehensive fallback to plain text. Check the `validate_markdown_v2` function output in logs.

#### Issue: Rate limiting or blocking
**Solution**: The improved version has randomized delays and better stealth. Consider increasing the base delay in `ForexNewsScraper.base_delay`.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This bot is for educational and personal use only. Please respect ForexFactory's terms of service and implement appropriate rate limiting. The authors are not responsible for any misuse of this software.

## 🆘 Support

If you encounter issues or have questions:

1. **Check the logs** for specific error messages
2. **Look for improved logging output** to identify the failure point
3. **Test locally first** using the same environment variables
4. **Open an issue** on GitHub with detailed information

### Getting Help

- **GitHub Issues**: For bug reports and feature requests
- **Documentation**: Check the code comments and docstrings
- **Community**: Join our discussions in GitHub Discussions

---

**Made with ❤️ for the Forex trading community**
