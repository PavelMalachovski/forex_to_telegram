
#!/usr/bin/env python3
"""
Скрипт для очистки базы данных от всех данных кроме пользователей.

Этот скрипт удаляет:
- Все новости (news_events)
- Логи скрапинга (scraping_logs)
- Справочные данные (currencies, impact_levels) - будут пересозданы

Сохраняет:
- Пользователей (bot_users)
- Настройки пользователей (user_currency_preferences, user_notification_settings)
"""

import argparse
import logging
import sys
from datetime import datetime

from sqlalchemy import text
from app.database.connection import SessionLocal
from app.database.models import (
    NewsEvent, ScrapingLog, Currency, ImpactLevel,
    BotUser, UserCurrencyPreference, UserNotificationSettings
)
from app.config import config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'clean_database_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

def get_table_counts(db) -> dict:
    """Получить количество записей в каждой таблице."""
    counts = {}
    tables = [
        ('news_events', NewsEvent),
        ('scraping_logs', ScrapingLog),
        ('currencies', Currency),
        ('impact_levels', ImpactLevel),
        ('bot_users', BotUser),
        ('user_currency_preferences', UserCurrencyPreference),
        ('user_notification_settings', UserNotificationSettings)
    ]
    
    for table_name, model in tables:
        try:
            count = db.query(model).count()
            counts[table_name] = count
        except Exception as e:
            logger.warning(f"Не удалось получить количество записей для {table_name}: {e}")
            counts[table_name] = "N/A"
    
    return counts

def show_current_state(db):
    """Показать текущее состояние базы данных."""
    logger.info("=== Текущее состояние базы данных ===")
    counts = get_table_counts(db)
    
    for table_name, count in counts.items():
        logger.info(f"{table_name}: {count} записей")
    
    return counts

def clean_data_tables(db, dry_run: bool = False) -> dict:
    """
    Очистить таблицы с данными (кроме пользователей).
    
    Args:
        db: Сессия базы данных
        dry_run: Если True, только показать что будет удалено
        
    Returns:
        dict: Статистика удаления
    """
    stats = {
        'deleted_news_events': 0,
        'deleted_scraping_logs': 0,
        'deleted_currencies': 0,
        'deleted_impact_levels': 0,
        'preserved_users': 0,
        'preserved_user_preferences': 0,
        'preserved_user_notifications': 0
    }
    
    try:
        # Получить статистику перед удалением
        stats['deleted_news_events'] = db.query(NewsEvent).count()
        stats['deleted_scraping_logs'] = db.query(ScrapingLog).count()
        stats['deleted_currencies'] = db.query(Currency).count()
        stats['deleted_impact_levels'] = db.query(ImpactLevel).count()
        
        # Статистика сохраняемых данных
        stats['preserved_users'] = db.query(BotUser).count()
        stats['preserved_user_preferences'] = db.query(UserCurrencyPreference).count()
        stats['preserved_user_notifications'] = db.query(UserNotificationSettings).count()
        
        if dry_run:
            logger.info("=== РЕЖИМ ПРЕДВАРИТЕЛЬНОГО ПРОСМОТРА ===")
            logger.info("Будет удалено:")
            logger.info(f"  - Новости: {stats['deleted_news_events']} записей")
            logger.info(f"  - Логи скрапинга: {stats['deleted_scraping_logs']} записей")
            logger.info(f"  - Валюты: {stats['deleted_currencies']} записей")
            logger.info(f"  - Уровни воздействия: {stats['deleted_impact_levels']} записей")
            logger.info("")
            logger.info("Будет сохранено:")
            logger.info(f"  - Пользователи: {stats['preserved_users']} записей")
            logger.info(f"  - Настройки валют: {stats['preserved_user_preferences']} записей")
            logger.info(f"  - Настройки уведомлений: {stats['preserved_user_notifications']} записей")
            return stats
        
        logger.info("Начинаю очистку данных...")
        
        # Удаляем в правильном порядке (учитывая внешние ключи)
        
        # 1. Удаляем новости (ссылаются на currencies и impact_levels)
        logger.info("Удаляю новости...")
        db.query(NewsEvent).delete()
        
        # 2. Удаляем логи скрапинга
        logger.info("Удаляю логи скрапинга...")
        db.query(ScrapingLog).delete()
        
        # 3. Удаляем настройки валют пользователей (ссылаются на currencies)
        logger.info("Удаляю настройки валют пользователей...")
        db.query(UserCurrencyPreference).delete()
        
        # 4. Удаляем справочники
        logger.info("Удаляю валюты...")
        db.query(Currency).delete()
        
        logger.info("Удаляю уровни воздействия...")
        db.query(ImpactLevel).delete()
        
        # Сбрасываем автоинкремент для очищенных таблиц
        if 'sqlite' in config.DATABASE_URL.lower():
            # Для SQLite - проверяем существование таблицы sqlite_sequence
            try:
                result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")).fetchone()
                if result:
                    tables_to_reset = ['news_events', 'scraping_logs', 'currencies', 'impact_levels', 'user_currency_preferences']
                    for table in tables_to_reset:
                        db.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table}'"))
            except Exception as e:
                logger.warning(f"Не удалось сбросить автоинкремент: {e}")
        elif 'postgresql' in config.DATABASE_URL.lower():
            # Для PostgreSQL
            sequences_to_reset = [
                'news_events_id_seq',
                'scraping_logs_id_seq', 
                'currencies_id_seq',
                'impact_levels_id_seq',
                'user_currency_preferences_id_seq'
            ]
            for seq in sequences_to_reset:
                try:
                    db.execute(text(f"ALTER SEQUENCE {seq} RESTART WITH 1"))
                except Exception as e:
                    logger.warning(f"Не удалось сбросить последовательность {seq}: {e}")
        
        db.commit()
        logger.info("Очистка данных завершена успешно!")
        
    except Exception as e:
        logger.error(f"Ошибка при очистке данных: {e}")
        db.rollback()
        raise
    
    return stats

def reinitialize_reference_data(db):
    """Пересоздать справочные данные."""
    logger.info("Пересоздаю справочные данные...")
    
    try:
        # Создаем валюты
        for currency_code in config.AVAILABLE_CURRENCIES:
            currency = Currency(
                code=currency_code,
                name=currency_code
            )
            db.add(currency)
        
        # Создаем уровни воздействия
        impact_levels = [
            ("NON_ECONOMIC", "Non-Economic", 0),
            ("LOW", "Low Impact", 1),
            ("MEDIUM", "Medium Impact", 2),
            ("HIGH", "High Impact", 3)
        ]
        
        for code, name, priority in impact_levels:
            impact_level = ImpactLevel(
                code=code,
                name=name,
                priority=priority
            )
            db.add(impact_level)
        
        db.commit()
        logger.info("Справочные данные пересозданы успешно!")
        
    except Exception as e:
        logger.error(f"Ошибка при пересоздании справочных данных: {e}")
        db.rollback()
        raise

def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(
        description="Очистка базы данных от всех данных кроме пользователей",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python clean_database.py --dry-run                    # Предварительный просмотр
  python clean_database.py --confirm                    # Выполнить очистку
  python clean_database.py --confirm --no-reinit       # Очистка без пересоздания справочников
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Показать что будет удалено без фактического удаления'
    )
    
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Подтвердить выполнение очистки (обязательный параметр для реального удаления)'
    )
    
    parser.add_argument(
        '--no-reinit',
        action='store_true',
        help='Не пересоздавать справочные данные после очистки'
    )
    
    args = parser.parse_args()
    
    # Проверка параметров
    if not args.dry_run and not args.confirm:
        logger.error("Для выполнения очистки необходимо указать --confirm")
        logger.error("Для предварительного просмотра используйте --dry-run")
        sys.exit(1)
    
    if args.dry_run and args.confirm:
        logger.error("Нельзя одновременно использовать --dry-run и --confirm")
        sys.exit(1)
    
    logger.info("=== СКРИПТ ОЧИСТКИ БАЗЫ ДАННЫХ ===")
    logger.info(f"Режим: {'Предварительный просмотр' if args.dry_run else 'Реальная очистка'}")
    logger.info(f"База данных: {config.DATABASE_URL}")
    
    db = SessionLocal()
    try:
        # Показать текущее состояние
        initial_counts = show_current_state(db)
        
        # Проверить есть ли что удалять
        total_data_records = (
            initial_counts.get('news_events', 0) +
            initial_counts.get('scraping_logs', 0) +
            initial_counts.get('currencies', 0) +
            initial_counts.get('impact_levels', 0)
        )
        
        if total_data_records == 0:
            logger.info("База данных уже пуста (нет данных для удаления)")
            return
        
        # Дополнительное подтверждение для реальной очистки
        if args.confirm and not args.dry_run:
            logger.warning("ВНИМАНИЕ! Вы собираетесь удалить все данные кроме пользователей!")
            logger.warning("Это действие необратимо!")
            
            response = input("Введите 'YES' для подтверждения: ")
            if response != 'YES':
                logger.info("Операция отменена пользователем")
                return
        
        # Выполнить очистку
        stats = clean_data_tables(db, dry_run=args.dry_run)
        
        if not args.dry_run:
            # Пересоздать справочные данные если нужно
            if not args.no_reinit:
                reinitialize_reference_data(db)
            
            # Показать финальное состояние
            logger.info("\n=== Финальное состояние базы данных ===")
            show_current_state(db)
            
            # Статистика
            logger.info("\n=== СТАТИСТИКА ОЧИСТКИ ===")
            logger.info(f"Удалено новостей: {stats['deleted_news_events']}")
            logger.info(f"Удалено логов скрапинга: {stats['deleted_scraping_logs']}")
            logger.info(f"Удалено валют: {stats['deleted_currencies']}")
            logger.info(f"Удалено уровней воздействия: {stats['deleted_impact_levels']}")
            logger.info(f"Сохранено пользователей: {stats['preserved_users']}")
            logger.info(f"Сохранено настроек валют: {stats['preserved_user_preferences']}")
            logger.info(f"Сохранено настроек уведомлений: {stats['preserved_user_notifications']}")
            
            if not args.no_reinit:
                logger.info(f"Пересоздано валют: {len(config.AVAILABLE_CURRENCIES)}")
                logger.info("Пересоздано уровней воздействия: 4")
            
            logger.info("\nОчистка базы данных завершена успешно!")
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
