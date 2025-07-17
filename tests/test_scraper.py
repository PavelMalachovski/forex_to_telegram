import os
import sys
from datetime import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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
    items = scraper._parse_news_from_html(html, "high")
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
