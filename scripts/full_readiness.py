
#!/usr/bin/env python3
"""
Полная проверка готовности системы для запуска Telegram бота
"""

import os
import sys
import subprocess
import psycopg2
import requests
from dotenv import load_dotenv
from urllib.parse import urlparse
import json

class SystemChecker:
    def __init__(self):
        load_dotenv()
        self.database_url = os.getenv('DATABASE_URL')
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.webhook_url = os.getenv('WEBHOOK_URL')
        self.render_api_key = os.getenv('RENDER_API_KEY')
        
        self.checks_passed = 0
        self.total_checks = 0
        self.critical_errors = []
        self.warnings = []

    def log_check(self, name, passed, message, critical=False):
        """Логирование результата проверки"""
        self.total_checks += 1
        if passed:
            self.checks_passed += 1
            print(f"✅ {name}: {message}")
        else:
            print(f"❌ {name}: {message}")
            if critical:
                self.critical_errors.append(f"{name}: {message}")
            else:
                self.warnings.append(f"{name}: {message}")

    def check_environment_variables(self):
        """Проверка переменных окружения"""
        print("\n🔍 ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ")
        print("="*50)
        
        self.log_check(
            "DATABASE_URL", 
            bool(self.database_url),
            "Установлена" if self.database_url else "Не найдена",
            critical=True
        )
        
        self.log_check(
            "TELEGRAM_BOT_TOKEN",
            bool(self.bot_token),
            "Установлен" if self.bot_token else "Не найден",
            critical=True
        )
        
        self.log_check(
            "WEBHOOK_URL",
            bool(self.webhook_url),
            "Установлен" if self.webhook_url else "Не найден (может быть установлен позже)"
        )
        
        self.log_check(
            "RENDER_API_KEY",
            bool(self.render_api_key),
            "Установлен" if self.render_api_key else "Не найден (опционально)"
        )

    def check_database_connection(self):
        """Проверка подключения к базе данных"""
        print("\n🔗 ПРОВЕРКА ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ")
        print("="*50)
        
        if not self.database_url:
            self.log_check("DB Connection", False, "DATABASE_URL не установлена", critical=True)
            return False
        
        try:
            # Парсим URL для отображения информации
            parsed = urlparse(self.database_url)
            print(f"Хост: {parsed.hostname}")
            print(f"База данных: {parsed.path[1:] if parsed.path else 'Не указана'}")
            print(f"Пользователь: {parsed.username}")
            
            # Тестируем подключение
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            
            # Проверяем версию PostgreSQL
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            self.log_check("DB Connection", True, f"Подключение успешно")
            print(f"  PostgreSQL: {version[:80]}...")
            
            # Проверяем права доступа
            cursor.execute("SELECT current_user, session_user;")
            users = cursor.fetchone()
            print(f"  Текущий пользователь: {users[0]}")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            self.log_check("DB Connection", False, f"Ошибка подключения: {e}", critical=True)
            return False

    def check_database_tables(self):
        """Проверка таблиц базы данных"""
        print("\n📊 ПРОВЕРКА ТАБЛИЦ БАЗЫ ДАННЫХ")
        print("="*50)
        
        if not self.database_url:
            self.log_check("DB Tables", False, "Нет подключения к БД", critical=True)
            return False
        
        expected_tables = [
            'users', 'user_settings', 'notifications', 
            'forex_data', 'trading_signals', 'user_subscriptions'
        ]
        
        try:
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            
            # Получаем список таблиц
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            print(f"Найдено таблиц: {len(existing_tables)}")
            
            # Проверяем каждую ожидаемую таблицу
            missing_tables = []
            for table in expected_tables:
                if table in existing_tables:
                    # Проверяем количество записей
                    cursor.execute(f"SELECT COUNT(*) FROM {table};")
                    count = cursor.fetchone()[0]
                    print(f"  ✅ {table}: {count} записей")
                else:
                    missing_tables.append(table)
                    print(f"  ❌ {table}: отсутствует")
            
            # Проверяем версию миграций
            if 'alembic_version' in existing_tables:
                cursor.execute("SELECT version_num FROM alembic_version;")
                version = cursor.fetchone()
                if version:
                    print(f"  🔄 Версия миграции: {version[0]}")
            
            cursor.close()
            conn.close()
            
            if missing_tables:
                self.log_check(
                    "DB Tables", 
                    False, 
                    f"Отсутствуют таблицы: {', '.join(missing_tables)}", 
                    critical=True
                )
                return False
            else:
                self.log_check("DB Tables", True, "Все необходимые таблицы присутствуют")
                return True
                
        except Exception as e:
            self.log_check("DB Tables", False, f"Ошибка проверки таблиц: {e}", critical=True)
            return False

    def check_bot_token_validity(self):
        """Проверка валидности токена бота"""
        print("\n🤖 ПРОВЕРКА ТОКЕНА TELEGRAM БОТА")
        print("="*50)
        
        if not self.bot_token:
            self.log_check("Bot Token", False, "Токен не установлен", critical=True)
            return False
        
        try:
            # Проверяем токен через Telegram API
            response = requests.get(f"https://api.telegram.org/bot{self.bot_token}/getMe")
            
            if response.status_code == 200:
                bot_info = response.json()
                if bot_info.get('ok'):
                    bot_data = bot_info['result']
                    self.log_check("Bot Token", True, f"Токен валиден")
                    print(f"  Имя бота: {bot_data.get('first_name', 'Не указано')}")
                    print(f"  Username: @{bot_data.get('username', 'Не указан')}")
                    print(f"  ID: {bot_data.get('id', 'Не указан')}")
                    return True
                else:
                    self.log_check("Bot Token", False, "Токен невалиден", critical=True)
                    return False
            else:
                self.log_check("Bot Token", False, f"Ошибка API: {response.status_code}", critical=True)
                return False
                
        except Exception as e:
            self.log_check("Bot Token", False, f"Ошибка проверки токена: {e}", critical=True)
            return False

    def check_dependencies(self):
        """Проверка зависимостей Python"""
        print("\n📦 ПРОВЕРКА ЗАВИСИМОСТЕЙ")
        print("="*50)
        
        required_packages = [
            'psycopg2', 'sqlalchemy', 'alembic', 
            'telebot', 'fastapi', 'uvicorn'
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"  ✅ {package}")
            except ImportError:
                print(f"  ❌ {package}")
                missing_packages.append(package)
        
        if missing_packages:
            self.log_check(
                "Dependencies", 
                False, 
                f"Отсутствуют пакеты: {', '.join(missing_packages)}"
            )
            return False
        else:
            self.log_check("Dependencies", True, "Все зависимости установлены")
            return True

    def check_file_structure(self):
        """Проверка структуры файлов проекта"""
        print("\n📁 ПРОВЕРКА СТРУКТУРЫ ПРОЕКТА")
        print("="*50)
        
        required_files = [
            'bot_runner.py',
            'config/alembic.ini',
            'alembic/env.py',
            '.env'
        ]
        
        missing_files = []
        
        for file_path in required_files:
            if os.path.exists(file_path):
                print(f"  ✅ {file_path}")
            else:
                print(f"  ❌ {file_path}")
                missing_files.append(file_path)
        
        if missing_files:
            self.log_check(
                "File Structure", 
                False, 
                f"Отсутствуют файлы: {', '.join(missing_files)}"
            )
            return False
        else:
            self.log_check("File Structure", True, "Все необходимые файлы присутствуют")
            return True

    def test_basic_operations(self):
        """Тестирование базовых операций с базой данных"""
        print("\n🧪 ТЕСТИРОВАНИЕ БАЗОВЫХ ОПЕРАЦИЙ")
        print("="*50)
        
        if not self.database_url:
            self.log_check("Basic Operations", False, "Нет подключения к БД", critical=True)
            return False
        
        try:
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            
            # Тест создания временной таблицы
            cursor.execute("""
                CREATE TEMPORARY TABLE test_table (
                    id SERIAL PRIMARY KEY,
                    test_data VARCHAR(100)
                );
            """)
            
            # Тест вставки данных
            cursor.execute("INSERT INTO test_table (test_data) VALUES (%s);", ("test_value",))
            
            # Тест чтения данных
            cursor.execute("SELECT test_data FROM test_table WHERE id = 1;")
            result = cursor.fetchone()
            
            if result and result[0] == "test_value":
                self.log_check("Basic Operations", True, "Операции чтения/записи работают")
                success = True
            else:
                self.log_check("Basic Operations", False, "Ошибка в операциях чтения/записи")
                success = False
            
            conn.rollback()  # Откатываем изменения
            cursor.close()
            conn.close()
            
            return success
            
        except Exception as e:
            self.log_check("Basic Operations", False, f"Ошибка тестирования: {e}")
            return False

    def generate_report(self):
        """Генерация итогового отчета"""
        print("\n" + "="*60)
        print("📋 ИТОГОВЫЙ ОТЧЕТ ГОТОВНОСТИ СИСТЕМЫ")
        print("="*60)
        
        success_rate = (self.checks_passed / self.total_checks * 100) if self.total_checks > 0 else 0
        
        print(f"Пройдено проверок: {self.checks_passed}/{self.total_checks} ({success_rate:.1f}%)")
        
        if self.critical_errors:
            print(f"\n❌ КРИТИЧЕСКИЕ ОШИБКИ ({len(self.critical_errors)}):")
            for error in self.critical_errors:
                print(f"  • {error}")
        
        if self.warnings:
            print(f"\n⚠️  ПРЕДУПРЕЖДЕНИЯ ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        print("\n" + "="*60)
        
        if not self.critical_errors:
            print("🎉 СИСТЕМА ГОТОВА К ЗАПУСКУ!")
            print("\nСледующие шаги:")
            print("1. Деплой на Render с установленными переменными окружения")
            print("2. Настройка webhook для Telegram бота")
            print("3. Запуск бота и мониторинг логов")
            return True
        else:
            print("❌ СИСТЕМА НЕ ГОТОВА К ЗАПУСКУ!")
            print("\nНеобходимо исправить критические ошибки:")
            print("1. Установить отсутствующие переменные окружения")
            print("2. Выполнить миграции базы данных")
            print("3. Проверить подключение к базе данных")
            return False

    def run_all_checks(self):
        """Запуск всех проверок"""
        print("🚀 ПОЛНАЯ ПРОВЕРКА ГОТОВНОСТИ TELEGRAM БОТА")
        print("="*60)
        
        self.check_environment_variables()
        self.check_database_connection()
        self.check_database_tables()
        self.check_bot_token_validity()
        self.check_dependencies()
        self.check_file_structure()
        self.test_basic_operations()
        
        return self.generate_report()

def main():
    checker = SystemChecker()
    ready = checker.run_all_checks()
    
    sys.exit(0 if ready else 1)

if __name__ == "__main__":
    main()
