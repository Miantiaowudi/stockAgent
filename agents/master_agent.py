"""Master Agent - 负责协调各 Agent 并生成最终建议"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel

from agents.base import BaseAgent, AgentInput, AgentOutput
from agents.data_agent import DataAgent, DataAgentInput
from agents.technical_agent import TechnicalAgent, TechnicalAgentInput
from agents.fundamental_agent import FundamentalAgent, FundamentalAgentInput
from app.logging import get_logger
from app.llm import get_default_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

logger = get_logger(__name__)


class UserTrade(BaseModel):
    """用户交易记录"""
    direction: str  # buy/sell
    price: float
    quantity: int
    trade_time: str


class CurrentPosition(BaseModel):
    """当前持仓"""
    hold_quantity: int
    avg_cost: float
    current_price: Optional[float] = None


class MasterAgentInput(AgentInput):
    """Master Agent 输入"""
    user_trades: List[UserTrade] = []
    current_position: Optional[CurrentPosition] = None
    fetch_kline: bool = True


class Lesson(BaseModel):
    """经验教训"""
    type: str  # success/warning/tip
    content: str


class MasterAgent(BaseAgent):
    """Master Agent - 协调各子 Agent 并生成最终分析和建议"""
    
    def __init__(self):
        super().__init__("MasterAgent")
        self.data_agent = DataAgent()
        self.technical_agent = TechnicalAgent()
        self.fundamental_agent = FundamentalAgent()
        self.llm = None  # Lazy load
    
    def _get_llm(self):
        """获取 LLM 实例（延迟加载）"""
        if self.llm is None:
            try:
                self.llm = get_default_llm()
            except Exception as e:
                logger.warning(f"无法加载 LLM: {e}")
                return None
        return self.llm
    
    def _generate_llm_analysis(
        self,
        stock_name: str,
        stock_code: str,
        current_price: float,
        user_trades: List[Dict],
        technical_result: Dict,
        fundamental_result: Dict
    ) -> Dict[str, Any]:
        """使用 LLM 生成智能分析"""
        llm = self._get_llm()
        if not llm:
            return None
        
        # 构建提示词
        prompt = ChatPromptTemplate.from_template("""你是一个专业的股票投资顾问。请根据以下信息生成投资分析和建议。

股票信息:
- 股票名称: {stock_name}
- 股票代码: {stock_code}
- 当前价格: ¥{current_price}

用户交易记录:
{user_trades}

技术分析:
{technical_analysis}

基本面分析:
{fundamental_analysis}

请生成以下格式的分析结果（JSON格式）:
{{
    "signal": "买入/持有/减持/观望",
    "confidence": 75,
    "lessons": [
        {{"type": "success/warning/tip", "content": "具体内容"}}
    ],
    "recommendations": ["具体建议1", "具体建议2"],
    "summary": "综合分析总结"
}}

注意：
1. lessons 中的 type 只能是 success, warning, 或 tip
2. signal 只能是 买入, 持有, 减持, 观望 之一
3. confidence 是 0-100 的整数
4. 只返回 JSON，不要其他内容
""")
        
        # 格式化交易记录
        trades_text = "\n".join([
            f"- {t.get('direction', 'N/A')} {t.get('quantity', 0)}股 @ ¥{t.get('price', 0)} ({t.get('trade_time', 'N/A')})"
            for t in user_trades
        ]) if user_trades else "暂无交易记录"
        
        # 格式化技术分析
        tech = technical_result or {}
        tech_text = f"""
- 趋势: {tech.get('trend', '未知')}
- 信号得分: {tech.get('signal_score', 50)}
- 技术信号: {tech.get('signals', [])}
""".strip()
        
        # 格式化基本面
        fund = fundamental_result or {}
        fund_text = f"""
- 估值: {fund.get('valuation', '未知')}
- 评分: {fund.get('score', 0)}
- 市盈率: {fund.get('pe_ratio', 0)}
- 市净率: {fund.get('pb_ratio', 0)}
- 股息率: {fund.get('dividend_yield', 0)}%
- 建议: {fund.get('recommendation', '未知')}
""".strip()
        
        try:
            # 调用 LLM
            chain = prompt | llm | JsonOutputParser()
            result = chain.invoke({
                "stock_name": stock_name,
                "stock_code": stock_code,
                "current_price": current_price,
                "user_trades": trades_text,
                "technical_analysis": tech_text,
                "fundamental_analysis": fund_text
            })
            
            logger.info(f"LLM 分析结果: {result}")
            return result
            
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return None
    
    def _calculate_user_profit(self, trades: List[UserTrade], current_price: float) -> Dict:
        """计算用户盈亏"""
        if not trades:
            return {"profit": 0, "profit_rate": 0, "hold_quantity": 0, "avg_cost": 0}
        
        total_buy = 0
        total_sell = 0
        total_buy_qty = 0
        total_sell_qty = 0
        
        for trade in trades:
            if trade.direction == "buy":
                total_buy += trade.price * trade.quantity
                total_buy_qty += trade.quantity
            else:
                total_sell += trade.price * trade.quantity
                total_sell_qty += trade.quantity
        
        hold_qty = total_buy_qty - total_sell_qty
        avg_cost = total_buy / total_buy_qty if total_buy_qty > 0 else 0
        
        if hold_qty > 0:
            profit = (current_price - avg_cost) * hold_qty
            profit_rate = (current_price - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0
        else:
            profit = total_sell - total_buy
            profit_rate = profit / total_buy * 100 if total_buy > 0 else 0
        
        return {
            "profit": round(profit, 2),
            "profit_rate": round(profit_rate, 2),
            "hold_quantity": hold_qty,
            "avg_cost": round(avg_cost, 2)
        }
    
    async def run(self, input_data: MasterAgentInput) -> AgentOutput:
        """执行综合分析"""
        self.log(f"开始综合分析股票 {input_data.stock_code}")
        
        stock_code = input_data.stock_code
        user_trades = input_data.user_trades
        current_position = input_data.current_position
        
        # 1. Data Agent - 获取数据
        self.log("Step 1: 收集数据...")
        data_input = DataAgentInput(
            stock_code=stock_code,
            stock_name=input_data.stock_name,
            fetch_kline=input_data.fetch_kline,
            kline_days=365
        )
        data_result = await self.data_agent.run(data_input)
        
        if data_result.result.get("error"):
            return AgentOutput(
                agent_name=self.name,
                result={"error": data_result.result.get("error")},
                confidence=0.3
            )
        
        current_price = data_result.result.get("current_price", 0)
        stock_name = data_result.result.get("stock_name", "")
        
        # 2. Technical Agent - 技术分析
        self.log("Step 2: 技术分析...")
        kline_data = data_result.result.get("kline_data", [])
        tech_input = TechnicalAgentInput(
            stock_code=stock_code,
            stock_name=stock_name,
            kline_data=kline_data
        )
        tech_result = await self.technical_agent.run(tech_input)
        
        # 3. Fundamental Agent - 基本面分析
        self.log("Step 3: 基本面分析...")
        fund_input = FundamentalAgentInput(
            stock_code=stock_code,
            stock_name=stock_name
        )
        fund_result = await self.fundamental_agent.run(fund_input)
        
        # 4. 计算用户盈亏
        self.log("Step 4: 计算用户盈亏...")
        user_profit = self._calculate_user_profit(user_trades, current_price)
        
        # 5. 使用 LLM 生成智能分析
        self.log("Step 5: LLM 智能分析...")
        llm_result = None
        try:
            llm_result = self._generate_llm_analysis(
                stock_name=stock_name,
                stock_code=stock_code,
                current_price=current_price,
                user_trades=[t.model_dump() for t in user_trades],
                technical_result=tech_result.result,
                fundamental_result=fund_result.result
            )
        except Exception as e:
            self.log(f"LLM 分析失败: {e}", "warning")
        
        # 6. 如果 LLM 失败，使用规则生成建议
        if not llm_result:
            llm_result = self._generate_rule_based_analysis(
                tech_result.result,
                fund_result.result,
                user_profit
            )
        
        # 7. 构建最终结果
        result = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "current_price": current_price,
            "price_change": data_result.result.get("price_change"),
            "price_change_rate": data_result.result.get("price_change_rate"),
            
            # 用户数据
            "user_trades": [t.model_dump() for t in user_trades],
            "user_profit": user_profit,
            
            # 技术分析
            "technical_analysis": {
                "trend": tech_result.result.get("trend"),
                "signal_score": tech_result.result.get("signal_score"),
                "signals": tech_result.result.get("signals", []),
                "indicators": tech_result.result.get("indicators"),
            },
            
            # 基本面分析
            "fundamental_analysis": fund_result.result,
            
            # LLM 分析结果
            "llm_analysis": llm_result,
            
            # 兼容旧格式
            "recommendation": {
                "signal": llm_result.get("signal", "持有") if llm_result else "持有",
                "confidence": llm_result.get("confidence", 50) if llm_result else 50,
                "recommendations": llm_result.get("recommendations", []) if llm_result else []
            },
            
            "lessons": llm_result.get("lessons", []) if llm_result else [],
            
            # 元数据
            "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.log(f"综合分析完成: 信号={llm_result.get('signal', '持有') if llm_result else '持有'}")
        
        return AgentOutput(
            agent_name=self.name,
            result=result,
            confidence=0.85
        )
    
    def _generate_rule_based_analysis(
        self,
        tech_result: Dict,
        fund_result: Dict,
        user_profit: Dict
    ) -> Dict:
        """基于规则生成分析（LLM 失败时的备用方案）"""
        # 计算信号得分
        tech_score = tech_result.get("signal_score", 50)
        fund_score = fund_result.get("score", 50)
        total_score = tech_score * 0.6 + fund_score * 0.4
        
        # 确定信号
        if total_score >= 65:
            signal = "买入"
        elif total_score >= 50:
            signal = "持有"
        elif total_score >= 35:
            signal = "减持"
        else:
            signal = "观望"
        
        # 生成建议
        recommendations = []
        if user_profit.get("profit_rate", 0) > 10:
            recommendations.append(f"当前盈利 {user_profit.get('profit_rate', 0):.1f}%，可考虑部分止盈")
        elif user_profit.get("profit_rate", 0) < -5:
            recommendations.append(f"当前亏损 {abs(user_profit.get('profit_rate', 0)):.1f}%，注意止损风险")
        
        if tech_score > 60:
            recommendations.append("技术面偏多，可适当加仓")
        elif tech_score < 40:
            recommendations.append("技术面偏弱，建议减仓观望")
        
        if fund_score > 60:
            recommendations.append("基本面良好，适合长期持有")
        
        if not recommendations:
            recommendations.append("建议保持现有仓位，等待机会")
        
        # 生成经验教训
        lessons = []
        if user_profit.get("profit_rate", 0) > 0:
            lessons.append({"type": "success", "content": f"✅ 当前盈利 {user_profit.get('profit_rate', 0):.1f}%，表现不错"})
        else:
            lessons.append({"type": "warning", "content": f"⚠️ 当前亏损 {abs(user_profit.get('profit_rate', 0)):.1f}%，注意风险"})
        
        lessons.append({"type": "tip", "content": f"📊 技术面得分 {tech_score}，基本面得分 {fund_score}"})
        
        return {
            "signal": signal,
            "confidence": int(total_score),
            "recommendations": recommendations,
            "lessons": lessons,
            "summary": f"综合评分 {total_score:.0f}，建议 {signal}"
        }


# 便捷函数
async def analyze_stock_comprehensive(
    stock_code: str,
    stock_name: str = "",
    user_trades: List[Dict] = None,
    current_position: Dict = None
) -> Dict[str, Any]:
    """快速进行综合分析"""
    agent = MasterAgent()
    
    trades = []
    if user_trades:
        for t in user_trades:
            trades.append(UserTrade(
                direction=t.get("direction", "buy"),
                price=t.get("price", 0),
                quantity=t.get("quantity", 0),
                trade_time=t.get("trade_time", "")
            ))
    
    position = None
    if current_position:
        position = CurrentPosition(**current_position)
    
    input_data = MasterAgentInput(
        stock_code=stock_code,
        stock_name=stock_name,
        user_trades=trades,
        current_position=position
    )
    
    output = await agent.run(input_data)
    return output.result
