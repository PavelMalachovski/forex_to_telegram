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
from datetime import datetime, timedelta
import pytz
import yfinance as yf

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
            # Added commodity and crypto support
            'XAU': ['XAUUSD=X'],              # Gold vs USD
            'BTC': ['BTC-USD'],               # Bitcoin vs USD (Yahoo symbol)
            'ETH': ['ETH-USD'],               # Ethereum vs USD (Yahoo symbol)
            # The following currencies are supported for mapping but may be hidden in UI
            'INR': ['USDINR=X', 'EURINR=X'],
            'BRL': ['USDBRL=X', 'EURBRL=X'],
            'RUB': ['USDRUB=X', 'EURRUB=X'],
            'KRW': ['USDKRW=X', 'EURKRW=X'],
            'MXN': ['USDMXN=X', 'EURMXN=X'],
            'SGD': ['USDSGD=X', 'EURSGD=X'],
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
            'XAUUSD=X': ['XAUUSD=X', 'GC=F'],
            'BTC-USD': ['BTC-USD'],
            'ETH-USD': ['ETH-USD'],
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
            # Enhanced logging for problematic currencies
            currency = self._extract_currency_from_symbol(symbol)
            is_problematic_currency = currency in ['GBP', 'EUR', 'AUD']
            
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

            if is_problematic_currency:
                logger.debug(f"🌐 Yahoo API request for {currency}: {url}")
                logger.debug(f"📊 Parameters: {params}")

            self._respect_rate_limit()
            resp = self._yf_session.get(url, params=params, timeout=20)
            
            if resp.status_code == 429:
                if is_problematic_currency:
                    logger.warning(f"⚠️ Rate limited for {currency} ({symbol}) - entering cooldown")
                self._enter_cooldown(90.0)
                return None
            
            if resp.status_code != 200:
                if is_problematic_currency:
                    logger.error(f"❌ HTTP {resp.status_code} for {currency} ({symbol}): {resp.text[:200]}")
                else:
                    logger.warning(f"HTTP {resp.status_code} for {symbol}: {resp.text[:200]}")
                return None
                
            resp.raise_for_status()
            payload = resp.json()

            chart = payload.get('chart', {})
            result_list = chart.get('result', [])
            if not result_list:
                if is_problematic_currency:
                    logger.warning(f"⚠️ No chart results for {currency} ({symbol})")
                return None
                
            result = result_list[0]
            timestamps = result.get('timestamp', [])
            if not timestamps:
                if is_problematic_currency:
                    logger.warning(f"⚠️ No timestamps for {currency} ({symbol})")
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
                if is_problematic_currency:
                    logger.warning(f"⚠️ No valid data points for {currency} ({symbol})")
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
            
            if is_problematic_currency and len(data) == 0:
                logger.warning(f"⚠️ {currency} ({symbol}) data exists but outside time window")
                logger.warning(f"📊 Data range: {ts[0]} to {ts[-1]}")
                logger.warning(f"⏰ Requested range: {start_time} to {end_time}")
            
            return data
            
        except Exception as e:
            currency = self._extract_currency_from_symbol(symbol)
            is_problematic_currency = currency in ['GBP', 'EUR', 'AUD']
            
            if is_problematic_currency:
                logger.error(f"❌ Yahoo chart API fetch failed for {currency} ({symbol}) {interval}: {e}")
                logger.error(f"📊 Symbol: {symbol}")
                logger.error(f"⏰ Time range: {start_time} to {end_time}")
                logger.error(f"🌍 Timezone: {start_time.tzinfo} -> {end_time.tzinfo}")
            else:
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
                logger.debug(f"Using cached data for {symbol} ({len(cached_data)} data points)")
                return cached_data

            # Enhanced logging for GBP, EUR, AUD issues
            currency = self._extract_currency_from_symbol(symbol)
            is_problematic_currency = currency in ['GBP', 'EUR', 'AUD']
            
            if is_problematic_currency:
                logger.info(f"🔍 Fetching data for {currency} symbol {symbol} from {start_time} to {end_time}")
                logger.info(f"📊 Time window: {(end_time - start_time).total_seconds() / 3600:.1f} hours")
                logger.info(f"🌍 Timezone: {start_time.tzinfo} -> {end_time.tzinfo}")
            else:
                logger.info(f"Fetching price data for {symbol} from {start_time} to {end_time}")

            # Try different intervals if 1m fails
            intervals = ['1m', '5m', '15m', '1h']

            for interval in intervals:
                try:
                    if is_problematic_currency:
                        logger.info(f"🔄 Attempting {interval} interval for {currency} ({symbol})")
                    
                    data = self._fetch_with_retry(symbol, start_time, end_time, interval)

                    if data is not None and not data.empty:
                        # Cache the data
                        self._cache_data(symbol, data, start_time, end_time)
                        if is_problematic_currency:
                            logger.info(f"✅ Successfully fetched {len(data)} data points for {currency} with {interval} interval")
                        return data
                    else:
                        if is_problematic_currency:
                            logger.warning(f"⚠️ No data found for {currency} ({symbol}) with {interval} interval")
                        else:
                            logger.warning(f"No data found for {symbol} with {interval} interval")

                except Exception as e:
                    if is_problematic_currency:
                        logger.warning(f"❌ Failed to fetch data for {currency} ({symbol}) with {interval} interval: {e}")
                    else:
                        logger.warning(f"Failed to fetch data for {symbol} with {interval} interval: {e}")
                    continue

            # If all intervals fail, try with a broader time range
            if is_problematic_currency:
                logger.info(f"🔄 Trying broader time range for {currency} ({symbol})")
            else:
                logger.info(f"Trying broader time range for {symbol}")
            
            try:
                broader_start = start_time - timedelta(days=1)
                broader_end = end_time + timedelta(days=1)

                data = self._fetch_with_retry(symbol, broader_start, broader_end, '1d')

                if data is not None and not data.empty:
                    if is_problematic_currency:
                        logger.info(f"✅ Successfully fetched {len(data)} data points for {currency} with broader range")
                    else:
                        logger.info(f"Successfully fetched {len(data)} data points for {symbol} with broader range")
                    self._cache_data(symbol, data, start_time, end_time)
                    return data

            except Exception as e:
                if is_problematic_currency:
                    logger.error(f"❌ Failed to fetch data with broader range for {currency} ({symbol}): {e}")
                else:
                    logger.error(f"Failed to fetch data with broader range for {symbol}: {e}")

            # Try alternative data sources
            if is_problematic_currency:
                logger.info(f"🔄 Trying alternative data sources for {currency} ({symbol})")
            else:
                logger.info(f"Trying alternative data sources for {symbol}")
            
            data = self._try_alternative_data_source(symbol, start_time, end_time)
            if data is not None and not data.empty:
                self._cache_data(symbol, data, start_time, end_time)
                if is_problematic_currency:
                    logger.info(f"✅ Alternative data source provided {len(data)} data points for {currency}")
                return data

            # If all else fails, optionally generate mock data
            if self.allow_mock_data:
                if is_problematic_currency:
                    logger.warning(f"⚠️ All data sources failed for {currency} ({symbol}), generating mock data for demonstration")
                else:
                    logger.warning(f"All data sources failed for {symbol}, generating mock data for demonstration")
                
                mock_data = self._generate_mock_data(symbol, start_time, end_time)
                if mock_data is not None and not mock_data.empty:
                    if is_problematic_currency:
                        logger.info(f"🎭 Using mock data for {currency} with {len(mock_data)} data points")
                    else:
                        logger.info(f"Using mock data for {symbol} with {len(mock_data)} data points")
                    return mock_data
            else:
                if is_problematic_currency:
                    logger.warning(f"❌ All data sources failed for {currency} ({symbol}) and mock data is disabled")
                else:
                    logger.warning("All data sources failed and mock data is disabled; returning None")

            if is_problematic_currency:
                logger.error(f"❌ No data found for {currency} ({symbol}) in the specified time range with any method")
                logger.error(f"📊 Symbol mapping: {symbol}")
                logger.error(f"⏰ Time range: {start_time} to {end_time}")
                logger.error(f"🌍 Timezone alignment: {start_time.tzinfo} -> {end_time.tzinfo}")
            else:
                logger.warning(f"No data found for {symbol} in the specified time range with any method")
            
            return None

        except Exception as e:
            currency = self._extract_currency_from_symbol(symbol)
            is_problematic_currency = currency in ['GBP', 'EUR', 'AUD']
            
            if is_problematic_currency:
                logger.error(f"❌ Error fetching price data for {currency} ({symbol}): {e}")
                logger.error(f"📊 Symbol: {symbol}")
                logger.error(f"⏰ Time range: {start_time} to {end_time}")
                logger.error(f"🌍 Timezone: {start_time.tzinfo} -> {end_time.tzinfo}")
            else:
                logger.error(f"Error fetching price data for {symbol}: {e}")
            return None

    def _extract_currency_from_symbol(self, symbol: str) -> str:
        """Extract currency from symbol for enhanced logging."""
        try:
            # Remove common suffixes
            clean_symbol = symbol.replace('=X', '').replace('-USD', '').replace('USD', '')
            
            # Common currency mappings
            if 'EUR' in clean_symbol:
                return 'EUR'
            elif 'GBP' in clean_symbol:
                return 'GBP'
            elif 'AUD' in clean_symbol:
                return 'AUD'
            elif 'JPY' in clean_symbol:
                return 'JPY'
            elif 'CAD' in clean_symbol:
                return 'CAD'
            elif 'CHF' in clean_symbol:
                return 'CHF'
            elif 'NZD' in clean_symbol:
                return 'NZD'
            elif 'USD' in clean_symbol:
                return 'USD'
            else:
                return clean_symbol[:3] if len(clean_symbol) >= 3 else 'UNK'
        except Exception:
            return 'UNK'

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
                logger.warning(f"Candlestick plot failed; synthesizing OHLC: {e}")
                try:
                    synth = self._synthesize_ohlc_from_close(price_data)
                    synth.index = local_index
                    self._plot_candlesticks(ax1, synth, f'{currency}/{symbol.split("=")[0][-3:]}')
                except Exception as e2:
                    logger.error(f"Failed to synthesize candlesticks: {e2}")
            ax1.set_ylabel('Price', fontsize=12)
            ax1.grid(True, alpha=0.3)

            # Add event marker (2x thinner dashed line)
            ax1.axvline(x=event_time_local, color='red', linestyle='--', linewidth=1, alpha=0.8, label='Event Time')

            # Add impact level indicator
            impact_colors = {'high': '#d62728', 'medium': '#ff7f0e', 'low': '#2ca02c'}
            impact_color = impact_colors.get(impact_level, '#ff7f0e')

            # Add shaded area around event time (reduced to ±15 minutes)
            event_window = timedelta(minutes=15)
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
                                   impact_level: str,
                                   window_hours: int) -> BytesIO:
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
                    logger.warning(f"Candlestick plot failed for {pair}; synthesizing OHLC: {e}")
                    try:
                        synth = self._synthesize_ohlc_from_close(data)
                        synth.index = local_index
                        self._plot_candlesticks(ax, synth, pair)
                    except Exception as e2:
                        logger.error(f"Failed to synthesize candlesticks for {pair}: {e2}")

            # Add event marker in display timezone (2x thinner dashed line)
            event_time_local = event_time.astimezone(self.display_tz)
            ax.axvline(x=event_time_local, color='red', linestyle='--', linewidth=1, alpha=0.8, label='Event Time')

            # Add impact level shading (reduced to ±15 minutes)
            impact_colors = {'high': '#d62728', 'medium': '#ff7f0e', 'low': '#2ca02c'}
            impact_color = impact_colors.get(impact_level, '#ff7f0e')

            event_window = timedelta(minutes=15)
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

            # Add event marker (2x thinner dashed line)
            ax.axvline(x=event_time_local, color='red', linestyle='--', linewidth=1, alpha=0.8, label='Event Time')

            # Add impact level shading (reduced to ±15 minutes)
            impact_colors = {'high': '#d62728', 'medium': '#ff7f0e', 'low': '#2ca02c'}
            impact_color = impact_colors.get(impact_level, '#ff7f0e')

            event_window = timedelta(minutes=15)
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

            # Work in display timezone for user-friendly axes/labels
            event_time_local = event_time.astimezone(self.display_tz)

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

            # Prefer candlesticks; fallback to synthesized candlesticks
            try:
                candlestick_data = plot_data[['Open', 'High', 'Low', 'Close']].copy()
                # Ensure index is in display timezone for consistent plotting
                try:
                    if candlestick_data.index.tzinfo:
                        candlestick_data.index = candlestick_data.index.tz_convert(self.display_tz)
                    else:
                        candlestick_data.index = candlestick_data.index.tz_localize(self.display_tz)
                except Exception:
                    pass
                # If we have too few points, skip plotting
                if len(candlestick_data) < 2:
                    raise ValueError("Not enough data points for candlesticks")
                self._plot_candlesticks(ax, candlestick_data, f'{primary_currency}/{secondary_currency}')
                ax.set_ylabel(f'{primary_currency} Price (in {secondary_currency})', fontsize=12)
                ax.set_xlabel('Time', fontsize=12)
                ax.grid(True, alpha=0.3)
            except Exception as e:
                logger.warning(f"Failed to create candlestick chart; synthesizing OHLC: {e}")
                try:
                    synth = self._synthesize_ohlc_from_close(plot_data)
                    try:
                        if synth.index.tzinfo:
                            synth.index = synth.index.tz_convert(self.display_tz)
                        else:
                            synth.index = synth.index.tz_localize(self.display_tz)
                    except Exception:
                        pass
                    if len(synth) < 2:
                        raise ValueError("Not enough data points for synthesized candlesticks")
                    self._plot_candlesticks(ax, synth, f'{primary_currency}/{secondary_currency}')
                    ax.set_ylabel(f'{primary_currency} Price (in {secondary_currency})', fontsize=12)
                    ax.set_xlabel('Time', fontsize=12)
                    ax.grid(True, alpha=0.3)
                except Exception as e2:
                    logger.error(f"Failed to synthesize candlesticks for direct pair: {e2}")

            # Add event marker (2x thinner dashed line)
            ax.axvline(x=event_time_local, color='red', linestyle='--', linewidth=1, alpha=0.8, label='Event Time')

            # Add impact level shading (reduced to ±15 minutes)
            impact_colors = {'high': '#d62728', 'medium': '#ff7f0e', 'low': '#2ca02c'}
            impact_color = impact_colors.get(impact_level, '#ff7f0e')

            event_window = timedelta(minutes=15)
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
            # As a last resort, try synthesizing from Close and replot
            try:
                synth = self._synthesize_ohlc_from_close(ohlc_data)
                self._plot_candlesticks(ax, synth, pair_name)
            except Exception:
                # Give up silently to avoid infinite recursion; caller handles logging
                pass

    def _synthesize_ohlc_from_close(self, data: pd.DataFrame) -> pd.DataFrame:
        """Build a minimal OHLC frame from Close (ensures candlestick rendering).

        - Open: previous close (first equals close)
        - High/Low: max/min of Open/Close per bar
        """
        try:
            if 'Close' not in data.columns:
                raise ValueError('No Close column available to synthesize OHLC')
            closes = data['Close']
            opens = closes.shift(1).fillna(closes)
            highs = pd.concat([opens, closes], axis=1).max(axis=1)
            lows = pd.concat([opens, closes], axis=1).min(axis=1)
            synth = pd.DataFrame({
                'Open': opens,
                'High': highs,
                'Low': lows,
                'Close': closes
            }, index=data.index)
            return synth
        except Exception as e:
            logger.error(f"Failed to synthesize OHLC: {e}")
            raise

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

    def create_gpt_analysis_chart(self,
                                   symbol: str,
                                   features: Dict[str, object],
                                   window_hours: int = 48) -> Optional[BytesIO]:
        """Create a 5-minute candle chart for the last window_hours with GPT overlays.

        Overlays include:
        - EMA20 and EMA50 (computed on fetched data)
        - Current price line
        - Recent swing high/low from features
        - Round levels
        - Fair Value Gaps (price bands)
        - Equal highs/lows zones (liquidity clusters)
        - Prior session open
        """
        try:
            end_time = datetime.now(self.display_tz)
            start_time = end_time - timedelta(hours=window_hours)

            # Fetch explicit 5m data; fallback to general fetch
            data = self._fetch_with_retry(symbol, start_time, end_time, '5m')
            if data is None or data.empty:
                data = self.fetch_price_data(symbol, start_time, end_time)
            if data is None or data.empty:
                logger.warning(f"No price data for {symbol} to render GPT analysis chart")
                return None

            # Ensure timezone-local index for plotting
            try:
                local_index = data.index.tz_convert(self.display_tz) if data.index.tzinfo else data.index.tz_localize(self.display_tz)
            except Exception:
                local_index = data.index

            # Compute EMAs on Close (ensure alignment with price)
            ema20 = data['Close'].ewm(span=20, adjust=False).mean()
            ema50 = data['Close'].ewm(span=50, adjust=False).mean()

            plt.style.use('default')
            fig, ax = plt.subplots(figsize=(13, 8))

            # Prepare OHLC for candlesticks
            try:
                ohlc = data[['Open', 'High', 'Low', 'Close']].copy()
                ohlc.index = local_index
                self._plot_candlesticks(ax, ohlc, pair_name=self._pretty_pair_name(symbol))
            except Exception as e:
                logger.warning(f"Candlestick plot failed in GPT chart; synthesizing: {e}")
                try:
                    synth = self._synthesize_ohlc_from_close(data)
                    synth.index = local_index
                    self._plot_candlesticks(ax, synth, pair_name=self._pretty_pair_name(symbol))
                except Exception as e2:
                    logger.error(f"Failed to synthesize candlesticks in GPT chart: {e2}")

            # Overlay EMAs
            try:
                ax.plot(local_index, ema20.values, color='#1f77b4', linewidth=1.3, label='EMA20')
                ax.plot(local_index, ema50.values, color='#ff7f0e', linewidth=1.3, label='EMA50')
            except Exception:
                pass

            # Helper: draw horizontal level
            def hline(y, color, lw=1.0, ls='--', alpha=0.8, label=None):
                try:
                    ax.axhline(y=float(y), color=color, linewidth=lw, linestyle=ls, alpha=alpha, label=label)
                except Exception:
                    pass

            # Current price
            try:
                last_price = float(features.get('last_price')) if features.get('last_price') is not None else float(data['Close'].iloc[-1])
                hline(last_price, color='#2ca02c', lw=1.2, ls='-', alpha=0.8, label='Last Price')
            except Exception:
                pass

            # Prior session open
            po = features.get('prior_session_open')
            if po is not None:
                hline(po, color='#9467bd', lw=1.0, ls=':', alpha=0.9, label='Prev Session Open')

            # Round levels
            rlevels = features.get('round_levels') or []
            for lvl in rlevels:
                hline(lvl, color='#7f7f7f', lw=0.8, ls='--', alpha=0.6)

            # Recent swing high/low
            if features.get('recent_swing_high') is not None:
                hline(features.get('recent_swing_high'), color='#d62728', lw=1.0, ls='--', alpha=0.85, label='Recent High')
            if features.get('recent_swing_low') is not None:
                hline(features.get('recent_swing_low'), color='#17becf', lw=1.0, ls='--', alpha=0.85, label='Recent Low')

            # Annotate swing high/low with labels and arrows
            try:
                swing_hi = features.get('recent_swing_high')
                swing_hi_t = features.get('recent_swing_high_time')
                swing_lo = features.get('recent_swing_low')
                swing_lo_t = features.get('recent_swing_low_time')
                # Helper to convert ISO time to local tz
                def _to_local(ts_iso):
                    import pandas as _pd
                    try:
                        ts = _pd.to_datetime(ts_iso, utc=True)
                        return ts.tz_convert(self.display_tz)
                    except Exception:
                        return None
                if swing_hi is not None and swing_hi_t:
                    ts_loc = _to_local(swing_hi_t)
                    if ts_loc is not None:
                        ax.annotate(f"Swing High: {swing_hi:.4f}",
                                    xy=(ts_loc, float(swing_hi)),
                                    xytext=(ts_loc + timedelta(hours=6), float(swing_hi) + (abs(float(swing_hi))*0.0002)),
                                    arrowprops=dict(arrowstyle="->", color='#d62728', lw=1.0),
                                    fontsize=9, color='#d62728', bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.6))
                if swing_lo is not None and swing_lo_t:
                    ts_loc = _to_local(swing_lo_t)
                    if ts_loc is not None:
                        ax.annotate(f"Swing Low: {swing_lo:.4f}",
                                    xy=(ts_loc, float(swing_lo)),
                                    xytext=(ts_loc + timedelta(hours=6), float(swing_lo) - (abs(float(swing_lo))*0.0002)),
                                    arrowprops=dict(arrowstyle="->", color='#17becf', lw=1.0),
                                    fontsize=9, color='#17becf', bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.6))
            except Exception:
                pass

            # Equal highs/lows clusters as bands (liquidity)
            try:
                eq_hi = features.get('equal_highs') or []
                eq_lo = features.get('equal_lows') or []
                if len(eq_hi) >= 1:
                    ax.axhspan(min(eq_hi), max(eq_hi), color='#ff9896', alpha=0.15, label='Equal Highs Zone')
                if len(eq_lo) >= 1:
                    ax.axhspan(min(eq_lo), max(eq_lo), color='#98df8a', alpha=0.15, label='Equal Lows Zone')
            except Exception:
                pass

            # FVG bands (price-only, spanning full x-range)
            try:
                fvgs = features.get('fvgs') or []
                for g in fvgs:
                    start_p = g.get('start')
                    end_p = g.get('end')
                    if start_p is None or end_p is None:
                        continue
                    low = min(float(start_p), float(end_p))
                    high = max(float(start_p), float(end_p))
                    ax.axhspan(low, high, color='#c5b0d5', alpha=0.18, label='FVG')
            except Exception:
                pass

            ax.set_ylabel('Price', fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper left', ncol=3, fontsize=8)

            # Psychological levels (round numbers) across visible range
            try:
                # Determine decimals/step by symbol
                dec = 2 if ('JPY' in symbol or '/JPY' in self._pretty_pair_name(symbol)) else 4
                step = 0.5 if dec == 2 else 0.005
                # Determine min/max from plotted data and overlays
                y_candidates = [
                    float(data['Low'].min()), float(data['High'].max()),
                    *(rlevels or []),
                ]
                if po is not None:
                    y_candidates.append(float(po))
                if swing_hi is not None:
                    y_candidates.append(float(swing_hi))
                if swing_lo is not None:
                    y_candidates.append(float(swing_lo))
                for g in (fvgs or []):
                    if g.get('start') is not None and g.get('end') is not None:
                        y_candidates.append(float(min(g['start'], g['end'])))
                        y_candidates.append(float(max(g['start'], g['end'])))
                y_min = min(y_candidates) if y_candidates else float(data['Low'].min())
                y_max = max(y_candidates) if y_candidates else float(data['High'].max())
                # Draw psych levels within range (coarse grid)
                from math import floor, ceil
                start_level = floor(y_min / step) * step
                end_level = ceil(y_max / step) * step
                lvl = start_level
                while lvl <= end_level:
                    ax.axhline(y=float(lvl), color='#cccccc', linewidth=0.6, linestyle=':', alpha=0.6)
                    lvl = round(lvl + step, dec + 1)
            except Exception:
                pass

            # X-axis formatting (will apply after zoom range)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M', tz=self.display_tz))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

            # Title
            pair_title = self._pretty_pair_name(symbol)
            fig.suptitle(f'{pair_title} — GPT Analysis (5m, last {window_hours}h)', fontsize=14, fontweight='bold')

            # Scenario annotations based on swings
            try:
                x_pos = local_index[int(len(local_index) * 0.8)] if len(local_index) > 0 else None
                if x_pos is not None:
                    if features.get('recent_swing_low') is not None:
                        lo = float(features['recent_swing_low'])
                        ax.annotate('📉 Break below ' + f"{lo:.4f}" + ' → bearish continuation',
                                    xy=(x_pos, lo), xytext=(x_pos, lo - (abs(lo) * 0.0015)),
                                    arrowprops=dict(arrowstyle='->', color='#d62728', lw=1.0),
                                    fontsize=9, color='#d62728', bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.6))
                    if features.get('recent_swing_high') is not None:
                        hi = float(features['recent_swing_high'])
                        ax.annotate('📈 Break above ' + f"{hi:.4f}" + ' → possible reversal',
                                    xy=(x_pos, hi), xytext=(x_pos, hi + (abs(hi) * 0.0015)),
                                    arrowprops=dict(arrowstyle='->', color='#2ca02c', lw=1.0),
                                    fontsize=9, color='#2ca02c', bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.6))
            except Exception:
                pass

            # Fit view to full 48h range (x) and auto-fit Y-axis to full price range
            try:
                # Full x-range
                ax.set_xlim(local_index[0], local_index[-1])

                # Choose a source for highs/lows aligned to local_index
                price_source = None
                try:
                    price_source = ohlc
                except NameError:
                    try:
                        price_source = synth
                    except NameError:
                        import pandas as _pd
                        price_source = _pd.DataFrame({
                            'High': data['High'].values,
                            'Low': data['Low'].values,
                        }, index=local_index)

                p_low = float(price_source['Low'].min())
                p_high = float(price_source['High'].max())

                # Include overlays in Y fit
                if po is not None:
                    p_low = min(p_low, float(po))
                    p_high = max(p_high, float(po))
                if features.get('recent_swing_low') is not None:
                    p_low = min(p_low, float(features['recent_swing_low']))
                if features.get('recent_swing_high') is not None:
                    p_high = max(p_high, float(features['recent_swing_high']))
                for g in (fvgs or []):
                    if g.get('start') is not None and g.get('end') is not None:
                        gl = float(min(g['start'], g['end']))
                        gh = float(max(g['start'], g['end']))
                        p_low = min(p_low, gl)
                        p_high = max(p_high, gh)
                for lvl in (rlevels or []):
                    try:
                        p_low = min(p_low, float(lvl))
                        p_high = max(p_high, float(lvl))
                    except Exception:
                        pass

                # Buffer by pair type
                is_jpy = ('JPY' in symbol) or ('/JPY' in pair_title)
                base_buffer = 0.1 if is_jpy else 0.0015
                y_range = max(1e-12, p_high - p_low)
                y_margin = max(y_range * 0.10, base_buffer)
                ax.set_ylim(p_low - y_margin, p_high + y_margin)
            except Exception:
                pass

            plt.tight_layout(rect=[0, 0.03, 1, 0.97])

            # Save to buffer and persist
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            try:
                filename = f"gpt_{pair_title.replace('/', '')}_{end_time.strftime('%Y%m%d_%H%M')}_w{window_hours}h.png"
                self._save_chart_buffer(buf, filename)
            except Exception:
                pass
            return buf
        except Exception as e:
            logger.error(f"Error generating GPT analysis chart for {symbol}: {e}")
            plt.close()
            return None

    def create_gpt_full_view_chart(self,
                                   symbol: str,
                                   features: Dict[str, object],
                                   window_hours: int = 48) -> Optional[BytesIO]:
        """Create a simplified full-view chart (5m, last 48h) showing only EMAs.

        - Uses full window_hours for both EMA calculations and display
        - No annotations, zones, or psychological levels
        """
        try:
            end_time = datetime.now(self.display_tz)
            start_time = end_time - timedelta(hours=window_hours)

            data = self._fetch_with_retry(symbol, start_time, end_time, '5m')
            if data is None or data.empty:
                data = self.fetch_price_data(symbol, start_time, end_time)
            if data is None or data.empty:
                return None

            try:
                local_index = data.index.tz_convert(self.display_tz) if data.index.tzinfo else data.index.tz_localize(self.display_tz)
            except Exception:
                local_index = data.index

            # EMAs from full series
            ema20 = data['Close'].ewm(span=20, adjust=False).mean()
            ema50 = data['Close'].ewm(span=50, adjust=False).mean()

            plt.style.use('default')
            fig, ax = plt.subplots(figsize=(13, 8))

            # Candlesticks
            ohlc = None
            try:
                ohlc = data[['Open', 'High', 'Low', 'Close']].copy()
                ohlc.index = local_index
                self._plot_candlesticks(ax, ohlc, pair_name=self._pretty_pair_name(symbol))
            except Exception:
                try:
                    synth = self._synthesize_ohlc_from_close(data)
                    synth.index = local_index
                    self._plot_candlesticks(ax, synth, pair_name=self._pretty_pair_name(symbol))
                except Exception:
                    pass

            # Only EMAs
            try:
                ax.plot(local_index, ema20.values, color='#1f77b4', linewidth=1.3, label='EMA20')
                ax.plot(local_index, ema50.values, color='#ff7f0e', linewidth=1.3, label='EMA50')
            except Exception:
                pass

            ax.set_ylabel('Price', fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper left', ncol=2, fontsize=9)

            # Full range fit
            try:
                ax.set_xlim(local_index[0], local_index[-1])
                src = ohlc if ohlc is not None else data
                p_low = float(src['Low'].min()) if 'Low' in src.columns else float(data['Close'].min())
                p_high = float(src['High'].max()) if 'High' in src.columns else float(data['Close'].max())
                y_range = max(1e-12, p_high - p_low)
                y_margin = y_range * 0.10
                ax.set_ylim(p_low - y_margin, p_high + y_margin)
            except Exception:
                pass

            # Axes
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M', tz=self.display_tz))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

            title = f"{self._pretty_pair_name(symbol)} — EMAs (5m, last {window_hours}h)"
            fig.suptitle(title, fontsize=14, fontweight='bold')

            plt.tight_layout(rect=[0, 0.03, 1, 0.97])
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            try:
                filename = f"gpt_full_{self._pretty_pair_name(symbol).replace('/', '')}_{end_time.strftime('%Y%m%d_%H%M')}_w{window_hours}h.png"
                self._save_chart_buffer(buf, filename)
            except Exception:
                pass
            return buf
        except Exception as e:
            logger.error(f"Error generating full-view chart for {symbol}: {e}")
            plt.close()
            return None

    def create_gpt_zoom_view_chart(self,
                                   symbol: str,
                                   features: Dict[str, object],
                                   window_hours: int = 48,
                                   zoom_hours: int = 12) -> Optional[BytesIO]:
        """Create a zoomed (last 12h) chart with all feature overlays and annotations."""
        try:
            end_time = datetime.now(self.display_tz)
            start_time = end_time - timedelta(hours=window_hours)

            data = self._fetch_with_retry(symbol, start_time, end_time, '5m')
            if data is None or data.empty:
                data = self.fetch_price_data(symbol, start_time, end_time)
            if data is None or data.empty:
                return None

            try:
                local_index = data.index.tz_convert(self.display_tz) if data.index.tzinfo else data.index.tz_localize(self.display_tz)
            except Exception:
                local_index = data.index

            # EMAs from full series
            ema20 = data['Close'].ewm(span=20, adjust=False).mean()
            ema50 = data['Close'].ewm(span=50, adjust=False).mean()

            plt.style.use('default')
            fig, ax = plt.subplots(figsize=(13, 8))

            # Candlesticks
            ohlc = None
            try:
                ohlc = data[['Open', 'High', 'Low', 'Close']].copy()
                ohlc.index = local_index
                self._plot_candlesticks(ax, ohlc, pair_name=self._pretty_pair_name(symbol))
            except Exception:
                try:
                    synth = self._synthesize_ohlc_from_close(data)
                    synth.index = local_index
                    self._plot_candlesticks(ax, synth, pair_name=self._pretty_pair_name(symbol))
                except Exception:
                    pass

            # EMAs
            try:
                ax.plot(local_index, ema20.values, color='#1f77b4', linewidth=1.3, label='EMA20')
                ax.plot(local_index, ema50.values, color='#ff7f0e', linewidth=1.3, label='EMA50')
            except Exception:
                pass

            # Helper
            def hline(y, color, lw=1.0, ls='--', alpha=0.8, label=None):
                try:
                    ax.axhline(y=float(y), color=color, linewidth=lw, linestyle=ls, alpha=alpha, label=label)
                except Exception:
                    pass

            # Current price
            try:
                last_price = float(features.get('last_price')) if features.get('last_price') is not None else float(data['Close'].iloc[-1])
                hline(last_price, color='#2ca02c', lw=1.2, ls='-', alpha=0.8, label='Last Price')
            except Exception:
                pass

            # Prior open, round levels, swings
            po = features.get('prior_session_open')
            if po is not None:
                hline(po, color='#9467bd', lw=1.0, ls=':', alpha=0.9, label='Prev Session Open')
            rlevels = features.get('round_levels') or []
            for lvl in rlevels:
                hline(lvl, color='#7f7f7f', lw=0.8, ls='--', alpha=0.6)
            if features.get('recent_swing_high') is not None:
                hline(features.get('recent_swing_high'), color='#d62728', lw=1.0, ls='--', alpha=0.85, label='Recent High')
            if features.get('recent_swing_low') is not None:
                hline(features.get('recent_swing_low'), color='#17becf', lw=1.0, ls='--', alpha=0.85, label='Recent Low')

            # Swing annotations
            try:
                swing_hi = features.get('recent_swing_high')
                swing_hi_t = features.get('recent_swing_high_time')
                swing_lo = features.get('recent_swing_low')
                swing_lo_t = features.get('recent_swing_low_time')
                import pandas as _pd
                def _to_local(ts_iso):
                    try:
                        ts = _pd.to_datetime(ts_iso, utc=True)
                        return ts.tz_convert(self.display_tz)
                    except Exception:
                        return None
                if swing_hi is not None and swing_hi_t:
                    ts_loc = _to_local(swing_hi_t)
                    if ts_loc is not None:
                        ax.annotate(f"Swing High: {swing_hi:.4f}", xy=(ts_loc, float(swing_hi)),
                                    xytext=(ts_loc + timedelta(hours=3), float(swing_hi) + (abs(float(swing_hi))*0.0002)),
                                    arrowprops=dict(arrowstyle="->", color='#d62728', lw=1.0), fontsize=9, color='#d62728',
                                    bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.6))
                if swing_lo is not None and swing_lo_t:
                    ts_loc = _to_local(swing_lo_t)
                    if ts_loc is not None:
                        ax.annotate(f"Swing Low: {swing_lo:.4f}", xy=(ts_loc, float(swing_lo)),
                                    xytext=(ts_loc + timedelta(hours=3), float(swing_lo) - (abs(float(swing_lo))*0.0002)),
                                    arrowprops=dict(arrowstyle="->", color='#17becf', lw=1.0), fontsize=9, color='#17becf',
                                    bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.6))
            except Exception:
                pass

            # Liquidity zones from equal highs/lows and FVGs
            try:
                eq_hi = features.get('equal_highs') or []
                eq_lo = features.get('equal_lows') or []
                if len(eq_hi) >= 1:
                    ax.axhspan(min(eq_hi), max(eq_hi), color='#ff9896', alpha=0.15, label='Equal Highs Zone')
                if len(eq_lo) >= 1:
                    ax.axhspan(min(eq_lo), max(eq_lo), color='#98df8a', alpha=0.15, label='Equal Lows Zone')
            except Exception:
                pass

            try:
                fvgs = features.get('fvgs') or []
                for g in fvgs:
                    start_p = g.get('start'); end_p = g.get('end')
                    if start_p is None or end_p is None:
                        continue
                    low = min(float(start_p), float(end_p)); high = max(float(start_p), float(end_p))
                    ax.axhspan(low, high, color='#c5b0d5', alpha=0.18, label='FVG')
            except Exception:
                pass

            # Psychological levels grid in view
            try:
                dec = 2 if ('JPY' in symbol or '/JPY' in self._pretty_pair_name(symbol)) else 4
                step = 0.5 if dec == 2 else 0.005
                from math import floor, ceil
                # Use overall range to draw grid; zoom will be applied later
                y_min = float(data['Low'].min()); y_max = float(data['High'].max())
                start_level = floor(y_min / step) * step
                end_level = ceil(y_max / step) * step
                lvl = start_level
                while lvl <= end_level:
                    ax.axhline(y=float(lvl), color='#cccccc', linewidth=0.6, linestyle=':', alpha=0.6)
                    lvl = round(lvl + step, dec + 1)
            except Exception:
                pass

            # Scenario labels
            try:
                x_pos = local_index[int(len(local_index) * 0.85)] if len(local_index) > 0 else None
                if x_pos is not None:
                    if features.get('recent_swing_low') is not None:
                        lo = float(features['recent_swing_low'])
                        ax.annotate('📉 Break below ' + f"{lo:.4f}" + ' → bearish continuation',
                                    xy=(x_pos, lo), xytext=(x_pos, lo - (abs(lo) * 0.0015)),
                                    arrowprops=dict(arrowstyle='->', color='#d62728', lw=1.0), fontsize=9, color='#d62728',
                                    bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.6))
                    if features.get('recent_swing_high') is not None:
                        hi = float(features['recent_swing_high'])
                        ax.annotate('📈 Break above ' + f"{hi:.4f}" + ' → possible reversal',
                                    xy=(x_pos, hi), xytext=(x_pos, hi + (abs(hi) * 0.0015)),
                                    arrowprops=dict(arrowstyle='->', color='#2ca02c', lw=1.0), fontsize=9, color='#2ca02c',
                                    bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.6))
            except Exception:
                pass

            # Apply zoom to last zoom_hours
            try:
                from datetime import timedelta as _td
                end_zoom = local_index[-1]; start_zoom = end_zoom - _td(hours=zoom_hours)
                mask = (local_index >= start_zoom) & (local_index <= end_zoom)
                if mask.any():
                    li = local_index[mask]
                    ax.set_xlim(li[0], li[-1])
                    src = ohlc if ohlc is not None else data
                    z_low = float(src.loc[li]['Low'].min()) if 'Low' in src.columns else float(data.loc[li]['Close'].min())
                    z_high = float(src.loc[li]['High'].max()) if 'High' in src.columns else float(data.loc[li]['Close'].max())
                    is_jpy = ('JPY' in symbol) or ('/JPY' in self._pretty_pair_name(symbol))
                    base_buffer = 0.1 if is_jpy else 0.0015
                    y_range = max(1e-12, z_high - z_low)
                    y_margin = max(y_range * 0.10, base_buffer)
                    ax.set_ylim(z_low - y_margin, z_high + y_margin)
                    ax.axvline(start_zoom, linestyle='--', color='gray', alpha=0.2)
                    ax.axvline(end_zoom, linestyle='--', color='gray', alpha=0.2)
            except Exception:
                pass

            # Axes and title
            ax.set_ylabel('Price', fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper left', ncol=3, fontsize=8)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M', tz=self.display_tz))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            fig.suptitle(f"{self._pretty_pair_name(symbol)} — Zoomed View (5m, last {zoom_hours}h)", fontsize=14, fontweight='bold')

            plt.tight_layout(rect=[0, 0.03, 1, 0.97])
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            try:
                filename = f"gpt_zoom_{self._pretty_pair_name(symbol).replace('/', '')}_{end_time.strftime('%Y%m%d_%H%M')}_z{zoom_hours}h.png"
                self._save_chart_buffer(buf, filename)
            except Exception:
                pass
            return buf
        except Exception as e:
            logger.error(f"Error generating zoom-view chart for {symbol}: {e}")
            plt.close()
            return None

    def _pretty_pair_name(self, symbol: str) -> str:
        try:
            if '-' in symbol:
                base, quote = symbol.split('-', 1)
                return f"{base}/{quote}"
            if symbol.endswith('=X') and len(symbol) >= 6:
                base = symbol[:3]
                quote = symbol[3:6]
                return f"{base}/{quote}"
            return symbol.replace('=X', '')
        except Exception:
            return symbol


# Global chart service instance
chart_service = ChartService()

# === Event-driven utilities and renderers ===

def get_pair_and_poll(currency: str) -> tuple[str, str, list[str]]:
    """
    Returns (yahoo_symbol, poll_question, poll_options)
    """
    mapping = {
        "USD": ("USDJPY=X", "Do you think USDJPY will go up or down?", ["Up", "Down"]),
        "JPY": ("USDJPY=X", "Do you think USDJPY will go up or down?", ["Up", "Down"]),
        "CAD": ("USDCAD=X", "Do you think USDCAD will go up or down?", ["Up", "Down"]),
        "EUR": ("EURUSD=X", "Do you think EURUSD will go up or down?", ["Up", "Down"]),
        "GBP": ("GBPUSD=X", "Do you think GBPUSD will go up or down?", ["Up", "Down"]),
    }
    return mapping.get(currency, ("EURUSD=X", f"Do you think {currency}/USD will go up or down?", ["Up", "Down"]))


def fetch_prices_with_backoff(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    """
    Guarantees non-empty OHLCV for [start, end]. Clamps `end` to now.
    Tries intervals in order: 1m → 5m → 15m → 60m, with 3 retries each.
    Returns trimmed DataFrame with columns Open, High, Low, Close, Volume.
    """
    if start.tzinfo is None:
        start = pytz.UTC.localize(start)
    now = datetime.now(tz=start.tzinfo)
    end = min(end, now)

    intervals = ["1m", "5m", "15m", "60m"]
    last_err = None

    for itv in intervals:
        for _ in range(3):
            try:
                df = yf.download(symbol, start=start, end=end, interval=itv, progress=False)
                if df is not None and not df.empty:
                    df = df.rename(columns=str.title)
                    for col in ["Open", "High", "Low", "Close", "Volume"]:
                        if col not in df.columns:
                            raise ValueError(f"Missing column {col} in downloaded data")
                    df = df[(df.index >= start) & (df.index <= end)]
                    if not df.empty:
                        return df
            except Exception as e:
                last_err = e
                continue

    raise RuntimeError(f"No data for {symbol} in window {start}–{end}: {last_err}")


from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def render_event_chart(
    ohlc: pd.DataFrame,
    title: str,
    subtitle: str,
    event_time: datetime | None,
    show_event_line: str = "tight",   # "none" | "tight"
    change_tuple: tuple[float, float] | None = None,  # (abs, pct)
    y_decimals: int | None = None
) -> BytesIO:
    """
    Renders candles; optional thin event line; optional Change badge.
    """
    fig, ax = plt.subplots(figsize=(12, 8))

    # Expect ohlc index tz-aware; if not, treat as UTC
    idx = ohlc.index
    # Minimal candlesticks
    for t, row in ohlc.iterrows():
        o, h, l, c = row["Open"], row["High"], row["Low"], row["Close"]
        color = "green" if c >= o else "red"
        # wick
        ax.plot([t, t], [l, h], color="black", linewidth=0.7, alpha=0.8)
        # body
        ax.add_patch(Rectangle((mdates.date2num(t) - 0.0015, min(o, c)),
                               0.003, abs(c - o),
                               facecolor=color, edgecolor="black", linewidth=0.4, alpha=0.8))

    # Thin or hidden event line
    if event_time and show_event_line != "none":
        ax.axvline(event_time, color="red", linestyle="--", linewidth=0.5, alpha=0.6)

    # Change badge
    if change_tuple is not None:
        abs_, pct_ = change_tuple
        fmt = (f"{{:+.{y_decimals}f}}" if y_decimals is not None else "{:+.4f}")
        ax.text(
            0.015, 0.975,
            f"Change: {fmt.format(abs_)} ({pct_:+.2f}%)",
            transform=ax.transAxes, va="top",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.85)
        )

    ax.set_title("Candlestick Chart", fontsize=12, fontweight="bold")
    plt.suptitle(f"{title}\n{subtitle}", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return buf


def create_chart_2h_after_event(currency: str, event_time: datetime, event_name: str, display_tz: str = "Europe/Prague") -> BytesIO:
    """
    Window: [event_time, event_time + 2h], clamped to 'now'.
    Computes Change (first close → last close). Hides or thins event line so candle remains visible.
    """
    tz = pytz.timezone(display_tz)
    if event_time.tzinfo is None:
        event_time = tz.localize(event_time)

    start = event_time
    end = event_time + timedelta(hours=2)

    symbol, _, _ = get_pair_and_poll(currency)
    df = fetch_prices_with_backoff(symbol, start, end)

    start_close = float(df["Close"].iloc[0])
    end_close = float(df["Close"].iloc[-1])
    change_abs = end_close - start_close
    change_pct = (change_abs / start_close) * 100.0

    y_decimals = 2 if "JPY" in symbol or symbol.endswith("JPY=X") else 4

    return render_event_chart(
        ohlc=df,
        title=f"{symbol} — 2h post-event",
        subtitle=event_time.astimezone(tz).strftime("%Y-%m-%d"),
        event_time=event_time,
        show_event_line="tight",
        change_tuple=(change_abs, change_pct),
        y_decimals=y_decimals
    )


def create_chart_15m_after_high_impact(currency: str, event_time: datetime, event_name: str, expected: float | None, actual: float | None, display_tz: str = "Europe/Prague") -> tuple[BytesIO, str]:
    """
    Window: 1h BEFORE to 15m AFTER the event on 1m timeframe (falls back if needed).
    Returns (png, 1–2 sentence summary comparing expected vs actual).
    """
    tz = pytz.timezone(display_tz)
    if event_time.tzinfo is None:
        event_time = tz.localize(event_time)

    start = event_time - timedelta(hours=1)
    end = event_time + timedelta(minutes=15)

    symbol, _, _ = get_pair_and_poll(currency)
    df = fetch_prices_with_backoff(symbol, start, end)

    chart = render_event_chart(
        ohlc=df,
        title=f"{symbol} — 1h pre / 15m post",
        subtitle=event_time.astimezone(tz).strftime("%Y-%m-%d"),
        event_time=event_time,
        show_event_line="tight",
        change_tuple=None
    )

    if expected is None or actual is None:
        summary = f"{event_name}: initial {symbol} reaction shown (1m candles, 1h pre / 15m post)."
    else:
        direction = "higher" if actual > expected else ("lower" if actual < expected else "in line with")
        summary = f"{event_name}: actual {actual} vs expected {expected} — actual came in {direction} than forecast. Initial {symbol} reaction shown (1m, 1h pre / 15m post)."

    return chart, summary
