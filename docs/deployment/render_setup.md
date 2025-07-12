
# 🚀 Полное руководство по настройке Render для Telegram бота

## 📋 Содержание
1. [Настройка переменных окружения в Render](#настройка-переменных-окружения)
2. [Выполнение миграций базы данных](#выполнение-миграций)
3. [Деплой приложения](#деплой-приложения)
4. [Проверка работоспособности](#проверка-работоспособности)
5. [Диагностика проблем](#диагностика-проблем)

## 🔧 Настройка переменных окружения

### Через Dashboard Render

1. **Откройте ваш сервис в Render Dashboard**
   - Перейдите на https://dashboard.render.com
   - Выберите ваш сервис (Web Service или Background Worker)

2. **Перейдите в раздел Environment**
   - В левом меню нажмите **Environment**
   - Вы увидите секцию **Environment Variables**

3. **Добавьте необходимые переменные**
   
   Нажмите **+ Add Environment Variable** и добавьте:

   ```
   DATABASE_URL = postgresql://forex_user:0VGr0I02HDKaiVUVT21Z3ORnEi...
   BOT_TOKEN = ваш_токен_telegram_бота
   WEBHOOK_URL = https://ваш-домен.onrender.com/webhook
   ```

   **Важно**: 
   - `DATABASE_URL` - используйте External Database URL из вашей PostgreSQL базы на Render
   - `BOT_TOKEN` - получите от @BotFather в Telegram
   - `WEBHOOK_URL` - будет доступен после первого деплоя

4. **Сохраните изменения**
   - Выберите **Save, rebuild, and deploy** для полного обновления
   - Или **Save and deploy** если код не изменился

### Через .env файл (для bulk добавления)

1. **Создайте .env файл локально**
   ```bash
   DATABASE_URL=postgresql://forex_user:0VGr0I02HDKaiVUVT21Z3ORnEi...
   BOT_TOKEN=ваш_токен_telegram_бота
   WEBHOOK_URL=https://ваш-домен.onrender.com/webhook
   ```

2. **Загрузите в Render**
   - В разделе Environment нажмите **Add from .env**
   - Скопируйте содержимое вашего .env файла
   - Нажмите **Add Variables**

### Через Render API (программно)

```bash
# Установка переменной через API
curl -X PUT "https://api.render.com/v1/services/YOUR_SERVICE_ID/env-vars/DATABASE_URL" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"value": "postgresql://forex_user:0VGr0I02HDKaiVUVT21Z3ORnEi..."}'
```

## 🗄️ Выполнение миграций базы данных

### Автоматические миграции при деплое

1. **Добавьте команду миграции в Build Command**
   ```bash
   pip install -r config/requirements.txt && python -m alembic -c config/alembic.ini upgrade head
   ```

2. **Или в Start Command**
   ```bash
   python -m alembic -c config/alembic.ini upgrade head && python bot_runner.py
   ```

### Ручное выполнение миграций

1. **Локально (для тестирования)**
   ```bash
   # Перейдите в папку проекта
   cd ~/forex_bot_postgresql/
   
   # Выполните скрипт миграций
   chmod +x scripts/run_migrations.sh
   ./scripts/run_migrations.sh
   ```

2. **Через Render Shell**
   - В Dashboard откройте ваш сервис
   - Перейдите в **Shell** (если доступно)
   - Выполните команды миграции

### Проверка миграций

```bash
# Проверка текущей версии
python -m alembic -c config/alembic.ini current

# История миграций
python -m alembic -c config/alembic.ini history

# Проверка таблиц
python scripts/check_tables.py
```

## 🚀 Деплой приложения

### Настройка Build Settings

1. **Build Command**
   ```bash
   pip install -r config/requirements.txt
   ```

2. **Start Command**
   ```bash
   python bot_runner.py
   ```

3. **Environment**
   - Python Version: 3.11 (или выше)
   - Node.js: не требуется

### Настройка Auto-Deploy

1. **Включите Auto-Deploy**
   - В настройках сервиса включите **Auto-Deploy**
   - Выберите ветку для автоматического деплоя (обычно `main`)

2. **Deploy Hooks**
   - Pre-deploy: миграции базы данных
   - Post-deploy: проверка здоровья приложения

### Ручной деплой

1. **Через Dashboard**
   - Нажмите **Manual Deploy** в вашем сервисе
   - Выберите **Deploy latest commit**

2. **Через Git**
   ```bash
   git add .
   git commit -m "Update bot configuration"
   git push origin main
   ```

## ✅ Проверка работоспособности

### Автоматическая проверка

```bash
# Полная проверка готовности системы
python scripts/full_readiness.py

# Проверка переменных окружения
python scripts/check_render_env.py

# Проверка таблиц базы данных
python scripts/check_tables.py
```

### Проверка через Render Dashboard

1. **Логи приложения**
   - Перейдите в **Logs** вашего сервиса
   - Проверьте отсутствие ошибок при запуске

2. **Метрики**
   - Проверьте **Metrics** для мониторинга производительности
   - Убедитесь что приложение не перезапускается

3. **Events**
   - В разделе **Events** проверьте успешность деплоев

### Тестирование бота

1. **Проверка webhook**
   ```bash
   curl -X GET "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
   ```

2. **Тест сообщения боту**
   - Отправьте `/start` вашему боту в Telegram
   - Проверьте ответ и логи в Render

## 🔧 Диагностика проблем

### Проблемы с переменными окружения

**Симптомы:**
- Ошибки "Environment variable not found"
- Бот не может подключиться к базе данных

**Решения:**
1. Проверьте правильность названий переменных
2. Убедитесь что переменные сохранены в Render
3. Перезапустите сервис после изменения переменных

```bash
# Проверка переменных локально
python scripts/check_render_env.py
```

### Проблемы с базой данных

**Симптомы:**
- "Connection refused" ошибки
- "Table doesn't exist" ошибки
- Таймауты подключения

**Решения:**
1. Проверьте правильность DATABASE_URL
2. Убедитесь что база данных запущена
3. Выполните миграции

```bash
# Диагностика базы данных
python test_db_connection.py

# Выполнение миграций
./scripts/run_migrations.sh
```

### Проблемы с миграциями

**Симптомы:**
- "Alembic version not found"
- "Migration failed" ошибки
- Конфликты версий

**Решения:**
1. Проверьте конфигурацию Alembic
2. Сбросьте версию миграций если необходимо
3. Выполните миграции вручную

```bash
# Сброс версии Alembic (ОСТОРОЖНО!)
python -m alembic -c config/alembic.ini stamp head

# Принудительное выполнение миграций
python -m alembic -c config/alembic.ini upgrade head --sql
```

### Проблемы с Telegram API

**Симптомы:**
- "Invalid bot token" ошибки
- Webhook не работает
- Сообщения не доходят

**Решения:**
1. Проверьте валидность токена бота
2. Настройте webhook правильно
3. Проверьте доступность вашего домена

```bash
# Проверка токена бота
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"

# Настройка webhook
python setup_webhook.py
```

### Логи и мониторинг

**Просмотр логов в Render:**
1. Dashboard → Ваш сервис → Logs
2. Фильтрация по времени и уровню логов
3. Поиск по ключевым словам

**Полезные команды для логирования:**
```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# В коде бота
logger.info("Bot started successfully")
logger.error(f"Database error: {error}")
```

### Контакты для поддержки

- **Render Support**: https://render.com/docs
- **Telegram Bot API**: https://core.telegram.org/bots/api
- **PostgreSQL**: https://www.postgresql.org/docs/

## 📚 Дополнительные ресурсы

- [Render Environment Variables Documentation](https://render.com/docs/environment-variables)
- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

**Последнее обновление:** 8 июля 2025
**Версия:** 1.0
