# Chart Features Documentation

## Overview

The forex bot now includes advanced chart generation capabilities that automatically create visual representations of price movements around news events. This feature helps users understand market reactions to economic announcements and provides valuable context for trading decisions.

## Features

### 1. Automatic Chart Generation
- **Real-time Data**: Fetches historical price data from Yahoo Finance API
- **Event Markers**: Vertical lines mark the exact time of news releases
- **Impact Visualization**: Color-coded shading indicates impact levels (High/Medium/Low)
- **Price Analysis**: Shows price changes and percentage movements

### 2. Chart Types

#### Single Pair Charts
- Shows price movement for the primary currency pair related to the event
- Includes volume data when available
- Displays price change statistics
- Example: USD Non-Farm Payrolls → EUR/USD chart

#### Multi-Pair Charts
- Compares multiple currency pairs simultaneously
- Normalized prices for easy comparison
- Broader market context
- Example: USD event shows EUR/USD, GBP/USD, USD/JPY

### 3. User Settings

#### Chart Enable/Disable
- Users can toggle chart generation on/off
- Free-tier users can disable to save API quota
- Premium users get enhanced chart features

#### Chart Type Selection
- **Single**: One currency pair chart
- **Multi**: Multiple pairs comparison
- **None**: Text-only notifications

#### Time Window Configuration
- Configurable hours before/after event (1, 2, 4, 6 hours)
- Default: 2 hours (1 hour before, 1 hour after)

## Technical Implementation

### Chart Service (`bot/chart_service.py`)

```python
class ChartService:
    def create_event_chart(self, currency, event_time, event_name, impact_level, window_hours)
    def create_multi_pair_chart(self, currency, event_time, event_name, impact_level, window_hours)
    def fetch_price_data(self, symbol, start_time, end_time)
```

### Key Features

#### Data Caching
- 15-minute cache for price data
- Reduces API calls to Yahoo Finance
- Automatic cache cleanup

#### Currency Pair Mapping
```python
currency_pairs = {
    'USD': 'EURUSD=X',  # EUR/USD for USD events
    'EUR': 'EURUSD=X',  # EUR/USD for EUR events
    'GBP': 'GBPUSD=X',  # GBP/USD for GBP events
    # ... more mappings
}
```

#### Chart Generation
- Uses matplotlib for high-quality charts
- Professional styling and formatting
- Impact level color coding
- Event time markers

### Database Schema

New columns added to `users` table:

```sql
ALTER TABLE users ADD COLUMN charts_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN chart_type VARCHAR(20) DEFAULT 'single';
ALTER TABLE users ADD COLUMN chart_window_hours INTEGER DEFAULT 2;
```

### Integration with Notification System

The chart service integrates seamlessly with the existing notification system:

1. **Event Detection**: When a news event is detected
2. **User Preferences**: Check if user has charts enabled
3. **Chart Generation**: Create appropriate chart type
4. **Message Sending**: Send photo with caption or fallback to text

## Usage Examples

### Basic Chart Generation
```python
from bot.chart_service import chart_service

# Generate single pair chart
chart_buffer = chart_service.create_event_chart(
    currency='USD',
    event_time=datetime.now(),
    event_name='Non-Farm Payrolls',
    impact_level='high',
    window_hours=2
)

# Send to Telegram
bot.send_photo(user_id, chart_buffer, caption="News Alert")
```

### Multi-Pair Chart
```python
# Generate multi-pair comparison
chart_buffer = chart_service.create_multi_pair_chart(
    currency='USD',
    event_time=datetime.now(),
    event_name='FOMC Meeting',
    impact_level='high',
    window_hours=4
)
```

## User Interface

### Settings Menu
Users can configure chart settings through the bot's settings menu:

1. **Settings** → **Notifications** → **Charts**
2. **Enable/Disable**: Toggle chart generation
3. **Chart Type**: Select single/multi/none
4. **Time Window**: Choose hours before/after event

### Example Settings Flow
```
⚙️ Your Settings:
🔔 Notifications: ✅
📈 Charts: ✅ (single)

Configure your chart settings:
📈 Charts: ✅
📊 Type: Single Pair
⏱️ Window: 2h
```

## Performance Considerations

### API Rate Limiting
- Yahoo Finance has rate limits
- Caching reduces API calls by 90%+
- Users can disable charts to save quota

### Memory Management
- Charts are generated on-demand
- Automatic cleanup of old cache entries
- Efficient image compression

### Error Handling
- Graceful fallback to text-only notifications
- Logging of chart generation failures
- User-friendly error messages

## Testing

Run the chart service tests:

```bash
python tests/test_chart_service.py
```

Tests cover:
- Service initialization
- Currency pair mapping
- Chart generation
- Error handling
- Cache functionality

## Migration

To add chart functionality to existing installations:

1. **Run Database Migration**:
```bash
alembic upgrade head
```

2. **Install Dependencies**:
```bash
pip install yfinance matplotlib plotly pandas numpy
```

3. **Restart Bot**: The new features will be available immediately

## Configuration

### Environment Variables
```bash
# Optional: Custom cache directory
CHART_CACHE_DIR=/path/to/cache
```

### Default Settings
- Charts disabled by default
- Single pair chart type
- 2-hour time window
- 15-minute data cache

## Troubleshooting

### Common Issues

1. **No Chart Generated**
   - Check if Yahoo Finance data is available
   - Verify event time is in the future
   - Check user chart settings

2. **API Rate Limits**
   - Reduce chart window size
   - Enable caching
   - Disable charts for free users

3. **Memory Issues**
   - Reduce chart quality (DPI)
   - Implement chart cleanup
   - Monitor cache size

### Debug Logging
```python
import logging
logging.getLogger('bot.chart_service').setLevel(logging.DEBUG)
```

## Future Enhancements

### Planned Features
- **Interactive Charts**: Plotly-based interactive charts
- **Technical Indicators**: RSI, MACD, moving averages
- **Custom Timeframes**: 5-minute, 15-minute intervals
- **Chart Templates**: Different visual styles
- **Export Options**: PDF, PNG, SVG formats

### Performance Improvements
- **Async Chart Generation**: Non-blocking chart creation
- **Pre-generated Charts**: Cache common event charts
- **Compression**: Optimize image sizes
- **CDN Integration**: Faster chart delivery

## Support

For issues with chart functionality:
1. Check the logs for error messages
2. Verify Yahoo Finance API access
3. Test with different currency pairs
4. Review user chart settings

The chart feature enhances the bot's value by providing visual context for news events, helping users make more informed trading decisions.
