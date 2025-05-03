
"""
Base scraper class for web scraping.
"""

from abc import ABC, abstractmethod
from typing import List, Dict
from datetime import date
import logging

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Abstract base class for web scrapers."""
    
    def __init__(self):
        self.logger = logger
    
    @abstractmethod
    def scrape_date_range(self, start_date: date, end_date: date) -> List[Dict]:
        """
        Scrape data for a date range.
        
        Args:
            start_date: Start date for scraping
            end_date: End date for scraping
            
        Returns:
            List of scraped event dictionaries
        """
        pass
    
    @abstractmethod
    def scrape_single_date(self, target_date: date) -> List[Dict]:
        """
        Scrape data for a single date.
        
        Args:
            target_date: Date to scrape
            
        Returns:
            List of scraped event dictionaries
        """
        pass
