# Deployment Instructions for Render.com

## Overview
These improved files fix the critical issues with ForexFactory anti-bot detection and Telegram MarkdownV2 formatting errors.

## Key Improvements

### 1. Enhanced Anti-Bot Detection Bypass
- **Comprehensive browser stealth configuration** with 25+ launch arguments
- **Dynamic selector waiting** with multiple fallback strategies
- **Request timing randomization** and exponential backoff retry logic
- **Enhanced headers and fingerprint masking**
- **Bot detection pattern recognition** and handling

### 2. Fixed Telegram MarkdownV2 Escaping
- **Corrected double escaping issue** in `escape_markdown_v2()` function
- **Proper character escaping order** (backslash first to prevent double escaping)
- **Comprehensive error handling** with fallback to plain text
- **Validation functions** for MarkdownV2 format

### 3. Improved Error Handling
- **Exponential backoff** for retry attempts (2^attempt + random jitter)
- **Better logging** for debugging selector timeouts
- **Multiple fallback mechanisms** for different ForexFactory layouts
- **Screenshot capture** on final failure for debugging

## Deployment Steps

### Step 1: Update Files
Replace the existing files in your repository:
```bash
# Replace bot/scraper.py with improved_scraper.py
# Replace bot/utils.py with improved_utils.py
# Update requirements.txt with requirements_updated.txt
```

### Step 2: Update Requirements (if needed)
The improved version adds optional dependencies for better performance:
- `fake-useragent`: For rotating user agents
- `tenacity`: For advanced retry mechanisms

### Step 3: Environment Variables
Ensure these environment variables are set in Render.com:
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
CHATGPT_API_KEY=your_openai_key (optional)
TIMEZONE=Europe/Prague (or your preferred timezone)
```

### Step 4: Render.com Configuration
Update your `render.yaml` or web service settings:

```yaml
services:
  - type: web
    name: forex-scraper
    env: python
    buildCommand: pip install -r requirements.txt && playwright install chromium
    startCommand: gunicorn app:app
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: PLAYWRIGHT_BROWSERS_PATH
        value: /opt/render/project/.playwright
```

### Step 5: Build Command Update
Make sure your build command includes Playwright browser installation:
```bash
pip install -r requirements.txt && playwright install chromium --with-deps
```

## Testing the Fixes

### 1. Test Anti-Bot Detection
The improved scraper should now:
- Successfully bypass ForexFactory's basic anti-bot measures
- Handle different page layouts and selector changes
- Retry with exponential backoff on failures
- Provide detailed logging for debugging

### 2. Test MarkdownV2 Formatting
The fixed utils should now:
- Properly escape special characters without double escaping
- Handle edge cases like periods and exclamation marks
- Fallback to plain text if MarkdownV2 fails
- Validate MarkdownV2 format before sending

## Monitoring and Debugging

### Logs to Watch For
- `"Successfully loaded content with selector: X"` - Indicates successful page loading
- `"Bot blocking detected: X"` - Indicates anti-bot measures triggered
- `"MarkdownV2 validation failed"` - Indicates formatting issues
- `"Successfully sent after fixing MarkdownV2 issues"` - Indicates successful recovery

### Common Issues and Solutions

#### Issue: Still getting selector timeouts
**Solution**: The improved version tries multiple selectors and has longer timeouts. Check logs for which selectors are being attempted.

#### Issue: MarkdownV2 errors persist
**Solution**: The new version has comprehensive fallback to plain text. Check the `validate_markdown_v2` function output in logs.

#### Issue: Rate limiting or blocking
**Solution**: The improved version has randomized delays and better stealth. Consider increasing the base delay in `ForexNewsScraper.base_delay`.

## Performance Considerations

### Memory Usage
The enhanced browser configuration may use slightly more memory. Monitor your Render.com resource usage.

### Request Timing
The improved version includes random delays (1-4 seconds) to mimic human behavior. This may slow down scraping but improves reliability.

### Retry Logic
Failed requests now retry up to 5 times with exponential backoff. This improves success rate but may increase execution time.

## Advanced Configuration

### Customizing Stealth Settings
You can modify the browser launch arguments in `get_browser_page()` function to adjust stealth level.

### Adjusting Retry Behavior
Modify `ForexNewsScraper.max_retries` and `ForexNewsScraper.base_delay` to customize retry behavior.

### Adding More Selectors
If ForexFactory changes their layout, add new selectors to the `selectors_to_try` lists in the scraper.

## Rollback Plan
If issues occur, you can quickly rollback by:
1. Reverting to the original `bot/scraper.py` and `bot/utils.py`
2. Removing the new dependencies from `requirements.txt`
3. Redeploying on Render.com

## Support
If you encounter issues:
1. Check the Render.com logs for specific error messages
2. Look for the improved logging output to identify the failure point
3. Consider enabling screenshot debugging by uncommenting Pillow in requirements
4. Test locally first using the same environment variables