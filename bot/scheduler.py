
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import pytz
from .scraper import scrape_and_send_forex_data
from .database import get_db_manager

logger = logging.getLogger(__name__)

class ForexScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        
    def schedule_daily_scraping(self):
        """Schedule daily scraping at 03:00 UTC"""
        trigger = CronTrigger(hour=3, minute=0, timezone=pytz.UTC)
        self.scheduler.add_job(
            func=self.daily_scraping_job,
            trigger=trigger,
            id='daily_forex_scraping',
            replace_existing=True
        )
        logger.info("Scheduled daily forex scraping at 03:00 UTC")
        
    def daily_scraping_job(self):
        """Daily job to scrape forex data for yesterday to 2 days ahead"""
        try:
            today = datetime.now().date()
            start_date = today - timedelta(days=1)  # Yesterday
            end_date = today + timedelta(days=2)    # 2 days ahead
            
            logger.info(f"Starting daily scraping job for {start_date} to {end_date}")
            
            # Check if data already exists
            db_manager = get_db_manager()
            if db_manager.check_data_exists(start_date, end_date):
                logger.info(f"Data already exists for {start_date} to {end_date}, skipping scrape")
                return
                
            # Scrape and send data
            scrape_and_send_forex_data(start_date, end_date)
            logger.info("Daily scraping job completed successfully")
            
        except Exception as e:
            logger.error(f"Error in daily scraping job: {e}")
            
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()

# Global scheduler instance
forex_scheduler = None

def get_scheduler():
    global forex_scheduler
    if forex_scheduler is None:
        forex_scheduler = ForexScheduler()
    return forex_scheduler

def start_scheduler():
    """Start the forex scheduler"""
    scheduler = get_scheduler()
    scheduler.schedule_daily_scraping()
    return scheduler
