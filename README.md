# Forex News Bot v2.0 - Modern FastAPI Implementation

A modern, scalable forex news bot built with FastAPI, async/await, and modern Python practices.

## 🚀 Features

### Core Features
- **Real-time Forex News**: Automated scraping and analysis of forex news events
- **Telegram Bot Integration**: Interactive bot with commands and notifications
- **Advanced Chart Generation**: Professional forex charts with multiple timeframes
- **Smart Notifications**: Personalized notifications based on user preferences
- **Multi-currency Support**: Support for major forex pairs and cryptocurrencies

### Modern Architecture
- **FastAPI**: High-performance async web framework
- **Async/Await**: Full async support throughout the application
- **Pydantic Models**: Type-safe data validation and serialization
- **SQLAlchemy 2.0**: Modern async ORM with type hints
- **Redis Caching**: High-performance caching layer
- **Celery**: Background task processing
- **Docker**: Containerized deployment
- **Structured Logging**: Comprehensive logging with structlog

### API Features
- **RESTful API**: Complete REST API with OpenAPI documentation
- **Webhook Support**: Telegram webhook integration
- **Health Checks**: Comprehensive health monitoring
- **Rate Limiting**: Built-in rate limiting and throttling
- **Authentication**: JWT-based authentication
- **Monitoring**: Prometheus metrics and observability

## 📋 Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL 15+
- Redis 7+
- Telegram Bot Token

## 🛠️ Installation

### Quick Start with Docker

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd forex_to_telegram
   ```

2. **Configure environment**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Deploy with Docker Compose**
   ```bash
   ./scripts/deploy.sh
   ```

### Manual Installation

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements-modern.txt
   ```

3. **Set up database**
   ```bash
   # Start PostgreSQL and Redis
   docker-compose -f docker-compose.modern.yml up -d postgres redis

   # Run migrations
   python scripts/migrate.py
   ```

4. **Start the application**
   ```bash
   uvicorn src.main:app --reload
   ```

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=forex_bot
DB_USER=forex_user
DB_PASSWORD=your_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/api/v1/telegram/webhook

# API Keys
API_OPENAI_API_KEY=your_openai_key
API_ALPHA_VANTAGE_KEY=your_alpha_vantage_key

# Security
SECURITY_SECRET_KEY=your_secret_key_minimum_32_chars
```

### Service Configuration

The application uses Pydantic Settings for configuration management:

- **Database Settings**: Connection pooling, timeouts, SSL
- **Redis Settings**: Connection configuration and clustering
- **Telegram Settings**: Bot token, webhook configuration
- **API Settings**: External API keys and rate limiting
- **Chart Settings**: Chart generation and caching
- **Security Settings**: JWT tokens and encryption
- **Logging Settings**: Log levels and formatting

## 📚 API Documentation

### Interactive Documentation

Once the application is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

#### Users
- `POST /api/v1/users/` - Create user
- `GET /api/v1/users/{telegram_id}` - Get user
- `PUT /api/v1/users/{telegram_id}` - Update user
- `PUT /api/v1/users/{telegram_id}/preferences` - Update preferences

#### Forex News
- `GET /api/v1/forex-news/` - Get news with filters
- `POST /api/v1/forex-news/` - Create news
- `GET /api/v1/forex-news/today/` - Get today's news

#### Charts
- `POST /api/v1/charts/generate` - Generate chart
- `POST /api/v1/charts/generate/image` - Generate chart image
- `GET /api/v1/charts/currencies` - Get supported currencies

#### Telegram
- `POST /api/v1/telegram/webhook` - Telegram webhook
- `GET /api/v1/telegram/webhook/info` - Webhook info
- `POST /api/v1/telegram/webhook/set` - Set webhook

#### Notifications
- `GET /api/v1/notifications/` - Get notifications
- `POST /api/v1/notifications/` - Create notification
- `GET /api/v1/notifications/pending/` - Get pending notifications

## 🏗️ Architecture

### Project Structure

```
src/
├── core/                 # Core application components
│   ├── config.py        # Configuration management
│   ├── exceptions.py    # Custom exceptions
│   └── logging.py       # Logging configuration
├── models/              # Pydantic data models
│   ├── user.py         # User models
│   ├── forex_news.py   # Forex news models
│   ├── chart.py        # Chart models
│   └── notification.py # Notification models
├── database/           # Database layer
│   ├── connection.py   # Database connection
│   └── models.py       # SQLAlchemy models
├── services/           # Business logic layer
│   ├── base.py        # Base service class
│   ├── user_service.py # User service
│   ├── forex_service.py # Forex service
│   └── chart_service.py # Chart service
├── api/                # API layer
│   └── v1/            # API version 1
│       ├── router.py  # Main router
│       └── endpoints/ # API endpoints
└── main.py            # FastAPI application
```

### Service Layer Pattern

The application follows a service layer pattern:

1. **Models**: Pydantic models for data validation
2. **Database Models**: SQLAlchemy models for persistence
3. **Services**: Business logic and data access
4. **API Endpoints**: HTTP request/response handling
5. **Dependency Injection**: FastAPI's built-in DI system

### Async/Await Support

All I/O operations are async:
- Database queries
- External API calls
- Telegram bot operations
- File operations
- Redis operations

## 🔄 Background Tasks

### Celery Integration

Background tasks are handled by Celery:

- **News Scraping**: Automated forex news collection
- **Chart Generation**: Async chart creation
- **Notifications**: Scheduled notification sending
- **Data Processing**: Heavy data processing tasks

### Task Types

- **Periodic Tasks**: Daily news scraping, digest generation
- **Event-driven Tasks**: Chart generation, notifications
- **Batch Tasks**: Bulk data processing, cleanup

## 📊 Monitoring and Observability

### Health Checks

- **Application Health**: `/health` endpoint
- **Database Health**: Connection and query checks
- **Redis Health**: Connection and operation checks
- **External APIs**: Service availability checks

### Logging

Structured logging with:
- **JSON Format**: Production-ready structured logs
- **Log Levels**: Configurable log levels
- **Context**: Request IDs, user IDs, correlation IDs
- **Performance**: Request timing and performance metrics

### Metrics

Prometheus metrics for:
- **Request Metrics**: Count, duration, status codes
- **Business Metrics**: User activity, news events
- **System Metrics**: Database, Redis, external APIs
- **Custom Metrics**: Chart generation, notification success

## 🚀 Deployment

### Docker Deployment

The application is fully containerized:

```bash
# Build and start all services
docker-compose -f docker-compose.modern.yml up -d

# View logs
docker-compose -f docker-compose.modern.yml logs -f

# Scale services
docker-compose -f docker-compose.modern.yml up -d --scale celery-worker=3
```

### Production Considerations

1. **Environment Variables**: Use secure environment variable management
2. **SSL/TLS**: Configure HTTPS for webhook endpoints
3. **Load Balancing**: Use nginx or cloud load balancers
4. **Monitoring**: Set up comprehensive monitoring
5. **Backups**: Regular database and Redis backups
6. **Security**: Regular security updates and vulnerability scanning

### Scaling

The application is designed for horizontal scaling:

- **Stateless Services**: All services are stateless
- **Database Connection Pooling**: Efficient connection management
- **Redis Clustering**: Support for Redis clusters
- **Celery Workers**: Multiple worker processes
- **Load Balancing**: Multiple app instances

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_user_service.py

# Run async tests
pytest -k async
```

### Test Structure

- **Unit Tests**: Individual service and model tests
- **Integration Tests**: API endpoint tests
- **Async Tests**: Async service tests
- **Mock Tests**: External API mocking

## 🔧 Development

### Code Quality

- **Black**: Code formatting
- **isort**: Import sorting
- **mypy**: Type checking
- **pre-commit**: Git hooks for quality checks

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-modern.txt

# Install pre-commit hooks
pre-commit install

# Run code quality checks
black src/
isort src/
mypy src/
```

## 📈 Performance

### Optimization Features

- **Async Operations**: Non-blocking I/O operations
- **Connection Pooling**: Efficient database connections
- **Redis Caching**: Fast data access
- **Background Tasks**: Non-blocking heavy operations
- **Database Indexing**: Optimized queries
- **Response Compression**: Reduced bandwidth usage

### Performance Monitoring

- **Request Timing**: Track API response times
- **Database Performance**: Query execution times
- **Cache Hit Rates**: Redis performance metrics
- **Background Task Performance**: Celery task metrics

## 🔒 Security

### Security Features

- **JWT Authentication**: Secure token-based auth
- **Input Validation**: Pydantic model validation
- **SQL Injection Prevention**: SQLAlchemy ORM protection
- **Rate Limiting**: API rate limiting
- **CORS Configuration**: Cross-origin request handling
- **Environment Security**: Secure configuration management

### Security Best Practices

1. **Environment Variables**: Never commit secrets
2. **HTTPS**: Use SSL/TLS in production
3. **Regular Updates**: Keep dependencies updated
4. **Access Control**: Implement proper authorization
5. **Audit Logging**: Log security events
6. **Vulnerability Scanning**: Regular security scans

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Development Guidelines

- Follow PEP 8 style guidelines
- Write comprehensive tests
- Document new features
- Use type hints
- Follow async/await patterns
- Write clear commit messages

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

- **Documentation**: Check the API docs at `/docs`
- **Issues**: Create GitHub issues for bugs
- **Discussions**: Use GitHub discussions for questions
- **Email**: Contact the development team

## 🎯 Roadmap

### Upcoming Features

- **Machine Learning**: AI-powered news analysis
- **Advanced Charts**: More chart types and indicators
- **Mobile App**: Native mobile application
- **Web Dashboard**: Web-based admin interface
- **Multi-language**: Internationalization support
- **Advanced Notifications**: Push notifications, email alerts

### Performance Improvements

- **GraphQL API**: More efficient data fetching
- **Microservices**: Service decomposition
- **Event Sourcing**: Event-driven architecture
- **CQRS**: Command Query Responsibility Segregation
- **Real-time Updates**: WebSocket support

---

**Forex News Bot v2.0** - Modern, scalable, and production-ready forex news automation.
