
"""
Data normalizer for different news sources.
"""
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class NewsNormalizer:
    """Normalizes news data from different sources into a common format."""
    
    @staticmethod
    def normalize_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized_events = []
        
        for event in events:
            try:
                normalized_event = NewsNormalizer._normalize_single_event(event)
                if normalized_event:
                    normalized_events.append(normalized_event)
            except Exception as e:
                logger.warning(f"Failed to normalize event: {e}")
                continue
        
        return normalized_events
    
    @staticmethod
    def _normalize_single_event(event: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a single event."""
        # Ensure required fields exist
        required_fields = ['source', 'time', 'currency', 'event', 'date']
        for field in required_fields:
            if field not in event:
                logger.warning(f"Missing required field '{field}' in event")
                return None
        
        # Clean and validate data
        normalized = {
            'source': str(event['source']).strip(),
            'time': NewsNormalizer._clean_time(event['time']),
            'currency': NewsNormalizer._clean_currency(event['currency']),
            'event': NewsNormalizer._clean_text(event['event']),
            'actual': NewsNormalizer._clean_value(event.get('actual', 'N/A')),
            'forecast': NewsNormalizer._clean_value(event.get('forecast', 'N/A')),
            'previous': NewsNormalizer._clean_value(event.get('previous', 'N/A')),
            'impact': NewsNormalizer._clean_impact(event.get('impact', 'medium')),
            'analysis': NewsNormalizer._clean_text(event.get('analysis', '')),
            'date': event['date'],
            'raw_data': event.get('raw_data', {})
        }
        
        return normalized
    
    @staticmethod
    def _clean_time(time_str: str) -> str:
        """Clean and validate time string."""
        if not time_str or time_str.strip() in ['', 'N/A', 'None']:
            return 'N/A'
        
        time_str = str(time_str).strip()
        
        # Try to extract HH:MM format
        import re
        time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
        if time_match:
            hour, minute = time_match.groups()
            return f"{hour.zfill(2)}:{minute}"
        
        return time_str[:10] if len(time_str) > 10 else time_str
    
    @staticmethod
    def _clean_currency(currency_str: str) -> str:
        """Clean and validate currency string."""
        if not currency_str:
            return 'N/A'
        
        currency_str = str(currency_str).strip().upper()
        
        # Remove common prefixes/suffixes
        currency_str = currency_str.replace('FOREX:', '').replace('CURRENCY:', '')
        
        # Validate currency codes
        valid_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD']
        if currency_str in valid_currencies:
            return currency_str
        
        # Try to extract valid currency from string
        for curr in valid_currencies:
            if curr in currency_str:
                return curr
        
        return currency_str[:10] if len(currency_str) <= 10 else currency_str[:10]
    
    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean text fields."""
        if not text or str(text).strip() in ['', 'N/A', 'None']:
            return 'N/A'
        
        text = str(text).strip()
        
        # Remove excessive whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        
        # Remove escape characters for display
        text = text.replace('\\', '')
        
        # Limit length
        if len(text) > 200:
            text = text[:197] + '...'
        
        return text
    
    @staticmethod
    def _clean_value(value: str) -> str:
        """Clean actual/forecast/previous values."""
        if not value or str(value).strip() in ['', 'N/A', 'None', 'null']:
            return 'N/A'
        
        value = str(value).strip()
        
        # Remove escape characters
        value = value.replace('\\', '')
        
        # Limit length
        if len(value) > 50:
            value = value[:47] + '...'
        
        return value
    
    @staticmethod
    def _clean_impact(impact: str) -> str:
        """Clean and validate impact level."""
        if not impact:
            return 'medium'
        
        impact = str(impact).strip().lower()
        
        if impact in ['high', 'important', 'critical']:
            return 'high'
        elif impact in ['low', 'minor']:
            return 'low'
        else:
            return 'medium'
    
    @staticmethod
    def deduplicate_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate events based on similarity."""
        if not events:
            return events
        
        unique_events = []
        seen_signatures = set()
        
        for event in events:
            # Create a signature for deduplication
            signature = NewsNormalizer._create_event_signature(event)
            
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_events.append(event)
            else:
                logger.debug(f"Duplicate event filtered: {event['event'][:50]}")
        
        logger.info(f"Deduplicated {len(events)} events to {len(unique_events)} unique events")
        return unique_events
    
    @staticmethod
    def _create_event_signature(event: Dict[str, Any]) -> str:
        """Create a signature for event deduplication."""
        # Use currency, event title (first 50 chars), and date
        currency = event.get('currency', '')
        event_title = event.get('event', '')[:50].lower().strip()
        date = str(event.get('date', ''))
        
        return f"{currency}_{event_title}_{date}"
    
    @staticmethod
    def filter_by_impact(events: List[Dict[str, Any]], min_impact: str = "medium") -> List[Dict[str, Any]]:
        """Filter events by minimum impact level."""
        impact_levels = {'low': 1, 'medium': 2, 'high': 3}
        min_level = impact_levels.get(min_impact, 2)
        
        filtered_events = []
        for event in events:
            event_impact = event.get('impact', 'medium')
            event_level = impact_levels.get(event_impact, 2)
            
            if event_level >= min_level:
                filtered_events.append(event)
        
        logger.info(f"Filtered {len(events)} events to {len(filtered_events)} events with impact >= {min_impact}")
        return filtered_events
