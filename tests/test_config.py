
"""
Tests for configuration.
"""

import pytest
import os
from app.config import Config

def test_config_defaults():
    """Test configuration defaults."""
    config = Config()
    
    assert config.LOG_LEVEL == 'INFO'
    assert config.SCRAPER_SCHEDULE_HOUR == 3
    assert config.SCRAPER_SCHEDULE_MINUTE == 0
    assert config.TIMEZONE == 'Europe/Prague'
    assert 'EUR' in config.AVAILABLE_CURRENCIES
    assert 'USD' in config.AVAILABLE_CURRENCIES

def test_config_validation():
    """Test configuration validation."""
    # Save original values
    original_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    original_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    try:
        # Test with missing required variables
        if 'TELEGRAM_BOT_TOKEN' in os.environ:
            del os.environ['TELEGRAM_BOT_TOKEN']
        if 'TELEGRAM_CHAT_ID' in os.environ:
            del os.environ['TELEGRAM_CHAT_ID']
        
        config = Config()
        assert not config.validate()
        
        # Test with required variables set
        os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token'
        os.environ['TELEGRAM_CHAT_ID'] = 'test_chat_id'
        
        config = Config()
        assert config.validate()
        
    finally:
        # Restore original values
        if original_token:
            os.environ['TELEGRAM_BOT_TOKEN'] = original_token
        elif 'TELEGRAM_BOT_TOKEN' in os.environ:
            del os.environ['TELEGRAM_BOT_TOKEN']
            
        if original_chat_id:
            os.environ['TELEGRAM_CHAT_ID'] = original_chat_id
        elif 'TELEGRAM_CHAT_ID' in os.environ:
            del os.environ['TELEGRAM_CHAT_ID']
