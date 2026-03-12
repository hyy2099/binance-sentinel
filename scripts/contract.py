#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BinanceSentinel - Contract & Wallet Scanner
Scans BNB Chain contracts and wallets for security risks
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

BSC_RPC = "https://bsc-rpc.publicnode.com"
SOURCIFY_BASE = "https://sourcify.dev/server"
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



def _make_opener():
    # Use direct connection; TUN-mode VPN routes traffic at OS level
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))

_opener = _make_opener()

# Risk keyword patterns in contract source code
HIGH_RISK_PATTERNS = [
    ("blacklist", "黑名单功能 — 可将地址加入黑名单禁止交易"),
    ("setMaxTxAmount", "交易限额可被修改"),
    ("excludeFromFee", "手续费豁免功能"),
    ("_isExcludedFromFee", "选择性手续费豁免"),
    ("swapAndLiquify", "自动流动性注入（可能影响价格）"),
    ("mint(", "代币铸造功能 — 增发风险"),
    ("renounceOwnership", "所有权已放弃（通常是好事）"),
    ("transferOwnership", "所有权可转移"),
    ("pause()", "合约可暂停交易"),
    ("Ownable", "有管理员权限"),
]

MEDIUM_RISK_PATTERNS = [
    ("setFee", "手续费可被修改"),
    ("updateFee", "手续费可被修改"),
    ("setTaxFee", "税率可被修改"),
    ("setLiquidityFeePercent", "流动性费率可修改"),
    ("setSwapAndLiquifyEnabled", "可关闭流动性注入"),
]


def fetch_url(url: str) -> dict:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BinanceSentinel/1.0"})
        with _opener.open(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e), "status": "0"}


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


def get_contract_info(address: str) -> dict:
    """Check contract verification via Sourcify, fall back to bytecode check"""
    # Check Sourcify for verified source
    check_url = f"{SOURCIFY_BASE}/check-by-addresses?addresses={address}&chainIds=56"
    check = fetch_url(check_url)
    if isinstance(check, list) and check:
        entry = check[0]
        status = entry.get("status", "false")
        if status in ("perfect", "partial"):
            # Fetch actual source files
            files_url = f"{SOURCIFY_BASE}/files/any/56/{address}"
            files = fetch_url(files_url)
            source = ""
            if isinstance(files, dict) and "files" in files:
                for f in files["files"]:
                    if f.get("name", "").endswith(".sol"):
                        source += f.get("content", "")
            return {"status": "1", "result": [{"SourceCode": source,
                                                "ContractName": entry.get("name", "Verified"),
                                                "CompilerVersion": ""}]}
    # Not verified - check if contract (has bytecode)
    code = rpc_call("eth_getCode", [address, "latest"])
    bytecode = code.get("result", "0x")
    if bytecode and bytecode != "0x":
        return {"status": "1", "result": [{"SourceCode": "", "ContractName": "Unverified", "CompilerVersion": ""}]}
    return {"status": "0", "result": []}


def get_token_info(address: str) -> dict:
    """Fetch token metadata via ERC-20 eth_call"""
    def call(sig_hex):
        r = rpc_call("eth_call", [{"to": address, "data": sig_hex}, "latest"])
        return r.get("result", "0x")

    def decode_string(hex_val):
        try:
            raw = bytes.fromhex(hex_val[2:])
            # ABI string: offset(32) + length(32) + data
            if len(raw) >= 64:
                length = int.from_bytes(raw[32:64], "big")
                return raw[64:64+length].decode("utf-8", errors="replace").strip("\x00")
        except Exception:
            pass
        return "Unknown"

    name   = decode_string(call("0x06fdde03"))  # name()
    symbol = decode_string(call("0x95d89b41"))  # symbol()
    supply_hex = call("0x18160ddd")             # totalSupply()
    try:
        total_supply = str(int(supply_hex, 16))
    except Exception:
        total_supply = "Unknown"

    return {"status": "1", "result": [{"tokenName": name, "symbol": symbol,
                                        "totalSupply": total_supply, "holdersCount": "0"}]}


def get_contract_txcount(address: str) -> int:
    """Estimate recent activity via Transfer event count in last ~6000 blocks (~5h)"""
    TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    block_data = rpc_call("eth_blockNumber", [])
    try:
        latest = int(block_data.get("result", "0x0"), 16)
    except (ValueError, TypeError):
        return 0
    from_block = latest - 6000
    logs = rpc_call("eth_getLogs", [{
        "fromBlock": hex(from_block),
        "toBlock": "latest",
        "address": address,
        "topics": [TRANSFER_TOPIC]
    }])
    return len(logs.get("result", []))


def get_creation_date(address: str) -> tuple:
    """Try Sourcify for creator info"""
    check_url = f"{SOURCIFY_BASE}/check-by-addresses?addresses={address}&chainIds=56"
    check = fetch_url(check_url)
    if isinstance(check, list) and check:
        creator = check[0].get("storageTimestamp", "")
        if creator:
            return "via Sourcify", ""
    return "Unknown", ""


def analyze_contract_source(source_code: str) -> tuple:
    """Analyze source code for risk patterns. Returns (high_risks, medium_risks)"""
    high_risks = []
    medium_risks = []

    source_lower = source_code.lower()
    for pattern, description in HIGH_RISK_PATTERNS:
        if pattern.lower() in source_lower:
            high_risks.append(description)

    for pattern, description in MEDIUM_RISK_PATTERNS:
        if pattern.lower() in source_lower:
            medium_risks.append(description)

    return high_risks, medium_risks


def calculate_risk_score(
    is_verified: bool,
    holder_count: int,
    tx_count: int,
    high_risks: list,
    medium_risks: list,
    age_days: int
) -> int:
    """Calculate risk score 0-100 (lower = safer)"""
    score = 0

    # Verification (major factor)
    if not is_verified:
        score += 40

    # Holder distribution
    if holder_count < 50:
        score += 25
    elif holder_count < 200:
        score += 15
    elif holder_count < 1000:
        score += 5

    # Transaction activity (based on recent Transfer events ~5h)
    if tx_count < 10:
        score += 15
    elif tx_count < 100:
        score += 5

    # Age
    if age_days < 3:
        score += 15
    elif age_days < 7:
        score += 8
    elif age_days < 30:
        score += 3

    # Risk patterns
    score += len(high_risks) * 3
    score += len(medium_risks) * 1

    return min(score, 100)


def risk_bar(score: int, width: int = 20) -> str:
    filled = int(score / 100 * width)
    if score >= 70:
        bar = "█" * filled + "░" * (width - filled)
        color = "🔴"
    elif score >= 40:
        bar = "█" * filled + "░" * (width - filled)
        color = "🟡"
    else:
        bar = "█" * filled + "░" * (width - filled)
        color = "🟢"
    return f"{color} [{bar}] {score}/100"


def scan_contract(address: str):
    now = datetime.now(tz=UTC8)
    print(f"\n🔍 合约风险扫描报告")
    print("━" * 55)
    print(f"🕐 扫描时间: {now.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)")
    print(f"📍 合约地址: {address[:6]}...{address[-4:]}")
    print(f"🔗 BSCScan: https://bscscan.com/address/{address}")
    print("━" * 55)

    print("⏳ 正在获取合约数据...\n")

    # Fetch all data
    contract_data = get_contract_info(address)
    token_data = get_token_info(address)
    creator, creation_tx = get_creation_date(address)
    tx_count = get_contract_txcount(address)

    # Parse contract info
    is_verified = False
    source_code = ""
    contract_name = "Unknown"
    compiler_version = "Unknown"

    if contract_data.get("status") == "1" and contract_data.get("result"):
        result = contract_data["result"][0]
        source_code = result.get("SourceCode", "")
        is_verified = bool(source_code and source_code != "")
        contract_name = result.get("ContractName", "Unknown")
        compiler_version = result.get("CompilerVersion", "Unknown")

    # Parse token info
    token_name = "Unknown"
    token_symbol = "Unknown"
    holder_count = 0
    total_supply = "Unknown"

    if token_data.get("status") == "1" and token_data.get("result"):
        t = token_data["result"]
        if isinstance(t, list):
            t = t[0]
        token_name = t.get("tokenName", "Unknown")
        token_symbol = t.get("symbol", "Unknown")
        total_supply = t.get("totalSupply", "Unknown")
        try:
            holder_count = int(t.get("holdersCount", "0"))
        except (ValueError, TypeError):
            holder_count = 0

    # Analyze source code
    high_risks, medium_risks = [], []
    if is_verified and source_code:
        high_risks, medium_risks = analyze_contract_source(source_code)

    # Calculate age (approximate)
    age_days = 30  # Default assumption if we can't get real age

    # Calculate risk score
    risk_score = calculate_risk_score(
        is_verified, holder_count, tx_count, high_risks, medium_risks, age_days
    )

    # Determine risk level
    if risk_score >= 70:
        risk_level = "🔴 高风险 HIGH RISK"
        risk_advice = "强烈建议谨慎操作，存在重大安全隐患"
    elif risk_score >= 40:
        risk_level = "🟡 中等风险 MEDIUM RISK"
        risk_advice = "建议深入研究后谨慎参与"
    else:
        risk_level = "🟢 低风险 LOW RISK"
        risk_advice = "相对安全，但仍需自行做好尽职调查"

    # Print report
    print(f"📋 基本信息")
    print(f"  代币名称:   {token_name} ({token_symbol})")
    print(f"  合约名称:   {contract_name}")
    print(f"  编译器版本: {compiler_version}")
    print(f"  持币地址数: {holder_count:,}" if holder_count else f"  持币地址数: 暂无数据")
    print(f"  近5小时Transfer: {tx_count:,} 笔")
    print(f"  创建者:     {creator[:10]}..." if len(creator) > 10 else f"  创建者:     {creator}")

    print(f"\n🔐 安全检查")
    print(f"  合约验证:   {'✅ 已验证' if is_verified else '❌ 未验证 (高风险)'}")

    if high_risks:
        print(f"\n⚠️  高风险特征 ({len(high_risks)}项):")
        for risk in high_risks:
            print(f"  🔴 {risk}")

    if medium_risks:
        print(f"\n⚡ 中等风险特征 ({len(medium_risks)}项):")
        for risk in medium_risks:
            print(f"  🟡 {risk}")

    if not high_risks and not medium_risks and is_verified:
        print(f"  ✅ 未发现明显风险特征")

    print(f"\n📊 风险评分")
    print(f"  {risk_bar(risk_score)}")
    print(f"  风险等级: {risk_level}")

    print(f"\n💡 安全建议")
    print(f"  {risk_advice}")
    print(f"  • 始终在小额测试后再投入大资金")
    print(f"  • 检查项目方社交媒体真实性")
    print(f"  • 查看锁仓/流动性锁定情况")
    print(f"  • 在 https://tokensniffer.com 做进一步检测")

    print("\n━" * 55)
    print("🛡️ 链哨 · BinanceSentinel — Read-Only Security Analysis")


def check_wallet(address: str):
    now = datetime.now(tz=UTC8)
    print(f"\n🔍 钱包安全检查报告")
    print("━" * 55)
    print(f"🕐 检查时间: {now.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)")
    print(f"👛 钱包地址: {address[:6]}...{address[-4:]}")
    print(f"🔗 BSCScan: https://bscscan.com/address/{address}")
    print("━" * 55)

    # Get BNB balance via RPC
    balance_data = rpc_call("eth_getBalance", [address, "latest"])
    bnb_balance = 0.0
    try:
        bnb_balance = int(balance_data.get("result", "0x0"), 16) / 1e18
    except (ValueError, TypeError):
        pass

    # No tx list available via free RPC without indexer; leave empty
    tx_data = {"status": "0"}
    token_data = {"status": "0"}

    # Get BNB price for USD conversion
    bnb_price_data = fetch_url("https://api.binance.com/api/v3/ticker/price?symbol=BNBUSDT")
    bnb_price = float(bnb_price_data.get("price", 300))

    print(f"\n💰 资产概览")
    print(f"  BNB余额: {bnb_balance:.4f} BNB (≈ ${bnb_balance * bnb_price:,.2f} USD)")

    # Recent transactions summary
    if tx_data.get("status") == "1" and tx_data.get("result"):
        txs = tx_data["result"]
        print(f"\n📊 最近交易记录 (最新{min(5, len(txs))}笔):")
        for tx in txs[:5]:
            ts = int(tx.get("timeStamp", "0"))
            dt = datetime.fromtimestamp(ts, tz=UTC8).strftime("%m-%d %H:%M")
            direction = "📤 OUT" if tx["from"].lower() == address.lower() else "📥 IN"
            value = int(tx.get("value", "0")) / 1e18
            status = "✅" if tx.get("txreceipt_status") == "1" else "❌"
            print(f"  {status} {dt} {direction} {value:.4f} BNB | {tx['hash'][:10]}...")

    # Token holdings
    if token_data.get("status") == "1" and token_data.get("result"):
        tokens_seen = {}
        for tx in token_data["result"]:
            symbol = tx.get("tokenSymbol", "?")
            if symbol not in tokens_seen:
                tokens_seen[symbol] = tx.get("contractAddress", "")

        if tokens_seen:
            print(f"\n🪙 近期交互代币 ({len(tokens_seen)}种):")
            for symbol, addr in list(tokens_seen.items())[:10]:
                print(f"  • {symbol}: {addr[:6]}...{addr[-4:]}")

    print(f"\n🔐 安全提醒")
    print(f"  ✅ 该工具仅读取公开链上数据，不会访问私钥")
    print(f"  ⚠️  定期检查并撤销不必要的代币授权")
    print(f"  🔗 撤销授权工具: https://revoke.cash")
    print(f"  🔗 更多授权检查: https://bscscan.com/tokenapprovalchecker")

    print("\n━" * 55)
    print("🛡️ 链哨 · BinanceSentinel — Read-Only Wallet Analysis")


def main():
    parser = argparse.ArgumentParser(description="BinanceSentinel Contract & Wallet Scanner")
    parser.add_argument("--address", type=str, help="Contract or wallet address to scan")
    parser.add_argument("--wallet", type=str, help="Wallet address to check")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.wallet:
        check_wallet(args.wallet)
    elif args.address:
        scan_contract(args.address)
    else:
        print("Usage: contract.py --address <contract_address>")
        print("       contract.py --wallet <wallet_address>")
        sys.exit(1)


if __name__ == "__main__":
    main()
