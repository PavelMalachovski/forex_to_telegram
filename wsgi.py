
#!/usr/bin/env python3
"""
WSGI entry point for the Forex Telegram Bot application.
This file is used by gunicorn and other WSGI servers.
"""

from app import app

if __name__ == "__main__":
    app.run()
