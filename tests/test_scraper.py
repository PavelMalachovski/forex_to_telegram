#!/usr/bin/env python3
"""Test script for scraper functionality."""

import sys
import os
from datetime import datetime

# Add the parent directory to the path to find the bot module
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch

from bot.config import Config
from bot.scraper import ForexNewsScraper, ChatGPTAnalyzer, MessageFormatter


def test_parse_news_from_html():
    config = Config()
    analyzer = ChatGPTAnalyzer(None)
    scraper = ForexNewsScraper(config, analyzer)
    html = '''
    <table class="calendar__table">
      <tr class="calendar__row" data-event-id="1">
        <td class="calendar__time">12:30pm</td>
        <td class="calendar__currency">USD</td>
        <td class="calendar__event-title">Nonfarm Payrolls</td>
        <td class="calendar__forecast">100K</td>
        <td class="calendar__previous">90K</td>
        <td class="calendar__impact"><span class="icon icon--ff-impact-red"></span></td>
      </tr>
    </table>
    '''
    items = scraper._parse_news_from_html(html)
    assert len(items) == 1
    item = items[0]
    assert item["currency"] == "USD"
    assert item["event"] == "Nonfarm Payrolls"


def test_message_formatter():
    news = [{
        "time": "12:30pm",
        "currency": "USD",
        "event": "NFP",
        "actual": "105K",
        "forecast": "100K",
        "previous": "90K",
        "analysis": "Test",
        "group_analysis": False
    }]
    msg = MessageFormatter.format_news_message(news, datetime(2024, 1, 1), "high", analysis_required=True)
    assert "Forex News for" in msg
    assert "USD" in msg
    assert "Test" in msg
    # Test without analysis
    msg_no = MessageFormatter.format_news_message(news, datetime(2024, 1, 1), "high", analysis_required=False)
    assert "Test" not in msg_no


def test_message_formatter_group_event():
    # Two events, same currency and time (group event)
    news = [
        {
            "time": "12:30pm",
            "currency": "USD",
            "event": "NFP",
            "actual": "105K",
            "forecast": "100K",
            "previous": "90K",
            "analysis": "GroupAnalysis",
            "group_analysis": True
        },
        {
            "time": "12:30pm",
            "currency": "USD",
            "event": "Unemployment",
            "actual": "4.0%",
            "forecast": "3.9%",
            "previous": "3.8%",
            "analysis": "GroupAnalysis",
            "group_analysis": True
        }
    ]
    msg = MessageFormatter.format_news_message(news, datetime(2024, 1, 1), "high", analysis_required=True)
    assert "GROUP EVENT" in msg
    assert "Group Analysis" in msg
    # Should only show analysis once
    assert msg.count("Group Analysis") == 1
    # Test without analysis
    msg_no = MessageFormatter.format_news_message(news, datetime(2024, 1, 1), "high", analysis_required=False)
    assert "Group Analysis" not in msg_no


def test_is_blocked_content():
    config = Config()
    analyzer = ChatGPTAnalyzer(None)
    scraper = ForexNewsScraper(config, analyzer)
    blocked_cases = [
        "<html>Cloudflare - Just a moment...</html>",
        "Access Denied", "Forbidden", "Rate limit exceeded", "Suspicious activity detected"
    ]
    for html in blocked_cases:
        assert scraper._is_blocked_content(html)
    assert not scraper._is_blocked_content("<html><body>Normal content with enough length" + ("a"*1000) + "</body></html>")

def test_parse_news_from_html_empty():
    config = Config()
    analyzer = ChatGPTAnalyzer(None)
    scraper = ForexNewsScraper(config, analyzer)
    assert scraper._parse_news_from_html("") == []

def test_parse_news_from_html_malformed():
    config = Config()
    analyzer = ChatGPTAnalyzer(None)
    scraper = ForexNewsScraper(config, analyzer)
    html = "<html><body><div>No table here</div></body></html>"
    assert scraper._parse_news_from_html(html) == []

def test_message_formatter_empty():
    msg = MessageFormatter.format_news_message([], datetime(2024, 1, 1), "high")
    assert "No news found" in msg

def test_chatgpt_analyzer_no_key():
    analyzer = ChatGPTAnalyzer(None)
    result = analyzer.analyze_news({"time": "", "currency": "", "event": "", "forecast": "", "previous": ""})
    assert "skipped" in result

def test_chatgpt_analyzer_with_key():
    analyzer = ChatGPTAnalyzer("fake-key")
    news_item = {"time": "", "currency": "", "event": "", "forecast": "", "previous": ""}
    with patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = {"choices": [{"message": {"content": "Test analysis"}}]}
        mock_post.return_value.raise_for_status = lambda: None
        result = analyzer.analyze_news(news_item)
        assert "Test analysis" in result
