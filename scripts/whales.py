#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BinanceSentinel - Whale Tracker
Tracks large BNB Chain transactions via public BSC RPC (Ankr)
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

BSC_RPC = "https://bsc-rpc.publicnode.com"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

# Token address -> (symbol, decimals, binance_pair or None for stablecoins)
TRACKED_TOKENS = {
    "0x55d398326f99059ff775485246999027b3197955": ("USDT", 18, None),
    "0xe9e7cea3dedca5984780bafc599bd69add087d56": ("BUSD", 18, None),
    "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d": ("USDC", 18, None),
    "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c": ("WBNB", 18, "BNBUSDT"),
    "0x2170ed0880ac9a755fd29b2688956bd959f933f8": ("ETH",  18, "ETHUSDT"),
    "0x7130d2a12b9bcbfae4f2634d864a1ee1ce3ead9c": ("BTCB", 18, "BTCUSDT"),
}

UTC8 = timezone(timedelta(hours=8))


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


def get_token_prices() -> dict:
    prices = {}
    for addr, (symbol, decimals, pair) in TRACKED_TOKENS.items():
        if pair is None:
            prices[addr] = 1.0
        else:
            data = fetch_url(f"https://api.binance.com/api/v3/ticker/price?symbol={pair}")
            prices[addr] = float(data["price"]) if "price" in data else 0.0
    return prices


def get_large_transfers(threshold_usd: float = 500000) -> list:
    results = []

    block_data = rpc_call("eth_blockNumber", [])
    if "result" not in block_data:
        return results
    latest_block = int(block_data["result"], 16)
    from_block = latest_block - 300  # ~15 minutes of BSC blocks

    prices = get_token_prices()

    for contract_addr, (symbol, decimals, _) in TRACKED_TOKENS.items():
        price = prices.get(contract_addr, 0.0)
        if price == 0.0:
            continue

        logs_data = rpc_call("eth_getLogs", [{
            "fromBlock": hex(from_block),
            "toBlock": "latest",
            "address": contract_addr,
            "topics": [TRANSFER_TOPIC]
        }])

        for log in logs_data.get("result", []):
            try:
                amount = int(log.get("data", "0x0"), 16) / (10 ** decimals)
                amount_usd = amount * price
                if amount_usd < threshold_usd:
                    continue

                topics = log.get("topics", [])
                from_addr = "0x" + topics[1][-40:] if len(topics) > 1 else "0x????"
                to_addr   = "0x" + topics[2][-40:] if len(topics) > 2 else "0x????"

                block_num = int(log.get("blockNumber", hex(latest_block)), 16)
                est_ts = int(datetime.now(UTC8).timestamp()) - (latest_block - block_num) * 3
                dt = datetime.fromtimestamp(est_ts, tz=UTC8)

                results.append({
                    "time": dt.strftime("%H:%M:%S"),
                    "from": from_addr[:6] + "..." + from_addr[-4:],
                    "to":   to_addr[:6] + "..." + to_addr[-4:],
                    "token": symbol,
                    "amount_usd": amount_usd,
                    "amount_token": amount,
                    "tx_hash": log.get("transactionHash", "")[:10] + "...",
                    "full_hash": log.get("transactionHash", ""),
                })
            except (ValueError, KeyError, IndexError):
                continue

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
    print(f"🔌 数据源: BSC RPC (Ankr) + Binance API")
    print("━" * 60)

    transfers = get_large_transfers(threshold_usd)

    if not transfers:
        print("⚠️  当前时段暂无满足阈值的大额转账")
        print("   (近300个区块内无符合条件的转账，约15分钟范围)")
        print("\n🛡️ 链哨 · BinanceSentinel")
        return

    print(f"\n📋 发现 {len(transfers)} 笔大额转账:\n")
    print(f"{'时间':<10} {'发送方':<16} {'接收方':<16} {'代币':<8} {'金额':<12} {'交易哈希'}")
    print("-" * 75)

    for tx in transfers:
        flag = "🔴" if tx["amount_usd"] >= 5_000_000 else "🟡" if tx["amount_usd"] >= 1_000_000 else "🟢"
        print(f"{flag} {tx['time']:<8} {tx['from']:<16} {tx['to']:<16} "
              f"{tx['token']:<8} {format_usd(tx['amount_usd']):<12} {tx['tx_hash']}")

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
