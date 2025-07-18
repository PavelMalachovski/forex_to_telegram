# PostgreSQL Integration for Forex Telegram Bot

## Overview
Complete PostgreSQL integration has been implemented for the forex telegram bot project. The bot now uses a PostgreSQL database for data persistence instead of in-memory storage.

## Database Configuration
- **Connection String**: `postgresql://forex_user:0VGr0I02HDKaiVUVT21Z3ORnEiCBAYtC@dpg-d1mkim2li9vc73c7toi0-a:5432/forex_db_0myg?sslmode=require`
- **Database Fields**: currencies, date, impact, actual, forecast, previous, event_title, created_at
- **Primary Key**: Auto-incrementing ID
- **Unique Constraint**: (currencies, date, event_title) to prevent duplicates

## New Dependencies Added
```
psycopg2-binary==2.9.7
SQLAlchemy==2.0.21
alembic==1.12.0
```

## Key Files Created/Modified

### New Files:
1. **`bot/database.py`** - Database models and connection management
2. **`bot/scheduler.py`** - Daily scheduled scraping at 03:00 UTC
3. **`manage.py`** - Command-line script for manual execution
4. **`alembic.ini`** - Alembic configuration
5. **`alembic/env.py`** - Alembic environment setup
6. **`alembic/versions/001_initial_schema.py`** - Database migration

### Modified Files:
1. **`requirements.txt`** - Added PostgreSQL dependencies
2. **`bot/config.py`** - Added database URL configuration
3. **`bot/scraper.py`** - Integrated database checking and storage
4. **`bot/telegram_handlers.py`** - Updated to use database instead of memory
5. **`app.py`** - Complete integration with scheduler and database

## Core Features Implemented

### 1. Database Integration
- SQLAlchemy ORM with PostgreSQL backend
- Automatic table creation on startup
- Connection pooling and session management
- Data deduplication using unique constraints

### 2. Data Flow
```
1. Check database for existing data
2. If no data exists, scrape from forexfactory.com
3. Store scraped data in PostgreSQL database
4. Send data to telegram bot
5. Handle errors and logging throughout
```

### 3. Scheduled Task
- Daily scraping at 03:00 UTC
- Scrapes data for yesterday to 2 days ahead
- Uses APScheduler for background scheduling
- Automatic startup with Flask application

### 4. Manual Execution
```bash
# Scrape specific date range
python manage.py scrape --from 2025-07-18 --to 2025-07-20

# Scrape from specific date to today
python manage.py scrape --from 2025-07-18

# Get help
python manage.py scrape --help
```

### 5. API Endpoints Updated
- **`/manual_scrape`** - Now supports date ranges with `start_date` and `end_date`
- **`/status`** - Includes database connection status
- **`/`** - Updated to show PostgreSQL integration features

## Database Schema
```sql
CREATE TABLE forex_events (
    id SERIAL PRIMARY KEY,
    currencies VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    impact VARCHAR(20) NOT NULL,
    actual VARCHAR(50),
    forecast VARCHAR(50),
    previous VARCHAR(50),
    event_title VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(currencies, date, event_title)
);
```

## Usage Examples

### Manual Scraping via API
```bash
curl -X POST http://localhost:10000/manual_scrape \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-07-18",
    "end_date": "2025-07-20"
  }'
```

### Manual Scraping via Command Line
```bash
# Scrape specific date range
python manage.py scrape --from 2025-07-18 --to 2025-07-20

# Scrape single date
python manage.py scrape --from 2025-07-18
```

### Telegram Bot Commands
All existing telegram commands work the same:
- `/today` - Get today's forex news (from database or scrape if needed)
- `/tomorrow` - Get tomorrow's forex news
- `/calendar` - Select specific date
- `/impact` - Set impact level filter

## Error Handling
- Database connection failures are logged and handled gracefully
- Scraping errors don't crash the application
- Duplicate data is automatically handled by unique constraints
- Failed telegram sends are logged with error details

## Deployment Notes
1. Database tables are created automatically on startup
2. Scheduler starts automatically with the Flask application
3. All existing environment variables are still required
4. Database URL can be overridden with `DATABASE_URL` environment variable

## Migration from In-Memory to Database
The transition is seamless:
- All existing functionality is preserved
- Data is now persistent across restarts
- Performance improved with database caching
- Duplicate prevention built-in

## Monitoring
- Database status available at `/status` endpoint
- Scheduler status logged on startup
- All database operations are logged
- Error notifications sent to telegram on failures

## Next Steps for Deployment
1. Push changes to repository: `git push origin feature/add-db2`
2. Deploy to Render with the updated code
3. Database will be automatically initialized on first run
4. Scheduler will start automatically
5. Test manual scraping via API or command line

The integration is complete and ready for production deployment!
