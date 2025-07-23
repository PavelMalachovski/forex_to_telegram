import os
import sys
from datetime import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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
        "actual": "105K",  # Added missing actual field
        "forecast": "100K",
        "previous": "90K",
        "analysis": "Test"
    }]
    msg = MessageFormatter.format_news_message(news, datetime(2024, 1, 1), "high")
    assert "Forex News for" in msg
    assert "USD" in msg


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
