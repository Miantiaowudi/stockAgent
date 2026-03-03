# StockAgent

股票交易分析 Agent - 基于 LangChain + LangGraph 的多 Agent 协作系统

## 项目简介

StockAgent 是一个智能股票交易分析系统，通过结合用户的买卖点、股票基本面、技术面等多方面因素，提供后续交易建议和经验教训。

## 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    Python FastAPI 后端                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Data Agent  │→ │ Tech Agent  │→ │ Fund Agent  │            │
│  │ 收集数据    │  │ 技术分析    │  │ 基本面分析  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│         ↓                ↓                ↓                     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              LangGraph 编排器                                ││
│  └─────────────────────────────────────────────────────────────┘│
│                           ↓                                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │        LLM (Ollama Qwen2.5:14B / OpenAI GPT-4)            ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## 技术栈

- **Agent 框架**: LangChain + LangGraph
- **Python 后端**: FastAPI
- **LLM**: Ollama Qwen2.5:14B (本地部署) / OpenAI GPT-4
- **数据获取**: 东方财富 API, yFinance

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件
```

**推荐使用 Ollama 本地部署** (无需 API Key):

```env
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:14b
OLLAMA_BASE_URL=http://localhost:11434
```

**或者使用 OpenAI**:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4
```

### 3. 运行服务

```bash
# 确保 Ollama 已启动并加载模型
# ollama run qwen2.5:14b

# 启动 FastAPI 服务
python -m uvicorn app.main:app --reload
```

### 4. 访问 API

- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## API 接口

### 分析股票

```bash
POST /api/analysis
{
  "stock_code": "600000",
  "user_trades": [
    {"direction": "buy", "price": 10.5, "quantity": 1000, "trade_time": "2024-01-15"}
  ],
  "current_position": {
    "hold_quantity": 1000,
    "avg_cost": 10.5
  }
}
```

### 批量分析

```bash
POST /api/analysis/batch
{
  "stocks": ["600000", "000001"]
}
```

### 复盘

```bash
GET /api/analysis/review?type=cleared
```

## 项目结构

```
stockAgent/
├── app/                    # 应用入口
│   ├── config.py           # 配置管理
│   ├── logging.py          # 日志配置
│   ├── llm.py              # LLM 配置
│   └── main.py             # FastAPI 应用
├── agents/                 # Agent 实现
│   ├── base.py             # 基础 Agent 类
│   ├── data_agent.py       # Data Agent
│   ├── technical_agent.py  # Technical Agent
│   ├── fundamental_agent.py # Fundamental Agent
│   └── master_agent.py     # Master Agent
├── tools/                  # 工具函数
│   ├── stock_data.py       # 股票数据获取
│   ├── indicators.py       # 技术指标计算
│   └── fundamental_data.py # 基本面数据
├── api/routes/             # API 路由
├── schemas/               # Pydantic 模型
├── requirements.txt
└── .env.example
```

## 开发计划

See [DEVELOPMENT_PLAN.md](./docs/DEVELOPMENT_PLAN.md)

## 许可证

MIT License
