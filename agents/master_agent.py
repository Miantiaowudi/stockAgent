"""Master Agent - 负责协调各 Agent 并生成最终建议"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel

from agents.base import BaseAgent, AgentInput, AgentOutput
from agents.data_agent import DataAgent, DataAgentInput
from agents.technical_agent import TechnicalAgent, TechnicalAgentInput
from agents.fundamental_agent import FundamentalAgent, FundamentalAgentInput
from app.logging import get_logger

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
    
    def _calculate_user_profit(self, trades: List[UserTrade], current_price: float) -> Dict:
        """计算用户盈亏"""
        if not trades:
            return {"profit": 0, "profit_rate": 0}
        
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
        
        # 当前持仓
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
    
    def _generate_lessons(
        self,
        trades: List[UserTrade],
        current_price: float,
        technical_result: Dict,
        fundamental_result: Dict
    ) -> List[Lesson]:
        """生成经验教训"""
        lessons = []
        
        if not trades:
            return [Lesson(type="tip", content="暂无交易记录，无法生成经验教训")]
        
        # 1. 基于买入时机分析
        buy_trades = [t for t in trades if t.direction == "buy"]
        if buy_trades:
            first_buy = min(buy_trades, key=lambda x: x.trade_time)
            # 简化判断：如果买入后价格上涨，说明买入时机较好
            if current_price > first_buy.price:
                lessons.append(Lesson(
                    type="success",
                    content=f"✅ 买入时机把握较好，建仓价 {first_buy.price} 元，低于当前价"
                ))
            else:
                lessons.append(Lesson(
                    type="warning",
                    content=f"⚠️ 买入时机不太理想，建仓价 {first_buy.price} 元高于当前价"
                ))
        
        # 2. 基于技术分析
        trend = technical_result.get("trend", "")
        signal_score = technical_result.get("signal_score", 50)
        
        if signal_score > 60:
            lessons.append(Lesson(
                type="tip",
                content=f"📈 技术面偏多（信号得分 {signal_score}），当前趋势 {trend}"
            ))
        elif signal_score < 40:
            lessons.append(Lesson(
                type="warning",
                content=f"📉 技术面偏弱（信号得分 {signal_score}），注意回调风险"
            ))
        
        # 3. 基于基本面分析
        valuation = fundamental_result.get("valuation", "")
        score = fundamental_result.get("score", 0)
        
        if score >= 60 and valuation in ["低估", "严重低估"]:
            lessons.append(Lesson(
                type="tip",
                content=f"💰 基本面优秀（评分 {score}），估值 {valuation}，适合长线持有"
            ))
        
        # 4. 基于仓位管理
        position = trades[0] if trades else None
        if position:
            if position.direction == "buy" and position.quantity < 1000:
                lessons.append(Lesson(
                    type="tip",
                    content=f"💡 建议控制仓位，不要一次性投入过多"
                ))
        
        # 5. 综合建议
        if signal_score > 50 and score > 50:
            lessons.append(Lesson(
                type="success",
                content="✨ 技术面和基本面共振，建议继续持有"
            ))
        
        return lessons
    
    def _generate_recommendation(
        self,
        signal_score: float,
        fundamental_score: int,
        user_profit_rate: float,
        position: Optional[CurrentPosition]
    ) -> Dict[str, Any]:
        """生成交易建议"""
        # 综合评分
        total_score = (signal_score * 0.6 + fundamental_score * 0.4)
        
        # 确定信号
        if total_score >= 65 and user_profit_rate > 0:
            signal = "增持"
        elif total_score >= 50:
            signal = "持有"
        elif total_score >= 35:
            signal = "减持"
        else:
            signal = "观望"
        
        # 生成建议文本
        recommendations = []
        
        if user_profit_rate > 10:
            recommendations.append(f"当前盈利 {user_profit_rate:.1f}%，可考虑部分止盈")
        elif user_profit_rate < -5:
            recommendations.append(f"当前亏损 {abs(user_profit_rate):.1f}%，注意止损风险")
        
        if signal_score > 60:
            recommendations.append("技术面偏多，可适当加仓")
        elif signal_score < 40:
            recommendations.append("技术面偏弱，建议减仓观望")
        
        if fundamental_score > 60:
            recommendations.append("基本面良好，适合长期持有")
        
        # 默认建议
        if not recommendations:
            recommendations.append("建议保持现有仓位，等待机会")
        
        return {
            "signal": signal,
            "confidence": round(total_score, 1),
            "recommendations": recommendations
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
        
        # 2. Technical Agent - 技术分析
        self.log("Step 2: 技术分析...")
        kline_data = data_result.result.get("kline_data", [])
        tech_input = TechnicalAgentInput(
            stock_code=stock_code,
            stock_name=data_result.result.get("stock_name", ""),
            kline_data=kline_data
        )
        tech_result = await self.technical_agent.run(tech_input)
        
        # 3. Fundamental Agent - 基本面分析
        self.log("Step 3: 基本面分析...")
        fund_input = FundamentalAgentInput(
            stock_code=stock_code,
            stock_name=data_result.result.get("stock_name", "")
        )
        fund_result = await self.fundamental_agent.run(fund_input)
        
        # 4. 计算用户盈亏
        self.log("Step 4: 计算用户盈亏...")
        user_profit = self._calculate_user_profit(user_trades, current_price)
        
        # 5. 生成经验教训
        self.log("Step 5: 生成经验教训...")
        lessons = self._generate_lessons(
            user_trades,
            current_price,
            tech_result.result,
            fund_result.result
        )
        
        # 6. 生成建议
        self.log("Step 6: 生成交易建议...")
        recommendation = self._generate_recommendation(
            tech_result.result.get("signal_score", 50),
            fund_result.result.get("score", 50),
            user_profit.get("profit_rate", 0),
            current_position
        )
        
        # 7. 构建最终结果
        result = {
            "stock_code": stock_code,
            "stock_name": data_result.result.get("stock_name", ""),
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
            
            # 建议
            "recommendation": recommendation,
            
            # 经验教训
            "lessons": [l.model_dump() for l in lessons],
            
            # 元数据
            "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.log(f"综合分析完成: 信号={recommendation['signal']}, 置信度={recommendation['confidence']}")
        
        return AgentOutput(
            agent_name=self.name,
            result=result,
            confidence=0.85
        )


# 便捷函数
async def analyze_stock_comprehensive(
    stock_code: str,
    stock_name: str = "",
    user_trades: List[Dict] = None,
    current_position: Dict = None
) -> Dict[str, Any]:
    """快速进行综合分析"""
    agent = MasterAgent()
    
    # 转换交易记录
    trades = []
    if user_trades:
        for t in user_trades:
            trades.append(UserTrade(
                direction=t.get("direction", "buy"),
                price=t.get("price", 0),
                quantity=t.get("quantity", 0),
                trade_time=t.get("trade_time", "")
            ))
    
    # 转换持仓
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
