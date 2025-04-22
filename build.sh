#!/bin/bash
echo "▶ Installing requirements"
pip install -r requirements.txt

echo "▶ Installing Playwright browsers"
playwright install chromium
