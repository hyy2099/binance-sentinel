#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BinanceSentinel - Market Sentiment Analysis
Fetches Binance market data and sentiment indicators
"""

import os
import sys
import io
import json
import argparse
import urllib.request
from datetime import datetime, timezone, timedelta

# Fix Windows console encoding for emojis and Chinese characters
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

UTC8 = timezone(timedelta(hours=8))

def _load_dotenv():
    """Auto-load .env from script dir or parent dir"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for path in [os.path.join(script_dir, '.env'),
                 os.path.join(os.path.dirname(script_dir), '.env')]:
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    key, _, val = line.partition('=')
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
            break

_load_dotenv()


BINANCE_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
]


def _make_opener():
    # Use direct connection; TUN-mode VPN routes traffic at OS level
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))

_opener = _make_opener()


def fetch_url(url: str) -> dict:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BinanceSentinel/1.0"})
        with _opener.open(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


def fetch_binance(path: str) -> dict | list:
    """Try multiple Binance API endpoints"""
    for base in BINANCE_BASES:
        data = fetch_url(f"{base}{path}")
        if "error" not in data:
            return data
    return {"error": "All Binance endpoints failed"}


def get_ticker_24h(symbol: str) -> dict:
    data = fetch_binance(f"/api/v3/ticker/24hr?symbol={symbol.upper()}USDT")
    if isinstance(data, dict) and "error" not in data:
        return data
    # Try without USDT suffix
    data2 = fetch_binance(f"/api/v3/ticker/24hr?symbol={symbol.upper()}")
    return data2


def get_all_tickers() -> list:
    data = fetch_binance("/api/v3/ticker/24hr")
    if isinstance(data, list):
        # Filter to USDT pairs only
        return [t for t in data if t.get("symbol", "").endswith("USDT")]
    return []


def get_fear_greed() -> dict:
    data = fetch_url("https://api.alternative.me/fng/?limit=3")
    if "data" in data:
        return data["data"][0]
    return {"value": "N/A", "value_classification": "Unknown"}


def get_klines(symbol: str, interval: str = "4h", limit: int = 10) -> list:
    data = fetch_binance(f"/api/v3/klines?symbol={symbol.upper()}USDT&interval={interval}&limit={limit}")
    if isinstance(data, list):
        return data
    return []


def format_change(pct: float) -> str:
    if pct >= 0:
        return f"+{pct:.2f}% 📈"
    return f"{pct:.2f}% 📉"


def format_large_num(n: float) -> str:
    if n >= 1_000_000_000:
        return f"${n/1_000_000_000:.2f}B"
    elif n >= 1_000_000:
        return f"${n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"${n/1_000:.1f}K"
    return f"${n:.2f}"


def fg_emoji(score: int) -> str:
    if score <= 20:   return "😱 极度恐惧"
    elif score <= 40: return "😨 恐惧"
    elif score <= 60: return "😐 中性"
    elif score <= 80: return "😏 贪婪"
    else:             return "🤑 极度贪婪"


def analyze_symbol(symbol: str):
    now = datetime.now(tz=UTC8)
    sym = symbol.upper()
    print(f"\n📊 {sym} 市场情绪分析报告")
    print("━" * 50)
    print(f"🕐 时间: {now.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)")
    print("━" * 50)

    ticker = get_ticker_24h(sym)
    fg = get_fear_greed()

    if "error" in ticker:
        print(f"⚠️  获取 {sym} 数据失败: {ticker['error']}")
        print("  请检查交易对是否存在 (如 BTC, ETH, BNB, CAKE)")
        return

    try:
        price = float(ticker["lastPrice"])
        change_pct = float(ticker["priceChangePercent"])
        high_24h = float(ticker["highPrice"])
        low_24h = float(ticker["lowPrice"])
        volume = float(ticker["quoteVolume"])  # in USDT
        count = int(ticker.get("count") or 0)

        fg_value = int(fg.get("value", 50))

        print(f"\n💰 {sym}/USDT")
        print(f"  现价:          ${price:,.4f}" if price < 1 else f"  现价:          ${price:,.2f}")
        print(f"  24h涨跌幅:     {format_change(change_pct)}")
        print(f"  24h成交额:     {format_large_num(volume)}")
        print(f"  24h成交笔数:   {count:,}")
        print(f"  24h最高/最低:  ${high_24h:,.2f} / ${low_24h:,.2f}")

        # Calculate range position
        if high_24h > low_24h:
            range_pos = (price - low_24h) / (high_24h - low_24h) * 100
            print(f"  价格位置:      在日区间 {range_pos:.0f}% 位置")

    except (KeyError, ValueError, TypeError) as e:
        print(f"⚠️  数据解析错误: {e}")
        return

    # Fear & Greed
    print(f"\n🧭 市场情绪指标")
    print(f"  恐惧贪婪指数:  {fg_value} — {fg_emoji(fg_value)}")

    # Price interpretation
    print(f"\n🧠 AI 情绪解读")

    if change_pct >= 5:
        print(f"  📈 {sym} 今日强势上涨，市场情绪偏多，注意追高风险")
    elif change_pct >= 2:
        print(f"  📈 {sym} 温和上涨，买方力量占优")
    elif change_pct <= -5:
        print(f"  📉 {sym} 今日大幅下跌，市场情绪偏空，可能是低吸机会")
    elif change_pct <= -2:
        print(f"  📉 {sym} 小幅回调，观察支撑是否有效")
    else:
        print(f"  📊 {sym} 价格横盘整理，方向待明朗")

    if fg_value <= 25:
        print(f"  😱 极度恐惧区间，历史上往往是中长期买入时机")
    elif fg_value >= 75:
        print(f"  🤑 极度贪婪区间，市场过热，注意回调风险")

    if volume > 1_000_000_000:
        print(f"  💧 24h成交额超10亿，流动性充裕")

    print(f"\n🛡️ 链哨 · BinanceSentinel")


def show_top_movers():
    now = datetime.now(tz=UTC8)
    print(f"\n📊 币安市场总览")
    print("━" * 60)
    print(f"🕐 时间: {now.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)")

    tickers = get_all_tickers()
    if not tickers:
        print("⚠️  获取市场数据失败")
        return

    # Filter valid data and sort
    valid = []
    for t in tickers:
        try:
            valid.append({
                "symbol": t["symbol"].replace("USDT", ""),
                "price": float(t["lastPrice"]),
                "change": float(t["priceChangePercent"]),
                "volume": float(t["quoteVolume"]),
            })
        except (KeyError, ValueError):
            continue

    # Sort by volume for market overview
    by_volume = sorted(valid, key=lambda x: x["volume"], reverse=True)[:5]
    gainers = sorted(valid, key=lambda x: x["change"], reverse=True)[:5]
    losers = sorted(valid, key=lambda x: x["change"])[:5]

    # Key coins
    key_symbols = ["BTC", "ETH", "BNB"]
    print(f"\n💎 主流币行情:")
    for coin in by_volume:
        if coin["symbol"] in key_symbols:
            print(f"  {coin['symbol']:<6} ${coin['price']:>12,.2f}  {format_change(coin['change'])}")

    print(f"\n🏆 24h涨幅榜 TOP5:")
    for coin in gainers:
        print(f"  {coin['symbol']:<8} ${coin['price']:>10,.4f}  {format_change(coin['change'])}"
              f"  Vol: {format_large_num(coin['volume'])}")

    print(f"\n📉 24h跌幅榜 TOP5:")
    for coin in losers:
        print(f"  {coin['symbol']:<8} ${coin['price']:>10,.4f}  {format_change(coin['change'])}"
              f"  Vol: {format_large_num(coin['volume'])}")

    # Fear & Greed
    fg = get_fear_greed()
    fg_value = int(fg.get("value", 50))
    print(f"\n🧭 恐惧贪婪指数: {fg_value} — {fg_emoji(fg_value)}")

    # Total market stats
    total_volume = sum(t["volume"] for t in valid)
    positive_count = sum(1 for t in valid if t["change"] > 0)
    print(f"\n📈 市场统计:")
    print(f"  总成交额: {format_large_num(total_volume)}")
    print(f"  上涨品种: {positive_count}/{len(valid)} ({positive_count/len(valid)*100:.0f}%)")

    print(f"\n🛡️ 链哨 · BinanceSentinel")


def main():
    parser = argparse.ArgumentParser(description="BinanceSentinel Market Analysis")
    parser.add_argument("--symbol", type=str, default="", help="Token symbol (e.g. BTC, ETH, BNB)")
    parser.add_argument("--overview", action="store_true", help="Show market overview")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.json:
        tickers = get_all_tickers()
        print(json.dumps(tickers[:20], indent=2))
    elif args.symbol:
        analyze_symbol(args.symbol)
    else:
        show_top_movers()


if __name__ == "__main__":
    main()
