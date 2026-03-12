# 🛡️ BinanceSentinel · 链哨
**币安链上情报守卫官 — Your Binance Ecosystem Intelligence Guardian**

> "当你睡觉时，链上的一切我都帮你盯着"

BinanceSentinel 是一个基于 OpenClaw 构建的 AI 智能体，专为币安生态系统提供实时链上情报、市场分析和安全防护。

---

## ✨ 功能亮点

| 功能 | 说明 |
|------|------|
| 🐋 **鲸鱼追踪** | 实时监控 BNB Chain 大额转账，追踪机构级资金动向 |
| 🛡️ **合约风险扫描** | 输入合约地址，10秒内获得安全评分报告 |
| 📊 **市场情绪分析** | 结合恐惧贪婪指数、价格数据的综合市场解读 |
| 📋 **每日情报简报** | 一键生成涵盖涨跌榜、Gas费、AI洞察的完整简报 |
| 👛 **钱包安全检查** | 分析钱包历史交易、代币授权风险 |
| 🔔 **Telegram价格预警** | 设定目标价，触发时自动推送通知 |

---

## 🚀 快速开始

### 方式一：作为 OpenClaw Skill 使用

将 `binance-sentinel/` 目录复制到 OpenClaw 的 skills 目录，或在 ClawHub 搜索 `binance-sentinel`：

```
/sentinel help
/sentinel whale 500000
/sentinel scan 0xContractAddress
/sentinel market BTC
/sentinel brief
/sentinel check 0xWalletAddress
```

### 方式二：作为 Claude Code Skill 使用

`~/.claude/skills/binance-sentinel.md` 已自动安装。在 Claude Code 中直接输入：

```
/binance-sentinel
```

或者自然语言触发：
- "帮我追踪今天的鲸鱼活动"
- "扫描这个合约 0x..."
- "给我BTC今日行情分析"
- "生成今天的市场简报"

### 方式三：直接运行脚本

```bash
# 安装依赖 (仅需 Python 3.8+，无第三方库依赖)
python --version

# 市场分析
python scripts/market.py --symbol BTC
python scripts/market.py  # 市场总览

# 每日简报
python scripts/report.py --type brief

# 鲸鱼追踪 (需要 BSCSCAN_API_KEY)
python scripts/whales.py --threshold 500000

# 合约扫描
python scripts/contract.py --address 0xYourContractAddress

# 钱包检查
python scripts/contract.py --wallet 0xYourWalletAddress

# Telegram推送
python scripts/telegram.py --test
python scripts/telegram.py --token BTC --target 75000
python scripts/telegram.py --briefing
```

---

## ⚙️ 环境配置

```bash
# 必须：BSCScan API Key (免费，注册于 bscscan.com)
export BSCSCAN_API_KEY="your_key_here"

# 可选：Telegram Bot 推送
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

Windows 用户：
```cmd
set BSCSCAN_API_KEY=your_key_here
```

---

## 📁 项目结构

```
binance-sentinel/
├── SKILL.md              # OpenClaw skill 入口文件
├── README.md             # 本文档
├── config.env.example    # 环境变量配置模板
└── scripts/
    ├── whales.py         # BNB Chain 鲸鱼追踪
    ├── contract.py       # 合约/钱包安全扫描
    ├── market.py         # 市场情绪分析
    ├── report.py         # 每日情报简报生成
    └── telegram.py       # Telegram 推送通知

~/.claude/skills/
└── binance-sentinel.md   # Claude Code skill 文件
```

---

## 🔐 安全声明

- **只读模式**：仅调用公开 API，不发起任何交易
- **零依赖**：只使用 Python 标准库，无需安装第三方包
- **数据不留存**：不存储或传输用户钱包信息
- **开源透明**：MIT-0 License，代码完全公开

---

## 📡 数据来源

| 数据类型 | 来源 | 是否需要Key |
|---------|------|------------|
| 市场价格/行情 | Binance Public API | ❌ 免费 |
| 恐惧贪婪指数 | Alternative.me API | ❌ 免费 |
| BNB Chain交易 | BSCScan API | ✅ 免费注册 |
| 合约安全信息 | BSCScan API | ✅ 免费注册 |

---

*🛡️ 链哨 · BinanceSentinel v1.0.0*
