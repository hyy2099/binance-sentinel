#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BinanceSentinel - Daily Intelligence Briefing Generator
Generates comprehensive market + chain intelligence reports
"""

import os
import sys
import io
import json
import argparse
import urllib.request
from datetime import datetime, timezone, timedelta

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

BSC_RPC = "https://bsc-rpc.publicnode.com"


def _make_opener():
    # Use direct connection; TUN-mode VPN routes traffic at OS level
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))

_opener = _make_opener()


def rpc_call(method: str, params: list) -> dict:
    payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    req = urllib.request.Request(
        BSC_RPC, data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "BinanceSentinel/1.0"}
    )
    try:
        with _opener.open(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


def fetch_url(url: str) -> dict | list:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BinanceSentinel/1.0"})
        with _opener.open(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


def fetch_binance(path: str) -> dict | list:
    for base in ["https://api.binance.com", "https://api1.binance.com"]:
        data = fetch_url(f"{base}{path}")
        if "error" not in data:
            return data
    return {"error": "Binance API unavailable"}


def format_change(pct: float) -> str:
    if pct >= 0:
        return f"+{pct:.2f}%"
    return f"{pct:.2f}%"


def format_large_num(n: float) -> str:
    if n >= 1_000_000_000:
        return f"${n/1_000_000_000:.2f}B"
    elif n >= 1_000_000:
        return f"${n/1_000_000:.1f}M"
    return f"${n/1_000:.1f}K"


def fg_label(score: int) -> str:
    if score <= 20:   return f"{score} 😱极度恐惧"
    elif score <= 40: return f"{score} 😨恐惧"
    elif score <= 60: return f"{score} 😐中性"
    elif score <= 80: return f"{score} 😏贪婪"
    else:             return f"{score} 🤑极度贪婪"


def get_key_coins() -> dict:
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    results = {}
    for sym in symbols:
        data = fetch_binance(f"/api/v3/ticker/24hr?symbol={sym}")
        if isinstance(data, dict) and "lastPrice" in data:
            results[sym.replace("USDT", "")] = {
                "price": float(data["lastPrice"]),
                "change": float(data["priceChangePercent"]),
                "volume": float(data["quoteVolume"]),
            }
    return results


def get_top_movers(n: int = 5) -> tuple:
    data = fetch_binance("/api/v3/ticker/24hr")
    if not isinstance(data, list):
        return [], []

    usdt_pairs = []
    for t in data:
        if not t.get("symbol", "").endswith("USDT"):
            continue
        try:
            usdt_pairs.append({
                "symbol": t["symbol"].replace("USDT", ""),
                "price": float(t["lastPrice"]),
                "change": float(t["priceChangePercent"]),
                "volume": float(t["quoteVolume"]),
            })
        except (KeyError, ValueError):
            continue

    gainers = sorted(usdt_pairs, key=lambda x: x["change"], reverse=True)[:n]
    losers = sorted(usdt_pairs, key=lambda x: x["change"])[:n]
    return gainers, losers


def get_gas_price() -> str:
    data = rpc_call("eth_gasPrice", [])
    if "result" in data:
        gwei = int(data["result"], 16) / 1e9
        return f"当前 Gas: {gwei:.1f} Gwei  (数据源: BSC RPC)"
    return "Gas数据暂时不可用"


def get_fear_greed() -> tuple:
    data = fetch_url("https://api.alternative.me/fng/?limit=3")
    if "data" in data and len(data["data"]) >= 1:
        current = int(data["data"][0]["value"])
        yesterday = int(data["data"][1]["value"]) if len(data["data"]) > 1 else current
        return current, yesterday
    return 50, 50


def generate_insights(coins: dict, gainers: list, losers: list, fg: int) -> list:
    """Generate AI-style market insights"""
    insights = []

    btc = coins.get("BTC", {})
    bnb = coins.get("BNB", {})

    if btc:
        if btc["change"] > 3:
            insights.append(f"BTC强势，市场情绪偏多，山寨币跟涨概率高")
        elif btc["change"] < -3:
            insights.append(f"BTC下跌，谨慎操作，等待企稳信号")
        else:
            insights.append(f"BTC横盘整理，关注方向选择时机")

    if gainers:
        top = gainers[0]
        insights.append(f"{top['symbol']} 今日领涨 {format_change(top['change'])}，关注相关赛道")

    if fg <= 25:
        insights.append(f"恐惧贪婪指数 {fg}，市场极度恐惧，历史上是中长期布局机会")
    elif fg >= 75:
        insights.append(f"恐惧贪婪指数 {fg}，市场过热贪婪，注意控制仓位")

    if bnb:
        insights.append(f"BNB {'上涨' if bnb['change'] > 0 else '下跌'} {abs(bnb['change']):.1f}%，"
                       f"关注BSC链上活跃度变化")

    insights.append("永远保持止损纪律，不要ALL IN单一资产")

    return insights[:5]


def print_daily_brief():
    now = datetime.now(tz=UTC8)
    print("\n" + "═" * 55)
    print(f"🛡️ 链哨每日情报简报 · BinanceSentinel Daily Brief")
    print("═" * 55)
    print(f"📅 {now.strftime('%Y年%m月%d日')} | {now.strftime('%H:%M')} UTC+8")
    print("═" * 55)

    print("\n⏳ 正在收集市场数据...\n")

    # Gather all data
    coins = get_key_coins()
    gainers, losers = get_top_movers(5)
    fg_now, fg_yesterday = get_fear_greed()
    gas = get_gas_price()

    # Market Overview
    print("📊 主流币行情")
    print("━" * 40)
    for sym, data in coins.items():
        arrow = "📈" if data["change"] >= 0 else "📉"
        print(f"  {sym:<4} ${data['price']:>10,.2f}  "
              f"{format_change(data['change']):>8}  {arrow}  "
              f"Vol: {format_large_num(data['volume'])}")

    # Fear & Greed
    fg_change = fg_now - fg_yesterday
    fg_trend = f"↑{fg_change}" if fg_change > 0 else (f"↓{abs(fg_change)}" if fg_change < 0 else "→")
    print(f"\n🧭 恐惧贪婪指数: {fg_label(fg_now)}  (昨日:{fg_yesterday} {fg_trend})")

    # Top Gainers
    if gainers:
        print(f"\n🏆 今日涨幅榜 TOP5")
        print("━" * 40)
        for i, coin in enumerate(gainers, 1):
            print(f"  {i}. {coin['symbol']:<8} ${coin['price']:>10,.4f}  "
                  f"+{coin['change']:.2f}%  Vol:{format_large_num(coin['volume'])}")

    # Top Losers
    if losers:
        print(f"\n📉 今日跌幅榜 TOP5")
        print("━" * 40)
        for i, coin in enumerate(losers, 1):
            print(f"  {i}. {coin['symbol']:<8} ${coin['price']:>10,.4f}  "
                  f"{coin['change']:.2f}%  Vol:{format_large_num(coin['volume'])}")

    # BSC Gas
    print(f"\n⛽ BSC Gas 价格")
    print(f"  {gas}")

    # AI Insights
    insights = generate_insights(coins, gainers, losers, fg_now)
    print(f"\n💡 今日操盘要点")
    print("━" * 40)
    for i, insight in enumerate(insights, 1):
        print(f"  {i}. {insight}")

    print("\n" + "━" * 55)
    print("🛡️ 链哨 · BinanceSentinel v1.0.0")
    print("   「当你睡觉时，链上的一切我都帮你盯着」")
    print("━" * 55)


def main():
    parser = argparse.ArgumentParser(description="BinanceSentinel Report Generator")
    parser.add_argument("--type", choices=["brief", "full"], default="brief")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.type == "brief":
        print_daily_brief()
    else:
        print_daily_brief()


if __name__ == "__main__":
    main()
