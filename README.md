# Forex Bot

Telegram bot for forex news and economic calendar notifications.

## Project Structure

```
forex_bot_postgresql/
├── app/                    # Main application code
│   ├── bot/               # Telegram bot implementation
│   ├── core/              # Core utilities and error handling
│   ├── database/          # Database models and connections
│   ├── services/          # Business logic services
│   ├── utils/             # Utility functions
│   ├── api/               # API endpoints
│   └── scrapers/          # Data scraping modules
├── docs/                  # Documentation
│   ├── api/               # API documentation
│   ├── deployment/        # Deployment guides
│   └── user_guide/        # User documentation
├── scripts/               # Utility scripts
│   ├── deployment/        # Deployment scripts
│   ├── maintenance/       # Maintenance scripts
│   └── testing/           # Testing scripts
├── tests/                 # Test files
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── config/                # Configuration files
│   ├── production/        # Production configs
│   └── development/       # Development configs
├── deployment/            # Deployment configurations
│   ├── docker/            # Docker files
│   ├── render/            # Render.com configs
│   └── systemd/           # Systemd service files
├── migrations/            # Database migrations (Alembic)
└── logs/                  # Log files
```

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r config/production/requirements.txt
   ```

2. Set environment variables:
   ```bash
   export TELEGRAM_BOT_TOKEN="your_bot_token"
   export DATABASE_URL="your_database_url"
   ```

3. Run migrations:
   ```bash
   alembic -c config/alembic.ini upgrade head
   ```

4. Start the bot:
   ```bash
   python main.py
   ```

## Features

- Economic calendar notifications
- Multi-currency support
- Customizable notification settings
- Impact level filtering
- Daily summaries
- Calendar view

## Configuration

See `docs/deployment/` for detailed configuration instructions.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License
