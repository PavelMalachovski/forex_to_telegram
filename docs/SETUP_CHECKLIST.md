# 📋 Forex Bot Setup Checklist

## ✅ Быстрая настройка (5 минут)

### 1. Получите токен бота
- [ ] Перейдите к [@BotFather](https://t.me/botfather) в Telegram
- [ ] Создайте нового бота или используйте существующий
- [ ] Скопируйте токен (формат: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### 2. Настройте конфигурацию
- [ ] Скопируйте пример: `cp .env.example .env`
- [ ] Откройте `.env` файл в редакторе
- [ ] Замените `your_telegram_bot_token_here` на ваш реальный токен
- [ ] Выберите режим: `BOT_MODE=polling` (разработка) или `BOT_MODE=webhook` (production)

### 3. Запустите бота
```bash
# Простейший способ
python quick_start.py

# Или выберите режим напрямую
python quick_start.py polling    # для разработки
python quick_start.py webhook    # для production
```

## 🔧 Детальная настройка

### Для разработки (Polling режим)

#### Конфигурация .env:
```bash
TELEGRAM_BOT_TOKEN=ваш_токен_здесь
BOT_MODE=polling
DATABASE_URL=sqlite:///./forex_bot.db
```

#### Запуск:
- [ ] `python quick_start.py polling`
- [ ] Или: `python bot_runner.py`

### Для production (Webhook режим)

#### Конфигурация .env:
```bash
TELEGRAM_BOT_TOKEN=ваш_токен_здесь
BOT_MODE=webhook
RENDER_EXTERNAL_URL=https://your-app.onrender.com
# или
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook
```

#### Запуск:
- [ ] `python quick_start.py webhook`
- [ ] Или: `python production_scheduler.py`

## 🚨 Решение проблемы 409

Если получаете ошибку: `Error code: 409. Description: Conflict: can't use getUpdates method while webhook is active`

### Автоматическое исправление:
- [ ] `python fix_409_conflict.py fix`

### Ручное исправление:
- [ ] `python webhook_manager.py delete` (удалить webhook)
- [ ] `export BOT_MODE=polling` (установить polling режим)
- [ ] `python bot_runner.py` (запустить бота)

## 🔍 Диагностика

### Проверка статуса:
- [ ] `python webhook_manager.py status` - статус webhook
- [ ] `python quick_start.py status` - общий статус
- [ ] `python fix_409_conflict.py diagnose` - диагностика конфликтов

### Проверка логов:
- [ ] `tail -f logs/bot.log` - просмотр логов в реальном времени
- [ ] `grep ERROR logs/bot.log` - поиск ошибок

## 🌐 Деплой на Render.com

### 1. Подготовка:
- [ ] Создайте аккаунт на [Render.com](https://render.com)
- [ ] Подключите ваш GitHub репозиторий

### 2. Настройка Web Service:
- [ ] **Build Command**: `pip install -r requirements.txt`
- [ ] **Start Command**: `python production_scheduler.py`

### 3. Переменные окружения:
- [ ] `BOT_MODE=webhook`
- [ ] `TELEGRAM_BOT_TOKEN=ваш_токен`
- [ ] `DATABASE_URL=ваш_postgresql_url`

### 4. После деплоя:
- [ ] Скопируйте URL вашего приложения
- [ ] Добавьте в .env: `RENDER_EXTERNAL_URL=https://your-app.onrender.com`
- [ ] Webhook настроится автоматически

## 🔄 Переключение режимов

### С Polling на Webhook:
- [ ] Остановите polling бота (Ctrl+C)
- [ ] `python webhook_manager.py set`
- [ ] Измените в .env: `BOT_MODE=webhook`
- [ ] `python production_scheduler.py`

### С Webhook на Polling:
- [ ] `python webhook_manager.py delete`
- [ ] Измените в .env: `BOT_MODE=polling`
- [ ] `python bot_runner.py`

## 🧪 Тестирование

### Проверка системы:
- [ ] `python test_webhook_system.py` - тест всех компонентов

### Проверка бота:
- [ ] Отправьте `/start` боту в Telegram
- [ ] Попробуйте команды: `/help`, `/today`, `/news`
- [ ] Проверьте логи на ошибки

## 📚 Полезные команды

### Управление webhook:
```bash
python webhook_manager.py status    # Проверить статус
python webhook_manager.py set       # Установить webhook
python webhook_manager.py delete    # Удалить webhook
python webhook_manager.py reset     # Сбросить webhook
```

### Быстрый запуск:
```bash
python quick_start.py              # Интерактивный режим
python quick_start.py polling      # Polling режим
python quick_start.py webhook      # Webhook режим
python quick_start.py auto         # Автоматический режим
python quick_start.py fix          # Исправить проблемы
```

### Исправление проблем:
```bash
python fix_409_conflict.py diagnose        # Диагностика
python fix_409_conflict.py fix             # Интерактивное исправление
python fix_409_conflict.py delete-webhook  # Удалить webhook
```

## ❗ Частые ошибки

### "TELEGRAM_BOT_TOKEN not configured"
- [ ] Проверьте .env файл
- [ ] Убедитесь что токен не содержит пробелов
- [ ] Токен должен быть в формате: `123456:ABC-DEF...`

### "No webhook URL configured"
- [ ] Для webhook режима нужен публичный HTTPS URL
- [ ] Установите `RENDER_EXTERNAL_URL` или `TELEGRAM_WEBHOOK_URL`
- [ ] Для локальной разработки используйте ngrok

### "Webhook не получает обновления"
- [ ] Проверьте что URL доступен по HTTPS
- [ ] `python webhook_manager.py reset`
- [ ] Проверьте логи на ошибки

### "Database connection failed"
- [ ] Проверьте `DATABASE_URL` в .env
- [ ] Для локальной разработки используйте SQLite
- [ ] Убедитесь что PostgreSQL сервер запущен

## 🎯 Готово к работе!

После выполнения чек-листа ваш бот должен:
- [ ] ✅ Отвечать на команды в Telegram
- [ ] ✅ Работать без ошибок 409
- [ ] ✅ Логировать активность
- [ ] ✅ Быть готовым к production деплою

## 📞 Получение помощи

Если что-то не работает:

1. **Проверьте логи**: `tail -f logs/bot.log`
2. **Запустите диагностику**: `python fix_409_conflict.py diagnose`
3. **Сбросьте настройки**: `python webhook_manager.py delete && python quick_start.py polling`
4. **Прочитайте документацию**: `README.md` и `CONFLICT_409_SOLUTION.md`

---

**💡 Совет**: Используйте `python quick_start.py` для интерактивной настройки - это самый простой способ!
