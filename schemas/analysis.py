"""Analysis API Schemas - Pydantic Models"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Trade(BaseModel):
    """用户交易记录"""
    direction: str = Field(..., description="买入/卖出方向: buy/sell")
    price: float = Field(..., description="成交价格")
    quantity: int = Field(..., description="成交数量")
    trade_time: str = Field(..., description="交易时间")


class Position(BaseModel):
    """持仓信息"""
    hold_quantity: int = Field(..., description="持仓数量")
    avg_cost: float = Field(..., description="平均成本")
    current_price: Optional[float] = Field(None, description="当前价格")
    floating_pnl: Optional[float] = Field(None, description="浮动盈亏")


class AnalysisRequest(BaseModel):
    """分析请求"""
    stock_code: str = Field(..., description="股票代码")
    user_trades: List[Trade] = Field(default_factory=list, description="用户交易记录")
    current_position: Optional[Position] = Field(None, description="当前持仓")


class BatchAnalysisRequest(BaseModel):
    """批量分析请求"""
    stocks: List[str] = Field(..., description="股票代码列表")


class TechnicalAnalysis(BaseModel):
    """技术分析结果"""
    rsi: float = Field(..., description="RSI 相对强弱指数")
    macd: Dict[str, float] = Field(..., description="MACD 指标")
    bollinger_bands: Dict[str, float] = Field(..., description="布林带")
    moving_averages: Dict[str, float] = Field(..., description="均线")
    trend: str = Field(..., description="趋势判断")


class FundamentalAnalysis(BaseModel):
    """基本面分析结果"""
    pe: float = Field(..., description="市盈率")
    pb: float = Field(..., description="市净率")
    market_cap: float = Field(..., description="市值")
    dividend_yield: float = Field(..., description="股息率")
    valuation: str = Field(..., description="估值判断")
    score: int = Field(..., description="基本面评分")


class AnalysisResponse(BaseModel):
    """分析响应"""
    stock_code: str
    stock_name: str
    signal: str = Field(..., description="交易信号: buy/sell/hold")
    confidence: float = Field(..., description="置信度 0-100")
    technical_analysis: Optional[TechnicalAnalysis] = None
    fundamental_analysis: Optional[FundamentalAnalysis] = None
    lessons: List[str] = Field(default_factory=list, description="经验教训")
    recommendation: str = Field(..., description="建议")
    user_profit_rate: Optional[float] = Field(None, description="用户盈亏率")


class ReviewSummary(BaseModel):
    """复盘摘要"""
    total_trades: int
    win_rate: float
    total_profit: float
    avg_holding_days: float


class ClearedPositionReview(BaseModel):
    """清仓股票复盘"""
    stock_code: str
    stock_name: str
    buy_avg_price: float
    sell_avg_price: float
    profit_loss: float
    profit_rate: float
    holding_days: int
    lessons: List[str] = Field(default_factory=list)


class ReviewResponse(BaseModel):
    """复盘响应"""
    summary: ReviewSummary
    positions: List[ClearedPositionReview]
