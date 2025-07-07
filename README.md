# Forex Bot - Telegram Bot для Forex Новостей

## Структура проекта

```
forex_bot_postgresql/
├── app/                    # Основной код приложения
│   ├── api/               # API маршруты
│   ├── bot/               # Telegram bot логика  
│   ├── database/          # Модели и подключение к БД
│   ├── scrapers/          # Скрейперы данных
│   ├── services/          # Бизнес-логика
│   └── utils/             # Утилиты
├── config/                # Конфигурационные файлы
├── docker/                # Docker файлы
├── docs/                  # Документация
├── logs/                  # Логи и результаты
├── scripts/               # Скрипты и утилиты
├── tests/                 # Тесты
├── alembic/              # Миграции БД
└── main.py               # Главный файл приложения
```

## Быстрый старт

### Локальная разработка

1. Установите зависимости:
```bash
pip install -r config/requirements.txt
```

2. Настройте переменные окружения в `.env`

3. Запустите приложение:
```bash
python main.py
```

### Docker

1. Соберите образ:
```bash
docker build -f docker/Dockerfile -t forex-bot .
```

2. Запустите с docker-compose:
```bash
docker-compose -f config/docker-compose.yml up
```

### Развертывание на Render

Используйте файлы конфигурации:
- `config/render.yaml` - базовая конфигурация
- `config/render_enhanced.yaml` - расширенная конфигурация

## Основные компоненты

- **main.py** - Точка входа приложения
- **app/bot/** - Telegram bot обработчики
- **app/scrapers/** - Парсинг новостей с Forex Factory
- **app/services/** - Бизнес-логика (уведомления, анализ)
- **scripts/** - Утилиты для обслуживания

## Тестирование

```bash
python -m pytest tests/ -v
```

## Документация

Подробная документация находится в папке `docs/`:
- `REFACTORING_REPORT.md` - Отчет о рефакторинге
- `PROJECT_STRUCTURE.md` - Структура проекта
- Другие руководства по развертыванию и использованию

## Логи

Все логи сохраняются в папке `logs/`:
- `app.log` - Основные логи приложения
- `error.log` - Логи ошибок
- `health.log` - Логи мониторинга

## Конфигурация

Основные настройки в `app/config.py`. Переменные окружения:
- `TELEGRAM_BOT_TOKEN` - Токен Telegram бота
- `DATABASE_URL` - URL подключения к БД
- `TIMEZONE` - Часовой пояс (по умолчанию Europe/Berlin)
