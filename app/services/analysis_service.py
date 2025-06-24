


"""
Analysis service for ChatGPT integration.
"""

import requests
from typing import List, Dict, Optional
from app.config import config
import logging

logger = logging.getLogger(__name__)

class AnalysisService:
    """Service for analyzing forex events using ChatGPT."""
    
    def __init__(self):
        self.api_key = config.OPENAI_API_KEY
        self.api_url = "https://api.openai.com/v1/chat/completions"
    
    def analyze_single_event(
        self,
        currency: str,
        event_name: str,
        forecast: Optional[str] = None,
        previous: Optional[str] = None,
        actual: Optional[str] = None
    ) -> str:
        """
        Analyze a single forex event.
        
        Args:
            currency: Currency code
            event_name: Name of the event
            forecast: Forecast value
            previous: Previous value
            actual: Actual value
            
        Returns:
            Analysis text
        """
        if not self.api_key or self.api_key.startswith('your_'):
            return "⚠️ ChatGPT analysis skipped - API key not configured"
        
        try:
            prompt = self._build_single_event_prompt(
                currency, event_name, forecast, previous, actual
            )
            
            return self._make_api_request(prompt)
            
        except Exception as e:
            logger.error(f"ChatGPT analysis failed for single event: {e}", exc_info=True)
            return f"⚠️ ChatGPT analysis failed: {str(e)}"
    
    def analyze_combined_events(self, events: List[Dict]) -> str:
        """
        Analyze multiple events with the same currency and time as one big news event.
        
        Args:
            events: List of event dictionaries
            
        Returns:
            Combined analysis text
        """
        if not events or not self.api_key or self.api_key.startswith('your_'):
            return "⚠️ ChatGPT analysis skipped - API key not configured"
        
        try:
            prompt = self._build_combined_events_prompt(events)
            return self._make_api_request(prompt)
            
        except Exception as e:
            logger.error(f"ChatGPT analysis failed for combined events: {e}", exc_info=True)
            return f"⚠️ ChatGPT analysis failed: {str(e)}"
    
    def _build_single_event_prompt(
        self,
        currency: str,
        event_name: str,
        forecast: Optional[str],
        previous: Optional[str],
        actual: Optional[str]
    ) -> str:
        """Build prompt for single event analysis."""
        prompt = (
            f"Analyze the potential impact of the following Forex event on the {currency} currency market:\n"
            f"Event: {event_name}\n"
        )
        
        if forecast and forecast != "N/A":
            prompt += f"Forecast: {forecast}\n"
        
        if previous and previous != "N/A":
            prompt += f"Previous: {previous}\n"
        
        if actual and actual != "N/A":
            prompt += f"Actual: {actual}\n"
        
        prompt += "\nProvide a brief analysis of the potential market impact."
        
        return prompt
    
    def _build_combined_events_prompt(self, events: List[Dict]) -> str:
        """Build prompt for combined events analysis."""
        if not events:
            return ""
        
        currency = events[0].get('currency', 'Unknown')
        event_names = [event.get('event_name', event.get('event', '')) for event in events]
        forecasts = [event.get('forecast', 'N/A') for event in events]
        previous_values = [event.get('previous_value', event.get('previous', 'N/A')) for event in events]
        actual_values = [event.get('actual_value', event.get('actual', 'N/A')) for event in events]
        
        prompt = (
            f"Analyze the potential combined impact of the following Forex events on the {currency} currency market:\n"
            f"Events: {', '.join(event_names)}\n"
            f"Forecasts: {', '.join(forecasts)}\n"
            f"Previous: {', '.join(previous_values)}\n"
            f"Actual: {', '.join(actual_values)}\n"
            f"\nProvide a brief analysis of the combined market impact."
        )
        
        return prompt
    
    def _make_api_request(self, prompt: str) -> str:
        """Make API request to OpenAI."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # ИСПРАВЛЕНИЕ 2: Убрать ограничения на длину анализа ChatGPT
        # Увеличиваем max_tokens для получения полного анализа
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,  # Увеличено с 195 до 500 для полного анализа
            "temperature": 0.7
        }
        
        response = requests.post(
            self.api_url, 
            headers=headers, 
            json=data, 
            timeout=10
        )
        response.raise_for_status()
        
        result = response.json()
        analysis = result["choices"][0]["message"]["content"].strip()
        
        logger.info("ChatGPT analysis completed successfully")
        return analysis
