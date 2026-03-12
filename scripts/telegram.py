#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BinanceSentinel - Telegram Notifier
Sends price alerts and market updates via Telegram Bot
"""

import os
import sys
import io
import json
import time
import argparse
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
UTC8 = timezone(timedelta(hours=8))


def _make_opener():
    # Use direct connection; TUN-mode VPN routes traffic at OS level
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))

_opener = _make_opener()


def fetch_url(url: str, data: bytes = None) -> dict:
    try:
        req = urllib.request.Request(url, data=data, headers={"User-Agent": "BinanceSentinel/1.0"})
        with _opener.open(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


def send_telegram(message: str, token: str = None, chat_id: str = None) -> bool:
    """Send a message via Telegram bot"""
    bot_token = token or TELEGRAM_BOT_TOKEN
    chat = chat_id or TELEGRAM_CHAT_ID

    if not bot_token or not chat:
        print("⚠️  缺少 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID 环境变量")
        print("  设置方法:")
        print("  export TELEGRAM_BOT_TOKEN='your_bot_token'")
        print("  export TELEGRAM_CHAT_ID='your_chat_id'")
        print("\n  获取Bot Token: 在Telegram联系 @BotFather")
        print("  获取Chat ID:   在Telegram联系 @userinfobot")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat,
        "text": message,
        "parse_mode": "HTML",
    }).encode()

    result = fetch_url(url, data=payload)
    if result.get("ok"):
        print(f"✅ Telegram消息发送成功")
        return True
    else:
        print(f"❌ 发送失败: {result.get('description', result.get('error', 'Unknown error'))}")
        return False


def get_price(symbol: str) -> float:
    for base in ["https://api.binance.com", "https://api1.binance.com"]:
        data = fetch_url(f"{base}/api/v3/ticker/price?symbol={symbol.upper()}USDT")
        if "price" in data:
            return float(data["price"])
    return 0.0


def monitor_price_alert(symbol: str, target: float, direction: str = "auto"):
    """Monitor price and send alert when target is hit"""
    sym = symbol.upper()
    initial_price = get_price(sym)

    if direction == "auto":
        direction = "above" if target > initial_price else "below"

    dir_zh = "突破" if direction == "above" else "跌破"
    print(f"🔔 开始监控 {sym} 价格预警")
    print(f"  当前价格: ${initial_price:,.4f}")
    print(f"  目标价格: ${target:,.4f} ({dir_zh}时发送通知)")
    print(f"  检查间隔: 每30秒")
    print(f"  按 Ctrl+C 停止监控\n")

    alert_sent = False
    check_count = 0

    while not alert_sent:
        try:
            time.sleep(30)
            current_price = get_price(sym)
            check_count += 1
            now = datetime.now(tz=UTC8).strftime("%H:%M:%S")

            print(f"  [{now}] {sym}: ${current_price:,.4f}", end="")

            triggered = (direction == "above" and current_price >= target) or \
                       (direction == "below" and current_price <= target)

            if triggered:
                print(f" ⚡ 触发!")
                msg = (
                    f"🛡️ <b>BinanceSentinel 价格预警</b>\n\n"
                    f"🪙 <b>{sym}/USDT</b>\n"
                    f"📍 当前价格: <b>${current_price:,.4f}</b>\n"
                    f"🎯 目标价格: <b>${target:,.4f}</b>\n"
                    f"📊 状态: <b>已{dir_zh}目标价!</b>\n\n"
                    f"🕐 时间: {datetime.now(tz=UTC8).strftime('%Y-%m-%d %H:%M:%S')} UTC+8\n\n"
                    f"⚠️ 本通知仅供参考，不构成投资建议\n"
                    f"<i>链哨 · BinanceSentinel</i>"
                )
                send_telegram(msg)
                alert_sent = True
            else:
                gap_pct = abs(current_price - target) / target * 100
                print(f" (距目标: {gap_pct:.2f}%)")

        except KeyboardInterrupt:
            print(f"\n⏹ 监控已停止 (共检查 {check_count} 次)")
            break


def send_briefing():
    """Send a market briefing to Telegram"""
    import subprocess
    import os

    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_script = os.path.join(script_dir, "report.py")

    try:
        result = subprocess.run(
            [sys.executable, report_script, "--type", "brief"],
            capture_output=True, text=True, timeout=30
        )
        content = result.stdout
    except Exception as e:
        content = f"报告生成失败: {e}"

    # Telegram has 4096 char limit, truncate if needed
    if len(content) > 4000:
        content = content[:3997] + "..."

    msg = f"<pre>{content}</pre>"
    send_telegram(msg)


def test_connection():
    """Test Telegram bot connection"""
    print("🔍 测试 Telegram Bot 连接...")

    if not TELEGRAM_BOT_TOKEN:
        print("❌ 未找到 TELEGRAM_BOT_TOKEN 环境变量")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
    result = fetch_url(url)

    if result.get("ok"):
        bot = result["result"]
        print(f"✅ Bot连接成功!")
        print(f"  Bot名称: {bot.get('first_name')}")
        print(f"  用户名:  @{bot.get('username')}")

        # Send test message
        test_msg = (
            "🛡️ <b>BinanceSentinel 链哨</b>\n\n"
            "✅ 连接测试成功！\n"
            "链哨已准备好为您监控币安生态。\n\n"
            "<i>「当你睡觉时，链上的一切我都帮你盯着」</i>"
        )
        return send_telegram(test_msg)
    else:
        print(f"❌ 连接失败: {result.get('description', 'Unknown error')}")
        print("  请确认 TELEGRAM_BOT_TOKEN 正确")
        return False


def main():
    parser = argparse.ArgumentParser(description="BinanceSentinel Telegram Notifier")
    parser.add_argument("--token", type=str, help="Token symbol to monitor")
    parser.add_argument("--target", type=float, help="Target price for alert")
    parser.add_argument("--direction", choices=["above", "below", "auto"], default="auto")
    parser.add_argument("--briefing", action="store_true", help="Send market briefing")
    parser.add_argument("--test", action="store_true", help="Test Telegram connection")
    parser.add_argument("--message", type=str, help="Send custom message")
    args = parser.parse_args()

    if args.test:
        test_connection()
    elif args.briefing:
        send_briefing()
    elif args.message:
        send_telegram(args.message)
    elif args.token and args.target:
        monitor_price_alert(args.token, args.target, args.direction)
    else:
        print("BinanceSentinel - Telegram Notifier")
        print("\nUsage:")
        print("  --test                          测试Bot连接")
        print("  --token BTC --target 50000      BTC价格预警")
        print("  --briefing                      发送每日简报")
        print("  --message 'Hello'               发送自定义消息")
        print("\n必须设置环境变量:")
        print("  TELEGRAM_BOT_TOKEN=your_token")
        print("  TELEGRAM_CHAT_ID=your_chat_id")


if __name__ == "__main__":
    main()
