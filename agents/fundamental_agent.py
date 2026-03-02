"""Fundamental Agent - 负责基本面分析"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from agents.base import BaseAgent, AgentInput, AgentOutput
from app.logging import get_logger

logger = get_logger(__name__)


class FundamentalAgentInput(AgentInput):
    """Fundamental Agent 输入"""
    market_cap: Optional[float] = None  # 市值
    pe_ratio: Optional[float] = None    # 市盈率
    pb_ratio: Optional[float] = None    # 市净率
    dividend_yield: Optional[float] = None  # 股息率
    revenue: Optional[Dict] = None      # 营收数据
    profit: Optional[Dict] = None       # 利润数据


class FundamentalAgent(BaseAgent):
    """基本面分析 Agent - 分析 P/E、P/B、营收、利润等"""
    
    def __init__(self):
        super().__init__("FundamentalAgent")
    
    def _get_valuation_level(self, pe: float, pb: float) -> str:
        """判断估值水平"""
        if pe <= 0 or pb <= 0:
            return "无法评估"
        elif pe < 10 and pb < 1:
            return "严重低估"
        elif pe < 15 and pb < 1.5:
            return "低估"
        elif pe < 25 and pb < 3:
            return "合理"
        elif pe < 40 and pb < 5:
            return "偏高"
        else:
            return "高估"
    
    def _calculate_score(self, pe: float, pb: float, dividend: float, has_profit: bool) -> int:
        """计算基本面评分 (0-100)"""
        score = 50
        
        # P/E 评分 (权重 30%)
        if pe > 0:
            if pe < 10:
                score += 15
            elif pe < 15:
                score += 10
            elif pe < 25:
                score += 0
            elif pe < 40:
                score -= 10
            else:
                score -= 15
        
        # P/B 评分 (权重 20%)
        if pb > 0:
            if pb < 1:
                score += 10
            elif pb < 1.5:
                score += 5
            elif pb < 3:
                score += 0
            elif pb < 5:
                score -= 5
            else:
                score -= 10
        
        # 股息率评分 (权重 20%)
        if dividend > 0:
            if dividend > 4:
                score += 10
            elif dividend > 3:
                score += 7
            elif dividend > 2:
                score += 4
            elif dividend > 1:
                score += 0
            else:
                score -= 5
        
        # 盈利状况评分 (权重 30%)
        if has_profit:
            score += 15
        else:
            score -= 15
        
        return max(0, min(100, score))
    
    def _get_recommendation(self, score: int, valuation: str) -> str:
        """基于评分给出建议"""
        if score >= 70:
            return "强烈推荐"
        elif score >= 50:
            return "建议持有"
        elif score >= 30:
            return "中性观望"
        else:
            return "建议回避"
    
    async def run(self, input_data: FundamentalAgentInput) -> AgentOutput:
        """执行基本面分析"""
        self.log(f"开始分析股票 {input_data.stock_code} 的基本面")
        
        # 使用输入数据或模拟数据
        pe = input_data.pe_ratio or 0
        pb = input_data.pb_ratio or 0
        dividend = input_data.dividend_yield or 0
        market_cap = input_data.market_cap or 0
        
        # 判断是否有盈利
        has_profit = True  # 简化处理
        
        # 1. 估值分析
        valuation = self._get_valuation_level(pe, pb)
        
        # 2. 计算基本面评分
        score = self._calculate_score(pe, pb, dividend, has_profit)
        
        # 3. 生成建议
        recommendation = self._get_recommendation(score, valuation)
        
        # 4. 构建结果
        result = {
            "stock_code": input_data.stock_code,
            "stock_name": input_data.stock_name,
            "market_cap": market_cap,  # 亿元
            "pe_ratio": pe,
            "pb_ratio": pb,
            "dividend_yield": dividend,  # %
            "valuation": valuation,
            "score": score,
            "recommendation": recommendation,
            "analysis": {
                "pe_level": "低" if pe < 15 else "中" if pe < 30 else "高",
                "pb_level": "低" if pb < 2 else "中" if pb < 4 else "高",
                "dividend_level": "高" if dividend > 3 else "中" if dividend > 1 else "低",
            }
        }
        
        self.log(f"基本面分析完成: 估值={valuation}, 评分={score}")
        
        return AgentOutput(
            agent_name=self.name,
            result=result,
            confidence=0.75
        )


# 便捷函数
async def analyze_fundamental(
    stock_code: str,
    stock_name: str = "",
    **kwargs
) -> Dict[str, Any]:
    """快速进行基本面分析"""
    agent = FundamentalAgent()
    input_data = FundamentalAgentInput(
        stock_code=stock_code,
        stock_name=stock_name,
        pe_ratio=kwargs.get("pe"),
        pb_ratio=kwargs.get("pb"),
        dividend_yield=kwargs.get("dividend"),
        market_cap=kwargs.get("market_cap"),
    )
    output = await agent.run(input_data)
    return output.result
