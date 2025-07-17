# Forex News Bot

A lean Telegram bot that scrapes Forex news from Forex Factory and pushes it straight to your channel—no fluff, just the headlines you need.

## Table of Contents

- [Forex News Bot](#forex-news-bot)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
    - [Clone \& Virtualenv](#clone--virtualenv)
    - [Install Dependencies](#install-dependencies)
  - [Configuration](#configuration)
  - [Running Locally](#running-locally)
  - [Deployment on Render.com](#deployment-on-rendercom)
  - [Usage](#usage)
    - [Telegram Commands](#telegram-commands)
    - [API Endpoints](#api-endpoints)
      - [Examples](#examples)
  - [Testing](#testing)
  - [Troubleshooting](#troubleshooting)
  - [Contributing](#contributing)

---

## Features

- **Date-picker interface** via Telegram calendar.
- **Impact filtering**: high — or medium+high — because you don’t have time for the noise.
- **Markdown-formatted** messages so headlines look sharp.
- **Keep-alive**: APScheduler pings itself every 5 min on Render to dodge idling.
- **Debug mode**: hit `/run?debug=1` and get raw JSON.

## Prerequisites

- Python 3.9+
- Telegram bot token (via BotFather)
- Telegram channel/chat ID (e.g., `@YourChannel` or numeric ID)
- (Optional) Render.com account for hassle-free hosting

## Installation

### Clone & Virtualenv

```bash
git clone https://github.com/your-username/forex_to_telegram.git
cd forex_to_telegram
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
playwright install
```

_If your `requirements.txt` is stale:_

```bash
pip install flask pyTelegramBotAPI beautifulsoup4 playwright pytz gunicorn apscheduler requests
playwright install
```

## Configuration

Create a `.env` file in the project root:

```dotenv
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id
API_KEY=your-secret-api-key
RENDER_EXTERNAL_HOSTNAME=your-render-hostname  # e.g., forex-to-telegram-1j5p.onrender.com
```

- **TELEGRAM_BOT_TOKEN**: From BotFather.
- **TELEGRAM_CHAT_ID**: Channel or group ID (must be bot-admin).
- **API_KEY**: Guards the `/run` endpoint.
- **RENDER_EXTERNAL_HOSTNAME**: Used for self-pings.

## Running Locally

```bash
python app.py
```

Open `http://0.0.0.0:5000` to check the bot’s heartbeat.

## Deployment on Render.com

1. **New Web Service** → Link GitHub repo → Branch: `main` (or your feature branch).
2. **Build Command**
   ```bash
   pip install -r requirements.txt && playwright install
   ```
3. **Start Command**
   ```bash
   python app.py
   ```
4. **Env Vars**: Paste the `.env` keys into Render’s dashboard.
5. **Deploy** and watch it stay alive with self-pings.

## Usage

### Telegram Commands

- `/start` or `/help` — Show commands.
- `/today` — Blast today’s high-impact news.
- `/calendar` — Pick a date & impact level.

### API Endpoints

- `GET /`
  Returns “Bot is online”
- `GET /ping`
  Self-ping endpoint for APScheduler.
- `GET /run?api_key=<KEY>&date=<YYYY-MM-DD>&impact=<high|medium>&debug=<0|1>`
  Scrapes news (defaults: today, high-impact).
- `POST /webhook`
  Telegram updates webhook.

#### Examples

```bash
# Trigger news for April 1, 2025
curl "https://<your-host>/run?api_key=KEY&date=2025-04-01"

# Debug mode
curl "https://<your-host>/run?api_key=KEY&debug=1&date=2025-04-01"
```

## Testing

1. **Logs** on Render should show:
   ```
   [INFO] All required environment variables are set
   [INFO] Telegram bot initialized
   [INFO] Webhook set to https://<your-host>/webhook
   [INFO] APScheduler started (5 min ping)
   ```
2. **Webhook status**:
   ```bash
   curl "https://api.telegram.org/bot<token>/getWebhookInfo"
   ```
3. **Bot commands**: `/start`, `/today`, `/calendar` → verify messages.

## Troubleshooting

- **Webhook fails**: Double-check `RENDER_EXTERNAL_HOSTNAME`.
- **Scraping errors**: Ensure `playwright install` ran; inspect `scraper.log`.
- **Telegram “403”**: Bot needs admin rights; verify `TELEGRAM_CHAT_ID`.

## Contributing

Feel free to fork, tweak, and PR. For big changes, open an issue first.
