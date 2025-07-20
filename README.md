# Forex Factory to Telegram Bot

An advanced Telegram bot that scrapes Forex Factory economic calendar and sends high-impact news updates to Telegram channels.

## Features

- **Advanced Anti-Bot Bypass**: Multiple strategies to bypass Cloudflare and other anti-bot protections
- **Multi-Strategy Scraping**: 
  - Advanced curl-based scraping with browser simulation
  - Enhanced HTTP requests with session management
  - Playwright with comprehensive stealth and Turnstile bypass
- **Intelligent Fallbacks**: Automatic fallback to alternative methods if primary fails
- **ChatGPT Integration**: Optional AI-powered analysis of news events
- **Flexible Scheduling**: Configurable news fetching intervals
- **Impact Level Filtering**: Filter news by impact level (high, medium, low, all)
- **Telegram Integration**: Clean, formatted messages sent to Telegram channels

## Recent Improvements

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

3. **Session Management**:
   - Intelligent session establishment
   - Cookie management and persistence
   - Rate limiting and delay mechanisms

4. **Robust Error Handling**:
   - Timeout mechanisms to prevent hanging
   - Detailed logging and debugging
   - Automatic retry with different strategies

## Installation

1. Clone the repository:
```bash
git clone https://github.com/PavelMalachovski/forex_to_telegram.git
cd forex_to_telegram
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
playwright install chromium
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

Create a `.env` file with the following variables:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
CHATGPT_API_KEY=your_openai_api_key_here  # Optional
TIMEZONE=Europe/Prague
```

## Usage

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

# Fetch news for today
news = await scraper.scrape_news(impact_level="high")

# Fetch news for specific date
target_date = datetime(2025, 7, 17)
news = await scraper.scrape_news(target_date, impact_level="high")
```

## API Endpoints

- `GET /` - Health check
- `POST /webhook` - Telegram webhook endpoint
- `GET /fetch-news` - Manual news fetch trigger
- `GET /fetch-news/<date>` - Fetch news for specific date (YYYY-MM-DD)

## Deployment

### Render.com

The bot is configured for easy deployment on Render.com:

1. Connect your GitHub repository
2. Set environment variables in Render dashboard
3. Deploy using the provided `Dockerfile`

### Docker

```bash
docker build -t forex-telegram-bot .
docker run -d --env-file .env forex-telegram-bot
```

## Technical Details

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

### Error Handling

- Comprehensive timeout mechanisms
- Automatic fallback between strategies
- Detailed logging for debugging
- Graceful degradation when services are unavailable

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This bot is for educational and personal use only. Please respect ForexFactory's terms of service and implement appropriate rate limiting. The authors are not responsible for any misuse of this software.

## Support

If you encounter issues or have questions, please open an issue on GitHub.
