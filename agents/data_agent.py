"""Data Agent - 负责收集股票数据"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from agents.base import BaseAgent, AgentInput, AgentOutput
from tools.stock_data import get_stock_name, get_stock_price, get_kline_data
from app.logging import get_logger

logger = get_logger(__name__)


class DataAgentInput(AgentInput):
    """Data Agent 输入"""
    fetch_kline: bool = True
    kline_days: int = 365


class StockPriceData(BaseModel):
    """股票价格数据"""
    stock_code: str
    stock_name: str
    current_price: float
    yesterday_close: float
    open_price: float
    high_price: float
    low_price: float
    volume: int
    amount: float
    price_change: float
    price_change_rate: float
    fetched_at: str


class DataAgent(BaseAgent):
    """数据收集 Agent - 获取实时价格、K线、财务数据等"""
    
    def __init__(self):
        super().__init__("DataAgent")
    
    async def run(self, input_data: DataAgentInput) -> AgentOutput:
        """执行数据收集"""
        self.log(f"开始收集股票 {input_data.stock_code} 的数据")
        
        stock_code = input_data.stock_code
        stock_name = input_data.stock_name or ""
        
        # 1. 获取股票名称
        if not stock_name:
            stock_name = get_stock_name(stock_code) or stock_code
            self.log(f"获取到股票名称: {stock_name}")
        
        # 2. 获取实时价格
        price_data = get_stock_price(stock_code)
        
        if not price_data:
            self.log(f"获取实时价格失败", "warning")
            return AgentOutput(
                agent_name=self.name,
                result={
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "error": "获取实时价格失败"
                },
                confidence=0.3
            )
        
        current_price = price_data.get("current_price", 0)
        yesterday_close = price_data.get("yesterday_close", 0)
        
        # 计算涨跌幅
        price_change = current_price - yesterday_close
        price_change_rate = (price_change / yesterday_close * 100) if yesterday_close > 0 else 0
        
        # 3. 获取K线数据
        kline_data = []
        if input_data.fetch_kline:
            kline_days = input_data.kline_days
            kline_data = get_kline_data(stock_code, kline_days)
            self.log(f"获取到 {len(kline_data)} 条K线数据")
        
        # 构建结果
        result = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "current_price": current_price,
            "yesterday_close": yesterday_close,
            "open_price": price_data.get("open_price", 0),
            "high_price": price_data.get("high_price", 0),
            "low_price": price_data.get("low_price", 0),
            "volume": price_data.get("volume", 0),
            "amount": price_data.get("amount", 0),
            "kline_data": kline_data,
            "price_change": round(price_change, 2),
            "price_change_rate": round(price_change_rate, 2),
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.log(f"数据收集完成: {stock_name} 当前价 {current_price}")
        
        return AgentOutput(
            agent_name=self.name,
            result=result,
            confidence=0.85
        )


# 便捷函数
async def fetch_stock_data(
    stock_code: str,
    stock_name: str = "",
    fetch_kline: bool = True,
    kline_days: int = 365
) -> Dict[str, Any]:
    """快速获取股票数据"""
    agent = DataAgent()
    input_data = DataAgentInput(
        stock_code=stock_code,
        stock_name=stock_name,
        fetch_kline=fetch_kline,
        kline_days=kline_days
    )
    output = await agent.run(input_data)
    return output.result
