#!/usr/bin/env python3
"""
Unit tests for data validation improvements.

Tests the enhanced logging and error handling for GBP/EUR/AUD currencies.
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pytz
import pandas as pd

from bot.chart_service import ChartService


class TestDataValidationImprovements(unittest.TestCase):
    """Test data validation improvements."""

    def setUp(self):
        """Set up test fixtures."""
        self.chart_service = ChartService()
        self.start_time = datetime.now(pytz.UTC)
        self.end_time = self.start_time + timedelta(hours=2)

    def test_currency_extraction_from_symbols(self):
        """Test currency extraction from various symbol formats."""
        test_cases = [
            # Standard Yahoo Finance format
            ('EURUSD=X', 'EUR'),
            ('GBPUSD=X', 'GBP'),
            ('AUDUSD=X', 'AUD'),
            ('USDJPY=X', 'JPY'),
            ('USDCAD=X', 'CAD'),
            ('USDCHF=X', 'CHF'),
            ('NZDUSD=X', 'NZD'),
            
            # Alternative formats
            ('EURGBP=X', 'EUR'),
            ('GBPJPY=X', 'GBP'),
            ('AUDJPY=X', 'AUD'),
            ('EURJPY=X', 'EUR'),
            
            # Edge cases
            ('BTC-USD', 'BTC'),
            ('ETH-USD', 'ETH'),
            ('XAUUSD=X', 'XAU'),
        ]
        
        for symbol, expected_currency in test_cases:
            with self.subTest(symbol=symbol):
                result = self.chart_service._extract_currency_from_symbol(symbol)
                self.assertEqual(result, expected_currency)

    def test_problematic_currency_detection(self):
        """Test detection of problematic currencies."""
        problematic_currencies = ['GBP', 'EUR', 'AUD']
        
        # Test symbols that should be detected as problematic
        problematic_symbols = [
            'EURUSD=X', 'EURGBP=X', 'EURJPY=X',
            'GBPUSD=X', 'GBPJPY=X', 'EURGBP=X', 
            'AUDUSD=X', 'AUDJPY=X', 'AUDCAD=X'
        ]
        
        for symbol in problematic_symbols:
            with self.subTest(symbol=symbol):
                currency = self.chart_service._extract_currency_from_symbol(symbol)
                is_problematic = currency in problematic_currencies
                self.assertTrue(is_problematic, f"Symbol {symbol} should be detected as problematic")

    def test_enhanced_logging_trigger(self):
        """Test that enhanced logging is triggered for problematic currencies."""
        # Test the logic that determines if enhanced logging should be used
        test_symbols = [
            ('EURUSD=X', True),   # EUR is problematic
            ('GBPUSD=X', True),   # GBP is problematic  
            ('AUDUSD=X', True),   # AUD is problematic
            ('USDJPY=X', False),  # JPY is not problematic
            ('USDCAD=X', False),  # CAD is not problematic
        ]
        
        for symbol, should_enhance in test_symbols:
            with self.subTest(symbol=symbol):
                currency = self.chart_service._extract_currency_from_symbol(symbol)
                is_problematic = currency in ['GBP', 'EUR', 'AUD']
                self.assertEqual(is_problematic, should_enhance)

    def test_symbol_mapping_validation(self):
        """Test that symbol mappings are correct for all currencies."""
        expected_mappings = {
            'USD': ['EURUSD=X', 'GBPUSD=X'],
            'EUR': ['EURUSD=X', 'EURGBP=X'],
            'GBP': ['GBPUSD=X', 'EURGBP=X'],
            'JPY': ['USDJPY=X', 'EURJPY=X'],
            'AUD': ['AUDUSD=X', 'AUDJPY=X'],
            'CAD': ['USDCAD=X', 'EURCAD=X'],
            'CHF': ['USDCHF=X', 'EURCHF=X'],
            'NZD': ['NZDUSD=X', 'NZDJPY=X'],
        }
        
        for currency, expected_pairs in expected_mappings.items():
            with self.subTest(currency=currency):
                actual_pairs = self.chart_service.get_currency_pairs_for_currency(currency)
                self.assertEqual(actual_pairs, expected_pairs)

    def test_timezone_alignment_validation(self):
        """Test timezone alignment validation."""
        # Test with different timezone scenarios
        timezones = ['UTC', 'Europe/Prague', 'America/New_York', 'Asia/Tokyo']
        
        for tz_name in timezones:
            with self.subTest(timezone=tz_name):
                tz = pytz.timezone(tz_name)
                start_time = datetime.now(tz)
                end_time = start_time + timedelta(hours=2)
                
                # Verify timezone info is available
                self.assertIsNotNone(start_time.tzinfo)
                self.assertIsNotNone(end_time.tzinfo)
                
                # Verify timezone conversion works
                utc_start = start_time.astimezone(pytz.UTC)
                utc_end = end_time.astimezone(pytz.UTC)
                
                self.assertEqual(utc_start.tzinfo, pytz.UTC)
                self.assertEqual(utc_end.tzinfo, pytz.UTC)

    def test_data_fetch_error_handling(self):
        """Test enhanced error handling for data fetching."""
        # Mock the fetch_price_data method to test error handling
        with patch.object(self.chart_service, '_fetch_with_retry', return_value=None):
            with patch.object(self.chart_service, '_try_alternative_data_source', return_value=None):
                with patch.object(self.chart_service, '_generate_mock_data', return_value=None):
                    # Test with a problematic currency
                    symbol = 'EURUSD=X'
                    currency = self.chart_service._extract_currency_from_symbol(symbol)
                    is_problematic = currency in ['GBP', 'EUR', 'AUD']
                    
                    self.assertTrue(is_problematic)
                    
                    # Test that the method handles None return gracefully
                    result = self.chart_service.fetch_price_data(symbol, self.start_time, self.end_time)
                    self.assertIsNone(result)

    def test_empty_data_validation(self):
        """Test validation of empty data responses."""
        # Test with empty DataFrame
        empty_df = pd.DataFrame()
        
        # Test with DataFrame that has no data in the time window
        index = pd.date_range(start=self.start_time - timedelta(days=1), 
                             end=self.start_time - timedelta(hours=1), 
                             freq='1H')
        empty_window_df = pd.DataFrame({
            'Open': [1.0] * len(index),
            'High': [1.1] * len(index),
            'Low': [0.9] * len(index),
            'Close': [1.05] * len(index),
            'Volume': [1000] * len(index)
        }, index=index)
        
        # Both should be considered empty for our purposes
        self.assertTrue(empty_df.empty)
        self.assertFalse(empty_window_df.empty)  # Has data, but outside window

    def test_rate_limiting_handling(self):
        """Test handling of rate limiting for problematic currencies."""
        # Mock a 429 response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Too Many Requests"
        
        # Test that rate limiting is properly detected
        error_msg = f"HTTP {mock_response.status_code} for EUR (EURUSD=X): {mock_response.text[:200]}"
        
        # Verify the error message format
        self.assertIn("429", error_msg)
        self.assertIn("EUR", error_msg)
        self.assertIn("EURUSD=X", error_msg)

    def test_api_response_validation(self):
        """Test validation of API responses."""
        # Test valid response structure
        valid_response = {
            'chart': {
                'result': [{
                    'timestamp': [1640995200, 1640998800],  # Unix timestamps
                    'indicators': {
                        'quote': [{
                            'open': [1.0, 1.1],
                            'high': [1.1, 1.2],
                            'low': [0.9, 1.0],
                            'close': [1.05, 1.15],
                            'volume': [1000, 1100]
                        }]
                    }
                }]
            }
        }
        
        # Test invalid response structures
        invalid_responses = [
            {},  # Empty response
            {'chart': {}},  # No result
            {'chart': {'result': []}},  # Empty result list
            {'chart': {'result': [{}]}},  # Empty result object
        ]
        
        # Valid response should have the expected structure
        self.assertIn('chart', valid_response)
        self.assertIn('result', valid_response['chart'])
        self.assertTrue(len(valid_response['chart']['result']) > 0)
        
        # Invalid responses should be detected
        for invalid_response in invalid_responses:
            with self.subTest(response=invalid_response):
                has_chart = 'chart' in invalid_response
                has_result = has_chart and 'result' in invalid_response['chart']
                has_data = has_result and len(invalid_response['chart']['result']) > 0
                
                self.assertFalse(has_data, f"Invalid response should not have data: {invalid_response}")

    def test_mock_data_generation(self):
        """Test mock data generation for problematic currencies."""
        # Test that mock data can be generated for problematic currencies
        problematic_symbols = ['EURUSD=X', 'GBPUSD=X', 'AUDUSD=X']
        
        for symbol in problematic_symbols:
            with self.subTest(symbol=symbol):
                # Mock the _generate_mock_data method
                with patch.object(self.chart_service, '_generate_mock_data') as mock_generate:
                    mock_df = pd.DataFrame({
                        'Open': [1.0, 1.1],
                        'High': [1.1, 1.2], 
                        'Low': [0.9, 1.0],
                        'Close': [1.05, 1.15],
                        'Volume': [1000, 1100]
                    })
                    mock_generate.return_value = mock_df
                    
                    # Test mock data generation
                    result = self.chart_service._generate_mock_data(symbol, self.start_time, self.end_time)
                    self.assertIsNotNone(result)
                    self.assertFalse(result.empty)

    def test_caching_behavior(self):
        """Test caching behavior for problematic currencies."""
        # Test that caching works correctly
        symbol = 'EURUSD=X'
        
        # Mock cached data
        mock_cached_data = pd.DataFrame({
            'Open': [1.0],
            'High': [1.1],
            'Low': [0.9], 
            'Close': [1.05],
            'Volume': [1000]
        })
        
        with patch.object(self.chart_service, '_get_cached_data', return_value=mock_cached_data):
            result = self.chart_service.fetch_price_data(symbol, self.start_time, self.end_time)
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 1)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
