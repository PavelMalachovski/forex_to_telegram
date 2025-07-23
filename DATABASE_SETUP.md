# Database Setup Guide

This guide will help you set up the PostgreSQL database for the Forex News Telegram Bot.

## 🗄️ Database Configuration

### PostgreSQL Database

The bot is configured to work with a PostgreSQL database. Example settings:

```
Hostname: your-db-hostname
Port: 5432
Database: your_db_name
Username: your_db_user
Password: your_db_password
Internal Database URL: postgresql://your_db_user:your_db_password@your-db-hostname/your_db_name
```

> **Never share your real database credentials. Use environment variables for all secrets.**

## 🔧 Environment Variables

Add these environment variables to your deployment:

### Required Variables
```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Database
DATABASE_URL=postgresql://your_db_user:your_db_password@your-db-hostname/your_db_name

# API Security
API_KEY=your_secure_api_key_here
```

### Optional Variables
```env
# ChatGPT Integration
CHATGPT_API_KEY=your_openai_api_key_here

# Timezone
TIMEZONE=Europe/Prague
```

## 🚀 Database Logic

The bot now implements the following database logic:

### 1. Check Database First
- When a user requests news, the bot first checks if data exists in the database
- If data exists, it retrieves and sends it to Telegram
- If no data exists, it scrapes from ForexFactory and stores the results

### 2. Data Storage
- All scraped news is automatically stored in the database
- Data is organized by date, impact (per item), and currency
- Duplicate data is prevented with smart checking

### 3. Bulk Import
- Use the bulk import script to populate historical data
- Perfect for importing data from 1.1.2025 onwards

## 📊 Database Schema

The database uses the following table structure:

```sql
CREATE TABLE forex_news (
    id SERIAL PRIMARY KEY,
    date TIMESTAMP NOT NULL,
    time VARCHAR(50) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    event TEXT NOT NULL,
    actual VARCHAR(100),
    forecast VARCHAR(100),
    previous VARCHAR(100),
    impact_level VARCHAR(20) NOT NULL, -- high, medium, low, tentative, none
    analysis TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_date_currency_time ON forex_news(date, currency, time);
CREATE INDEX idx_date_impact ON forex_news(date, impact_level);
```

## 🛠️ Setup Instructions

### 1. Local Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export DATABASE_URL="postgresql://your_db_user:your_db_password@your-db-hostname/your_db_name"
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
export API_KEY="your_api_key"

# Run database setup
python setup_database.py
```

### 2. Deployment

1. **Connect your GitHub repository** to your cloud provider
2. **Set environment variables** in the dashboard
3. **Deploy** using the provided Dockerfile
4. **Monitor logs** for database connection status

### 3. Bulk Data Import

To import historical data from 1.1.2025:

```bash
# Import data for January 2025
python bulk_import.py --start-date 2025-01-01 --end-date 2025-01-31 --impact-level high

# Import all impact levels for a date range
python bulk_import.py --start-date 2025-01-01 --end-date 2025-01-31 --impact-level all

# Dry run to see what would be imported
python bulk_import.py --start-date 2025-01-01 --end-date 2025-01-31 --impact-level high --dry-run
```

## 🔍 API Endpoints

### Database Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/db/stats` | GET | Get database statistics |
| `/db/check/<date>` | GET | Check if data exists for a date |
| `/db/import` | POST | Bulk import data (requires API key) |

### Example Usage

```bash
# Check database health
curl https://your-app-url/health

# Get database statistics
curl https://your-app-url/db/stats

# Check data for specific date
curl https://your-app-url/db/check/2025-01-01

# Import data via API
curl -X POST https://your-app-url/db/import \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "start_date": "2025-01-01",
    "end_date": "2025-01-31",
    "impact_level": "high"
  }'
```

## 📈 Database Statistics

The bot provides comprehensive statistics:

- **Total news count** by date range
- **Impact level distribution** (high, medium, low, tentative, none)
- **Currency distribution**
- **Database health status**

## 🛠️ Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check if DATABASE_URL is set correctly
   - Verify database credentials
   - Ensure database is accessible from your deployment

2. **Migration Errors**
   - Run `python setup_database.py` to create tables
   - Check logs for specific error messages

3. **Import Failures**
   - Verify API key is correct
   - Check date format (YYYY-MM-DD)
   - Monitor logs for scraping errors

### Health Checks

```bash
# Check application health
curl https://your-app-url/health

# Check database specifically
curl https://your-app-url/db/stats
```

## 🚀 Performance Optimization

### Database Indexes
- Composite indexes for efficient date/currency/time queries
- Separate index for date/impact level filtering
- Automatic cleanup of old data (configurable)

### Caching Strategy
- Database-first approach reduces scraping load
- Smart duplicate detection prevents redundant scraping
- Rate limiting built into bulk import

## 🛡️ Security

### API Key Protection
- All database operations require API key authentication
- Environment variables for sensitive data
- Secure database connection strings

### Data Privacy
- No personal data stored
- Only forex news data in database
- Automatic data retention policies

## 📚 Next Steps

1. **Deploy with the updated environment variables**
2. **Run the bulk import** for historical data from 1.1.2025
3. **Test the API endpoints** to verify functionality
4. **Monitor the application** for any issues
5. **Scale as needed** based on usage patterns

---

**Need Help?** Check the main README.md for additional information or open an issue on GitHub.
