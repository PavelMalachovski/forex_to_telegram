import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from bot.utils import escape_markdown_v2


def test_escape_markdown_v2():
    text = "Hello [World]! *Example* _test_"
    expected = "Hello \\[World\\]\\! \\*Example\\* \\_test\\_"
    assert escape_markdown_v2(text) == expected


def test_escape_markdown_v2_with_dots():
    text = "Price: 1.2345"
    expected = "Price: 1\\.2345"
    assert escape_markdown_v2(text) == expected


def test_escape_markdown_v2_comprehensive():
    text = "Test_*[]()~`>#+-=|{}.!\\"
    expected = "Test\\_\\*\\[\\]\\(\\)\\~\\`\\>\\#\\+\\-\\=\\|\\{\\}\\.\\!\\\\"
    assert escape_markdown_v2(text) == expected
