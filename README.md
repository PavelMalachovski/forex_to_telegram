# Forex News Telegram Bot

A Telegram bot that scrapes forex news from ForexFactory and sends high-impact news to a specified Telegram chat. The bot uses OpenAI's GPT to analyze and summarize news events.

## Features

- **Automated News Scraping**: Fetches forex news from ForexFactory
- **AI-Powered Analysis**: Uses OpenAI GPT to analyze and summarize news
- **Telegram Integration**: Sends formatted news updates to Telegram
- **Impact Filtering**: Filters news by impact level (high, medium, low)
- **Scheduled Updates**: Can be configured to run at specific times
- **Web Interface**: Provides REST API endpoints for manual triggering and status checks
- **Render.com Ready**: Configured for easy deployment on Render.com

## Setup

### Prerequisites

- Python 3.11+
- Telegram Bot Token (from @BotFather)
- OpenAI API Key
- Render.com account (for deployment)

### Environment Variables

Create a `.env` file or set the following environment variables:

```bash
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
OPENAI_API_KEY=your_openai_api_key
API_KEY=your_custom_api_key_for_manual_endpoints
RENDER_EXTERNAL_HOSTNAME=your-app-name.onrender.com  # For webhook setup
PORT=10000  # Default port for the web server
```

### Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/PavelMalachovski/forex_to_telegram.git
   cd forex_to_telegram
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

3. **Set environment variables** (create `.env` file or export them)

4. **Run the application**:
   ```bash
   python app.py
   ```

5. **Test the bot**:
   - Send `/start` to your bot in Telegram
   - Use `/news` to get today's high-impact news
   - Use `/news_all` to get all news regardless of impact

## API Endpoints

### Health Check
```bash
GET /ping
```
Returns basic health status and timestamp.

### Application Status
```bash
GET /status
```
Returns detailed application status including configuration and missing environment variables.

### Manual News Scraping
```bash
POST /manual_scrape
Content-Type: application/json
X-API-Key: your_api_key

{
  "date": "2024-01-15",  # Optional: specific date (YYYY-MM-DD)
  "impact_level": "high", # Optional: high, medium, low, all
  "debug": false          # Optional: return news data instead of sending to Telegram
}
```

### Telegram Webhook
```bash
POST /webhook
```
Endpoint for Telegram webhook (automatically configured).

## Usage

### Telegram Commands

- `/start` - Initialize the bot and get welcome message
- `/news` - Get today's high-impact forex news
- `/news_all` - Get all today's forex news regardless of impact
- `/help` - Show available commands

### Manual Testing

Run the application locally:

```bash
python app.py
```

Open `http://0.0.0.0:10000` to check the bot's heartbeat.

## Deployment on Render.com

1. **New Web Service** → Link GitHub repo → Branch: `main` (or your feature branch).
2. **Build Command**
   ```bash
   pip install -r requirements.txt && playwright install chromium
   ```
3. **Start Command**: Leave empty (uses Procfile)
4. **Environment Variables**: Add all required variables listed above
5. **Auto-Deploy**: Enable for automatic deployments on git push

### Render.com Configuration

- **Runtime**: Python 3.11
- **Build Command**: `pip install -r requirements.txt && playwright install chromium`
- **Start Command**: (empty - uses Procfile)
- **Health Check Path**: `/ping`
- **Port**: 10000 (automatically configured)

## Project Structure

```
forex_to_telegram/
├── app.py                 # Main Flask application
├── bot/
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── scraper.py         # ForexFactory scraping logic
│   ├── telegram_handlers.py # Telegram bot handlers
│   └── utils.py           # Utility functions
├── tests/
│   ├── test_scraper.py    # Scraper tests
│   └── test_utils.py      # Utility tests
├── Dockerfile             # Docker configuration
├── Procfile              # Render.com process configuration
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Key Components

### ForexNewsScraper
Handles web scraping of ForexFactory using Playwright with Chromium browser.

### ChatGPTAnalyzer
Integrates with OpenAI API to analyze and summarize forex news events.

### TelegramBotManager
Manages Telegram bot initialization, webhook setup, and message handling.

### RenderKeepAlive
Prevents Render.com free tier from sleeping by sending periodic requests.

## Troubleshooting

### Common Issues

1. **Bot not responding**: Check `TELEGRAM_BOT_TOKEN` and ensure bot is started with `/start`
2. **No news received**: Verify `TELEGRAM_CHAT_ID` and check `/status` endpoint
3. **OpenAI errors**: Ensure `OPENAI_API_KEY` is valid and has sufficient credits
4. **Scraping failures**: ForexFactory might be blocking requests; check logs
5. **Webhook issues**: Ensure `RENDER_EXTERNAL_HOSTNAME` matches your Render app URL

### Debugging

- Check application logs in Render.com dashboard
- Use `/status` endpoint to verify configuration
- Test manual scraping with `debug: true` parameter
- Monitor `scraper.log` file for detailed scraping logs

### Environment Variables Validation

The application validates required environment variables on startup:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID` 
- `API_KEY`

Optional variables:
- `OPENAI_API_KEY` (required for AI analysis)
- `RENDER_EXTERNAL_HOSTNAME` (required for webhook setup)
- `PORT` (defaults to 10000)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.
