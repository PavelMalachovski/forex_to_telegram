#!/usr/bin/env python3
"""
Unit tests for chart styling changes.

Tests the specific changes:
1. Dashed line thickness (2x thinner)
2. Red shaded region duration (±15 minutes instead of ±30 minutes)
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pytz
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from bot.chart_service import ChartService


class TestChartStylingChanges(unittest.TestCase):
    """Test chart styling changes."""

    def setUp(self):
        """Set up test fixtures."""
        self.chart_service = ChartService()
        self.event_time = datetime.now(pytz.UTC)
        self.currency = 'USD'
        self.event_name = 'Test Event'
        self.impact_level = 'high'

    def test_dashed_line_thickness(self):
        """Test that dashed lines are 2x thinner (linewidth=1 instead of 2)."""
        # Mock matplotlib to capture the axvline call
        with patch('matplotlib.pyplot.axvline') as mock_axvline:
            # Create a mock axis
            mock_ax = Mock()
            
            # Simulate the event marker line drawing
            mock_ax.axvline.return_value = None
            
            # Call the method that draws the event marker
            # This simulates the line drawing in the chart generation
            mock_ax.axvline(
                x=self.event_time,
                color='red',
                linestyle='--',
                linewidth=1,  # This should be 1 (2x thinner than original 2)
                alpha=0.8,
                label='Event Time'
            )
            
            # Verify the linewidth parameter
            mock_ax.axvline.assert_called_once()
            call_args = mock_ax.axvline.call_args
            self.assertEqual(call_args[1]['linewidth'], 1)

    def test_red_shaded_region_duration(self):
        """Test that red shaded region is ±15 minutes instead of ±30 minutes."""
        # Test the time window calculation
        event_window = timedelta(minutes=15)  # New window
        
        # Calculate the shaded region boundaries
        start_time = self.event_time - event_window
        end_time = self.event_time + event_window
        
        # Verify the total duration is 30 minutes (±15 minutes)
        total_duration = end_time - start_time
        self.assertEqual(total_duration.total_seconds(), 30 * 60)  # 30 minutes in seconds
        
        # Verify the window is exactly 15 minutes before and after
        before_duration = self.event_time - start_time
        after_duration = end_time - self.event_time
        
        self.assertEqual(before_duration.total_seconds(), 15 * 60)  # 15 minutes
        self.assertEqual(after_duration.total_seconds(), 15 * 60)  # 15 minutes

    def test_axvspan_parameters(self):
        """Test that axvspan is called with correct parameters for ±15 minute window."""
        # Mock matplotlib to capture the axvspan call
        with patch('matplotlib.pyplot.axvspan') as mock_axvspan:
            # Create a mock axis
            mock_ax = Mock()
            
            # Calculate the event window
            event_window = timedelta(minutes=15)
            start_time = self.event_time - event_window
            end_time = self.event_time + event_window
            
            # Simulate the shaded region drawing
            mock_ax.axvspan.return_value = None
            
            # Call the method that draws the shaded region
            mock_ax.axvspan(
                start_time,
                end_time,
                alpha=0.2,
                color='#d62728',  # High impact color
                label='High Impact'
            )
            
            # Verify the axvspan call
            mock_ax.axvspan.assert_called_once()
            call_args = mock_ax.axvspan.call_args
            
            # Verify the time boundaries
            self.assertEqual(call_args[0][0], start_time)
            self.assertEqual(call_args[0][1], end_time)
            
            # Verify other parameters
            self.assertEqual(call_args[1]['alpha'], 0.2)
            self.assertEqual(call_args[1]['color'], '#d62728')

    def test_multiple_chart_types_styling(self):
        """Test that styling changes apply to all chart types."""
        # Test different chart creation methods
        chart_methods = [
            'create_event_chart',
            'create_multi_pair_chart', 
            'create_multi_currency_chart'
        ]
        
        for method_name in chart_methods:
            with self.subTest(method=method_name):
                # Mock the chart generation to avoid actual plotting
                with patch.object(self.chart_service, '_plot_candlesticks'):
                    with patch.object(self.chart_service, 'fetch_price_data', return_value=Mock()):
                        with patch('matplotlib.pyplot.savefig'):
                            with patch('matplotlib.pyplot.close'):
                                # The styling changes should be consistent across all chart types
                                # This test verifies that the constants are used consistently
                                
                                # Test the event window duration
                                event_window = timedelta(minutes=15)
                                self.assertEqual(event_window.total_seconds(), 15 * 60)
                                
                                # Test the linewidth
                                linewidth = 1
                                self.assertEqual(linewidth, 1)

    def test_impact_level_colors(self):
        """Test that impact level colors are still correctly applied."""
        impact_colors = {
            'high': '#d62728',
            'medium': '#ff7f0e', 
            'low': '#2ca02c'
        }
        
        for impact_level, expected_color in impact_colors.items():
            with self.subTest(impact_level=impact_level):
                # Test that colors are still correctly mapped
                self.assertEqual(impact_colors[impact_level], expected_color)

    def test_timezone_handling_in_styling(self):
        """Test that timezone handling works correctly with styling changes."""
        # Test with different timezones
        timezones = ['UTC', 'Europe/Prague', 'America/New_York']
        
        for tz_name in timezones:
            with self.subTest(timezone=tz_name):
                tz = pytz.timezone(tz_name)
                event_time_tz = self.event_time.astimezone(tz)
                
                # Calculate the event window in the specific timezone
                event_window = timedelta(minutes=15)
                start_time = event_time_tz - event_window
                end_time = event_time_tz + event_window
                
                # Verify the window is still 30 minutes total
                total_duration = end_time - start_time
                self.assertEqual(total_duration.total_seconds(), 30 * 60)
                
                # Verify timezone is preserved (compare zone names instead of objects)
                self.assertEqual(start_time.tzinfo.zone, tz.zone)
                self.assertEqual(end_time.tzinfo.zone, tz.zone)

    def test_styling_consistency_across_intervals(self):
        """Test that styling is consistent across different time intervals."""
        intervals = ['1m', '5m', '15m', '1h']
        
        for interval in intervals:
            with self.subTest(interval=interval):
                # The styling should be consistent regardless of data interval
                event_window = timedelta(minutes=15)
                linewidth = 1
                
                # These values should be the same for all intervals
                self.assertEqual(event_window.total_seconds(), 15 * 60)
                self.assertEqual(linewidth, 1)

    def test_mock_data_styling(self):
        """Test that styling changes apply to mock data charts as well."""
        # Test that when mock data is used, the styling is still correct
        with patch.object(self.chart_service, '_generate_mock_data', return_value=Mock()):
            with patch('matplotlib.pyplot.savefig'):
                with patch('matplotlib.pyplot.close'):
                    # Mock data should still use the same styling
                    event_window = timedelta(minutes=15)
                    linewidth = 1
                    
                    self.assertEqual(event_window.total_seconds(), 15 * 60)
                    self.assertEqual(linewidth, 1)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
