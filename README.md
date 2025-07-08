# Forex News Telegram Bot

Telegram бот для получения новостей и экономических событий с ForexFactory с поддержкой уведомлений и персонализированных настроек.

## 🚀 Быстрый старт

### Метод 1: Автоматический запуск (рекомендуется)

```bash
# Клонирование и установка
git clone <repository-url>
cd forex_bot_postgresql
pip install -r requirements.txt

# Настройка
cp .env.example .env
# Отредактируйте .env файл - установите TELEGRAM_BOT_TOKEN

# Быстрый запуск (интерактивный режим)
python quick_start.py

# Или автоматический запуск
python quick_start.py auto
```

### Метод 2: Ручная настройка

#### 1. Клонирование и установка

```bash
git clone <repository-url>
cd forex_bot_postgresql
pip install -r requirements.txt
```

#### 2. Настройка переменных окружения

Скопируйте файл с примером настроек:
```bash
cp .env.example .env
```

Отредактируйте `.env` файл:
```bash
# Обязательные настройки
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
BOT_MODE=polling  # для разработки
DATABASE_URL=postgresql://user:password@localhost:5432/forex_bot

# Для production (webhook режим)
BOT_MODE=webhook
RENDER_EXTERNAL_URL=https://your-app.onrender.com
```

#### 3. Инициализация базы данных

```bash
python -c "from app.database.connection import init_database; init_database()"
```

#### 4. Запуск бота

**Для разработки (polling режим):**
```bash
python quick_start.py polling
# или
BOT_MODE=polling python bot_runner.py
```

**Для production (webhook режим):**
```bash
python quick_start.py webhook
# или
BOT_MODE=webhook python production_scheduler.py
```

## 📋 Режимы работы

### Polling режим (для разработки)

- **Использование**: Локальная разработка и тестирование
- **Преимущества**: Простота настройки, не требует публичного URL
- **Недостатки**: Постоянные запросы к Telegram API, не подходит для production

```bash
# Установка режима
export BOT_MODE=polling

# Запуск
python bot_runner.py
```

### Webhook режим (для production)

- **Использование**: Production деплой на серверах
- **Преимущества**: Эффективность, мгновенная доставка сообщений
- **Недостатки**: Требует HTTPS URL, более сложная настройка

```bash
# Установка режима
export BOT_MODE=webhook
export RENDER_EXTERNAL_URL=https://your-app.onrender.com

# Запуск
python production_scheduler.py
```

## 🔧 Управление и утилиты

### Quick Start (рекомендуется)

Используйте `quick_start.py` для простого управления ботом:

```bash
# Интерактивный режим
python quick_start.py

# Прямые команды
python quick_start.py polling    # Запуск в polling режиме
python quick_start.py webhook    # Запуск в webhook режиме
python quick_start.py auto       # Автоматический запуск по BOT_MODE
python quick_start.py fix        # Исправление конфликтов
python quick_start.py status     # Проверка статуса
```

### Управление Webhook

Используйте `webhook_manager.py` для управления webhook:

```bash
python webhook_manager.py status                    # Проверка статуса
python webhook_manager.py set                       # Установка webhook
python webhook_manager.py delete                    # Удаление webhook
python webhook_manager.py reset                     # Сброс webhook
python webhook_manager.py set --url https://...     # Кастомный URL
```

### Исправление конфликтов

Используйте `fix_409_conflict.py` для решения проблем:

```bash
python fix_409_conflict.py diagnose        # Диагностика
python fix_409_conflict.py fix             # Интерактивное исправление
python fix_409_conflict.py delete-webhook  # Принудительное удаление
```

## ⚙️ Переменные окружения

### Обязательные

| Переменная | Описание | Пример |
|------------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `BOT_MODE` | Режим работы: `polling` или `webhook` | `polling` |
| `DATABASE_URL` | URL подключения к базе данных | `postgresql://user:pass@localhost/db` |

### Для webhook режима

| Переменная | Описание | Пример |
|------------|----------|---------|
| `TELEGRAM_WEBHOOK_URL` | Полный URL webhook | `https://domain.com/webhook` |
| `RENDER_EXTERNAL_URL` | URL Render сервиса (автоматически добавляет /webhook) | `https://app.onrender.com` |
| `LOCAL_WEBHOOK_URL` | Локальный webhook URL (для ngrok) | `https://abc123.ngrok.io` |

### Дополнительные

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `PORT` | Порт для Flask сервера | `8000` |
| `HOST` | Хост для Flask сервера | `0.0.0.0` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `LOG_DIR` | Директория для логов | `./logs` |
| `DEBUG` | Режим отладки | `False` |

## 🐛 Решение проблем

### Ошибка 409: Conflict webhook/polling

**Проблема**: `Error code: 409. Description: Conflict: can't use getUpdates method while webhook is active`

**Автоматическое решение**:
```bash
# Диагностика проблемы
python fix_409_conflict.py diagnose

# Интерактивное исправление
python fix_409_conflict.py fix

# Принудительное удаление webhook
python fix_409_conflict.py delete-webhook
```

**Ручное решение**:
```bash
# Удалите webhook для polling режима
python webhook_manager.py delete
export BOT_MODE=polling

# Или переключитесь на webhook режим
export BOT_MODE=webhook
python webhook_manager.py set
```

### Webhook не получает обновления

**Проверьте**:
1. URL доступен по HTTPS
2. Сертификат SSL валидный
3. Endpoint `/webhook` отвечает на POST запросы

```bash
# Проверка статуса
python webhook_manager.py status

# Сброс webhook
python webhook_manager.py reset
```

### База данных недоступна

**Проверьте**:
1. Правильность `DATABASE_URL`
2. Доступность сервера БД
3. Права доступа пользователя

```bash
# Тест подключения
python -c "from app.database.connection import test_connection; test_connection()"
```

### Бот не отвечает на команды

**Проверьте**:
1. Токен бота корректный
2. Бот добавлен в чат
3. Логи на наличие ошибок

```bash
# Проверка логов
tail -f logs/bot.log
```

## 📁 Структура проекта

```
forex_bot_postgresql/
├── app/                          # Основное приложение
│   ├── bot/                      # Telegram bot логика
│   │   ├── handlers.py          # Обработчики команд
│   │   ├── keyboards.py         # Клавиатуры
│   │   └── utils/               # Утилиты бота
│   ├── database/                # База данных
│   │   ├── models.py           # SQLAlchemy модели
│   │   └── connection.py       # Подключение к БД
│   ├── services/               # Бизнес логика
│   │   ├── news_service.py     # Сервис новостей
│   │   ├── user_service.py     # Сервис пользователей
│   │   └── notification_service.py # Уведомления
│   └── utils/                  # Общие утилиты
├── logs/                       # Логи приложения
├── bot_runner.py              # Универсальный запускатель
├── production_scheduler.py    # Production запускатель
├── webhook_manager.py         # Управление webhook
├── setup_webhook.py          # Старый скрипт webhook (deprecated)
├── .env.example              # Пример настроек
└── README.md                 # Документация
```

## 🚀 Деплой

### Render.com

1. **Создайте Web Service** на Render.com
2. **Настройте переменные окружения**:
   ```
   BOT_MODE=webhook
   TELEGRAM_BOT_TOKEN=your_token
   DATABASE_URL=your_postgres_url
   ```
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `python production_scheduler.py`

### Heroku

1. **Создайте приложение**:
   ```bash
   heroku create your-app-name
   ```

2. **Настройте переменные**:
   ```bash
   heroku config:set BOT_MODE=webhook
   heroku config:set TELEGRAM_BOT_TOKEN=your_token
   heroku config:set DATABASE_URL=your_postgres_url
   ```

3. **Деплой**:
   ```bash
   git push heroku main
   ```

### VPS/Dedicated Server

1. **Установите зависимости**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Настройте systemd service** (`/etc/systemd/system/forex-bot.service`):
   ```ini
   [Unit]
   Description=Forex News Telegram Bot
   After=network.target

   [Service]
   Type=simple
   User=your-user
   WorkingDirectory=/path/to/forex_bot_postgresql
   Environment=BOT_MODE=webhook
   Environment=TELEGRAM_BOT_TOKEN=your_token
   Environment=DATABASE_URL=your_db_url
   ExecStart=/usr/bin/python3 production_scheduler.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

3. **Запустите сервис**:
   ```bash
   sudo systemctl enable forex-bot
   sudo systemctl start forex-bot
   ```

## 🔄 Переключение между режимами

### С polling на webhook

```bash
# 1. Остановите polling бота
# Ctrl+C или kill процесс

# 2. Установите webhook
export BOT_MODE=webhook
python webhook_manager.py set

# 3. Запустите в webhook режиме
python production_scheduler.py
```

### С webhook на polling

```bash
# 1. Удалите webhook
python webhook_manager.py delete

# 2. Установите polling режим
export BOT_MODE=polling

# 3. Запустите в polling режиме
python bot_runner.py
```

## 📊 Мониторинг

### Проверка статуса приложения

```bash
# Webhook статус
curl https://your-app.com/status

# Health check
curl https://your-app.com/health

# Webhook info
python webhook_manager.py status
```

### Логи

```bash
# Просмотр логов
tail -f logs/bot.log

# Поиск ошибок
grep ERROR logs/bot.log

# Статистика webhook
grep "webhook" logs/bot.log | tail -20
```

## 🤝 Разработка

### Локальная разработка

1. **Используйте polling режим**:
   ```bash
   export BOT_MODE=polling
   python bot_runner.py
   ```

2. **Для тестирования webhook локально** (с ngrok):
   ```bash
   # Запустите ngrok
   ngrok http 8000
   
   # Установите переменные
   export BOT_MODE=webhook
   export LOCAL_WEBHOOK_URL=https://abc123.ngrok.io
   
   # Настройте webhook
   python webhook_manager.py set
   
   # Запустите приложение
   python bot_runner.py
   ```

### Тестирование

```bash
# Тест подключения к БД
python -c "from app.database.connection import test_connection; test_connection()"

# Тест импортов
python -c "from app.config import config; print('Config OK')"

# Тест бота (dry run)
BOT_MODE=polling python bot_runner.py --dry-run
```

## 📝 Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Запуск бота и регистрация |
| `/help` | Справка по командам |
| `/news [date] [impact]` | Новости за дату |
| `/today` | Новости на сегодня |
| `/tomorrow` | Новости на завтра |
| `/week` | Новости на неделю |
| `/calendar` | Календарь выбора даты |
| `/preferences` | Настройки пользователя |
| `/status` | Статус пользователя |

## 🔐 Безопасность

- Никогда не коммитьте `.env` файл
- Используйте переменные окружения для секретов
- Регулярно обновляйте зависимости
- Используйте HTTPS для webhook
- Ограничьте доступ к базе данных

## 📞 Поддержка

При возникновении проблем:

1. **Проверьте логи**: `tail -f logs/bot.log`
2. **Проверьте статус webhook**: `python webhook_manager.py status`
3. **Проверьте переменные окружения**: `env | grep -E "(BOT_|TELEGRAM_|DATABASE_)"`
4. **Перезапустите с чистого листа**:
   ```bash
   python webhook_manager.py delete
   export BOT_MODE=polling
   python bot_runner.py
   ```

## 📄 Лицензия

MIT License - см. файл LICENSE для деталей.
