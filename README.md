# 🛡️ BinanceSentinel · 链哨
**币安链上情报守卫官 — Your Binance Ecosystem Intelligence Guardian**

> "当你睡觉时，链上的一切我都帮你盯着"

BinanceSentinel 是一个基于 Claude Code Skill 构建的 AI 智能体，专为币安生态系统提供实时链上情报、市场分析和安全防护。**完全免费，无需任何 API Key。**

---

## ✨ 功能亮点

| 功能 | 说明 |
|------|------|
| 🐋 **鲸鱼追踪** | 实时监控 BNB Chain 大额转账，追踪 USDT/BUSD/USDC/WBNB/ETH/BTCB 六种资产的机构级资金动向 |
| 🛡️ **合约风险扫描** | 输入合约地址，获得安全评分报告（验证状态、代码风险模式、活跃度分析）|
| 📊 **市场情绪分析** | 结合恐惧贪婪指数、价格数据的综合市场解读 |
| 📋 **每日情报简报** | 一键生成涵盖涨跌榜、Gas 费、AI 洞察的完整简报 |
| 👛 **钱包安全检查** | 查询钱包 BNB 余额及链上安全提示 |
| 🔔 **Telegram 价格预警** | 设定目标价，触发时自动推送通知（需配置 Bot Token）|

---

## 🚀 快速开始

### 作为 Claude Code Skill 使用

安装后在 Claude Code 中直接输入：

```
链哨，鲸鱼追踪
```

或自然语言触发：
- `帮我追踪今天的鲸鱼活动`
- `扫描这个合约 0x...`
- `BTC 今日行情分析`
- `生成今天的市场简报`

### 直接运行脚本

```bash
# 环境要求：Python 3.8+，无需安装任何第三方库

# 鲸鱼追踪（监控 $500K 以上大额转账）
python scripts/whales.py --threshold 500000

# 合约风险扫描
python scripts/contract.py --address 0xYourContractAddress

# 钱包检查
python scripts/contract.py --wallet 0xYourWalletAddress

# 市场行情分析
python scripts/market.py --symbol BTC
python scripts/market.py  # 市场总览

# 每日情报简报
python scripts/report.py --type brief

# Telegram 推送
python scripts/telegram.py --test
python scripts/telegram.py --token BTC --target 75000
python scripts/telegram.py --briefing
```

---

## ⚙️ 环境配置

所有核心功能**无需 API Key**，开箱即用。

```bash
# 可选：Telegram Bot 推送通知
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

Windows 用户：
```cmd
set TELEGRAM_BOT_TOKEN=your_bot_token
set TELEGRAM_CHAT_ID=your_chat_id
```

> 网络说明：脚本使用直连模式，如在中国大陆使用建议开启 TUN 模式 VPN。

---

## 📁 项目结构

```
binance-sentinel/
├── README.md
├── .gitignore
└── scripts/
    ├── whales.py         # BNB Chain 鲸鱼追踪（BSC RPC + Binance API）
    ├── contract.py       # 合约/钱包安全扫描（BSC RPC + Sourcify）
    ├── market.py         # 市场情绪分析（Binance API）
    ├── report.py         # 每日情报简报（Binance API + BSC RPC）
    └── telegram.py       # Telegram 推送通知

~/.claude/skills/
└── binance-sentinel.md   # Claude Code skill 入口文件
```

---

## 📡 数据来源

| 数据类型 | 来源 | 是否需要 Key |
|---------|------|-------------|
| 市场价格 / 行情 | Binance Public API | ❌ 免费 |
| 恐惧贪婪指数 | Alternative.me API | ❌ 免费 |
| BNB Chain 链上数据 | BSC RPC (publicnode.com) | ❌ 免费 |
| 合约验证信息 | Sourcify (sourcify.dev) | ❌ 免费 |
| Gas 价格 | BSC RPC (publicnode.com) | ❌ 免费 |

---

## 🔐 安全声明

- **只读模式**：仅调用公开 API，不发起任何交易
- **零依赖**：只使用 Python 标准库，无需安装第三方包
- **数据不留存**：不存储或传输用户钱包信息
- **开源透明**：MIT-0 License，代码完全公开

---

*🛡️ 链哨 · BinanceSentinel v1.1.0*
