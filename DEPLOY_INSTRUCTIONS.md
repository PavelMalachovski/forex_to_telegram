# Инструкции по деплою Forex Bot

## Исправленные проблемы после рефакторинга

### 1. Проблема с Dockerfile для Render
**Проблема**: Render искал Dockerfile в корне проекта, но после рефакторинга он находился в папке `docker/`.

**Решение**: Созданы симлинки в корне проекта:
- `Dockerfile` → `docker/Dockerfile.production`
- `Dockerfile.enhanced` → `docker/Dockerfile.enhanced`
- `Procfile` → `docker/Procfile`

### 2. Обновленные конфигурационные файлы
- `config/render.yaml`: `dockerfilePath: ./Dockerfile`
- `config/render_enhanced.yaml`: `dockerfilePath: ./Dockerfile.enhanced`
- `config/docker-compose.yml`: обновлен контекст сборки

### 3. Созданы отсутствующие файлы
- `production_scheduler.py` (копия main.py)
- `enhanced_main.py` (копия main.py)

## Деплой на Render

### Вариант 1: Стандартный деплой
```bash
# Используйте config/render.yaml
# Dockerfile: ./Dockerfile (симлинк на docker/Dockerfile.production)
# Health check: /ping
```

### Вариант 2: Расширенный деплой (рекомендуется)
```bash
# Используйте config/render_enhanced.yaml
# Dockerfile: ./Dockerfile.enhanced (симлинк на docker/Dockerfile.enhanced)
# Health check: /health
# План: standard (для лучшей стабильности)
```

## Локальная разработка

### Docker Compose
```bash
cd config/
docker-compose up --build
```

### Прямой запуск
```bash
python main.py
```

## Переменные окружения

Обязательные переменные для Render:
- `DATABASE_URL` - URL PostgreSQL базы данных
- `TELEGRAM_BOT_TOKEN` - токен Telegram бота
- `TELEGRAM_CHAT_ID` - ID чата для уведомлений
- `REDIS_URL` - URL Redis (опционально)
- `OPENAI_API_KEY` - ключ OpenAI API
- `API_KEY` - внутренний API ключ

## Структура проекта после рефакторинга

```
forex_bot_postgresql/
├── app/                    # Основной код приложения
├── config/                 # Конфигурационные файлы
├── docker/                 # Docker файлы
├── docs/                   # Документация
├── scripts/                # Вспомогательные скрипты
├── tests/                  # Тесты
├── Dockerfile              # Симлинк на docker/Dockerfile.production
├── Dockerfile.enhanced     # Симлинк на docker/Dockerfile.enhanced
├── Procfile               # Симлинк на docker/Procfile
├── main.py                # Основной файл запуска
├── production_scheduler.py # Файл для продакшн деплоя
└── enhanced_main.py       # Расширенный файл запуска
```

## Проверка перед деплоем

1. **Проверка импортов**:
```bash
python3 -c "
import sys
sys.path.insert(0, 'app')
from app.config import Config
from app.bot.handlers import BotHandlers
print('Все импорты работают!')
"
```

2. **Проверка симлинков**:
```bash
ls -la Dockerfile* Procfile
```

3. **Проверка конфигурационных файлов**:
```bash
grep -r "dockerfilePath" config/
```

## Troubleshooting

### Ошибка "no such file or directory" при деплое
- Убедитесь, что симлинки созданы в корне проекта
- Проверьте, что пути в render.yaml правильные

### Ошибки импорта
- Убедитесь, что PYTHONPATH=/app установлен
- Проверьте структуру папок app/

### Проблемы с зависимостями
- Используйте правильный requirements файл:
  - `config/requirements.production.txt` для продакшн
  - `config/requirements_enhanced.txt` для расширенной версии
