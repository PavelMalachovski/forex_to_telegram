# Deployment Guide for Forex Bot

## Решение проблемы webhook/polling конфликта

Этот гайд поможет решить ошибку: **"can't use getUpdates method while webhook is active; use deleteWebhook to delete the webhook first"**

## Быстрое решение

### 1. Удалить существующий webhook
```bash
python manage_webhook.py delete
```

### 2. Проверить статус
```bash
python manage_webhook.py status
```
Должно показать: `URL: Not set`

### 3. Для локальной разработки
```bash
# Убедитесь, что webhook удален
python manage_webhook.py delete

# Запустите в режиме polling
python main.py
```

### 4. Для продакшена на Render.com
```bash
# Установите webhook для Render.com
python manage_webhook.py set-render
```

## Подробное руководство по деплою

### Локальная разработка

1. **Настройка окружения**:
```bash
# Клонируйте репозиторий
git clone <repository>
cd forex_bot_postgresql

# Установите зависимости
pip install -r requirements.txt

# Создайте .env файл
cp .env.example .env
```

2. **Настройте .env файл**:
```env
TELEGRAM_BOT_TOKEN=your_real_bot_token_here
DATABASE_URL=sqlite:///forex_bot.db
# Не устанавливайте WEBHOOK_MODE для локальной разработки
```

3. **Убедитесь, что webhook отключен**:
```bash
python manage_webhook.py delete
python manage_webhook.py status
```

4. **Запустите приложение**:
```bash
python main.py
```

Приложение автоматически запустится в режиме polling.

### Деплой на Render.com

1. **Подготовка репозитория**:
   - Убедитесь, что все файлы закоммичены в git
   - Файл `render.yaml` уже настроен

2. **Создание сервиса на Render.com**:
   - Подключите ваш GitHub репозиторий
   - Render автоматически использует `render.yaml`

3. **Настройка переменных окружения** в Render Dashboard:
```env
DATABASE_URL=<автоматически создается Render>
TELEGRAM_BOT_TOKEN=your_real_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id
RENDER_EXTERNAL_HOSTNAME=<автоматически устанавливается>
```

4. **Деплой**:
   - Render автоматически задеплоит приложение
   - Приложение автоматически определит режим webhook
   - Webhook будет установлен автоматически

5. **Проверка деплоя**:
```bash
curl https://your-app-name.onrender.com/health
```

Ответ должен содержать:
```json
{
  "status": "healthy",
  "mode": "webhook",
  "bot_available": true
}
```

## Управление webhook

### Команды управления

```bash
# Показать текущий статус webhook
python manage_webhook.py status

# Установить webhook для Render.com
python manage_webhook.py set-render

# Установить кастомный webhook
python manage_webhook.py set https://your-domain.com/webhook

# Удалить webhook
python manage_webhook.py delete
```

### Автоматическое определение режима

Приложение автоматически определяет режим работы:

- **Polling режим** (локальная разработка):
  - Когда `RENDER_EXTERNAL_HOSTNAME` не установлен
  - Когда `WEBHOOK_MODE` не равен `true`

- **Webhook режим** (продакшен):
  - Когда `RENDER_EXTERNAL_HOSTNAME` установлен (Render.com)
  - Когда `WEBHOOK_MODE=true` установлен вручную

## Troubleshooting

### Проблема: "can't use getUpdates method while webhook is active"

**Решение**:
```bash
# 1. Удалите webhook
python manage_webhook.py delete

# 2. Проверьте статус
python manage_webhook.py status

# 3. Для локальной разработки - запустите polling
python main.py

# 4. Для продакшена - установите webhook
python manage_webhook.py set-render
```

### Проблема: Bot не отвечает в продакшене

**Проверки**:
1. Убедитесь, что webhook установлен:
```bash
python manage_webhook.py status
```

2. Проверьте health endpoint:
```bash
curl https://your-app-name.onrender.com/health
```

3. Проверьте логи в Render Dashboard

### Проблема: Database connection failed

**Решение**:
1. Убедитесь, что PostgreSQL сервис создан в Render
2. Проверьте переменную `DATABASE_URL`
3. Убедитесь, что база данных доступна

### Проблема: Invalid bot token

**Решение**:
1. Получите новый токен от @BotFather
2. Обновите `TELEGRAM_BOT_TOKEN` в настройках Render
3. Перезапустите сервис

## Мониторинг

### Health Check
```bash
curl https://your-app-name.onrender.com/health
```

### API Status
```bash
curl https://your-app-name.onrender.com/api/status
```

### Webhook Status
```bash
python manage_webhook.py status
```

## Переключение между режимами

### С polling на webhook
```bash
# 1. Остановите polling приложение (Ctrl+C)
# 2. Установите webhook
python manage_webhook.py set https://your-domain.com/webhook
# 3. Запустите в webhook режиме
WEBHOOK_MODE=true python main.py
```

### С webhook на polling
```bash
# 1. Удалите webhook
python manage_webhook.py delete
# 2. Запустите в polling режиме
python main.py
```

## Архитектура

```
┌─────────────────┐    ┌─────────────────┐
│   Development   │    │   Production    │
│   (Polling)     │    │   (Webhook)     │
├─────────────────┤    ├─────────────────┤
│ • Local testing │    │ • Render.com    │
│ • SQLite DB     │    │ • PostgreSQL    │
│ • Bot polling   │    │ • Webhook       │
│ • Flask API     │    │ • Flask server  │
└─────────────────┘    └─────────────────┘
```

## Заключение

Новая архитектура автоматически решает конфликт webhook/polling:

1. **Автоматическое определение режима** на основе окружения
2. **Единый entry point** (`main.py`) для обоих режимов
3. **Утилиты управления webhook** для ручного контроля
4. **Улучшенная обработка ошибок** и логирование
5. **Подробная документация** для troubleshooting

Теперь бот будет корректно работать как в разработке (polling), так и в продакшене (webhook) без конфликтов.
