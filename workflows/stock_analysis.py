"""
Stock Analysis Workflow - 基于 LangGraph 的多 Agent 股票分析系统
"""
from typing import TypedDict, List, Optional, Any, Annotated
from pydantic import BaseModel
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage

from agents.data_agent import DataAgent, DataAgentInput
from agents.technical_agent import TechnicalAgent, TechnicalAgentInput
from agents.fundamental_agent import FundamentalAgent, FundamentalAgentInput
from app.llm import get_default_llm
from app.logging import get_logger

logger = get_logger(__name__)


# ==================== State 定义 ====================

class StockAnalysisState(TypedDict):
    """股票分析工作流状态"""
    # 输入
    stock_code: str
    stock_name: str
    user_trades: List[dict]
    current_position: Optional[dict]
    
    # 中间数据
    stock_data: Optional[dict]           # 实时行情数据
    kline_data: List[dict]               # K线数据
    technical_analysis: Optional[dict]     # 技术分析结果
    fundamental_analysis: Optional[dict]   # 基本面分析结果
    
    # LLM 分析
    llm_analysis: Optional[dict]
    
    # 输出
    final_report: Optional[dict]
    error: Optional[str]
    
    # 元数据
    steps: List[str]


# ==================== Node 定义 ====================

async def collect_stock_data_node(state: StockAnalysisState) -> StockAnalysisState:
    """收集股票数据 Node"""
    stock_code = state["stock_code"]
    stock_name = state.get("stock_name", "")
    
    logger.info(f"[Node 1] 收集股票数据: {stock_code}")
    
    try:
        agent = DataAgent()
        input_data = DataAgentInput(
            stock_code=stock_code,
            stock_name=stock_name,
            fetch_kline=True,
            kline_days=365
        )
        result = await agent.run(input_data)
        
        if result.result.get("error"):
            state["error"] = result.result.get("error")
            return state
        
        state["stock_data"] = {
            "current_price": result.result.get("current_price"),
            "price_change": result.result.get("price_change"),
            "price_change_rate": result.result.get("price_change_rate"),
            "stock_name": result.result.get("stock_name"),
        }
        state["kline_data"] = result.result.get("kline_data", [])
        state["steps"].append("✅ 数据收集完成")
        
    except Exception as e:
        logger.error(f"数据收集失败: {e}")
        state["error"] = str(e)
    
    return state


async def technical_analysis_node(state: StockAnalysisState) -> StockAnalysisState:
    """技术分析 Node"""
    stock_code = state["stock_code"]
    stock_name = state.get("stock_data", {}).get("stock_name", "")
    kline_data = state.get("kline_data", [])
    
    logger.info(f"[Node 2] 技术分析: {stock_code}")
    
    if not kline_data:
        state["error"] = "没有K线数据"
        return state
    
    try:
        agent = TechnicalAgent()
        input_data = TechnicalAgentInput(
            stock_code=stock_code,
            stock_name=stock_name,
            kline_data=kline_data
        )
        result = await agent.run(input_data)
        
        state["technical_analysis"] = result.result
        state["steps"].append("✅ 技术分析完成")
        
    except Exception as e:
        logger.error(f"技术分析失败: {e}")
        state["error"] = str(e)
    
    return state


async def fundamental_analysis_node(state: StockAnalysisState) -> StockAnalysisState:
    """基本面分析 Node"""
    stock_code = state["stock_code"]
    stock_name = state.get("stock_data", {}).get("stock_name", "")
    
    logger.info(f"[Node 3] 基本面分析: {stock_code}")
    
    try:
        agent = FundamentalAgent()
        input_data = FundamentalAgentInput(
            stock_code=stock_code,
            stock_name=stock_name
        )
        result = await agent.run(input_data)
        
        state["fundamental_analysis"] = result.result
        state["steps"].append("✅ 基本面分析完成")
        
    except Exception as e:
        logger.error(f"基本面分析失败: {e}")
        state["error"] = str(e)
    
    return state


def calculate_user_profit_node(state: StockAnalysisState) -> StockAnalysisState:
    """计算用户盈亏 Node"""
    user_trades = state.get("user_trades", [])
    current_price = state.get("stock_data", {}).get("current_price", 0)
    
    logger.info(f"[Node 4] 计算用户盈亏")
    
    if not user_trades:
        state["steps"].append("✅ 无交易记录")
        return state
    
    # 计算
    total_buy = 0
    total_sell = 0
    buy_qty = 0
    sell_qty = 0
    
    for trade in user_trades:
        direction = trade.get("direction", "")
        price = trade.get("price", 0)
        quantity = trade.get("quantity", 0)
        
        if direction == "buy":
            total_buy += price * quantity
            buy_qty += quantity
        else:
            total_sell += price * quantity
            sell_qty += quantity
    
    hold_qty = buy_qty - sell_qty
    avg_cost = total_buy / buy_qty if buy_qty > 0 else 0
    
    profit = 0
    profit_rate = 0
    if hold_qty > 0 and current_price > 0:
        profit = (current_price - avg_cost) * hold_qty
        profit_rate = (current_price - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0
    
    state["user_profit"] = {
        "total_buy": total_buy,
        "total_sell": total_sell,
        "buy_qty": buy_qty,
        "sell_qty": sell_qty,
        "hold_qty": hold_qty,
        "avg_cost": avg_cost,
        "profit": round(profit, 2),
        "profit_rate": round(profit_rate, 2)
    }
    state["steps"].append("✅ 盈亏计算完成")
    
    return state


async def llm_analysis_node(state: StockAnalysisState) -> StockAnalysisState:
    """LLM 综合分析 Node"""
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser
    
    logger.info(f"[Node 5] LLM 智能分析")
    
    try:
        llm = get_default_llm()
    except Exception as e:
        logger.warning(f"无法加载 LLM: {e}")
        state["steps"].append("⚠️ LLM 加载失败")
        return state
    
    # 构建提示词
    prompt = ChatPromptTemplate.from_template("""你是一位专业、资深的股票投资顾问。请根据用户提供的成交明细和技术面、基本面分析，生成一份专业、详细的投资分析报告。

股票信息:
- 股票名称: {stock_name}
- 股票代码: {stock_code}
- 当前价格: ¥{current_price}

用户财务情况:
{financial_summary}

用户交易明细:
{user_trades}

技术分析:
{technical_analysis}

基本面分析:
{fundamental_analysis}

请生成以下格式的分析报告（JSON格式）:
{{
    "signal": "买入/持有/减持/观望",
    "confidence": 85,
    
    // 财务盘点
    "financial_summary": {{
        "total_buy_amount": "买入总额 XX元",
        "avg_buy_price": "买入均价 XX元",
        "total_sell_amount": "卖出总额 XX元", 
        "avg_sell_price": "卖出均价 XX元",
        "current_hold_quantity": "当前持仓 XX股",
        "current_cost": "持仓成本 XX元/股",
        "profit_loss": "浮盈/浮亏 XX%"
    }},
    
    // 市场局势分析
    "market_analysis": {{
        "recent_trend": "近期走势分析",
        "support_resistance": "支撑位和压力位分析"
    }},
    
    // 操作建议
    "recommendations": [
        {{
            "type": "激进/稳健/保守",
            "action": "具体动作",
            "target": "目标价位"
        }}
    ],
    
    // 经验教训
    "lessons": [
        {{"type": "success/warning/tip", "content": "内容"}}
    ],
    
    // 总结
    "summary": "一句话总结"
}}

重要要求：
1. 必须进行详细的财务计算
2. 根据当前价格和持仓成本计算浮盈亏
3. 建议要具体，包含具体价位
4. 只返回 JSON
""")
    
    # 准备数据
    stock_data = state.get("stock_data", {})
    user_profit = state.get("user_profit", {})
    tech = state.get("technical_analysis", {})
    fund = state.get("fundamental_analysis", {})
    trades = state.get("user_trades", [])
    
    # 格式化交易记录
    trades_text = "\n".join([
        f"- {t.get('direction', 'N/A')} {t.get('quantity', 0)}股 @ ¥{t.get('price', 0)} ({t.get('trade_time', 'N/A')})"
        for t in trades
    ]) if trades else "暂无交易记录"
    
    # 财务摘要
    financial_summary = f"""
- 买入总额: ¥{user_profit.get('total_buy', 0):,.2f}
- 卖出总额: ¥{user_profit.get('total_sell', 0):,.2f}
- 当前持仓: {user_profit.get('hold_qty', 0)}股
- 持仓成本: ¥{user_profit.get('avg_cost', 0):.2f}/股
- 当前盈亏: ¥{user_profit.get('profit', 0):.2f} ({user_profit.get('profit_rate', 0):.2f}%)
""".strip()
    
    # 技术分析
    tech_text = f"""
- 趋势: {tech.get('trend', '未知')}
- 信号得分: {tech.get('signal_score', 50)}
- 技术信号: {', '.join([s.get('name', '') for s in tech.get('signals', [])])}
""".strip()
    
    # 基本面
    fund_text = f"""
- 估值: {fund.get('valuation', '未知')}
- 评分: {fund.get('score', 0)}
- 市盈率: {fund.get('pe_ratio', 'N/A')}
- 市净率: {fund.get('pb_ratio', 'N/A')}
- 股息率: {fund.get('dividend_yield', 0)}%
""".strip()
    
    try:
        chain = prompt | llm | JsonOutputParser()
        result = chain.invoke({
            "stock_name": stock_data.get("stock_name", ""),
            "stock_code": state["stock_code"],
            "current_price": stock_data.get("current_price", 0),
            "financial_summary": financial_summary,
            "user_trades": trades_text,
            "technical_analysis": tech_text,
            "fundamental_analysis": fund_text
        })
        
        state["llm_analysis"] = result
        state["steps"].append("✅ LLM 分析完成")
        
    except Exception as e:
        logger.error(f"LLM 分析失败: {e}")
        state["llm_analysis"] = None
        state["steps"].append(f"⚠️ LLM 分析失败: {e}")
    
    return state


def synthesize_report_node(state: StockAnalysisState) -> StockAnalysisState:
    """汇总报告 Node"""
    logger.info(f"[Node 6] 汇总报告")
    
    stock_data = state.get("stock_data", {})
    user_profit = state.get("user_profit", {})
    llm_analysis = state.get("llm_analysis")
    
    # 构建最终报告
    final_report = {
        "stock_code": state["stock_code"],
        "stock_name": stock_data.get("stock_name", ""),
        "current_price": stock_data.get("current_price", 0),
        "price_change": stock_data.get("price_change", 0),
        "price_change_rate": stock_data.get("price_change_rate", 0),
        
        # 用户数据
        "user_profit": user_profit,
        
        # 技术分析
        "technical_analysis": state.get("technical_analysis"),
        
        # 基本面
        "fundamental_analysis": state.get("fundamental_analysis"),
        
        # LLM 分析
        "llm_analysis": llm_analysis,
        
        # 兼容格式
        "recommendation": {
            "signal": llm_analysis.get("signal", "持有") if llm_analysis else "持有",
            "confidence": llm_analysis.get("confidence", 50) if llm_analysis else 50,
            "recommendations": llm_analysis.get("recommendations", []) if llm_analysis else []
        },
        "lessons": llm_analysis.get("lessons", []) if llm_analysis else [],
        
        # 元数据
        "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "steps": state.get("steps", [])
    }
    
    state["final_report"] = final_report
    state["steps"].append("✅ 报告生成完成")
    
    return state


# ==================== 构建 Graph ====================

def create_stock_analysis_graph():
    """创建股票分析工作流图"""
    
    # 创建图
    workflow = StateGraph(StockAnalysisState)
    
    # 添加节点
    workflow.add_node("collect_data", collect_stock_data_node)
    workflow.add_node("technical_analysis", technical_analysis_node)
    workflow.add_node("fundamental_analysis", fundamental_analysis_node)
    workflow.add_node("calculate_profit", calculate_user_profit_node)
    workflow.add_node("llm_analysis", llm_analysis_node)
    workflow.add_node("synthesize", synthesize_report_node)
    
    # 定义边
    workflow.add_edge("__start__", "collect_data")
    workflow.add_edge("collect_data", "technical_analysis")
    workflow.add_edge("collect_data", "fundamental_analysis")
    workflow.add_edge("technical_analysis", "calculate_profit")
    workflow.add_edge("fundamental_analysis", "calculate_profit")
    workflow.add_edge("calculate_profit", "llm_analysis")
    workflow.add_edge("llm_analysis", "synthesize")
    workflow.add_edge("synthesize", END)
    
    # 编译
    return workflow.compile()


# ==================== 执行入口 ====================

async def run_stock_analysis(
    stock_code: str,
    stock_name: str = "",
    user_trades: List[dict] = None,
    current_position: dict = None
) -> dict:
    """
    执行股票分析工作流
    
    Args:
        stock_code: 股票代码
        stock_name: 股票名称
        user_trades: 用户交易记录
        current_position: 当前持仓
    
    Returns:
        分析报告
    """
    # 初始化状态
    initial_state: StockAnalysisState = {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "user_trades": user_trades or [],
        "current_position": current_position,
        "stock_data": None,
        "kline_data": [],
        "technical_analysis": None,
        "fundamental_analysis": None,
        "llm_analysis": None,
        "final_report": None,
        "error": None,
        "steps": []
    }
    
    # 创建并执行图
    graph = create_stock_analysis_graph()
    
    try:
        result = await graph.ainvoke(initial_state)
        return result.get("final_report", {})
    except Exception as e:
        logger.error(f"工作流执行失败: {e}")
        return {
            "error": str(e),
            "steps": initial_state.get("steps", [])
        }
