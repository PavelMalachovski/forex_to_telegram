# Руководство по миграции на Enhanced Main

## Проблема
Приложение получает сигнал SIGTERM и останавливается по следующим причинам:

### 1. Основные причины SIGTERM на Render.com:
- **Health Check Failures**: Таймаут 5 секунд на запрос, 15 минут на деплой, 60 секунд для перезапуска
- **Превышение лимитов ресурсов**: OOM (нехватка памяти) - самая частая причина
- **Лимиты Starter плана**: 0.5 CPU, 512MB RAM может быть недостаточно
- **Zero-downtime deploys**: Старые инстансы получают SIGTERM после запуска новых

### 2. Текущее состояние:
- Используется старый `main.py` без обработки сигналов
- Нет мониторинга ресурсов
- Отсутствует автоматический перезапуск
- Недостаточно логирования для диагностики

## Решение

### Шаг 1: Переход на Enhanced Main
```bash
# Создать резервную копию
cp main.py main.py.backup
cp Dockerfile Dockerfile.backup
cp render.yaml render.yaml.backup

# Использовать новые файлы
cp Dockerfile.enhanced Dockerfile
cp render_enhanced.yaml render.yaml
```

### Шаг 2: Обновить настройки в Render Dashboard
1. Перейти в Service Settings
2. Изменить Start Command с `python main.py` на `python enhanced_main.py`
3. Изменить Health Check Path на `/health`
4. Обновить план с Starter на Standard (рекомендуется)

### Шаг 3: Настроить переменные окружения
Добавить в Render Dashboard:
```
ENHANCED_STABILITY=true
HEALTH_CHECK_ENABLED=true
GRACEFUL_SHUTDOWN_TIMEOUT=25
RESOURCE_MONITORING=true
```

### Шаг 4: Деплой
```bash
git add .
git commit -m "Migrate to enhanced stability system"
git push origin main
```

## Улучшения Enhanced Main

### 1. Обработка сигналов
- Перехват SIGTERM/SIGINT с детальным логированием
- Graceful shutdown с таймаутом 25 секунд
- Логирование stack trace и состояния системы при получении сигнала

### 2. Мониторинг ресурсов
- Отслеживание CPU, памяти, потоков каждые 30 секунд
- Предупреждения при высоком использовании ресурсов
- Логирование в JSON формате для анализа

### 3. Health Checks
- Расширенный `/health` endpoint с проверкой БД, бота, ресурсов
- Простой `/ping` endpoint для базовых проверок
- Информация об uptime и режиме работы

### 4. Автоматический перезапуск
- Watchdog script для локального использования
- Systemd service для серверов
- Docker restart policies

## Диагностика проблем

### Проверить логи
```bash
# Основные логи приложения
tail -f logs/enhanced_app.log

# Мониторинг ресурсов
tail -f logs/resource_monitor.log

# Использование ресурсов в JSON
tail -f logs/resource_usage.json
```

### Тестирование health checks
```bash
# Проверить health endpoint
curl -f http://localhost:5000/health

# Простая проверка
curl -f http://localhost:5000/ping
```

### Мониторинг в реальном времени
```bash
# Запустить мониторинг ресурсов
python scripts/resource_monitor.py

# Запустить watchdog (для локального использования)
./scripts/watchdog.sh
```

## Настройка для разных платформ

### Render.com (рекомендуется)
- Использовать `render_enhanced.yaml`
- Обновить план до Standard
- Настроить уведомления в Dashboard

### Docker Compose
```yaml
version: '3.8'
services:
  forex-bot:
    build:
      context: .
      dockerfile: Dockerfile.enhanced
    restart: unless-stopped
    environment:
      - ENHANCED_STABILITY=true
      - RESOURCE_MONITORING=true
```

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: forex-bot
        image: forex-bot:enhanced
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 30
```

### Systemd (для VPS)
```bash
# Установить service
sudo cp forex_bot.service /etc/systemd/system/
sudo systemctl enable forex-bot
sudo systemctl start forex-bot

# Проверить статус
sudo systemctl status forex-bot
```

## Мониторинг и алерты

### Render Dashboard
1. Settings → Notifications
2. Включить уведомления о сбоях деплоя
3. Включить уведомления о перезапуске сервиса

### Внешний мониторинг
- Настроить webhook уведомления
- Использовать Render Metrics API
- Интеграция с DataDog/New Relic

### Паттерны в логах для мониторинга
```bash
# Высокое использование памяти
grep "HIGH.*MEMORY" logs/resource_monitor.log

# Получение сигналов
grep "SIGTERM\|SIGKILL" logs/enhanced_app.log

# Сбои health checks
grep "health.*fail" logs/enhanced_app.log
```

## Оптимизация производительности

### Память
- Использовать connection pooling для БД
- Реализовать кэширование запросов
- Регулярно очищать временные файлы
- Мониторить утечки памяти

### CPU
- Использовать async/await для I/O операций
- Реализовать throttling запросов
- Оптимизировать запросы к БД
- Использовать фоновые задачи для тяжелых операций

## Поддержка и эскалация

### При проблемах с Render
- Использовать "Contact Support" в dashboard
- Указать имя сервиса и логи ошибок
- Упомянуть "signal 9" или "OOM" проблемы
- Запросить рекомендации по типу инстанса

### Сообщество
- Render Community Forum
- GitHub Issues для багов приложения
- Stack Overflow для технических вопросов

## Регулярное обслуживание

### Ежедневно
- Проверять логи приложения на ошибки
- Мониторить тренды использования ресурсов
- Проверять ответы health check

### Еженедельно
- Анализировать паттерны использования ресурсов
- Обновлять зависимости при необходимости
- Тестировать процедуры backup и recovery

### Ежемесячно
- Анализировать метрики производительности
- Пересматривать и обновлять пороги мониторинга
- Планировать обновления мощности при необходимости
