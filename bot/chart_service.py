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
import mplfinance as mpf
import numpy as np
from io import BytesIO
import pytz
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json

logger = logging.getLogger(__name__)


class ChartService:
    """Service for generating forex charts around news events."""

    def __init__(self, cache_dir: str = None, allow_mock_data: Optional[bool] = None, enable_alpha_vantage: Optional[bool] = None, enable_alternative_symbols: Optional[bool] = None):
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), 'forex_charts')
        self._ensure_cache_dir()
        # Persistent charts directory and retention policy
        self.charts_dir = os.path.join(self.cache_dir, 'charts')
        self._ensure_charts_dir()
        self.chart_retention_days = int(os.getenv('CHART_RETENTION_DAYS', '3'))
        self._last_chart_prune = datetime.min

        # Control whether mock data is allowed as a last resort
        if allow_mock_data is None:
            # Default to real data only unless ALLOW_MOCK_DATA is explicitly set ("1", "true")
            env_val = os.getenv('ALLOW_MOCK_DATA', '0').strip().lower()
            self.allow_mock_data = env_val in ('1', 'true', 'yes')
        else:
            self.allow_mock_data = bool(allow_mock_data)

        # Control use of Alpha Vantage fallback (disabled by default)
        if enable_alpha_vantage is None:
            env_val = os.getenv('ENABLE_ALPHA_VANTAGE', '0').strip().lower()
            self.enable_alpha_vantage = env_val in ('1', 'true', 'yes')
        else:
            self.enable_alpha_vantage = bool(enable_alpha_vantage)

        # Control whether to try alternate FX symbols (disabled by default)
        if enable_alternative_symbols is None:
            env_val = os.getenv('ENABLE_ALT_SYMBOLS', '0').strip().lower()
            self.enable_alternative_symbols = env_val in ('1', 'true', 'yes')
        else:
            self.enable_alternative_symbols = bool(enable_alternative_symbols)

        # Basic rate-limit controls for Yahoo/yfinance
        self._min_request_interval_sec: float = float(os.getenv('YF_MIN_REQUEST_INTERVAL_SEC', '3.0'))
        self._last_request_ts: float = 0.0
        self._cooldown_until_ts: float = 0.0

        # Display timezone (for plotting and labels)
        self.display_timezone_name = os.getenv('DISPLAY_TIMEZONE', 'Europe/Prague')
        try:
            self.display_tz = pytz.timezone(self.display_timezone_name)
        except Exception:
            logger.warning(f"Invalid DISPLAY_TIMEZONE '{self.display_timezone_name}', falling back to UTC")
            self.display_tz = pytz.UTC

        # Currency pair mappings for different currencies with alternatives
        self.currency_pairs = {
            'USD': ['EURUSD=X', 'GBPUSD=X'],  # EUR/USD and GBP/USD for USD events
            'EUR': ['EURUSD=X', 'EURGBP=X'],  # EUR/USD and EUR/GBP for EUR events
            'GBP': ['GBPUSD=X', 'EURGBP=X'],  # GBP/USD and EUR/GBP for GBP events
            'JPY': ['USDJPY=X', 'EURJPY=X'],  # USD/JPY and EUR/JPY for JPY events
            'AUD': ['AUDUSD=X', 'AUDJPY=X'],  # AUD/USD and AUD/JPY for AUD events
            'CAD': ['USDCAD=X', 'EURCAD=X'],  # USD/CAD and EUR/CAD for CAD events
            'CHF': ['USDCHF=X', 'EURCHF=X'],  # USD/CHF and EUR/CHF for CHF events
            'NZD': ['NZDUSD=X', 'NZDJPY=X'],  # NZD/USD and NZD/JPY for NZD events
            'CNY': ['USDCNY=X', 'EURCNY=X'],  # USD/CNY and EUR/CNY for CNY events
            # Removed: INR, BRL, RUB, KRW, MXN, SGD per request
            'HKD': ['USDHKD=X', 'EURHKD=X'],  # USD/HKD and EUR/HKD for HKD events
        }

        # Alternative indices for broader market context
        self.indices = {
            'DXY': 'DX-Y.NYB',  # US Dollar Index
            'VIX': '^VIX',       # Volatility Index
        }

        # Cache for price data to avoid repeated API calls
        self._price_cache = {}
        self._cache_ttl = timedelta(minutes=15)  # Cache data for 15 minutes

        # Configure retry strategy for requests
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Dedicated yfinance session with browser-like headers
        self._yf_session = self._init_yf_session()

        # Alternative symbol mappings for when Yahoo Finance fails
        self.alternative_symbols = {
            'EURUSD=X': ['EURUSD=X', 'EURUSD=X', 'EURUSD=X'],
            'GBPUSD=X': ['GBPUSD=X', 'GBPUSD=X', 'EURUSD=X'],
            'USDJPY=X': ['USDJPY=X', 'EURJPY=X', 'JPY=X', 'EURUSD=X'],
            'AUDUSD=X': ['AUDUSD=X', 'AUDJPY=X', 'EURUSD=X'],
            'USDCAD=X': ['USDCAD=X', 'EURCAD=X', 'EURUSD=X'],
            'USDCHF=X': ['USDCHF=X', 'EURCHF=X', 'EURUSD=X'],
            'NZDUSD=X': ['NZDUSD=X', 'NZDJPY=X', 'EURUSD=X'],
        }

    def _init_yf_session(self) -> requests.Session:
        """Initialize a session for yfinance with realistic headers and retries."""
        s = requests.Session()
        retry_strategy = Retry(total=3, backoff_factor=0.8, status_forcelist=[429, 500, 502, 503, 504], respect_retry_after_header=True)
        adapter = HTTPAdapter(max_retries=retry_strategy)
        s.mount("http://", adapter)
        s.mount("https://", adapter)
        # Browser-like headers
        s.headers.update({
            'User-Agent': os.getenv('YF_USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                                                   'Chrome/124.0.0.0 Safari/537.36'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
        })
        # Optional proxy support
        proxy = os.getenv('YF_PROXY')
        if proxy:
            s.proxies.update({'http': proxy, 'https': proxy})
        return s

    def _respect_rate_limit(self):
        """Sleep if needed to respect min interval and cooldown."""
        import time as _time
        import random as _random
        now = _time.time()
        if now < self._cooldown_until_ts:
            sleep_for = max(0.0, self._cooldown_until_ts - now)
            logger.info(f"yfinance cooldown in effect; sleeping {sleep_for:.1f}s to avoid 429")
            _time.sleep(sleep_for)
        elapsed = now - self._last_request_ts
        if elapsed < self._min_request_interval_sec:
            jitter = _random.uniform(0, 0.5)
            sleep_for = self._min_request_interval_sec - elapsed + jitter
            _time.sleep(sleep_for)
        self._last_request_ts = _time.time()

    def _enter_cooldown(self, seconds: float = 60.0):
        """Enter a cooldown period to avoid hammering Yahoo after 429s."""
        import time as _time
        import random as _random
        jitter = _random.uniform(0, seconds * 0.25)
        self._cooldown_until_ts = _time.time() + seconds + jitter
        # Increase spacing between requests
        self._min_request_interval_sec = max(self._min_request_interval_sec, 3.0)
        logger.warning(f"Entering yfinance cooldown for ~{seconds + jitter:.1f}s due to rate limiting")

    def _is_in_cooldown(self) -> bool:
        import time as _time
        return _time.time() < self._cooldown_until_ts

    def _ensure_cache_dir(self):
        """Ensure the cache directory exists."""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            logger.info(f"Created chart cache directory: {self.cache_dir}")

    def _ensure_charts_dir(self):
        """Ensure the charts directory exists for persisted images."""
        try:
            if not os.path.exists(self.charts_dir):
                os.makedirs(self.charts_dir)
                logger.info(f"Created charts directory: {self.charts_dir}")
        except Exception as e:
            logger.error(f"Failed to create charts directory: {e}")

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

    def _fetch_with_retry(self, symbol: str, start_time: datetime, end_time: datetime, interval: str = '1h') -> Optional[pd.DataFrame]:
        """Fetch data directly from Yahoo's unofficial chart API with retries and backoff."""
        max_retries = 3
        base_delay = 2

        for attempt in range(max_retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{max_retries} to fetch {symbol} with {interval} interval")

                # Add delay between attempts to avoid rate limiting
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))  # Exponential backoff
                    logger.info(f"Waiting {delay} seconds before retry...")
                    time.sleep(delay)

                # Primary: call Yahoo chart API directly
                data = self._fetch_from_yahoo_chart_api(symbol, start_time, end_time, interval)
                if data is not None and not data.empty:
                    logger.info(f"Successfully fetched {len(data)} data points for {symbol}")
                    return data
                else:
                    logger.warning(f"Empty data received for {symbol} with {interval} interval from Yahoo chart API")

            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {error_msg}")
                if '429' in error_msg or 'Too Many Requests' in error_msg:
                    self._enter_cooldown(90.0)
                    break
                # Retry on network-type issues
                if any(keyword in error_msg.lower() for keyword in ['timeout', 'connection', 'network']):
                    continue
                continue

        logger.error(f"All {max_retries} attempts failed for {symbol}")

        # No other sources if Alpha Vantage disabled and alternatives off; return None
        return None

    def _fetch_from_yahoo_chart_api(self, symbol: str, start_time: datetime, end_time: datetime, interval: str) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from Yahoo's unofficial chart API."""
        try:
            # Normalize interval to Yahoo-supported values
            interval_map = { '1h': '60m' }
            yf_interval = interval_map.get(interval, interval)

            period1 = int(start_time.timestamp())
            period2 = int(end_time.timestamp())

            params = {
                'period1': str(period1),
                'period2': str(period2),
                'interval': yf_interval,
            }

            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

            self._respect_rate_limit()
            resp = self._yf_session.get(url, params=params, timeout=20)
            if resp.status_code == 429:
                self._enter_cooldown(90.0)
                return None
            resp.raise_for_status()
            payload = resp.json()

            chart = payload.get('chart', {})
            result_list = chart.get('result', [])
            if not result_list:
                return None
            result = result_list[0]
            timestamps = result.get('timestamp', [])
            if not timestamps:
                return None
            indicators = result.get('indicators', {})
            quote_list = indicators.get('quote', [{}])
            quote = quote_list[0] if quote_list else {}

            opens = quote.get('open', [])
            highs = quote.get('high', [])
            lows = quote.get('low', [])
            closes = quote.get('close', [])
            volumes = quote.get('volume', [])

            # Build DataFrame, align lengths safely
            size = min(len(timestamps), len(closes))
            if size == 0:
                return None
            ts = pd.to_datetime(timestamps[:size], unit='s', utc=True)
            data = pd.DataFrame({
                'Open': pd.Series(opens[:size], index=ts),
                'High': pd.Series(highs[:size], index=ts),
                'Low': pd.Series(lows[:size], index=ts),
                'Close': pd.Series(closes[:size], index=ts),
                'Volume': pd.Series(volumes[:size], index=ts),
            })
            # Trim exactly to window
            data = data.loc[(data.index >= pd.to_datetime(start_time, utc=True)) & (data.index <= pd.to_datetime(end_time, utc=True))]
            return data
        except Exception as e:
            logger.warning(f"Yahoo chart API fetch failed for {symbol} {interval}: {e}")
            return None

    def _try_alternative_data_source(self, symbol: str, start_time: datetime, end_time: datetime) -> Optional[pd.DataFrame]:
        """Try alternative data sources when yfinance fails."""
        try:
            # Optionally use Alpha Vantage (disabled by default)
            if self.enable_alpha_vantage:
                api_key = os.getenv('ALPHA_VANTAGE_API_KEY') or os.getenv('API_KEY')
                if api_key:
                    logger.info(f"🔄 Using Alpha Vantage as primary data source for {symbol}")
                    data = self._fetch_from_alpha_vantage(symbol, start_time, end_time, api_key)
                    if data is not None and not data.empty:
                        logger.info(f"✅ Alpha Vantage successfully provided {len(data)} data points for {symbol}")
                        return data
                    else:
                        logger.warning(f"⚠️ Alpha Vantage returned empty data for {symbol}")
                else:
                    logger.info("Alpha Vantage enabled but no API key configured; skipping")
            else:
                logger.info("Alpha Vantage fallback is disabled; using yfinance only")

            # Optionally try Yahoo Finance with different symbol format
            if self.enable_alternative_symbols and not self._is_in_cooldown():
                alt_symbols = self._get_alternative_symbols(symbol)
                for alt_symbol in alt_symbols:
                    if alt_symbol != symbol:  # Don't retry the same symbol
                        logger.info(f"Trying alternative symbol format: {alt_symbol}")
                        data = self._fetch_with_retry(alt_symbol, start_time, end_time, '1h')
                        if data is not None and not data.empty:
                            return data

            # Try with mock data for testing purposes (only if allowed)
            if self.allow_mock_data:
                logger.info(f"Trying mock data for {symbol}")
                return self._generate_mock_data(symbol, start_time, end_time)
            else:
                logger.info("Mock data is disabled; returning None from alternative data source")
                return None

            return None

        except Exception as e:
            logger.error(f"Alternative data source failed for {symbol}: {e}")
            return None

    def _generate_mock_data(self, symbol: str, start_time: datetime, end_time: datetime) -> Optional[pd.DataFrame]:
        """Generate mock data for testing when real data is unavailable."""
        try:
            # Generate mock price data with higher frequency
            duration = end_time - start_time
            if duration <= timedelta(hours=4):
                freq = '5min'  # 5-minute intervals for short periods
                min_points = 12  # At least 12 points for 1 hour
            elif duration <= timedelta(hours=12):
                freq = '15min'  # 15-minute intervals for medium periods
                min_points = 8   # At least 8 points
            else:
                freq = '1H'  # Hourly intervals for longer periods
                min_points = 6   # At least 6 points

            time_range = pd.date_range(start=start_time, end=end_time, freq=freq)

            # Ensure minimum number of data points
            if len(time_range) < min_points:
                logger.warning(f"Only {len(time_range)} points with freq {freq}, generating more...")
                # Generate more frequent data to ensure enough points
                if duration <= timedelta(hours=1):
                    freq = '5min'
                elif duration <= timedelta(hours=4):
                    freq = '10min'
                else:
                    freq = '30min'
                time_range = pd.date_range(start=start_time, end=end_time, freq=freq)

                # If still not enough, create a minimum set manually
                if len(time_range) < 6:
                    time_range = pd.date_range(start=start_time, end=end_time, periods=12)

            # Start with a base price (typical forex prices)
            base_prices = {
                # Major pairs
                'EURUSD=X': 1.08,
                'GBPUSD=X': 1.25,
                'USDJPY=X': 150.0,
                'AUDUSD=X': 0.65,
                'USDCAD=X': 1.35,
                'USDCHF=X': 0.90,
                'NZDUSD=X': 0.60,

                # Cross pairs
                'EURGBP=X': 0.86,
                'EURJPY=X': 162.0,
                'GBPJPY=X': 188.0,
                'AUDCAD=X': 0.88,
                'EURCHF=X': 0.97,

                # Inverted pairs (calculated from major pairs)
                'USDEUR=X': 1.0 / 1.08,      # ~0.926
                'USDGBP=X': 1.0 / 1.25,      # ~0.80
                'JPYUSD=X': 1.0 / 150.0,     # ~0.0067
                'USDAUD=X': 1.0 / 0.65,      # ~1.538
                'CADUSD=X': 1.0 / 1.35,      # ~0.741
                'CHFUSD=X': 1.0 / 0.90,      # ~1.111
                'USDNZD=X': 1.0 / 0.60,      # ~1.667

                # More inverted cross pairs
                'GBPEUR=X': 1.0 / 0.86,      # ~1.163
                'JPYEUR=X': 1.0 / 162.0,     # ~0.0062
                'JPYGBP=X': 1.0 / 188.0,     # ~0.0053
            }

            base_price = base_prices.get(symbol, 1.0)

            # Use current timestamp as seed for more variety
            import time as time_module
            np.random.seed(int(time_module.time()) % 1000)

            # Generate realistic price movements with trending behavior
            price_changes = np.random.normal(0, 0.0005, len(time_range))  # Smaller changes

            # Add some trending behavior (slight upward or downward bias)
            trend = np.random.choice([-1, 0, 1]) * 0.0001
            price_changes += trend

            prices = [base_price]
            for change in price_changes[1:]:
                new_price = prices[-1] * (1 + change)
                # Keep prices within realistic bounds
                if new_price > base_price * 1.02:  # Max 2% change
                    new_price = base_price * 1.02
                elif new_price < base_price * 0.98:  # Max 2% change
                    new_price = base_price * 0.98
                prices.append(new_price)

            # Generate OHLC data
            opens = []
            highs = []
            lows = []
            closes = prices.copy()

            for i, close_price in enumerate(closes):
                if i == 0:
                    open_price = close_price
                else:
                    open_price = closes[i-1]

                # Generate high and low based on close
                high_offset = abs(np.random.normal(0, 0.0003))
                low_offset = abs(np.random.normal(0, 0.0003))

                high_price = max(open_price, close_price) + (close_price * high_offset)
                low_price = min(open_price, close_price) - (close_price * low_offset)

                opens.append(open_price)
                highs.append(high_price)
                lows.append(low_price)

            # Create DataFrame
            data = pd.DataFrame({
                'Open': opens,
                'High': highs,
                'Low': lows,
                'Close': closes,
                'Volume': [np.random.randint(1000, 10000) for _ in range(len(time_range))]
            }, index=time_range)

            logger.info(f"Generated mock data for {symbol} with {len(data)} data points (freq: {freq})")
            logger.info(f"Mock price range: {data['Close'].min():.4f} - {data['Close'].max():.4f}")
            return data

        except Exception as e:
            logger.error(f"Failed to generate mock data for {symbol}: {e}")
            return None

    def _fetch_from_alpha_vantage(self, symbol: str, start_time: datetime, end_time: datetime, api_key: str) -> Optional[pd.DataFrame]:
        """Fetch data from Alpha Vantage API."""
        try:
            # Convert Yahoo Finance symbol to Alpha Vantage format
            av_symbol = symbol.replace('=X', '')

            url = f"https://www.alphavantage.co/query"
            params = {
                'function': 'FX_INTRADAY',
                'from_symbol': av_symbol[:3],
                'to_symbol': av_symbol[3:6],
                'interval': '60min',
                'apikey': api_key
            }

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if 'Time Series FX (60min)' in data:
                time_series = data['Time Series FX (60min)']
                records = []

                for timestamp, values in time_series.items():
                    dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                    if start_time <= dt <= end_time:
                        records.append({
                            'timestamp': dt,
                            'Open': float(values['1. open']),
                            'High': float(values['2. high']),
                            'Low': float(values['3. low']),
                            'Close': float(values['4. close']),
                            'Volume': 0  # Alpha Vantage doesn't provide volume for FX
                        })

                if records:
                    # Create DataFrame with proper datetime index
                    df = pd.DataFrame(records)
                    df.set_index('timestamp', inplace=True)
                    logger.info(f"Successfully fetched {len(df)} data points from Alpha Vantage for {symbol}")
                    return df

            return None

        except Exception as e:
            logger.error(f"Alpha Vantage fetch failed for {symbol}: {e}")
            return None

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
                    data = self._fetch_with_retry(symbol, start_time, end_time, interval)

                    if data is not None and not data.empty:
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
                broader_start = start_time - timedelta(days=1)
                broader_end = end_time + timedelta(days=1)

                data = self._fetch_with_retry(symbol, broader_start, broader_end, '1d')

                if data is not None and not data.empty:
                    logger.info(f"Successfully fetched {len(data)} data points for {symbol} with broader range")
                    self._cache_data(symbol, data, start_time, end_time)
                    return data

            except Exception as e:
                logger.error(f"Failed to fetch data with broader range for {symbol}: {e}")

            # Try alternative data sources
            logger.info(f"Trying alternative data sources for {symbol}")
            data = self._try_alternative_data_source(symbol, start_time, end_time)
            if data is not None and not data.empty:
                self._cache_data(symbol, data, start_time, end_time)
                return data

            # If all else fails, optionally generate mock data
            if self.allow_mock_data:
                logger.warning(f"All data sources failed for {symbol}, generating mock data for demonstration")
                mock_data = self._generate_mock_data(symbol, start_time, end_time)
                if mock_data is not None and not mock_data.empty:
                    logger.info(f"Using mock data for {symbol} with {len(mock_data)} data points")
                    return mock_data
            else:
                logger.warning("All data sources failed and mock data is disabled; returning None")

            logger.warning(f"No data found for {symbol} in the specified time range with any method")
            return None

        except Exception as e:
            logger.error(f"Error fetching price data for {symbol}: {e}")
            return None

    def _get_alternative_symbols(self, symbol: str) -> list:
        """Get alternative symbols for a given currency pair."""
        return self.alternative_symbols.get(symbol, [symbol])

    def get_currency_pair_for_event(self, currency: str) -> str:
        """Get the appropriate currency pair symbol for a given currency."""
        pairs = self.currency_pairs.get(currency, ['EURUSD=X'])
        return pairs[0] if isinstance(pairs, list) else pairs  # Return first pair

    def get_currency_pair_for_currency(self, currency: str) -> str:
        """Get the appropriate currency pair symbol for a given currency (alias for compatibility)."""
        return self.get_currency_pair_for_event(currency)

    def get_currency_pairs_for_currency(self, currency: str) -> list:
        """Get all available currency pairs for a given currency."""
        pairs = self.currency_pairs.get(currency, ['EURUSD=X'])
        return pairs if isinstance(pairs, list) else [pairs]

    def create_event_chart(self,
                          currency: str,
                          event_time: datetime,
                          event_name: str,
                          impact_level: str = 'medium',
                          window_hours: int = 2) -> Optional[BytesIO]:
        """Create a chart showing price movement around a news event."""
        try:
            # Ensure event_time is timezone-aware; assume stored times are in display timezone (e.g., Prague)
            if event_time.tzinfo is None:
                try:
                    event_time = self.display_tz.localize(event_time)
                except Exception:
                    event_time = pytz.UTC.localize(event_time)

            # Validate event time - don't try to fetch future data
            # Convert to display tz for comparison to local current time
            now = datetime.now(self.display_tz)
            if event_time.astimezone(self.display_tz) > now:
                logger.warning(f"Event time {event_time} is in the future, cannot fetch price data")
                return None

            # Get all available currency pairs for this currency
            symbols = self.get_currency_pairs_for_currency(currency)

            # Calculate time window (1 hour before to 1 hour after by default)
            start_time = event_time - timedelta(hours=window_hours)
            end_time = event_time + timedelta(hours=window_hours)

            # Ensure we don't request future data
            now = datetime.now(self.display_tz)
            if end_time.astimezone(self.display_tz) > now:
                end_time = now.astimezone(event_time.tzinfo)
                logger.info(f"Adjusted end time to current time: {end_time}")

            # Try each currency pair until we find one with data
            price_data = None
            successful_symbol = None

            for symbol in symbols:
                logger.info(f"Trying currency pair: {symbol}")
                price_data = self.fetch_price_data(symbol, start_time, end_time)
                if price_data is not None and not price_data.empty:
                    successful_symbol = symbol
                    logger.info(f"Successfully found data for {symbol}")
                    break
                else:
                    logger.warning(f"No price data available for {symbol} around {event_time}")

            if price_data is None or price_data.empty:
                logger.warning(f"No price data available for any currency pairs for {currency} around {event_time}")
                return None

            # Create the chart
            return self._generate_chart(
                price_data,
                event_time,
                event_name,
                currency,
                successful_symbol,
                impact_level,
                window_hours
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
                       impact_level: str,
                       window_hours: int) -> BytesIO:
        """Generate a matplotlib chart with the price data and event marker."""
        try:
            # Set up the plot
            plt.style.use('default')
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[3, 1])
            # Format the event date for display (in local/display TZ)
            event_date_str = event_time.astimezone(self.display_tz).strftime('%Y-%m-%d')
            fig.suptitle(f'{currency} News Event: {event_name}\n{event_date_str}', fontsize=14, fontweight='bold')

            # Convert data and event time to display timezone for plotting
            local_index = price_data.index.tz_convert(self.display_tz) if price_data.index.tzinfo else price_data.index.tz_localize(self.display_tz)
            event_time_local = event_time.astimezone(self.display_tz)

            # Plot price data as candlesticks when OHLC is available
            try:
                ohlc = price_data[['Open', 'High', 'Low', 'Close']].copy()
                ohlc.index = local_index
                self._plot_candlesticks(ax1, ohlc, f'{currency}/{symbol.split("=")[0][-3:]}')
            except Exception as e:
                logger.warning(f"Candlestick plot failed, falling back to line chart: {e}")
                ax1.plot(local_index, price_data['Close'], linewidth=1.5, color='#1f77b4', alpha=0.8)
            ax1.set_ylabel('Price', fontsize=12)
            ax1.grid(True, alpha=0.3)

            # Add event marker
            ax1.axvline(x=event_time_local, color='red', linestyle='--', linewidth=2, alpha=0.8, label='Event Time')

            # Add impact level indicator
            impact_colors = {'high': '#d62728', 'medium': '#ff7f0e', 'low': '#2ca02c'}
            impact_color = impact_colors.get(impact_level, '#ff7f0e')

            # Add shaded area around event time
            event_window = timedelta(minutes=30)
            ax1.axvspan(
                event_time_local - event_window,
                event_time_local + event_window,
                alpha=0.2,
                color=impact_color,
                label=f'{impact_level.title()} Impact'
            )

            # Plot volume
            if 'Volume' in price_data.columns:
                ax2.bar(local_index, price_data['Volume'], alpha=0.6, color='#2ca02c')
                ax2.set_ylabel('Volume', fontsize=12)
                ax2.grid(True, alpha=0.3)

            # Format x-axis
            # X-axis: show ticks every 30 minutes for consistency
            major_interval = 30
            for ax in [ax1, ax2]:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M', tz=self.display_tz))
                ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=major_interval))
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
            # Persist chart to disk and prune old ones
            try:
                filename = f"{event_time_local.strftime('%Y%m%d_%H%M')}_{currency}_{symbol}_w{window_hours}h_{self._slugify(event_name)}.png"
                self._save_chart_buffer(img_buffer, filename)
            except Exception as e:
                logger.warning(f"Failed to persist chart image: {e}")
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
            # Ensure event_time is timezone-aware; assume times from UI/DB are in display timezone
            if event_time.tzinfo is None:
                try:
                    event_time = self.display_tz.localize(event_time)
                except Exception:
                    event_time = pytz.UTC.localize(event_time)

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

            # Plot each currency pair as candlesticks in small multiples for clarity
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
            for i, (pair, data) in enumerate(all_data.items()):
                color = colors[i % len(colors)]
                local_index = data.index.tz_convert(self.display_tz) if data.index.tzinfo else data.index.tz_localize(self.display_tz)
                try:
                    ohlc = data[['Open', 'High', 'Low', 'Close']].copy()
                    ohlc.index = local_index
                    self._plot_candlesticks(ax, ohlc, pair)
                except Exception as e:
                    logger.warning(f"Candlestick plot failed for {pair}, using line chart: {e}")
                    ax.plot(local_index, data['Close'], label=pair, linewidth=1.2, color=color, alpha=0.8)

            # Add event marker in display timezone
            event_time_local = event_time.astimezone(self.display_tz)
            ax.axvline(x=event_time_local, color='red', linestyle='--', linewidth=2, alpha=0.8, label='Event Time')

            # Add impact level shading
            impact_colors = {'high': '#d62728', 'medium': '#ff7f0e', 'low': '#2ca02c'}
            impact_color = impact_colors.get(impact_level, '#ff7f0e')

            event_window = timedelta(minutes=30)
            ax.axvspan(
                event_time_local - event_window,
                event_time_local + event_window,
                alpha=0.2,
                color=impact_color,
                label=f'{impact_level.title()} Impact'
            )

            ax.set_title(f'{currency} News Event: {event_name}', fontsize=14, fontweight='bold')
            ax.set_ylabel('Normalized Price (Base=100)', fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper right')

            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M', tz=self.display_tz))
            ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=30))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

            plt.tight_layout()

            # Save to BytesIO
            img_buffer = BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close()

            try:
                filename = f"{event_time_local.strftime('%Y%m%d_%H%M')}_{currency}_multi_w{window_hours}h_{self._slugify(event_name)}.png"
                self._save_chart_buffer(img_buffer, filename)
            except Exception as e:
                logger.warning(f"Failed to persist multi-pair chart image: {e}")

            return img_buffer

        except Exception as e:
            logger.error(f"Error generating multi-pair chart: {e}")
            plt.close()
            return None

    def create_multi_currency_chart(self,
                                   primary_currency: str,
                                   secondary_currency: str,
                                   event_time: datetime,
                                   event_name: str,
                                   impact_level: str = 'medium',
                                   window_hours: int = 2,
                                   before_hours: float = None,
                                   after_hours: float = None) -> Optional[BytesIO]:
        """Create a chart showing price movement for two currencies around a news event."""
        try:
            # Ensure event_time is timezone-aware; assume stored times are in display timezone
            if event_time.tzinfo is None:
                try:
                    event_time = self.display_tz.localize(event_time)
                except Exception:
                    event_time = pytz.UTC.localize(event_time)

            # Validate event time - don't try to fetch future data
            now = datetime.now(pytz.UTC)
            if event_time > now:
                logger.warning(f"Event time {event_time} is in the future, cannot fetch price data")
                return None

            # Get currency pairs for both currencies
            primary_symbols = self.get_currency_pairs_for_currency(primary_currency)
            secondary_symbols = self.get_currency_pairs_for_currency(secondary_currency)

            # Calculate time window - use asymmetric if provided, otherwise symmetric
            if before_hours is not None and after_hours is not None:
                start_time = event_time - timedelta(hours=before_hours)
                end_time = event_time + timedelta(hours=after_hours)
                logger.info(f"Using asymmetric time window: {before_hours}h before, {after_hours}h after")
            else:
                start_time = event_time - timedelta(hours=window_hours)
                end_time = event_time + timedelta(hours=window_hours)
                logger.info(f"Using symmetric time window: ±{window_hours}h")

            # Ensure we don't request future data
            if end_time.astimezone(self.display_tz) > now:
                end_time = now.astimezone(event_time.tzinfo)
                logger.info(f"Adjusted end time to current time: {end_time}")

            # Try to find a direct pair between the two currencies
            direct_pair = None
            data_is_inverted = False

            if primary_currency != secondary_currency:
                # Create candidates but prioritize major pairs
                candidate1 = f"{primary_currency}{secondary_currency}=X"
                candidate2 = f"{secondary_currency}{primary_currency}=X"

                # Major pairs that are more likely to have data
                major_pairs = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X', 'USDCAD=X', 'USDCHF=X', 'NZDUSD=X']

                # Prioritize the major pair if available
                if candidate2 in major_pairs:
                    # Try major pair first (inverted)
                    logger.info(f"Trying major pair (inverted): {candidate2}")
                    data = self.fetch_price_data(candidate2, start_time, end_time)
                    if data is not None and not data.empty:
                        direct_pair = candidate2
                        data_is_inverted = True
                        logger.info(f"Found major pair data (will invert): {candidate2}")
                    else:
                        # Try the original pair
                        logger.info(f"Trying direct pair: {candidate1}")
                        data = self.fetch_price_data(candidate1, start_time, end_time)
                        if data is not None and not data.empty:
                            direct_pair = candidate1
                            data_is_inverted = False
                            logger.info(f"Found direct pair data: {candidate1}")
                elif candidate1 in major_pairs:
                    # Try major pair first (direct)
                    logger.info(f"Trying major pair (direct): {candidate1}")
                    data = self.fetch_price_data(candidate1, start_time, end_time)
                    if data is not None and not data.empty:
                        direct_pair = candidate1
                        data_is_inverted = False
                        logger.info(f"Found major pair data: {candidate1}")
                    else:
                        # Try the inverted pair
                        logger.info(f"Trying inverted pair: {candidate2}")
                        data = self.fetch_price_data(candidate2, start_time, end_time)
                        if data is not None and not data.empty:
                            direct_pair = candidate2
                            data_is_inverted = True
                            logger.info(f"Found inverted pair data: {candidate2}")
                else:
                    # Try both candidates
                    for candidate in [candidate1, candidate2]:
                        logger.info(f"Trying direct pair: {candidate}")
                        data = self.fetch_price_data(candidate, start_time, end_time)
                        if data is not None and not data.empty:
                            direct_pair = candidate
                            data_is_inverted = (candidate == candidate2)
                            logger.info(f"Found direct pair data: {candidate}")
                            break

            # If no direct pair found, try to construct it from individual currencies
            if direct_pair is None:
                logger.info("No direct pair found, trying to construct from individual currencies")

                # Fetch data for primary currency (against USD)
                primary_data = None
                primary_symbol = None
                for symbol in primary_symbols:
                    logger.info(f"Trying primary currency pair: {symbol}")
                    primary_data = self.fetch_price_data(symbol, start_time, end_time)
                    if primary_data is not None and not primary_data.empty:
                        primary_symbol = symbol
                        logger.info(f"Successfully found data for primary {symbol}")
                        break

                # Fetch data for secondary currency (against USD)
                secondary_data = None
                secondary_symbol = None
                for symbol in secondary_symbols:
                    logger.info(f"Trying secondary currency pair: {symbol}")
                    secondary_data = self.fetch_price_data(symbol, start_time, end_time)
                    if secondary_data is not None and not secondary_data.empty:
                        secondary_symbol = symbol
                        logger.info(f"Successfully found data for secondary {symbol}")
                        break

                if primary_data is None or primary_data.empty:
                    logger.warning(f"No price data available for primary currency {primary_currency}")
                    return None

                if secondary_data is None or secondary_data.empty:
                    logger.warning(f"No price data available for secondary currency {secondary_currency}")
                    return None

                # Create the cross-rate chart
                return self._generate_cross_rate_chart(
                    primary_data,
                    secondary_data,
                    primary_symbol,
                    secondary_symbol,
                    primary_currency,
                    secondary_currency,
                    event_time,
                    event_name,
                    impact_level
                )
            else:
                # Use direct pair data
                data = self.fetch_price_data(direct_pair, start_time, end_time)
                if data is not None and not data.empty:
                    return self._generate_direct_pair_chart(
                        data,
                        direct_pair,
                        primary_currency,
                        secondary_currency,
                        event_time,
                        event_name,
                        impact_level,
                        data_is_inverted
                    )

            return None

        except Exception as e:
            logger.error(f"Error creating multi-currency chart for {primary_currency}/{secondary_currency} event: {e}")
            return None

    def _generate_cross_rate_chart(self,
                                  primary_data: pd.DataFrame,
                                  secondary_data: pd.DataFrame,
                                  primary_symbol: str,
                                  secondary_symbol: str,
                                  primary_currency: str,
                                  secondary_currency: str,
                                  event_time: datetime,
                                  event_name: str,
                                  impact_level: str) -> BytesIO:
        """Generate a chart showing cross-rate between two currencies."""
        try:
            # Calculate cross-rate (primary/secondary)
            # We need to align the data by time index
            common_index = primary_data.index.intersection(secondary_data.index)

            if len(common_index) == 0:
                logger.warning("No common time points between primary and secondary currency data")
                return None

            # Get aligned data
            primary_aligned = primary_data.loc[common_index]
            secondary_aligned = secondary_data.loc[common_index]

            # Calculate cross-rate: primary_currency / secondary_currency
            # This gives us the price of primary currency in terms of secondary currency
            cross_rate = primary_aligned['Close'] / secondary_aligned['Close']

            # Create the chart
            fig, ax = plt.subplots(figsize=(12, 8))

            # Convert event time to display timezone for plotting
            event_time_local = event_time.astimezone(self.display_tz)

            # Create cross-rate candlestick chart if we have OHLC data
            if len(common_index) >= 4 and all(col in primary_aligned.columns for col in ['Open', 'High', 'Low', 'Close']):
                try:
                    # Calculate cross-rate OHLC
                    cross_ohlc = pd.DataFrame(index=common_index)
                    cross_ohlc['Open'] = primary_aligned['Open'] / secondary_aligned['Open']
                    cross_ohlc['High'] = primary_aligned['High'] / secondary_aligned['Low']  # Max when secondary is lowest
                    cross_ohlc['Low'] = primary_aligned['Low'] / secondary_aligned['High']   # Min when secondary is highest
                    cross_ohlc['Close'] = primary_aligned['Close'] / secondary_aligned['Close']

                    # Plot candlesticks
                    self._plot_candlesticks(ax, cross_ohlc, f'{primary_currency}/{secondary_currency}')

                except Exception as e:
                    logger.warning(f"Failed to create cross-rate candlestick chart, using line chart: {e}")
                    # Fallback to line chart
                    cross_rate = primary_aligned['Close'] / secondary_aligned['Close']
                    ax.plot(common_index, cross_rate, linewidth=2, color='#1f77b4', alpha=0.8,
                           label=f'{primary_currency}/{secondary_currency}')
            else:
                # Use line chart for cross-rate
                cross_rate = primary_aligned['Close'] / secondary_aligned['Close']
                ax.plot(common_index, cross_rate, linewidth=2, color='#1f77b4', alpha=0.8,
                       label=f'{primary_currency}/{secondary_currency}')

            ax.set_ylabel(f'{primary_currency} Price (in {secondary_currency})', fontsize=12)
            ax.set_xlabel('Time', fontsize=12)
            ax.grid(True, alpha=0.3)

            # Add event marker
            ax.axvline(x=event_time_local, color='red', linestyle='--', linewidth=2, alpha=0.8, label='Event Time')

            # Add impact level shading
            impact_colors = {'high': '#d62728', 'medium': '#ff7f0e', 'low': '#2ca02c'}
            impact_color = impact_colors.get(impact_level, '#ff7f0e')

            event_window = timedelta(minutes=30)
            ax.axvspan(
                event_time_local - event_window,
                event_time_local + event_window,
                alpha=0.2,
                color=impact_color,
                label=f'{impact_level.title()} Impact'
            )

            # Set title
            event_date_str = event_time.strftime('%Y-%m-%d')
            ax.set_title(f'{primary_currency}/{secondary_currency} News Event: {event_name}\n{event_date_str}',
                        fontsize=14, fontweight='bold')

            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M', tz=self.display_tz))
            ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=30))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

            # Add price change annotation
            if len(cross_rate) > 1:
                start_price = cross_rate.iloc[0]
                end_price = cross_rate.iloc[-1]
                price_change = end_price - start_price
                price_change_pct = (price_change / start_price) * 100

                change_text = f"Change: {price_change:.4f} ({price_change_pct:+.2f}%)"
                ax.text(0.02, 0.98, change_text, transform=ax.transAxes,
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

            plt.tight_layout()

            # Save to BytesIO
            img_buffer = BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close()

            logger.info(f"Successfully generated cross-rate chart for {primary_currency}/{secondary_currency} event: {event_name}")
            try:
                filename = f"{event_time_local.strftime('%Y%m%d_%H%M')}_{primary_currency}_{secondary_currency}_cross_{self._slugify(event_name)}.png"
                self._save_chart_buffer(img_buffer, filename)
            except Exception as e:
                logger.warning(f"Failed to persist cross-rate chart image: {e}")
            return img_buffer

        except Exception as e:
            logger.error(f"Error generating cross-rate chart: {e}")
            plt.close()  # Ensure plot is closed even on error
            return None

    def _generate_direct_pair_chart(self,
                                   data: pd.DataFrame,
                                   pair_symbol: str,
                                   primary_currency: str,
                                   secondary_currency: str,
                                   event_time: datetime,
                                   event_name: str,
                                   impact_level: str,
                                   invert_data: bool = False) -> BytesIO:
        """Generate a chart for a direct currency pair."""
        try:
            # Create the chart
            fig, ax = plt.subplots(figsize=(12, 8))

            # Convert timezone to UTC for consistent plotting
            event_time_utc = event_time.astimezone(pytz.UTC)

            # Handle data inversion if needed
            if invert_data:
                logger.info(f"Inverting data from {pair_symbol} to show {primary_currency}/{secondary_currency}")
                # Invert all OHLC values
                plot_data = data.copy()
                for col in ['Open', 'High', 'Low', 'Close']:
                    if col in plot_data.columns:
                        plot_data[col] = 1.0 / plot_data[col]
                # For inverted data, we need to swap High and Low
                if 'High' in plot_data.columns and 'Low' in plot_data.columns:
                    plot_data['High'], plot_data['Low'] = plot_data['Low'], plot_data['High']
            else:
                plot_data = data

            # Prefer candlesticks; fallback to line chart
            try:
                candlestick_data = plot_data[['Open', 'High', 'Low', 'Close']].copy()
                self._plot_candlesticks(ax, candlestick_data, f'{primary_currency}/{secondary_currency}')
                ax.set_ylabel(f'{primary_currency} Price (in {secondary_currency})', fontsize=12)
                ax.set_xlabel('Time', fontsize=12)
                ax.grid(True, alpha=0.3)
            except Exception as e:
                logger.warning(f"Failed to create candlestick chart, falling back to line chart: {e}")
                ax.plot(plot_data.index, plot_data['Close'], linewidth=2, color='#1f77b4', alpha=0.8,
                        label=f'{primary_currency}/{secondary_currency}')
                ax.set_ylabel(f'{primary_currency} Price (in {secondary_currency})', fontsize=12)
                ax.set_xlabel('Time', fontsize=12)
                ax.grid(True, alpha=0.3)
                ax.legend(loc='upper right')
            else:
                # Not enough data for candlesticks, use line chart
                ax.plot(plot_data.index, plot_data['Close'], linewidth=2, color='#1f77b4', alpha=0.8,
                       label=f'{primary_currency}/{secondary_currency}')
                ax.set_ylabel(f'{primary_currency} Price (in {secondary_currency})', fontsize=12)
                ax.set_xlabel('Time', fontsize=12)
                ax.grid(True, alpha=0.3)
                ax.legend(loc='upper right')

            # Add event marker
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

            # Set title
            event_date_str = event_time.strftime('%Y-%m-%d')
            ax.set_title(f'{primary_currency}/{secondary_currency} News Event: {event_name}\n{event_date_str}',
                        fontsize=14, fontweight='bold')

            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M', tz=self.display_tz))
            ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=30))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

            # Add price change annotation
            if len(plot_data) > 1:
                start_price = plot_data['Close'].iloc[0]
                end_price = plot_data['Close'].iloc[-1]
                price_change = end_price - start_price
                price_change_pct = (price_change / start_price) * 100

                change_text = f"Change: {price_change:.4f} ({price_change_pct:+.2f}%)"
                ax.text(0.02, 0.98, change_text, transform=ax.transAxes,
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

            plt.tight_layout()

            # Save to BytesIO
            img_buffer = BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close()

            logger.info(f"Successfully generated direct pair chart for {primary_currency}/{secondary_currency} event: {event_name}")
            try:
                filename = f"{event_time.strftime('%Y%m%d_%H%M')}_{primary_currency}_{secondary_currency}_direct_{self._slugify(event_name)}.png"
                self._save_chart_buffer(img_buffer, filename)
            except Exception as e:
                logger.warning(f"Failed to persist direct chart image: {e}")
            return img_buffer

        except Exception as e:
            logger.error(f"Error generating direct pair chart: {e}")
            plt.close()  # Ensure plot is closed even on error
            return None

    def _plot_candlesticks(self, ax, ohlc_data: pd.DataFrame, pair_name: str):
        """Plot candlestick chart on the given axes."""
        try:
            # Convert datetime index to matplotlib dates
            dates = ohlc_data.index
            opens = ohlc_data['Open'].values
            highs = ohlc_data['High'].values
            lows = ohlc_data['Low'].values
            closes = ohlc_data['Close'].values

            # Calculate colors (green for up, red for down)
            colors = ['green' if close >= open else 'red'
                     for open, close in zip(opens, closes)]

            # Plot candlesticks manually
            for i, (date, open_price, high, low, close, color) in enumerate(
                zip(dates, opens, highs, lows, closes, colors)
            ):
                # Body of the candlestick
                body_height = abs(close - open_price)
                body_bottom = min(close, open_price)

                # Width based on time interval
                if len(dates) > 1:
                    time_diff = (dates[1] - dates[0]).total_seconds() / 3600  # hours
                    width = time_diff / 24 * 0.6  # Fraction of a day
                else:
                    width = 0.02  # Default width

                # Draw the high-low line
                ax.plot([date, date], [low, high], color='black', linewidth=1, alpha=0.8)

                # Draw the body rectangle
                body = Rectangle((date - timedelta(hours=width*12), body_bottom),
                               timedelta(hours=width*24), body_height,
                               facecolor=color, alpha=0.7, edgecolor='black', linewidth=0.5)
                ax.add_patch(body)

            # Set labels and title
            ax.set_title(f'Candlestick Chart: {pair_name}', fontsize=12, fontweight='bold')

            # Format the price axis
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.4f}'))

        except Exception as e:
            logger.error(f"Error plotting candlesticks: {e}")
            # Fallback to line chart
            ax.plot(ohlc_data.index, ohlc_data['Close'], linewidth=2, color='#1f77b4', alpha=0.8,
                   label=pair_name)
            ax.legend(loc='upper right')

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

    def _slugify(self, text_val: str) -> str:
        """Make a safe filename component from text."""
        try:
            import re as _re
            text_val = (text_val or "").lower()
            text_val = _re.sub(r"[^a-z0-9]+", "_", text_val)
            return text_val.strip('_')[:80]
        except Exception:
            return "chart"

    def _save_chart_buffer(self, img_buffer: BytesIO, filename: str) -> Optional[str]:
        """Save chart buffer to charts directory and trigger pruning."""
        try:
            self._ensure_charts_dir()
            # Keep caller buffer position
            current_pos = img_buffer.tell()
            img_buffer.seek(0)
            filepath = os.path.join(self.charts_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(img_buffer.read())
            # Restore buffer position
            try:
                img_buffer.seek(current_pos)
            except Exception:
                pass
            logger.info(f"Saved chart image: {filepath}")
            self._maybe_prune_charts()
            return filepath
        except Exception as e:
            logger.warning(f"Failed to save chart to disk: {e}")
            return None

    def _maybe_prune_charts(self):
        """Prune charts periodically (every ~6 hours)."""
        try:
            now = datetime.now()
            if (now - self._last_chart_prune).total_seconds() < 6 * 3600:
                return
            self._last_chart_prune = now
            self.prune_old_charts()
        except Exception as e:
            logger.warning(f"Chart prune check failed: {e}")

    def prune_old_charts(self) -> int:
        """Delete charts older than retention period. Returns number deleted."""
        try:
            self._ensure_charts_dir()
            cutoff = datetime.now() - timedelta(days=self.chart_retention_days)
            deleted = 0
            for name in os.listdir(self.charts_dir):
                path = os.path.join(self.charts_dir, name)
                try:
                    if not os.path.isfile(path):
                        continue
                    mtime = datetime.fromtimestamp(os.path.getmtime(path))
                    if mtime < cutoff:
                        os.remove(path)
                        deleted += 1
                except Exception:
                    continue
            if deleted:
                logger.info(f"Pruned {deleted} chart image(s) older than {self.chart_retention_days} days")
            return deleted
        except Exception as e:
            logger.error(f"Failed to prune old charts: {e}")
            return 0


# Global chart service instance
chart_service = ChartService()
