
#!/usr/bin/env python3
"""
Скрипт для массовой загрузки данных за указанный период.

Этот скрипт:
- Загружает данные с ForexFactory за указанный период
- Перезаписывает существующие данные за те же даты
- Показывает прогресс и детальную статистику
- Обрабатывает ошибки с повторными попытками
- Ведет подробное логирование
"""

import argparse
import logging
import sys
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import time

from tqdm import tqdm
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_

from app.database.connection import SessionLocal
from app.database.models import NewsEvent, Currency, ImpactLevel, ScrapingLog
from app.scrapers.forex_factory_scraper import ForexFactoryScraper
from app.config import config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'bulk_load_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

class BulkDataLoader:
    """Класс для массовой загрузки данных."""
    
    def __init__(self):
        self.scraper = ForexFactoryScraper()
        self.stats = {
            'total_days': 0,
            'successful_days': 0,
            'failed_days': 0,
            'total_events_scraped': 0,
            'total_events_inserted': 0,
            'total_events_updated': 0,
            'total_events_skipped': 0,
            'total_errors': 0,
            'start_time': None,
            'end_time': None
        }
        self.failed_dates = []
        
    def get_currency_map(self, db) -> Dict[str, int]:
        """Получить маппинг кода валюты на ID."""
        currencies = db.query(Currency).all()
        return {c.code: c.id for c in currencies}
    
    def get_impact_level_map(self, db) -> Dict[str, int]:
        """Получить маппинг кода уровня воздействия на ID."""
        impact_levels = db.query(ImpactLevel).all()
        return {il.code: il.id for il in impact_levels}
    
    def validate_date_range(self, start_date: date, end_date: date) -> bool:
        """Валидация диапазона дат."""
        if start_date > end_date:
            logger.error("Дата начала не может быть больше даты окончания")
            return False
        
        if end_date > date.today():
            logger.warning("Дата окончания в будущем, будет ограничена сегодняшним днем")
            return True
        
        days_diff = (end_date - start_date).days + 1
        if days_diff > 365:
            logger.warning(f"Большой диапазон дат: {days_diff} дней. Это может занять много времени.")
            response = input("Продолжить? (y/N): ")
            return response.lower() == 'y'
        
        return True
    
    def clear_existing_data(self, db, target_date: date) -> int:
        """Удалить существующие данные за указанную дату."""
        try:
            deleted_count = db.query(NewsEvent).filter(
                NewsEvent.event_date == target_date
            ).delete()
            
            if deleted_count > 0:
                logger.debug(f"Удалено {deleted_count} существующих записей за {target_date}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Ошибка при удалении данных за {target_date}: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    def scrape_date_with_retry(self, target_date: date) -> List[Dict]:
        """Скрапинг данных за дату с повторными попытками."""
        logger.debug(f"Попытка скрапинга данных за {target_date}")
        return self.scraper.scrape_single_date(target_date)
    
    def process_single_date(self, db, target_date: date, currency_map: Dict[str, int], 
                          impact_map: Dict[str, int], overwrite: bool = True) -> Tuple[int, int, int]:
        """
        Обработать данные за одну дату.
        
        Returns:
            Tuple[inserted, updated, skipped]
        """
        inserted = updated = skipped = 0
        
        try:
            # Удалить существующие данные если нужно
            if overwrite:
                self.clear_existing_data(db, target_date)
            
            # Скрапинг данных
            events = self.scrape_date_with_retry(target_date)
            self.stats['total_events_scraped'] += len(events)
            
            if not events:
                logger.debug(f"Нет событий за {target_date}")
                return inserted, updated, skipped
            
            # Обработка каждого события
            for event_data in events:
                try:
                    result = self.process_single_event(
                        db, event_data, currency_map, impact_map, overwrite
                    )
                    
                    if result == 'inserted':
                        inserted += 1
                    elif result == 'updated':
                        updated += 1
                    else:
                        skipped += 1
                        
                except Exception as e:
                    logger.error(f"Ошибка при обработке события {event_data.get('event_name', 'Unknown')}: {e}")
                    skipped += 1
                    self.stats['total_errors'] += 1
            
            db.commit()
            logger.debug(f"Обработка {target_date} завершена: +{inserted}, ~{updated}, -{skipped}")
            
        except Exception as e:
            logger.error(f"Ошибка при обработке даты {target_date}: {e}")
            db.rollback()
            raise
        
        return inserted, updated, skipped
    
    def process_single_event(self, db, event_data: Dict, currency_map: Dict[str, int], 
                           impact_map: Dict[str, int], overwrite: bool) -> str:
        """
        Обработать одно событие.
        
        Returns:
            'inserted', 'updated', или 'skipped'
        """
        # Валидация данных
        currency_code = event_data.get('currency', '').upper()
        if currency_code not in currency_map:
            logger.debug(f"Неизвестная валюта: {currency_code}")
            return 'skipped'
        
        impact_code = event_data.get('impact_level', 'LOW')
        if impact_code not in impact_map:
            logger.debug(f"Неизвестный уровень воздействия: {impact_code}, использую LOW")
            impact_code = 'LOW'
        
        # Парсинг даты и времени
        try:
            event_date = datetime.strptime(event_data['date'], '%Y-%m-%d').date()
            event_time = datetime.strptime(event_data['time'], '%H:%M').time()
        except (ValueError, KeyError) as e:
            logger.debug(f"Ошибка парсинга даты/времени: {e}")
            return 'skipped'
        
        # Проверка существования записи
        existing_event = db.query(NewsEvent).filter(
            and_(
                NewsEvent.event_date == event_date,
                NewsEvent.event_time == event_time,
                NewsEvent.currency_id == currency_map[currency_code],
                NewsEvent.event_name == event_data.get('event_name', '')
            )
        ).first()
        
        if existing_event and not overwrite:
            return 'skipped'
        
        # Создание или обновление записи
        if existing_event:
            # Обновление существующей записи
            existing_event.forecast = event_data.get('forecast', 'N/A')
            existing_event.previous_value = event_data.get('previous_value', 'N/A')
            existing_event.actual_value = event_data.get('actual_value', 'N/A')
            existing_event.analysis = event_data.get('analysis', '')
            existing_event.source_url = event_data.get('source_url', '')
            existing_event.impact_level_id = impact_map[impact_code]
            existing_event.updated_at = datetime.utcnow()
            
            return 'updated'
        else:
            # Создание новой записи
            new_event = NewsEvent(
                event_date=event_date,
                event_time=event_time,
                currency_id=currency_map[currency_code],
                impact_level_id=impact_map[impact_code],
                event_name=event_data.get('event_name', ''),
                forecast=event_data.get('forecast', 'N/A'),
                previous_value=event_data.get('previous_value', 'N/A'),
                actual_value=event_data.get('actual_value', 'N/A'),
                analysis=event_data.get('analysis', ''),
                source_url=event_data.get('source_url', '')
            )
            
            db.add(new_event)
            return 'inserted'
    
    def create_scraping_log(self, db, start_date: date, end_date: date, 
                          status: str, error_message: Optional[str] = None):
        """Создать запись в логе скрапинга."""
        try:
            duration = None
            if self.stats['start_time'] and self.stats['end_time']:
                duration = int((self.stats['end_time'] - self.stats['start_time']).total_seconds())
            
            log_entry = ScrapingLog(
                start_date=start_date,
                end_date=end_date,
                events_scraped=self.stats['total_events_scraped'],
                events_updated=self.stats['total_events_inserted'] + self.stats['total_events_updated'],
                errors_count=self.stats['total_errors'],
                duration_seconds=duration,
                status=status,
                error_message=error_message
            )
            
            db.add(log_entry)
            db.commit()
            
        except Exception as e:
            logger.error(f"Ошибка при создании лога скрапинга: {e}")
    
    def load_data_range(self, start_date: date, end_date: date, overwrite: bool = True) -> bool:
        """
        Загрузить данные за диапазон дат.
        
        Returns:
            True если загрузка прошла успешно
        """
        # Ограничить дату окончания сегодняшним днем
        if end_date > date.today():
            end_date = date.today()
            logger.info(f"Дата окончания ограничена сегодняшним днем: {end_date}")
        
        # Валидация
        if not self.validate_date_range(start_date, end_date):
            return False
        
        self.stats['start_time'] = datetime.now()
        self.stats['total_days'] = (end_date - start_date).days + 1
        
        logger.info(f"Начинаю загрузку данных с {start_date} по {end_date}")
        logger.info(f"Всего дней для обработки: {self.stats['total_days']}")
        logger.info(f"Режим перезаписи: {'Включен' if overwrite else 'Отключен'}")
        
        db = SessionLocal()
        try:
            # Получить маппинги
            currency_map = self.get_currency_map(db)
            impact_map = self.get_impact_level_map(db)
            
            if not currency_map:
                logger.error("Не найдены валюты в базе данных. Запустите init_data.py")
                return False
            
            if not impact_map:
                logger.error("Не найдены уровни воздействия в базе данных. Запустите init_data.py")
                return False
            
            # Обработка каждой даты
            current_date = start_date
            with tqdm(total=self.stats['total_days'], desc="Загрузка данных") as pbar:
                while current_date <= end_date:
                    try:
                        pbar.set_description(f"Обработка {current_date}")
                        
                        inserted, updated, skipped = self.process_single_date(
                            db, current_date, currency_map, impact_map, overwrite
                        )
                        
                        self.stats['total_events_inserted'] += inserted
                        self.stats['total_events_updated'] += updated
                        self.stats['total_events_skipped'] += skipped
                        self.stats['successful_days'] += 1
                        
                        pbar.set_postfix({
                            'Добавлено': inserted,
                            'Обновлено': updated,
                            'Пропущено': skipped
                        })
                        
                    except Exception as e:
                        logger.error(f"Ошибка при обработке {current_date}: {e}")
                        self.failed_dates.append(current_date)
                        self.stats['failed_days'] += 1
                        self.stats['total_errors'] += 1
                        
                        pbar.set_postfix({'Ошибка': str(e)[:50]})
                    
                    current_date += timedelta(days=1)
                    pbar.update(1)
                    
                    # Небольшая пауза между запросами
                    time.sleep(0.5)
            
            self.stats['end_time'] = datetime.now()
            
            # Создать лог скрапинга
            status = 'success' if self.stats['failed_days'] == 0 else (
                'partial' if self.stats['successful_days'] > 0 else 'failed'
            )
            
            error_message = None
            if self.failed_dates:
                error_message = f"Ошибки при обработке дат: {', '.join(str(d) for d in self.failed_dates[:10])}"
                if len(self.failed_dates) > 10:
                    error_message += f" и еще {len(self.failed_dates) - 10} дат"
            
            self.create_scraping_log(db, start_date, end_date, status, error_message)
            
            return status in ['success', 'partial']
            
        except Exception as e:
            logger.error(f"Критическая ошибка при загрузке данных: {e}")
            self.stats['end_time'] = datetime.now()
            
            # Создать лог с ошибкой
            self.create_scraping_log(db, start_date, end_date, 'failed', str(e))
            return False
            
        finally:
            db.close()
    
    def print_final_stats(self):
        """Вывести финальную статистику."""
        duration = None
        if self.stats['start_time'] and self.stats['end_time']:
            duration = self.stats['end_time'] - self.stats['start_time']
        
        logger.info("\n" + "="*60)
        logger.info("ФИНАЛЬНАЯ СТАТИСТИКА ЗАГРУЗКИ")
        logger.info("="*60)
        logger.info(f"Период выполнения: {self.stats['start_time']} - {self.stats['end_time']}")
        if duration:
            logger.info(f"Время выполнения: {duration}")
        logger.info(f"Всего дней: {self.stats['total_days']}")
        logger.info(f"Успешно обработано дней: {self.stats['successful_days']}")
        logger.info(f"Дней с ошибками: {self.stats['failed_days']}")
        logger.info(f"Всего событий получено: {self.stats['total_events_scraped']}")
        logger.info(f"Событий добавлено: {self.stats['total_events_inserted']}")
        logger.info(f"Событий обновлено: {self.stats['total_events_updated']}")
        logger.info(f"Событий пропущено: {self.stats['total_events_skipped']}")
        logger.info(f"Всего ошибок: {self.stats['total_errors']}")
        
        if self.failed_dates:
            logger.info(f"\nДаты с ошибками ({len(self.failed_dates)}):")
            for failed_date in self.failed_dates[:20]:  # Показать первые 20
                logger.info(f"  - {failed_date}")
            if len(self.failed_dates) > 20:
                logger.info(f"  ... и еще {len(self.failed_dates) - 20} дат")
        
        success_rate = (self.stats['successful_days'] / self.stats['total_days'] * 100) if self.stats['total_days'] > 0 else 0
        logger.info(f"\nУспешность: {success_rate:.1f}%")
        logger.info("="*60)

def parse_date(date_str: str) -> date:
    """Парсинг даты из строки."""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Неверный формат даты: {date_str}. Используйте YYYY-MM-DD")

def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(
        description="Массовая загрузка данных с ForexFactory за указанный период",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python bulk_load_data.py --from 2024-06-01 --to 2024-06-30    # Загрузить данные за июнь 2024
  python bulk_load_data.py --from 2024-01-01 --to today         # Загрузить данные с начала года
  python bulk_load_data.py --from 2024-06-01 --to 2024-06-30 --no-overwrite  # Не перезаписывать существующие
        """
    )
    
    parser.add_argument(
        '--from',
        dest='start_date',
        type=parse_date,
        required=True,
        help='Дата начала в формате YYYY-MM-DD'
    )
    
    parser.add_argument(
        '--to',
        dest='end_date',
        type=lambda x: date.today() if x.lower() == 'today' else parse_date(x),
        required=True,
        help='Дата окончания в формате YYYY-MM-DD или "today"'
    )
    
    parser.add_argument(
        '--no-overwrite',
        action='store_true',
        help='Не перезаписывать существующие данные'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Подробное логирование'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("=== СКРИПТ МАССОВОЙ ЗАГРУЗКИ ДАННЫХ ===")
    logger.info(f"База данных: {config.DATABASE_URL}")
    logger.info(f"Период: {args.start_date} - {args.end_date}")
    logger.info(f"Перезапись: {'Отключена' if args.no_overwrite else 'Включена'}")
    
    # Создать загрузчик и запустить
    loader = BulkDataLoader()
    
    try:
        success = loader.load_data_range(
            start_date=args.start_date,
            end_date=args.end_date,
            overwrite=not args.no_overwrite
        )
        
        loader.print_final_stats()
        
        if success:
            logger.info("Загрузка данных завершена успешно!")
            sys.exit(0)
        else:
            logger.error("Загрузка данных завершена с ошибками!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Загрузка прервана пользователем")
        loader.print_final_stats()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        loader.print_final_stats()
        sys.exit(1)

if __name__ == "__main__":
    main()
