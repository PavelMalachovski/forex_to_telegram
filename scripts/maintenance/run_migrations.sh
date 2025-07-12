
#!/bin/bash

# Скрипт для выполнения миграций базы данных

set -e  # Остановка при ошибке

echo "🔄 Запуск миграций базы данных для Telegram бота"
echo "=================================================="

# Проверяем наличие .env файла
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден!"
    echo "Создайте .env файл с DATABASE_URL"
    exit 1
fi

# Загружаем переменные окружения
source .env

# Проверяем наличие DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL не установлена в .env файле!"
    exit 1
fi

echo "✅ DATABASE_URL найдена"

# Проверяем наличие Alembic
if [ ! -f "config/alembic.ini" ]; then
    echo "❌ Файл alembic.ini не найден в папке config!"
    exit 1
fi

echo "✅ Конфигурация Alembic найдена"

# Проверяем подключение к базе данных
echo ""
echo "🔗 Проверка подключения к базе данных..."
python3 -c "
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    cursor.execute('SELECT version();')
    version = cursor.fetchone()
    print(f'✅ Подключение успешно! PostgreSQL: {version[0][:50]}...')
    cursor.close()
    conn.close()
except Exception as e:
    print(f'❌ Ошибка подключения: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Не удалось подключиться к базе данных!"
    exit 1
fi

# Проверяем текущую версию миграции
echo ""
echo "📋 Проверка текущего состояния миграций..."
python3 -m alembic -c config/alembic.ini current

# Показываем доступные миграции
echo ""
echo "📋 Доступные миграции:"
python3 -m alembic -c config/alembic.ini history

# Выполняем миграции
echo ""
echo "🚀 Выполнение миграций..."
python3 -m alembic -c config/alembic.ini upgrade head

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Миграции выполнены успешно!"
    
    # Проверяем результат
    echo ""
    echo "📊 Проверка созданных таблиц..."
    python3 scripts/check_tables.py
    
    echo ""
    echo "🎉 Миграции завершены успешно!"
    echo "Теперь можно запускать Telegram бота."
else
    echo ""
    echo "❌ Ошибка при выполнении миграций!"
    echo ""
    echo "🔧 Возможные решения:"
    echo "1. Проверьте подключение к базе данных"
    echo "2. Убедитесь что DATABASE_URL корректна"
    echo "3. Проверьте права доступа к базе данных"
    echo "4. Посмотрите логи выше для деталей ошибки"
    exit 1
fi
