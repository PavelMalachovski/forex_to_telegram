# 🚀 **REDIS DEPLOYMENT GUIDE**

## 📋 **OVERVIEW**

This guide provides comprehensive instructions for deploying the Forex Bot application with Redis integration using Docker and Docker Compose.

## 🏗️ **DEPLOYMENT ARCHITECTURE**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Redis       │    │   FastAPI App   │
│   Database      │    │     Cache       │    │   Application   │
│                 │    │                 │    │                 │
│  - User Data    │    │  - Sessions     │    │  - API Server   │
│  - Forex News   │    │  - Rate Limits  │    │  - Webhooks     │
│  - Charts       │    │  - Pub/Sub      │    │  - Health Check │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Celery Stack  │
                    │                 │
                    │  - Worker       │
                    │  - Beat         │
                    │  - Flower       │
                    └─────────────────┘
```

## 🔧 **PREREQUISITES**

### **System Requirements**
- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 10GB disk space

### **Environment Variables**
Create a `.env` file with the following variables:

```bash
# Database Configuration
DB_NAME=forex_bot
DB_USER=forex_user
DB_PASSWORD=your_secure_password

# Redis Configuration
REDIS_PASSWORD=your_redis_password

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook

# API Keys
API_ALPHA_VANTAGE_KEY=your_alpha_vantage_key
API_OPENAI_API_KEY=your_openai_key

# Security
SECURITY_SECRET_KEY=your_secret_key

# Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

## 🚀 **DEPLOYMENT STEPS**

### **1. Clone and Prepare**

```bash
# Clone the repository
git clone <your-repo-url>
cd forex_to_telegram

# Make scripts executable
chmod +x scripts/*.sh
chmod +x scripts/*.py
```

### **2. Configure Redis**

```bash
# Review Redis configuration
cat redis.conf

# Customize Redis settings if needed
# Key settings:
# - maxmemory: 256mb (adjust based on available RAM)
# - maxmemory-policy: allkeys-lru
# - notify-keyspace-events: Ex
```

### **3. Build and Start Services**

```bash
# Build all services
docker-compose build

# Start services in background
docker-compose up -d

# Check service status
docker-compose ps
```

### **4. Verify Deployment**

```bash
# Check Redis health
docker-compose exec redis redis-cli ping

# Check application health
curl http://localhost:8000/health

# Check Redis statistics
curl http://localhost:8000/api/v1/redis/stats
```

## 📊 **MONITORING**

### **Service Health Checks**

```bash
# Check all services
docker-compose ps

# Check Redis logs
docker-compose logs redis

# Check application logs
docker-compose logs app

# Check Redis memory usage
docker-compose exec redis redis-cli info memory
```

### **Redis Monitoring**

```bash
# Use the Redis monitoring script
python scripts/redis_monitor.py --health

# Monitor Redis commands in real-time
python scripts/redis_monitor.py --monitor 30

# Get comprehensive Redis information
python scripts/redis_monitor.py --all
```

### **API Endpoints**

- **Health Check**: `GET /health`
- **Redis Stats**: `GET /api/v1/redis/stats`
- **Redis Health**: `GET /api/v1/redis/health`
- **Cache Hit Ratio**: `GET /api/v1/redis/cache/hit-ratio`

## 🔧 **CONFIGURATION**

### **Redis Configuration** (`redis.conf`)

```conf
# Memory Management
maxmemory 256mb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Performance
hz 10
dynamic-hz yes

# Security
requirepass your_redis_password
```

### **Docker Compose Configuration**

```yaml
services:
  redis:
    image: redis:7-alpine
    command: redis-server /usr/local/etc/redis/redis.conf
    volumes:
      - redis_data:/data
      - ./redis.conf:/usr/local/etc/redis/redis.conf:ro
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
```

## 🚀 **PRODUCTION DEPLOYMENT**

### **1. Production Environment**

```bash
# Set production environment
export ENVIRONMENT=production
export DEBUG=false
export LOG_LEVEL=INFO

# Use production Docker Compose
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

### **2. Security Hardening**

```bash
# Generate secure passwords
openssl rand -base64 32  # For REDIS_PASSWORD
openssl rand -base64 32  # For SECURITY_SECRET_KEY

# Update redis.conf for production
# - Enable authentication
# - Disable dangerous commands
# - Set appropriate memory limits
```

### **3. SSL/TLS Configuration**

```bash
# For production, use HTTPS
# Update TELEGRAM_WEBHOOK_URL to use HTTPS
# Configure reverse proxy (nginx/traefik)
```

## 📈 **SCALING**

### **Horizontal Scaling**

```bash
# Scale application instances
docker-compose up -d --scale app=3

# Scale Celery workers
docker-compose up -d --scale celery-worker=5
```

### **Redis Clustering** (Advanced)

```yaml
# For high availability, consider Redis Cluster
services:
  redis-master:
    image: redis:7-alpine
    command: redis-server --appendonly yes

  redis-replica:
    image: redis:7-alpine
    command: redis-server --replicaof redis-master 6379
```

## 🔍 **TROUBLESHOOTING**

### **Common Issues**

#### **1. Redis Connection Failed**

```bash
# Check Redis logs
docker-compose logs redis

# Test Redis connectivity
docker-compose exec app redis-cli -h redis ping

# Check Redis configuration
docker-compose exec redis redis-cli CONFIG GET "*"
```

#### **2. Application Startup Issues**

```bash
# Check application logs
docker-compose logs app

# Check Redis wait script
docker-compose exec app python scripts/wait_for_redis.py

# Verify environment variables
docker-compose exec app env | grep REDIS
```

#### **3. Memory Issues**

```bash
# Check Redis memory usage
docker-compose exec redis redis-cli info memory

# Check system memory
docker stats

# Adjust Redis memory limit
# Edit redis.conf: maxmemory 512mb
```

### **Debug Commands**

```bash
# Redis CLI access
docker-compose exec redis redis-cli

# Application shell access
docker-compose exec app bash

# Check Redis keys
docker-compose exec redis redis-cli KEYS "*"

# Monitor Redis commands
docker-compose exec redis redis-cli MONITOR
```

## 📊 **PERFORMANCE OPTIMIZATION**

### **Redis Optimization**

```bash
# Optimize Redis configuration
docker-compose exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
docker-compose exec redis redis-cli CONFIG SET notify-keyspace-events Ex
docker-compose exec redis redis-cli CONFIG SET timeout 300
```

### **Application Optimization**

```bash
# Enable Redis optimization on startup
export REDIS_OPTIMIZE_ON_START=true

# Enable Redis monitoring
export REDIS_MONITORING_ENABLED=true

# Restart application
docker-compose restart app
```

## 🔒 **SECURITY**

### **Redis Security**

```bash
# Enable Redis authentication
echo "requirepass your_secure_password" >> redis.conf

# Disable dangerous commands
echo "rename-command FLUSHDB \"\"" >> redis.conf
echo "rename-command FLUSHALL \"\"" >> redis.conf

# Restart Redis
docker-compose restart redis
```

### **Network Security**

```bash
# Use internal networks
# Update docker-compose.yml to use custom networks
# Restrict Redis port exposure
```

## 📚 **MAINTENANCE**

### **Backup and Restore**

```bash
# Backup Redis data
docker-compose exec redis redis-cli BGSAVE

# Backup Docker volumes
docker run --rm -v forex_to_telegram_redis_data:/data -v $(pwd):/backup alpine tar czf /backup/redis-backup.tar.gz /data

# Restore Redis data
docker run --rm -v forex_to_telegram_redis_data:/data -v $(pwd):/backup alpine tar xzf /backup/redis-backup.tar.gz -C /
```

### **Updates**

```bash
# Update Redis version
# Edit docker-compose.yml: image: redis:8-alpine
docker-compose pull redis
docker-compose up -d redis

# Update application
git pull
docker-compose build app
docker-compose up -d app
```

## 🎯 **DEPLOYMENT CHECKLIST**

### **Pre-Deployment**

- [ ] Environment variables configured
- [ ] Redis password set
- [ ] SSL certificates ready (production)
- [ ] Domain configured
- [ ] Database migrations ready

### **Deployment**

- [ ] Services built successfully
- [ ] Redis health check passed
- [ ] Application health check passed
- [ ] Database migrations completed
- [ ] Redis initialization completed

### **Post-Deployment**

- [ ] All endpoints accessible
- [ ] Redis statistics available
- [ ] Monitoring configured
- [ ] Logs being collected
- [ ] Backup strategy implemented

## 🚀 **QUICK START**

```bash
# 1. Clone repository
git clone <your-repo-url>
cd forex_to_telegram

# 2. Configure environment
cp .env.example .env
# Edit .env with your values

# 3. Start services
docker-compose up -d

# 4. Verify deployment
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/redis/stats

# 5. Monitor Redis
python scripts/redis_monitor.py --health
```

## 📞 **SUPPORT**

For deployment issues:

1. Check service logs: `docker-compose logs <service>`
2. Verify Redis connectivity: `docker-compose exec redis redis-cli ping`
3. Check application health: `curl http://localhost:8000/health`
4. Review Redis configuration: `docker-compose exec redis redis-cli CONFIG GET "*"`

---

**Redis deployment completed successfully!** 🚀

Your Forex Bot application is now running with enterprise-grade Redis integration, providing high-performance caching, real-time features, and robust session management.
