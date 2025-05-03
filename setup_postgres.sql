-- PostgreSQL Setup Script for Forex Bot
-- Этот скрипт создает пользователя и базу данных для Forex Bot

-- Подключитесь к PostgreSQL как суперпользователь (postgres) и выполните этот скрипт
-- Команда: psql -U postgres -f setup_postgres.sql

-- 1. Создание пользователя для приложения
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'forex_user') THEN
        CREATE ROLE forex_user WITH LOGIN PASSWORD 'forex_password_123';
        RAISE NOTICE 'Пользователь forex_user создан успешно';
    ELSE
        RAISE NOTICE 'Пользователь forex_user уже существует';
    END IF;
END
$$;

-- 2. Предоставление прав на создание баз данных
ALTER ROLE forex_user CREATEDB;

-- 3. Создание базы данных
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'forex_bot') THEN
        PERFORM dblink_exec('dbname=postgres', 'CREATE DATABASE forex_bot OWNER forex_user');
        RAISE NOTICE 'База данных forex_bot создана успешно';
    ELSE
        RAISE NOTICE 'База данных forex_bot уже существует';
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        -- Если dblink недоступен, используем альтернативный метод
        RAISE NOTICE 'Создайте базу данных вручную: CREATE DATABASE forex_bot OWNER forex_user;';
END
$$;

-- 4. Подключение к созданной базе данных и настройка прав
\c forex_bot

-- 5. Предоставление всех прав на базу данных
GRANT ALL PRIVILEGES ON DATABASE forex_bot TO forex_user;

-- 6. Предоставление прав на схему public
GRANT ALL ON SCHEMA public TO forex_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO forex_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO forex_user;

-- 7. Установка прав по умолчанию для будущих объектов
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO forex_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO forex_user;

-- 8. Создание расширений, которые могут понадобиться
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Вывод информации о созданных объектах
\echo 'Настройка PostgreSQL завершена!'
\echo 'Пользователь: forex_user'
\echo 'База данных: forex_bot'
\echo 'Хост: localhost'
\echo 'Порт: 5432'

-- Проверка подключения
SELECT 'Подключение успешно! PostgreSQL версия: ' || version() AS status;
