
# Forex Bot with PostgreSQL

A Telegram bot for forex news and analysis with PostgreSQL database support and Make.com integration.

## Features

- 📈 Real-time forex news from ForexFactory
- 🤖 Telegram bot interface
- 📊 PostgreSQL database for data persistence
- 🔄 Make.com integration for automated scheduling
- 🌐 Webhook support for production deployment
- 📱 User notification preferences
- 📅 Calendar view for news events

## Architecture

The application supports two modes:

### Development Mode (Polling)
- Uses Telegram polling for local development
- Runs Flask API server for Make.com integration
- Suitable for testing and development

### Production Mode (Webhook)
- Uses Telegram webhooks for production deployment
- Automatically detected on Render.com
- More efficient for production use

## Quick Start

### Local Development

1. **Clone and setup**:
```bash
git clone <repository>
cd forex_bot_postgresql
pip install -r requirements.txt
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Setup database**:
```bash
# For PostgreSQL
createdb forex_bot
python -c "from app.database.connection import init_database; init_database()"

# For SQLite (development)
python -c "from app.database.connection import init_database; init_database()"
```

4. **Run the application**:
```bash
python main.py
```

The bot will start in polling mode and the API server will be available at `http://localhost:5000`.

### Production Deployment on Render.com

1. **Setup environment variables** in Render dashboard:
```
DATABASE_URL=postgresql://user:password@host:port/database
TELEGRAM_BOT_TOKEN=your_bot_token
RENDER_EXTERNAL_HOSTNAME=your-app-name.onrender.com
```

2. **Deploy using render.yaml**:
The application will automatically:
- Detect Render.com environment
- Switch to webhook mode
- Setup webhook URL automatically
- Start Flask server for webhook handling

3. **Verify deployment**:
```bash
curl https://your-app-name.onrender.com/health
```

## Webhook Management

### Automatic Setup
The application automatically manages webhooks in production mode.

### Manual Management
Use the webhook management script:

```bash
# Check current webhook status
python manage_webhook.py status

# Set webhook for Render.com
python manage_webhook.py set-render

# Set custom webhook URL
python manage_webhook.py set https://your-domain.com/webhook

# Delete webhook (switch to polling)
python manage_webhook.py delete
```

### Troubleshooting Webhook Issues

If you get the error "can't use getUpdates method while webhook is active":

1. **Delete existing webhook**:
```bash
python manage_webhook.py delete
```

2. **For local development**, ensure no webhook is set:
```bash
python manage_webhook.py status
# Should show "URL: Not set"
```

3. **For production**, set webhook properly:
```bash
python manage_webhook.py set-render
```

## Environment Variables

### Required
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `DATABASE_URL`: PostgreSQL connection string

### Optional
- `RENDER_EXTERNAL_HOSTNAME`: Auto-set by Render.com
- `WEBHOOK_MODE`: Force webhook mode (true/false)
- `WEBHOOK_URL`: Custom webhook URL
- `FLASK_PORT`: Server port (default: 5000)
- `FLASK_HOST`: Server host (default: 0.0.0.0)
- `LOG_LEVEL`: Logging level (default: INFO)

## API Endpoints

### Health Check
```
GET /health
GET /ping
```

### Make.com Integration
```
POST /api/load-data
POST /api/send-today
GET /api/status
```

### Webhook
```
POST /webhook  # Telegram webhook endpoint
```

## Database

### PostgreSQL (Production)
```bash
# Connection string format
DATABASE_URL=postgresql://username:password@hostname:port/database_name
```

### SQLite (Development)
```bash
# File-based database
DATABASE_URL=sqlite:///forex_bot.db
```

### Migrations
```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description"
```

## Make.com Integration

The bot provides API endpoints for Make.com automation:

1. **Data Loading** (scheduled at 05:00):
   - Endpoint: `POST /api/load-data`
   - Loads forex data for upcoming days

2. **Daily Notifications** (scheduled at 07:00):
   - Endpoint: `POST /api/send-today`
   - Sends today's news to all active users

## Bot Commands

- `/start` - Start the bot and register user
- `/today` - Get today's forex news
- `/tomorrow` - Get tomorrow's forex news
- `/week` - Get this week's forex news
- `/calendar` - Show calendar view
- `/settings` - Configure notification preferences
- `/help` - Show help message

## Development

### Project Structure
```
forex_bot_postgresql/
├── app/
│   ├── bot/           # Telegram bot handlers
│   ├── database/      # Database models and connection
│   ├── services/      # Business logic services
│   ├── scrapers/      # Data scraping modules
│   ├── api/          # API routes
│   └── utils/        # Utility functions
├── main.py           # Main application entry point
├── webhook_utils.py  # Webhook management utilities
├── manage_webhook.py # Webhook management script
└── requirements.txt  # Python dependencies
```

### Running Tests
```bash
pytest tests/
```

### Code Style
```bash
# Format code
black .

# Lint code
flake8 .
```

## Troubleshooting

### Common Issues

1. **Webhook conflicts**:
   - Use `python manage_webhook.py delete` to clear webhooks
   - Check status with `python manage_webhook.py status`

2. **Database connection issues**:
   - Verify DATABASE_URL format
   - Check database server accessibility
   - Run `python -c "from app.database.connection import test_connection; test_connection()"`

3. **Bot not responding**:
   - Verify TELEGRAM_BOT_TOKEN
   - Check bot permissions in Telegram
   - Review application logs

4. **Render.com deployment issues**:
   - Check environment variables in Render dashboard
   - Verify RENDER_EXTERNAL_HOSTNAME is set
   - Check application logs in Render dashboard

### Logs

Application logs are available:
- Local: `logs/app.log` and `logs/error.log`
- Render.com: In the Render dashboard logs section

## License

MIT License - see LICENSE file for details.
