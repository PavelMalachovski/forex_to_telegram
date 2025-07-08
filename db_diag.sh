
#!/bin/bash

# Скрипт диагностики подключения к PostgreSQL на Render
# Автор: AI Assistant
# Использование: ./db_diag.sh

echo "🔧 Диагностика подключения к PostgreSQL на Render"
echo "=================================================="

# Проверяем наличие DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ОШИБКА: Переменная окружения DATABASE_URL не установлена!"
    echo ""
    echo "Установите DATABASE_URL одним из способов:"
    echo "1. export DATABASE_URL='postgresql://user:password@host:port/database'"
    echo "2. Создайте файл .env с DATABASE_URL=..."
    echo "3. Добавьте DATABASE_URL в переменные окружения Render"
    exit 1
fi

echo "✅ DATABASE_URL найдена"

# Извлекаем компоненты из DATABASE_URL
HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
if [ -z "$PORT" ]; then
    PORT=5432
fi

echo "🔍 Анализ подключения:"
echo "   Хост: $HOST"
echo "   Порт: $PORT"

# Проверяем доступность хоста
echo ""
echo "🌐 Проверка доступности хоста..."
if command -v ping >/dev/null 2>&1; then
    if ping -c 1 -W 5 "$HOST" >/dev/null 2>&1; then
        echo "✅ Хост $HOST доступен"
    else
        echo "⚠️  Хост $HOST недоступен через ping (это нормально для некоторых серверов)"
    fi
else
    echo "⚠️  Команда ping недоступна"
fi

# Проверяем доступность порта
echo ""
echo "🔌 Проверка доступности порта..."
if command -v nc >/dev/null 2>&1; then
    if nc -z -w5 "$HOST" "$PORT" 2>/dev/null; then
        echo "✅ Порт $PORT на хосте $HOST доступен"
    else
        echo "❌ Порт $PORT на хосте $HOST недоступен"
    fi
elif command -v telnet >/dev/null 2>&1; then
    if timeout 5 telnet "$HOST" "$PORT" </dev/null 2>/dev/null | grep -q "Connected"; then
        echo "✅ Порт $PORT на хосте $HOST доступен"
    else
        echo "❌ Порт $PORT на хосте $HOST недоступен"
    fi
else
    echo "⚠️  Инструменты для проверки порта недоступны (nc, telnet)"
fi

# Устанавливаем psycopg2 если не установлен
echo ""
echo "📦 Проверка зависимостей..."
if ! python3 -c "import psycopg2" 2>/dev/null; then
    echo "📥 Установка psycopg2-binary..."
    pip install -q psycopg2-binary
    if [ $? -eq 0 ]; then
        echo "✅ psycopg2-binary установлен"
    else
        echo "❌ Ошибка установки psycopg2-binary"
        exit 1
    fi
else
    echo "✅ psycopg2 уже установлен"
fi

# Запускаем тест подключения
echo ""
echo "🧪 Запуск теста подключения к базе данных..."
python3 test_db_connection.py

# Проверяем результат
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Диагностика завершена успешно!"
    echo "   Ваша база данных настроена правильно и доступна."
else
    echo ""
    echo "❌ Диагностика выявила проблемы."
    echo "   Проверьте инструкции в README_DB_SETUP.md"
fi

echo ""
echo "📚 Дополнительные команды для диагностики:"
echo "   - Проверить переменные окружения: env | grep DATABASE"
echo "   - Подключиться через psql: psql \$DATABASE_URL"
echo "   - Проверить логи Render: в Dashboard -> Logs"
