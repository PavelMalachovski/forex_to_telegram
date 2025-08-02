import logging
import os
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import numpy as np
from io import BytesIO
import pytz

logger = logging.getLogger(__name__)


class ChartService:
    """Service for generating forex charts around news events."""

    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), 'forex_charts')
        self._ensure_cache_dir()

        # Currency pair mappings for different currencies
        self.currency_pairs = {
            'USD': 'EURUSD=X',  # EUR/USD as benchmark for USD events
            'EUR': 'EURUSD=X',  # EUR/USD for EUR events
            'GBP': 'GBPUSD=X',  # GBP/USD for GBP events
            'JPY': 'USDJPY=X',  # USD/JPY for JPY events
            'AUD': 'AUDUSD=X',  # AUD/USD for AUD events
            'CAD': 'USDCAD=X',  # USD/CAD for CAD events
            'CHF': 'USDCHF=X',  # USD/CHF for CHF events
            'NZD': 'NZDUSD=X',  # NZD/USD for NZD events
            'CNY': 'USDCNY=X',  # USD/CNY for CNY events
            'INR': 'USDINR=X',  # USD/INR for INR events
            'BRL': 'USDBRL=X',  # USD/BRL for BRL events
            'RUB': 'USDRUB=X',  # USD/RUB for RUB events
            'KRW': 'USDKRW=X',  # USD/KRW for KRW events
            'MXN': 'USDMXN=X',  # USD/MXN for MXN events
            'SGD': 'USDSGD=X',  # USD/SGD for SGD events
            'HKD': 'USDHKD=X',  # USD/HKD for HKD events
        }

        # Alternative indices for broader market context
        self.indices = {
            'DXY': 'DX-Y.NYB',  # US Dollar Index
            'VIX': '^VIX',       # Volatility Index
        }

        # Cache for price data to avoid repeated API calls
        self._price_cache = {}
        self._cache_ttl = timedelta(minutes=15)  # Cache data for 15 minutes

    def _ensure_cache_dir(self):
        """Ensure the cache directory exists."""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            logger.info(f"Created chart cache directory: {self.cache_dir}")

    def _get_cached_data(self, symbol: str, start_time: datetime, end_time: datetime) -> Optional[pd.DataFrame]:
        """Get cached price data if available and fresh."""
        cache_key = f"{symbol}_{start_time.strftime('%Y%m%d_%H%M')}_{end_time.strftime('%Y%m%d_%H%M')}"

        if cache_key in self._price_cache:
            cached_data, cache_time = self._price_cache[cache_key]
            if datetime.now() - cache_time < self._cache_ttl:
                logger.info(f"Using cached data for {symbol}")
                return cached_data

        return None

    def _cache_data(self, symbol: str, data: pd.DataFrame, start_time: datetime, end_time: datetime):
        """Cache price data with timestamp."""
        cache_key = f"{symbol}_{start_time.strftime('%Y%m%d_%H%M')}_{end_time.strftime('%Y%m%d_%H%M')}"
        self._price_cache[cache_key] = (data, datetime.now())

        # Clean up old cache entries
        cutoff_time = datetime.now() - timedelta(hours=1)
        old_keys = [
            key for key, (_, cache_time) in self._price_cache.items()
            if cache_time < cutoff_time
        ]
        for key in old_keys:
            del self._price_cache[key]

    def fetch_price_data(self, symbol: str, start_time: datetime, end_time: datetime) -> Optional[pd.DataFrame]:
        """Fetch historical price data for a given symbol and time range."""
        try:
            # Check cache first
            cached_data = self._get_cached_data(symbol, start_time, end_time)
            if cached_data is not None:
                return cached_data

            logger.info(f"Fetching price data for {symbol} from {start_time} to {end_time}")

            # Try different intervals if 1m fails
            intervals = ['1m', '5m', '15m', '1h']

            for interval in intervals:
                try:
                    # Fetch data from Yahoo Finance
                    ticker = yf.Ticker(symbol)
                    data = ticker.history(
                        start=start_time,
                        end=end_time,
                        interval=interval
                    )

                    if not data.empty:
                        logger.info(f"Successfully fetched {len(data)} data points for {symbol} using {interval} interval")
                        # Cache the data
                        self._cache_data(symbol, data, start_time, end_time)
                        return data
                    else:
                        logger.warning(f"No data found for {symbol} with {interval} interval")

                except Exception as e:
                    logger.warning(f"Failed to fetch data for {symbol} with {interval} interval: {e}")
                    continue

            # If all intervals fail, try with a broader time range
            logger.info(f"Trying broader time range for {symbol}")
            try:
                ticker = yf.Ticker(symbol)
                # Try with 1-day interval and broader range
                broader_start = start_time - timedelta(days=1)
                broader_end = end_time + timedelta(days=1)

                data = ticker.history(
                    start=broader_start,
                    end=broader_end,
                    interval='1d'
                )

                if not data.empty:
                    logger.info(f"Successfully fetched {len(data)} data points for {symbol} with broader range")
                    self._cache_data(symbol, data, start_time, end_time)
                    return data

            except Exception as e:
                logger.error(f"Failed to fetch data with broader range for {symbol}: {e}")

            logger.warning(f"No data found for {symbol} in the specified time range with any method")
            return None

        except Exception as e:
            logger.error(f"Error fetching price data for {symbol}: {e}")
            return None

    def get_currency_pair_for_event(self, currency: str) -> str:
        """Get the appropriate currency pair symbol for a given currency."""
        return self.currency_pairs.get(currency, 'EURUSD=X')  # Default to EUR/USD

    def get_currency_pair_for_currency(self, currency: str) -> str:
        """Get the appropriate currency pair symbol for a given currency (alias for compatibility)."""
        return self.get_currency_pair_for_event(currency)

    def create_event_chart(self,
                          currency: str,
                          event_time: datetime,
                          event_name: str,
                          impact_level: str = 'medium',
                          window_hours: int = 2) -> Optional[BytesIO]:
        """Create a chart showing price movement around a news event."""
        try:
            # Validate event time - don't try to fetch future data
            now = datetime.now()
            if event_time > now:
                logger.warning(f"Event time {event_time} is in the future, cannot fetch price data")
                return None

            # Get the appropriate currency pair
            symbol = self.get_currency_pair_for_event(currency)

            # Calculate time window (1 hour before to 1 hour after by default)
            start_time = event_time - timedelta(hours=window_hours)
            end_time = event_time + timedelta(hours=window_hours)

            # Ensure we don't request future data
            if end_time > now:
                end_time = now
                logger.info(f"Adjusted end time to current time: {end_time}")

            # Fetch price data
            price_data = self.fetch_price_data(symbol, start_time, end_time)
            if price_data is None or price_data.empty:
                logger.warning(f"No price data available for {symbol} around {event_time}")
                return None

            # Create the chart
            return self._generate_chart(
                price_data,
                event_time,
                event_name,
                currency,
                symbol,
                impact_level
            )

        except Exception as e:
            logger.error(f"Error creating chart for {currency} event at {event_time}: {e}")
            return None

    def _generate_chart(self,
                       price_data: pd.DataFrame,
                       event_time: datetime,
                       event_name: str,
                       currency: str,
                       symbol: str,
                       impact_level: str) -> BytesIO:
        """Generate a matplotlib chart with the price data and event marker."""
        try:
            # Set up the plot
            plt.style.use('default')
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[3, 1])
            fig.suptitle(f'{currency} News Event: {event_name}', fontsize=14, fontweight='bold')

            # Convert timezone to UTC for consistent plotting
            event_time_utc = event_time.astimezone(pytz.UTC)

            # Plot price data
            ax1.plot(price_data.index, price_data['Close'], linewidth=1.5, color='#1f77b4', alpha=0.8)
            ax1.set_ylabel('Price', fontsize=12)
            ax1.grid(True, alpha=0.3)

            # Add event marker
            ax1.axvline(x=event_time_utc, color='red', linestyle='--', linewidth=2, alpha=0.8, label='Event Time')

            # Add impact level indicator
            impact_colors = {'high': '#d62728', 'medium': '#ff7f0e', 'low': '#2ca02c'}
            impact_color = impact_colors.get(impact_level, '#ff7f0e')

            # Add shaded area around event time
            event_window = timedelta(minutes=30)
            ax1.axvspan(
                event_time_utc - event_window,
                event_time_utc + event_window,
                alpha=0.2,
                color=impact_color,
                label=f'{impact_level.title()} Impact'
            )

            # Plot volume
            if 'Volume' in price_data.columns:
                ax2.bar(price_data.index, price_data['Volume'], alpha=0.6, color='#2ca02c')
                ax2.set_ylabel('Volume', fontsize=12)
                ax2.grid(True, alpha=0.3)

            # Format x-axis
            for ax in [ax1, ax2]:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=30))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

            # Add legend
            ax1.legend(loc='upper right')

            # Add price change annotation
            if len(price_data) > 1:
                start_price = price_data['Close'].iloc[0]
                end_price = price_data['Close'].iloc[-1]
                price_change = end_price - start_price
                price_change_pct = (price_change / start_price) * 100

                change_text = f"Change: {price_change:.4f} ({price_change_pct:+.2f}%)"
                ax1.text(0.02, 0.98, change_text, transform=ax1.transAxes,
                        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

            plt.tight_layout()

            # Save to BytesIO
            img_buffer = BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close()

            logger.info(f"Successfully generated chart for {currency} event: {event_name}")
            return img_buffer

        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            plt.close()  # Ensure plot is closed even on error
            return None

    def create_multi_pair_chart(self,
                               currency: str,
                               event_time: datetime,
                               event_name: str,
                               impact_level: str = 'medium',
                               window_hours: int = 2) -> Optional[BytesIO]:
        """Create a chart showing multiple currency pairs for broader market context."""
        try:
            # Get primary currency pair
            primary_symbol = self.get_currency_pair_for_currency(currency)

            # Get additional pairs for context
            context_pairs = []
            if currency == 'USD':
                context_pairs = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X']
            elif currency == 'EUR':
                context_pairs = ['EURUSD=X', 'EURGBP=X', 'EURJPY=X']
            elif currency == 'GBP':
                context_pairs = ['GBPUSD=X', 'EURGBP=X', 'GBPJPY=X']
            else:
                context_pairs = [primary_symbol, 'EURUSD=X', 'USDJPY=X']

            # Fetch data for all pairs
            all_data = {}
            start_time = event_time - timedelta(hours=window_hours)
            end_time = event_time + timedelta(hours=window_hours)

            for pair in context_pairs:
                data = self.fetch_price_data(pair, start_time, end_time)
                if data is not None and not data.empty:
                    all_data[pair] = data

            if not all_data:
                logger.warning(f"No price data available for any pairs around {event_time}")
                return None

            # Create multi-pair chart
            return self._generate_multi_pair_chart(
                all_data,
                event_time,
                event_name,
                currency,
                impact_level
            )

        except Exception as e:
            logger.error(f"Error creating multi-pair chart for {currency} event: {e}")
            return None

    def _generate_multi_pair_chart(self,
                                  all_data: Dict[str, pd.DataFrame],
                                  event_time: datetime,
                                  event_name: str,
                                  currency: str,
                                  impact_level: str) -> BytesIO:
        """Generate a chart showing multiple currency pairs."""
        try:
            fig, ax = plt.subplots(figsize=(12, 8))

            # Plot each currency pair
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
            for i, (pair, data) in enumerate(all_data.items()):
                color = colors[i % len(colors)]
                # Normalize prices to start at 100 for easier comparison
                normalized_data = (data['Close'] / data['Close'].iloc[0]) * 100
                ax.plot(data.index, normalized_data, label=pair, linewidth=1.5, color=color, alpha=0.8)

            # Add event marker
            event_time_utc = event_time.astimezone(pytz.UTC)
            ax.axvline(x=event_time_utc, color='red', linestyle='--', linewidth=2, alpha=0.8, label='Event Time')

            # Add impact level shading
            impact_colors = {'high': '#d62728', 'medium': '#ff7f0e', 'low': '#2ca02c'}
            impact_color = impact_colors.get(impact_level, '#ff7f0e')

            event_window = timedelta(minutes=30)
            ax.axvspan(
                event_time_utc - event_window,
                event_time_utc + event_window,
                alpha=0.2,
                color=impact_color,
                label=f'{impact_level.title()} Impact'
            )

            ax.set_title(f'{currency} News Event: {event_name}', fontsize=14, fontweight='bold')
            ax.set_ylabel('Normalized Price (Base=100)', fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper right')

            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=30))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

            plt.tight_layout()

            # Save to BytesIO
            img_buffer = BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close()

            return img_buffer

        except Exception as e:
            logger.error(f"Error generating multi-pair chart: {e}")
            plt.close()
            return None

    def cleanup_cache(self):
        """Clean up old cached data."""
        try:
            # Clean up memory cache
            cutoff_time = datetime.now() - timedelta(hours=1)
            old_keys = [
                key for key, (_, cache_time) in self._price_cache.items()
                if cache_time < cutoff_time
            ]
            for key in old_keys:
                del self._price_cache[key]

            logger.info(f"Cleaned up {len(old_keys)} cached price data entries")

        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")


# Global chart service instance
chart_service = ChartService()
