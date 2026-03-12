#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BinanceSentinel - Whale Tracker
Tracks large BNB Chain transactions via BSCScan API
"""

import os
import sys
import io
import json
import argparse
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BSCSCAN_API_KEY = os.environ.get("BSCSCAN_API_KEY", "YourApiKeyToken")
BSCSCAN_BASE = "https://api.bscscan.com/api"

# Known token decimals and prices (fallback if API unavailable)
KNOWN_TOKENS = {
    "BNB":  {"decimals": 18, "symbol": "BNB"},
    "BUSD": {"decimals": 18, "symbol": "BUSD"},
    "USDT": {"decimals": 18, "symbol": "USDT"},
    "USDC": {"decimals": 18, "symbol": "USDC"},
    "CAKE": {"decimals": 18, "symbol": "CAKE"},
}

# Major BSC token contracts
MAJOR_TOKENS = {
    "0x55d398326f99059ff775485246999027b3197955": "USDT",
    "0xe9e7cea3dedca5984780bafc599bd69add087d56": "BUSD",
    "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d": "USDC",
    "0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82": "CAKE",
    "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c": "WBNB",
    "0x2170ed0880ac9a755fd29b2688956bd959f933f8": "ETH",
    "0x7130d2a12b9bcbfae4f2634d864a1ee1ce3ead9c": "BTCB",
}

UTC8 = timezone(timedelta(hours=8))


def fetch_url(url: str) -> dict:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BinanceSentinel/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


def get_bnb_price() -> float:
    data = fetch_url("https://api.binance.com/api/v3/ticker/price?symbol=BNBUSDT")
    if "price" in data:
        return float(data["price"])
    return 300.0  # fallback


def get_large_transfers(threshold_usd: float = 500000) -> list:
    """Fetch recent large token transfers from BSCScan"""
    results = []

    # Get recent large BNB transfers (internal txs to major DEX/bridges)
    url = (f"{BSCSCAN_BASE}?module=account&action=txlist"
           f"&address=0x10ed43c718714eb63d5aa57b78b54704e256024e"  # PancakeSwap Router
           f"&sort=desc&offset=50&page=1"
           f"&apikey={BSCSCAN_API_KEY}")

    data = fetch_url(url)
    bnb_price = get_bnb_price()

    if data.get("status") == "1" and data.get("result"):
        for tx in data["result"][:50]:
            try:
                value_bnb = int(tx.get("value", "0")) / 1e18
                value_usd = value_bnb * bnb_price
                if value_usd >= threshold_usd:
                    ts = int(tx.get("timeStamp", "0"))
                    dt = datetime.fromtimestamp(ts, tz=UTC8)
                    results.append({
                        "time": dt.strftime("%H:%M:%S"),
                        "from": tx["from"][:6] + "..." + tx["from"][-4:],
                        "to":   tx["to"][:6] + "..." + tx["to"][-4:],
                        "token": "BNB",
                        "amount_usd": value_usd,
                        "amount_token": value_bnb,
                        "tx_hash": tx["hash"][:10] + "...",
                        "full_hash": tx["hash"],
                    })
            except (ValueError, KeyError):
                continue

    # Also fetch large USDT transfers
    url2 = (f"{BSCSCAN_BASE}?module=account&action=tokentx"
            f"&contractaddress=0x55d398326f99059ff775485246999027b3197955"
            f"&sort=desc&offset=100&page=1"
            f"&apikey={BSCSCAN_API_KEY}")

    data2 = fetch_url(url2)
    if data2.get("status") == "1" and data2.get("result"):
        for tx in data2["result"][:100]:
            try:
                decimals = int(tx.get("tokenDecimal", "18"))
                amount = int(tx.get("value", "0")) / (10 ** decimals)
                if amount >= threshold_usd:  # USDT is 1:1 USD
                    ts = int(tx.get("timeStamp", "0"))
                    dt = datetime.fromtimestamp(ts, tz=UTC8)
                    results.append({
                        "time": dt.strftime("%H:%M:%S"),
                        "from": tx["from"][:6] + "..." + tx["from"][-4:],
                        "to":   tx["to"][:6] + "..." + tx["to"][-4:],
                        "token": tx.get("tokenSymbol", "USDT"),
                        "amount_usd": amount,
                        "amount_token": amount,
                        "tx_hash": tx["hash"][:10] + "...",
                        "full_hash": tx["hash"],
                    })
            except (ValueError, KeyError):
                continue

    # Sort by amount descending
    results.sort(key=lambda x: x["amount_usd"], reverse=True)
    return results[:20]


def format_usd(amount: float) -> str:
    if amount >= 1_000_000:
        return f"${amount/1_000_000:.2f}M"
    elif amount >= 1_000:
        return f"${amount/1_000:.1f}K"
    return f"${amount:.0f}"


def print_whale_report(threshold_usd: float):
    now = datetime.now(tz=UTC8)
    print(f"\n🐋 BNB链鲸鱼追踪报告")
    print("━" * 60)
    print(f"🕐 时间: {now.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)")
    print(f"📊 监控阈值: {format_usd(threshold_usd)}")
    print("━" * 60)

    transfers = get_large_transfers(threshold_usd)

    if not transfers:
        print("⚠️  当前时段暂无满足阈值的大额转账")
        print("   (可能是API限制或暂时无活动)")
        print(f"\n💡 建议: 设置 BSCSCAN_API_KEY 环境变量以获取更完整数据")
        print("\n🛡️ 链哨 · BinanceSentinel")
        return

    print(f"\n📋 发现 {len(transfers)} 笔大额转账:\n")
    print(f"{'时间':<10} {'发送方':<16} {'接收方':<16} {'代币':<8} {'金额':<12} {'交易哈希'}")
    print("-" * 75)

    for tx in transfers:
        flag = "🔴" if tx["amount_usd"] >= 5_000_000 else "🟡" if tx["amount_usd"] >= 1_000_000 else "🟢"
        print(f"{flag} {tx['time']:<8} {tx['from']:<16} {tx['to']:<16} "
              f"{tx['token']:<8} {format_usd(tx['amount_usd']):<12} {tx['tx_hash']}")

    # AI-style analysis
    total_usd = sum(t["amount_usd"] for t in transfers)
    large_count = sum(1 for t in transfers if t["amount_usd"] >= 1_000_000)

    print("\n━" * 60)
    print("🧠 鲸鱼动向AI分析:")
    print(f"  • 大额转账总量: {format_usd(total_usd)}")
    print(f"  • 百万级交易: {large_count} 笔")

    if large_count >= 5:
        print("  • 📈 市场活跃度高，大资金频繁流动，注意跟踪趋势")
    elif large_count >= 2:
        print("  • 📊 中等活跃度，有机构级资金在操作")
    else:
        print("  • 🔍 市场相对平静，无异常大额流动")

    print(f"\n🔗 BSCScan: https://bscscan.com")
    print("🛡️ 链哨 · BinanceSentinel")


def main():
    parser = argparse.ArgumentParser(description="BinanceSentinel Whale Tracker")
    parser.add_argument("--threshold", type=float, default=500000,
                        help="Minimum USD value to track (default: 500000)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.json:
        transfers = get_large_transfers(args.threshold)
        print(json.dumps(transfers, indent=2, ensure_ascii=False))
    else:
        print_whale_report(args.threshold)


if __name__ == "__main__":
    main()
