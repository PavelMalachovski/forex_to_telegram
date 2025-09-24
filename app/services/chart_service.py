"""Chart generation service implementation."""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import yfinance as yf
import pytz

from app.models.chart import ChartRequest, ChartResponse, ChartData, OHLCData
from app.core.exceptions import ChartGenerationError, DataFetchError
from app.core.config import settings
import structlog

logger = structlog.get_logger(__name__)


class ChartService:
    """Chart generation service."""

    def __init__(self):
        self.timezone = pytz.timezone(settings.chart.display_timezone)
        self.min_request_interval = settings.chart.yf_min_request_interval_sec

    async def generate_chart(self, request: ChartRequest) -> ChartResponse:
        """Generate chart for the given request."""
        try:
            logger.info("Generating chart", currency=request.currency, event_name=request.event_name)

            # Fetch price data
            chart_data = await self._fetch_price_data(request)

            if not chart_data or not chart_data.data:
                return ChartResponse(
                    success=False,
                    error_message="No price data available for the specified time range"
                )

            # Generate chart image
            chart_image = await self._generate_chart_image(chart_data, request)

            return ChartResponse(
                success=True,
                chart_data=chart_data,
                chart_image=chart_image,
                metadata={
                    "currency": request.currency,
                    "event_name": request.event_name,
                    "impact_level": request.impact_level,
                    "data_points": len(chart_data.data),
                    "generated_at": datetime.utcnow().isoformat()
                }
            )

        except Exception as e:
            logger.error("Failed to generate chart", error=str(e), exc_info=True)
            return ChartResponse(
                success=False,
                error_message=f"Chart generation failed: {str(e)}"
            )

    async def _fetch_price_data(self, request: ChartRequest) -> Optional[ChartData]:
        """Fetch price data for the chart."""
        try:
            # Calculate time range
            start_time = request.event_time - timedelta(hours=request.window_hours)
            end_time = request.event_time + timedelta(hours=request.window_hours)

            # Get currency pairs for the currency
            symbols = self._get_currency_pairs_for_currency(request.currency)

            if not symbols:
                raise DataFetchError(f"No currency pairs found for {request.currency}")

            # Fetch data for the first available symbol
            symbol = symbols[0]
            logger.info("Fetching price data", symbol=symbol, start=start_time, end=end_time)

            # Convert to timezone-aware datetimes
            start_utc = start_time.astimezone(pytz.UTC)
            end_utc = end_time.astimezone(pytz.UTC)

            # Fetch data from Yahoo Finance
            ticker = yf.Ticker(symbol)
            data = ticker.history(
                start=start_utc,
                end=end_utc,
                interval="1h" if request.window_hours <= 12 else "1d"
            )

            if data.empty:
                raise DataFetchError(f"No data available for {symbol}")

            # Convert to OHLC data
            ohlc_data = []
            for timestamp, row in data.iterrows():
                ohlc_data.append(OHLCData(
                    timestamp=timestamp.to_pydatetime(),
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=float(row['Volume']) if 'Volume' in row else None
                ))

            return ChartData(
                currency=request.currency,
                data=ohlc_data,
                metadata={
                    "symbol": symbol,
                    "data_source": "yahoo_finance",
                    "interval": "1h" if request.window_hours <= 12 else "1d"
                }
            )

        except Exception as e:
            logger.error("Failed to fetch price data", error=str(e), exc_info=True)
            raise DataFetchError(f"Failed to fetch price data: {e}")

    def _get_currency_pairs_for_currency(self, currency: str) -> list:
        """Get currency pairs for a given currency."""
        currency_pairs = {
            "USD": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "NZDUSD=X"],
            "EUR": ["EURUSD=X", "EURGBP=X", "EURJPY=X", "EURAUD=X", "EURCAD=X", "EURCHF=X"],
            "GBP": ["GBPUSD=X", "EURGBP=X", "GBPJPY=X", "GBPAUD=X", "GBPCAD=X", "GBPCHF=X"],
            "JPY": ["USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X", "CADJPY=X", "CHFJPY=X"],
            "AUD": ["AUDUSD=X", "EURAUD=X", "GBPAUD=X", "AUDJPY=X", "AUDCAD=X", "AUDCHF=X"],
            "CAD": ["USDCAD=X", "EURCAD=X", "GBPCAD=X", "CADJPY=X", "AUDCAD=X", "CADCHF=X"],
            "CHF": ["USDCHF=X", "EURCHF=X", "GBPCHF=X", "CHFJPY=X", "AUDCHF=X", "CADCHF=X"],
            "NZD": ["NZDUSD=X", "NZDEUR=X", "NZDGBP=X", "NZDJPY=X", "NZDAUD=X", "NZDCAD=X"],
            "XAU": ["XAUUSD=X", "XAU=X"],
            "BTC": ["BTC-USD", "BTCUSD=X"],
            "ETH": ["ETH-USD", "ETHUSD=X"]
        }

        return currency_pairs.get(currency, [])

    async def _generate_chart_image(self, chart_data: ChartData, request: ChartRequest) -> bytes:
        """Generate chart image."""
        try:
            # Set up matplotlib
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(12, 8))

            # Extract data
            timestamps = [d.timestamp for d in chart_data.data]
            opens = [d.open for d in chart_data.data]
            highs = [d.high for d in chart_data.data]
            lows = [d.low for d in chart_data.data]
            closes = [d.close for d in chart_data.data]
            volumes = [d.volume for d in chart_data.data] if chart_data.data[0].volume else None

            # Plot candlesticks
            self._plot_candlesticks(ax, timestamps, opens, highs, lows, closes)

            # Plot volume if available
            if volumes:
                ax2 = ax.twinx()
                ax2.bar(timestamps, volumes, alpha=0.3, color='gray', width=0.8)
                ax2.set_ylabel('Volume', color='gray')
                ax2.tick_params(axis='y', labelcolor='gray')

            # Customize chart
            ax.set_title(
                f"{request.currency} Price Chart - {request.event_name}",
                fontsize=16,
                fontweight='bold',
                color='white'
            )
            ax.set_xlabel('Time', color='white')
            ax.set_ylabel('Price', color='white')
            ax.tick_params(colors='white')

            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
            plt.xticks(rotation=45)

            # Add event time line
            ax.axvline(x=request.event_time, color='red', linestyle='--', alpha=0.7, label='Event Time')

            # Add impact level annotation
            ax.text(
                0.02, 0.98,
                f"Impact: {request.impact_level.upper()}",
                transform=ax.transAxes,
                fontsize=12,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='red', alpha=0.7)
            )

            # Add price change annotation
            if len(closes) >= 2:
                price_change = closes[-1] - closes[0]
                price_change_pct = (price_change / closes[0]) * 100
                color = 'green' if price_change >= 0 else 'red'
                ax.text(
                    0.98, 0.98,
                    f"Change: {price_change:.4f} ({price_change_pct:+.2f}%)",
                    transform=ax.transAxes,
                    fontsize=12,
                    verticalalignment='top',
                    horizontalalignment='right',
                    color=color,
                    bbox=dict(boxstyle='round', facecolor='black', alpha=0.7)
                )

            # Adjust layout
            plt.tight_layout()

            # Save to bytes
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            image_bytes = buffer.getvalue()
            buffer.close()
            plt.close(fig)

            return image_bytes

        except Exception as e:
            logger.error("Failed to generate chart image", error=str(e), exc_info=True)
            raise ChartGenerationError(f"Failed to generate chart image: {e}")

    def _plot_candlesticks(self, ax, timestamps, opens, highs, lows, closes):
        """Plot candlestick chart."""
        for i, (timestamp, open_price, high, low, close) in enumerate(zip(timestamps, opens, highs, lows, closes)):
            color = 'green' if close >= open_price else 'red'

            # Draw the high-low line
            ax.plot([timestamp, timestamp], [low, high], color='white', linewidth=1)

            # Draw the open-close rectangle
            height = abs(close - open_price)
            bottom = min(open_price, close)

            ax.bar(timestamp, height, bottom=bottom, width=0.8, color=color, alpha=0.8)

            # Draw the open and close ticks
            ax.plot([timestamp - 0.3, timestamp], [open_price, open_price], color='white', linewidth=2)
            ax.plot([timestamp, timestamp + 0.3], [close, close], color='white', linewidth=2)
