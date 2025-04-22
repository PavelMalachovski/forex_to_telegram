# 📊 Forex News to Telegram Bot

An automated bot that scrapes **high-impact economic events** from [ForexFactory.com](https://www.forexfactory.com/calendar) and sends them to Telegram every morning.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Playwright](https://img.shields.io/badge/Playwright-enabled-green)
![Render](https://img.shields.io/badge/Deployed%20on-Render-success)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue)

---

## 🚀 Features

- 🔍 Scrapes **only high-impact** events
- 📅 Automatically uses the current date
- 💬 Sends clean, formatted messages to Telegram
- ☁️ Runs on [Render.com](https://render.com)
- ⏰ Can be triggered daily via [Make.com](https://make.com) or any scheduler

---

## 🛠️ Setup

### 1. Clone the repository

```bash
git clone https://github.com/PavelMalachovski/forex_to_telegram.git
cd forex_to_telegram
```
### 2. Install dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```
### 3. Create a .env file
```env
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## 🌐 Deployment on Render
### 1. Create a new Web Service on Render.com
### 2. Set:
 * Build Command:
```bash
./build.sh
```
 * Start Command:
```bash
python app.py
```
### 3. Add environment variables:
* ```TELEGRAM_TOKEN```
* ```TELEGRAM_CHAT_ID```
### 4. After deployment, trigger your bot via:
```bash
https://your-app-name.onrender.com/run
```

## ⏰ Automate with Make.com
### 1. Create a new scenario
### 2. Add HTTP → Make a request
### 3. Configure:
* Method: ```GET```
* URL: ```https://your-app-name.onrender.com/run```
### 4. Set the schedule to Every Day at 7:00

## 📬 Telegram Message Preview
```yaml
🗓️ High-Impact Forex News for 22.04.2025 (EST):

⏰ Time: 08:30
💰 Currency: USD
📰 Event: CPI m/m
📈 Forecast: 0.3%
📊 Previous: 0.4%
---
...
```
## 🤝 Author
Created with ❤️ by @PavelMalachovski

## 📌 Roadmap / TODO
 * Add medium-impact events
 * Integrate crypto market news
 * Support ```/today``` command in Telegram
