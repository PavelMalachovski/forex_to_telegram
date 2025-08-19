import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple

import numpy as np
import pandas as pd
import pytz
import requests

from .chart_service import chart_service

logger = logging.getLogger(__name__)

# Simple in-memory rate limiter for GPT calls
_LAST_GPT_CALLS: Dict[str, float] = {}


def _get_symbol_from_currencies(base_currency: str, quote_currency: str) -> str:
    base = (base_currency or '').upper()
    quote = (quote_currency or '').upper()
    # Crypto pairs on Yahoo use dash notation, e.g., BTC-USD, ETH-EUR
    crypto = {"BTC", "ETH"}
    if base in crypto or quote in crypto:
        # Prefer crypto as the left side (Yahoo style)
        if base in crypto and quote not in crypto:
            return f"{base}-{quote}"
        if quote in crypto and base not in crypto:
            return f"{quote}-{base}"
        # Crypto-to-crypto (fallback dash form)
        return f"{base}-{quote}"
    # Metals/FX pairs use =X suffix, e.g., XAUUSD=X, EURUSD=X
    return f"{base}{quote}=X"


def _infer_price_decimals(symbol: str) -> int:
    # JPY pairs conventionally use 2 decimals; others use 4
    return 2 if "JPY" in symbol else 4


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()


def _find_swings(data: pd.DataFrame, lookback: int = 3) -> Tuple[List[Tuple[pd.Timestamp, float]], List[Tuple[pd.Timestamp, float]]]:
    highs: List[Tuple[pd.Timestamp, float]] = []
    lows: List[Tuple[pd.Timestamp, float]] = []
    for i in range(lookback, len(data) - lookback):
        window = data.iloc[i - lookback:i + lookback + 1]
        if data['High'].iloc[i] == window['High'].max():
            highs.append((data.index[i], float(data['High'].iloc[i])))
        if data['Low'].iloc[i] == window['Low'].min():
            lows.append((data.index[i], float(data['Low'].iloc[i])))
    return highs, lows


def _detect_bos(data: pd.DataFrame, swings_hi: List[Tuple[pd.Timestamp, float]], swings_lo: List[Tuple[pd.Timestamp, float]]) -> Dict[str, Any]:
    bos: Optional[Dict[str, Any]] = None
    last_break: Optional[str] = None
    last_break_time: Optional[pd.Timestamp] = None

    hi_levels = [v for _, v in swings_hi]
    lo_levels = [v for _, v in swings_lo]

    for t, row in data.iterrows():
        high = row.get('High')
        low = row.get('Low')
        if len(hi_levels) > 0 and high is not None and high > max(hi_levels[:-1] or [hi_levels[-1]]):
            last_break = 'BOS_UP'
            last_break_time = t
        if len(lo_levels) > 0 and low is not None and low < min(lo_levels[:-1] or [lo_levels[-1]]):
            last_break = 'BOS_DOWN'
            last_break_time = t

    if last_break and last_break_time:
        bos = {"type": last_break, "time": last_break_time.isoformat()}
    return bos or {"type": None, "time": None}


def _find_last_order_block(data: pd.DataFrame, bos: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not bos.get('type') or not bos.get('time'):
        return None
    bos_time = pd.to_datetime(bos['time'])
    try:
        bos_idx = data.index.get_loc(bos_time, method='nearest')
    except Exception:
        return None
    lookback_slice = data.iloc[max(0, bos_idx - 20):bos_idx]
    if bos['type'] == 'BOS_UP':
        bearish = lookback_slice[lookback_slice['Close'] < lookback_slice['Open']]
        if len(bearish) == 0:
            return None
        last = bearish.iloc[-1]
    else:
        bullish = lookback_slice[lookback_slice['Close'] > lookback_slice['Open']]
        if len(bullish) == 0:
            return None
        last = bullish.iloc[-1]
    ts = last.name
    return {
        "time": ts.isoformat(),
        "open": float(last['Open']),
        "high": float(last['High']),
        "low": float(last['Low']),
        "close": float(last['Close'])
    }


def _find_fvgs(data: pd.DataFrame, limit: int = 3) -> List[Dict[str, Any]]:
    gaps: List[Dict[str, Any]] = []
    for i in range(len(data) - 2):
        c0 = data.iloc[i]
        c2 = data.iloc[i + 2]
        # Upside FVG: low of c2 > high of c0
        if c2['Low'] > c0['High']:
            gaps.append({
                "dir": "up",
                "start": float(c0['High']),
                "end": float(c2['Low']),
                "time0": data.index[i].isoformat(),
                "time2": data.index[i + 2].isoformat()
            })
        # Downside FVG: high of c2 < low of c0
        if c2['High'] < c0['Low']:
            gaps.append({
                "dir": "down",
                "start": float(c2['High']),
                "end": float(c0['Low']),
                "time0": data.index[i].isoformat(),
                "time2": data.index[i + 2].isoformat()
            })
    gaps = gaps[-limit:]
    return gaps


def _find_equal_highs_lows(data: pd.DataFrame, decimals: int) -> Dict[str, List[float]]:
    tol = 10 ** (-decimals)
    highs = []
    lows = []
    rolling_max = data['High'].rolling(5).max()
    rolling_min = data['Low'].rolling(5).min()
    for i in range(5, len(data)):
        h = data['High'].iloc[i]
        if abs(h - rolling_max.iloc[i - 1]) <= tol:
            highs.append(float(round(h, decimals)))
        l = data['Low'].iloc[i]
        if abs(l - rolling_min.iloc[i - 1]) <= tol:
            lows.append(float(round(l, decimals)))
    return {"equal_highs": sorted(list(set(highs)))[-3:], "equal_lows": sorted(list(set(lows)))[-3:]}


def _round_levels_near(price: float, decimals: int) -> List[float]:
    step = 0.5 if decimals == 2 else 0.005
    base = round(price / step) * step
    return [float(round(base - step, decimals)), float(round(base, decimals)), float(round(base + step, decimals))]


def _daily_ranges_from_intraday(df_1h: pd.DataFrame) -> pd.DataFrame:
    daily = df_1h.resample('1D').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
    daily.dropna(inplace=True)
    return daily


def compute_local_features(symbol: str, tz: str = 'Europe/Prague') -> Optional[Dict[str, Any]]:
    try:
        display_tz = pytz.timezone(tz)
        end_time = datetime.now(display_tz)
        start_time_1h = end_time - timedelta(days=2)
        start_time_5m = end_time - timedelta(days=2)

        data_1h = chart_service.fetch_price_data(symbol, start_time_1h, end_time)
        data_5m = chart_service.fetch_price_data(symbol, start_time_5m, end_time)
        if data_1h is None or data_1h.empty:
            return None
        if data_5m is None or data_5m.empty:
            data_5m = data_1h.copy()

        decimals = _infer_price_decimals(symbol)
        last_price = float(round(data_5m['Close'].iloc[-1], decimals))

        prior_session_open = None
        try:
            start_of_day = end_time.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
            recent = data_1h.loc[data_1h.index >= pd.to_datetime(start_of_day, utc=True)]
            if len(recent) > 0:
                prior_session_open = float(round(recent['Open'].iloc[0], decimals))
        except Exception:
            prior_session_open = float(round(data_1h['Open'].iloc[0], decimals))

        price_change = None
        price_change_pct = None
        if prior_session_open is not None and prior_session_open != 0:
            price_change = float(round(last_price - prior_session_open, decimals))
            price_change_pct = float(round((price_change / prior_session_open) * 100, 2))

        swings_hi, swings_lo = _find_swings(data_1h)
        bos = _detect_bos(data_1h, swings_hi, swings_lo)
        order_block = _find_last_order_block(data_1h, bos)
        fvgs = _find_fvgs(data_1h, limit=3)
        lz = _find_equal_highs_lows(data_1h, decimals)

        ema20 = _ema(data_1h['Close'], 20)
        ema50 = _ema(data_1h['Close'], 50)
        ema20_dist = float(round(last_price - float(ema20.iloc[-1]), decimals)) if not np.isnan(ema20.iloc[-1]) else None
        ema50_dist = float(round(last_price - float(ema50.iloc[-1]), decimals)) if not np.isnan(ema50.iloc[-1]) else None
        ema20_slope = None
        ema50_slope = None
        try:
            if len(ema20) >= 2 and not (np.isnan(ema20.iloc[-1]) or np.isnan(ema20.iloc[-2])):
                ema20_slope = float(round(float(ema20.iloc[-1] - ema20.iloc[-2]), decimals))
            if len(ema50) >= 2 and not (np.isnan(ema50.iloc[-1]) or np.isnan(ema50.iloc[-2])):
                ema50_slope = float(round(float(ema50.iloc[-1] - ema50.iloc[-2]), decimals))
        except Exception:
            pass

        atr14 = _atr(data_1h['High'], data_1h['Low'], data_1h['Close'], 14)
        atr_val = float(round(atr14.iloc[-1], decimals)) if not np.isnan(atr14.iloc[-1]) else None

        daily = _daily_ranges_from_intraday(data_1h)
        if len(daily) >= 5:
            daily['range'] = daily['High'] - daily['Low']
            adr = float(round(daily['range'].tail(5).mean(), decimals))
            prev_day_high = float(round(daily['High'].iloc[-2], decimals)) if len(daily) >= 2 else None
            prev_day_low = float(round(daily['Low'].iloc[-2], decimals)) if len(daily) >= 2 else None
        else:
            adr = None
            prev_day_high = None
            prev_day_low = None

        round_levels = _round_levels_near(last_price, decimals)

        features: Dict[str, Any] = {
            "symbol": symbol,
            "timeframe": "last 1-2 days on 1H & 5m",
            "display_timezone": tz,
            "price_decimals": decimals,
            "last_price": last_price,
            "prior_session_open": prior_session_open,
            "change": price_change,
            "change_pct": price_change_pct,
            "recent_swing_high": swings_hi[-1][1] if swings_hi else None,
            "recent_swing_high_time": swings_hi[-1][0].isoformat() if swings_hi else None,
            "recent_swing_low": swings_lo[-1][1] if swings_lo else None,
            "recent_swing_low_time": swings_lo[-1][0].isoformat() if swings_lo else None,
            "last_bos": bos,
            "last_order_block": order_block,
            "fvgs": fvgs,
            "equal_highs": lz.get('equal_highs'),
            "equal_lows": lz.get('equal_lows'),
            "prev_day_high": prev_day_high,
            "prev_day_low": prev_day_low,
            "round_levels": round_levels,
            "ema20_dist": ema20_dist,
            "ema50_dist": ema50_dist,
            "ema20_slope": ema20_slope,
            "ema50_slope": ema50_slope,
            "atr14": atr_val,
            "adr5": adr,
        }
        return features
    except Exception as e:
        logger.error(f"Failed to compute features for {symbol}: {e}")
        return None


def format_features_for_gpt(features: Dict[str, Any]) -> str:
    def fmt(value: Any) -> str:
        if value is None:
            return "NA"
        if isinstance(value, float):
            return f"{value:.5f}".rstrip('0').rstrip('.')
        return str(value)

    parts = [
        f"symbol={features.get('symbol')}",
        f"timeframe={features.get('timeframe')}",
        f"last_price={fmt(features.get('last_price'))}",
        f"prior_session_open={fmt(features.get('prior_session_open'))}",
        f"change={fmt(features.get('change'))}",
        f"change_pct={fmt(features.get('change_pct'))}%",
        f"recent_swing_high={fmt(features.get('recent_swing_high'))}@{fmt(features.get('recent_swing_high_time'))}",
        f"recent_swing_low={fmt(features.get('recent_swing_low'))}@{fmt(features.get('recent_swing_low_time'))}",
        f"last_bos={features.get('last_bos', {}).get('type')}@{features.get('last_bos', {}).get('time')}",
        f"order_block={features.get('last_order_block')}",
        f"fvgs={features.get('fvgs')}",
        f"equal_highs={features.get('equal_highs')}",
        f"equal_lows={features.get('equal_lows')}",
        f"prev_day_high={fmt(features.get('prev_day_high'))}",
        f"prev_day_low={fmt(features.get('prev_day_low'))}",
        f"round_levels={features.get('round_levels')}",
        f"ema20_dist={fmt(features.get('ema20_dist'))}",
        f"ema50_dist={fmt(features.get('ema50_dist'))}",
        f"atr14={fmt(features.get('atr14'))}",
        f"adr5={fmt(features.get('adr5'))}",
    ]
    return " | ".join(parts)


def call_openai_gpt(summary: str, api_key: Optional[str]) -> Optional[str]:
    if not api_key:
        return None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    prompt = (
        "You are a concise FX market analyst. Given the numeric features, write a compact analysis (max 8 bullets) "
        "covering structure (BOS/CHOCH), key levels, OB/FVG, liquidity, and momentum. Avoid fluff."
    )
    data = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.25")),
        "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "500")),
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Features: {summary}"},
        ],
    }
    url = "https://api.openai.com/v1/chat/completions"
    # Simple token- and error-aware retry with backoff
    backoffs = [0.5, 1.0, 2.0]
    for attempt, delay in enumerate(backoffs, start=1):
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=20)
            if resp.status_code in (429, 500, 502, 503, 504):
                logger.warning(f"OpenAI transient error {resp.status_code}; attempt {attempt}/{len(backoffs)}")
                if attempt < len(backoffs):
                    import time as _t
                    _t.sleep(delay)
                    continue
            resp.raise_for_status()
            j = resp.json()
            return j.get("choices", [{}])[0].get("message", {}).get("content", "").strip() or None
        except Exception as e:
            logger.warning(f"OpenAI call failed on attempt {attempt}: {e}")
            if attempt < len(backoffs):
                import time as _t
                _t.sleep(delay)
                continue
            return None
    return None


def build_user_output(features: Dict[str, Any], gpt_text: Optional[str]) -> str:
    def _fmt_num(val: Any, decimals: int) -> str:
        if val is None:
            return "NA"
        if isinstance(val, (int, float)):
            return f"{val:.{decimals}f}".rstrip('0').rstrip('.')
        return str(val)

    def _fmt_time(val: Optional[str], tz_name: Optional[str]) -> str:
        if not val:
            return "NA"
        try:
            ts = pd.to_datetime(val, utc=True)
            if tz_name:
                tz_obj = pytz.timezone(tz_name)
                ts = ts.tz_convert(tz_obj)
            return ts.strftime('%Y-%m-%d %H:%M')
        except Exception:
            return str(val)

    def _fmt_fixed(val: Any, decimals: int) -> str:
        if val is None:
            return "NA"
        try:
            return f"{float(val):.{decimals}f}"
        except Exception:
            return str(val)

    def _fmt_signed(val: Any, decimals: int) -> str:
        if val is None:
            return "NA"
        try:
            v = float(val)
            s = f"{abs(v):.{decimals}f}"
            return ("−" if v < 0 else "+") + s
        except Exception:
            return str(val)

    tz_name = features.get('display_timezone')
    decimals = int(features.get('price_decimals') or 4)

    # Display decimals: 2 for JPY pairs, else 4
    price_dec = 2 if decimals <= 2 else 4
    fvg_dec = max(4, price_dec)  # prefer 4 for FVG precision

    last_price = features.get('last_price')
    prior_open = features.get('prior_session_open')
    change = features.get('change')
    change_pct = features.get('change_pct')

    lp = _fmt_fixed(last_price, price_dec)
    chg_signed = _fmt_signed(change, price_dec)
    pct_signed = _fmt_signed(change_pct, 2).replace('+', '')  # drop plus for %

    swing_h = _fmt_num(features.get('recent_swing_high'), decimals)
    swing_h_t = _fmt_time(features.get('recent_swing_high_time'), tz_name)
    swing_l = _fmt_num(features.get('recent_swing_low'), decimals)
    swing_l_t = _fmt_time(features.get('recent_swing_low_time'), tz_name)
    bos_type = features.get('last_bos', {}).get('type') or 'None'
    bos_time = _fmt_time(features.get('last_bos', {}).get('time'), tz_name)

    pdh = _fmt_fixed(features.get('prev_day_high'), price_dec)
    pdl = _fmt_fixed(features.get('prev_day_low'), price_dec)
    rlevels = features.get('round_levels') or []
    rlevels_str = ", ".join(_fmt_fixed(x, price_dec) for x in rlevels)

    ema20 = _fmt_fixed(features.get('ema20_dist'), price_dec)
    ema50 = _fmt_fixed(features.get('ema50_dist'), price_dec)
    atr14 = _fmt_fixed(features.get('atr14'), price_dec)
    adr5 = _fmt_fixed(features.get('adr5'), price_dec)

    # Pretty pair name from symbol like USDJPY=X -> USD/JPY
    symbol = features.get('symbol') or ''
    try:
        base = symbol[:3]
        quote = symbol[3:6]
        pair_name = f"{base}/{quote}"
    except Exception:
        pair_name = symbol.replace('=X', '')

    lines: List[str] = []
    # Header
    lines.append(f"{pair_name} — Quick Overview")
    lines.append(f"📅 Analysis period: last 1–2 days (1H and 5m charts)")
    lines.append(f"💰 Current price: {lp}")
    po_line = f"{_fmt_fixed(prior_open, price_dec)}" if prior_open is not None else "NA"
    lines.append(f"📉 Change: {chg_signed} ({pct_signed}% from previous open)")
    lines.append("")

    # Key points
    lines.append("Key points:")
    lines.append(f"- Recent high: {swing_h} ({swing_h_t})")
    lines.append(f"- Recent low: {swing_l} ({swing_l_t})")
    lines.append(f"- Round levels: {rlevels_str}")
    lines.append("")

    # FVG section
    fvgs = features.get('fvgs') or []
    if fvgs:
        lines.append("Fair Value Gaps (FVG) — areas where price may react:")
        for g in fvgs:
            g_start = _fmt_fixed(g.get('start'), fvg_dec)
            g_end = _fmt_fixed(g.get('end'), fvg_dec)
            lines.append(f"- {g_start} → {g_end}")
        lines.append("")

    # Liquidity section
    eq_hi = sorted([x for x in (features.get('equal_highs') or [])])
    eq_lo = sorted([x for x in (features.get('equal_lows') or [])])
    hi_min = _fmt_fixed(min(eq_hi), price_dec) if eq_hi else None
    hi_max = _fmt_fixed(max(eq_hi), price_dec) if eq_hi else None
    lo_min = _fmt_fixed(min(eq_lo), price_dec) if eq_lo else None
    lo_max = _fmt_fixed(max(eq_lo), price_dec) if eq_lo else None

    lines.append("Liquidity:")
    if hi_min and hi_max:
        lines.append(f"- Above current price: cluster of orders at {hi_min}–{hi_max} (resistance)")
    if lo_min and lo_max:
        lines.append(f"- Below price: support area around {lo_min}–{lo_max} (previous levels)")
    if last_price is not None and prior_open:
        try:
            if float(last_price) < float(prior_open):
                lines.append(f"- Price is below the previous session open ({_fmt_fixed(prior_open, price_dec)}) → possible move upward to “collect liquidity”")
            else:
                lines.append(f"- Price is above the previous session open ({_fmt_fixed(prior_open, price_dec)}) → watch for potential liquidity grab below")
        except Exception:
            pass
    lines.append("")

    # Momentum section
    # Determine bias from percentage when numeric
    try:
        pct_val = float(change_pct) if change_pct is not None else None
    except Exception:
        pct_val = None
    bias = "mixed"
    if pct_val is not None:
        bias = "bearish" if pct_val < 0 else ("bullish" if pct_val > 0 else "neutral")
    lines.append("Momentum:")
    lines.append(f"- Slight {bias} bias (price {pct_signed}%)")
    # Qualitative EMA notes
    try:
        e20 = float(features.get('ema20_dist')) if features.get('ema20_dist') is not None else None
        e50 = float(features.get('ema50_dist')) if features.get('ema50_dist') is not None else None
        s20 = float(features.get('ema20_slope')) if features.get('ema20_slope') is not None else None
        s50 = float(features.get('ema50_slope')) if features.get('ema50_slope') is not None else None
        near_thr = 0.5 * (10 ** (-price_dec))  # small threshold
        slope_desc = lambda s: ("down" if s < -near_thr else ("up" if s > near_thr else "flat")) if s is not None else "flat"
        if e20 is not None:
            lines.append(f"- EMA20: {'below' if e20 < 0 else 'above'} price (Δ {ema20}, slope {slope_desc(s20)})")
        if e50 is not None:
            side = 'near flat around price' if abs(e50) < near_thr else ('below' if e50 < 0 else 'above') + ' price'
            lines.append(f"- EMA50: {side} (Δ {ema50}, slope {slope_desc(s50)})")
        if atr14 != 'NA':
            lines.append(f"- ATR14: {atr14}")
        if adr5 != 'NA':
            lines.append(f"- ADR5: {adr5}")
    except Exception:
        pass
    lines.append("")

    # What to watch next
    lines.append("What to watch next:")
    if swing_l != 'NA':
        lines.append(f"- Bearish scenario: break below {swing_l} → possible further downside")
    if swing_h != 'NA':
        lines.append(f"- Bullish scenario: reclaim above {swing_h} → possible upward reversal")
    if fvgs:
        lines.append(f"- Watch price reaction at FVGs — these are the key entry areas")

    # Optional GPT view at the end
    if gpt_text:
        safe_gpt = gpt_text.replace('**', '*')
        lines.append("")
        lines.append("GPT view:")
        lines.append(safe_gpt)

    return "\n".join(lines)


def run_pair_analysis(base_currency: str, quote_currency: str, openai_api_key: Optional[str], tz: str, user_id: Optional[int] = None) -> Optional[str]:
    symbol = _get_symbol_from_currencies(base_currency, quote_currency)
    # Rate limit: per user+symbol cooldown
    try:
        import time as _t
        cooldown_sec = float(os.getenv("OPENAI_RATE_LIMIT_SECONDS", "15"))
        if user_id is not None:
            key = f"{user_id}:{symbol}"
            last = _LAST_GPT_CALLS.get(key, 0.0)
            now = _t.time()
            if now - last < cooldown_sec:
                logger.info(f"GPT rate-limited for {key}; skipping external call")
                openai_api_key = None  # force local-only output
            else:
                _LAST_GPT_CALLS[key] = now
    except Exception:
        pass
    features = compute_local_features(symbol, tz)
    if not features:
        return None
    summary = format_features_for_gpt(features)
    # Runtime toggle
    if os.getenv("OPENAI_ENABLED", "true").strip().lower() not in ("1", "true", "yes", "on"):
        openai_api_key = None
    gpt_text = call_openai_gpt(summary, openai_api_key)
    return build_user_output(features, gpt_text)


def run_pair_analysis_with_features(base_currency: str, quote_currency: str, openai_api_key: Optional[str], tz: str, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Compute features and GPT text for a pair and return both for charting.

    Returns dict with keys: text (str), features (dict), symbol (str).
    """
    symbol = _get_symbol_from_currencies(base_currency, quote_currency)
    # Rate limit handling mirrors run_pair_analysis
    try:
        import time as _t
        cooldown_sec = float(os.getenv("OPENAI_RATE_LIMIT_SECONDS", "15"))
        if user_id is not None:
            key = f"{user_id}:{symbol}"
            last = _LAST_GPT_CALLS.get(key, 0.0)
            now = _t.time()
            if now - last < cooldown_sec:
                logger.info(f"GPT rate-limited for {key}; skipping external call")
                openai_api_key = None
            else:
                _LAST_GPT_CALLS[key] = now
    except Exception:
        pass
    features = compute_local_features(symbol, tz)
    if not features:
        return None
    summary = format_features_for_gpt(features)
    if os.getenv("OPENAI_ENABLED", "true").strip().lower() not in ("1", "true", "yes", "on"):
        openai_api_key = None
    gpt_text = call_openai_gpt(summary, openai_api_key)
    text = build_user_output(features, gpt_text)
    return {"text": text, "features": features, "symbol": symbol}

