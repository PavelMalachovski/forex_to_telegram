
# Forex Bot with PostgreSQL

A Telegram bot for forex news notifications with PostgreSQL database and make.com integration.

## Architecture

The project is now split into two main components:

1. **Telegram Bot** (`main.py`) - Handles user interactions
2. **API Server** (`api_server.py`) - Provides endpoints for make.com automation

## Features

- Real-time forex news scraping from ForexFactory
- Telegram bot for user interactions
- PostgreSQL database for data persistence
- API endpoints for external automation
- User preference management
- High-impact news notifications

## Project Structure

```
forex_bot_postgresql/
├── app/                          # Main application package
│   ├── bot/                      # Telegram bot handlers
│   ├── database/                 # Database models and connection
│   ├── scrapers/                 # Web scrapers
│   ├── services/                 # Business logic services
│   └── utils/                    # Utility functions
├── api_server.py                 # Flask API server
├── main.py                       # Telegram bot entry point
├── wsgi.py                       # WSGI entry point
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker for bot
├── Dockerfile.api                # Docker for API server
└── docker-compose.yml            # Docker compose configuration
```

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 12+
- Telegram Bot Token

### Local Development

1. Clone the repository:
```bash
git clone <repository-url>
cd forex_bot_postgresql
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

5. Initialize database:
```bash
python init_data.py
```

### Docker Deployment

#### Telegram Bot
```bash
docker build -t forex-bot .
docker run -d --name forex-bot --env-file .env forex-bot
```

#### API Server
```bash
docker build -f Dockerfile.api -t forex-api .
docker run -d --name forex-api -p 8000:8000 --env-file .env forex-api
```

#### Using Docker Compose
```bash
docker-compose up -d
```

## API Endpoints

The API server provides the following endpoints for make.com integration:

### Health Check
```
GET /health
```
Returns server health status.

### Load Data
```
POST /api/load-data
```
Loads forex data starting from the previous day (for updating actual impact values).

**Request Body (optional):**
```json
{
  "days_ahead": 5
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "status": "success",
    "events_loaded": 25,
    "errors_count": 0,
    "duration_seconds": 45,
    "start_date": "2025-06-23",
    "end_date": "2025-06-28"
  },
  "timestamp": "2025-06-24T16:30:00"
}
```

### Send Today
```
POST /api/send-today
```
Sends today's high-impact news to all active users.

**Response:**
```json
{
  "success": true,
  "result": {
    "status": "success",
    "users_notified": 15,
    "errors_count": 0,
    "total_users": 15
  },
  "timestamp": "2025-06-24T07:00:00"
}
```

### Status
```
GET /api/status
```
Returns API server status and configuration.

## Make.com Integration

### Setup Instructions

1. **Create a Make.com Account**
   - Sign up at [make.com](https://make.com)
   - Create a new scenario

2. **Configure Data Loading (05:00 Schedule)**
   - Add a "Schedule" trigger module
   - Set time to 05:00 (your timezone)
   - Set frequency to "Every day"
   - Add an "HTTP" action module
   - Configure:
     - URL: `https://your-api-server.com/api/load-data`
     - Method: POST
     - Headers: `Content-Type: application/json`
     - Body: `{"days_ahead": 5}`

3. **Configure Today News Sending (07:00 Schedule)**
   - Create a second scenario or add to existing
   - Add a "Schedule" trigger module
   - Set time to 07:00 (your timezone)
   - Set frequency to "Every day"
   - Add an "HTTP" action module
   - Configure:
     - URL: `https://your-api-server.com/api/send-today`
     - Method: POST
     - Headers: `Content-Type: application/json`

4. **Error Handling (Optional)**
   - Add error handling modules to retry failed requests
   - Add notification modules to alert on failures
   - Use the `/api/status` endpoint for health monitoring

### Webhook URLs

Replace `your-api-server.com` with your actual API server domain:

- **Data Loading**: `https://your-api-server.com/api/load-data`
- **Today News**: `https://your-api-server.com/api/send-today`
- **Health Check**: `https://your-api-server.com/health`
- **Status**: `https://your-api-server.com/api/status`

### Scheduling Recommendations

- **05:00**: Load data from previous day (updates actual impact values)
- **07:00**: Send today's news to all users
- **Health checks**: Every 15 minutes using `/health` endpoint

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/forex_bot

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Flask
FLASK_HOST=0.0.0.0
FLASK_PORT=8000
FLASK_DEBUG=false

# Timezone
TIMEZONE=Europe/Berlin

# Optional: Render.com
RENDER_EXTERNAL_HOSTNAME=your-app.onrender.com
```

## Bot Commands

- `/start` - Start the bot and register user
- `/today` - Get today's high-impact news
- `/tomorrow` - Get tomorrow's high-impact news
- `/week` - Get this week's high-impact news
- `/calendar` - Interactive calendar for date selection
- `/settings` - Manage notification preferences
- `/help` - Show available commands

## Development

### Running Tests
```bash
pytest tests/
```

### Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

### Logs
Application logs are stored in the `logs/` directory:
- `app.log` - General application logs
- `error.log` - Error logs

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Check DATABASE_URL format
   - Ensure PostgreSQL is running
   - Verify network connectivity

2. **Telegram Bot Not Responding**
   - Verify TELEGRAM_BOT_TOKEN
   - Check bot permissions
   - Review logs for errors

3. **API Endpoints Not Working**
   - Check Flask server is running
   - Verify port configuration
   - Check firewall settings

4. **Make.com Integration Issues**
   - Verify webhook URLs are accessible
   - Check API server logs
   - Test endpoints manually with curl

### Support

For issues and questions, please check the logs first and ensure all environment variables are properly configured.
