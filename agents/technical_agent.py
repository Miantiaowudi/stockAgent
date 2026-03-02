"""Technical Agent - 负责技术分析"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from agents.base import BaseAgent, AgentInput, AgentOutput
from tools.indicators import calculate_all_indicators
from app.logging import get_logger

logger = get_logger(__name__)


class TechnicalAgentInput(AgentInput):
    """Technical Agent 输入"""
    kline_data: List[Dict[str, Any]] = []


class TechnicalSignals(BaseModel):
    """技术信号"""
    name: str
    value: str
    signal: str  # bullish / bearish / neutral


class TechnicalAgent(BaseAgent):
    """技术分析 Agent - 计算技术指标并生成分析报告"""
    
    def __init__(self):
        super().__init__("TechnicalAgent")
    
    def _analyze_rsi(self, rsi: float) -> TechnicalSignals:
        """分析 RSI"""
        if rsi >= 70:
            return TechnicalSignals(name="RSI", value=str(rsi), signal="bearish")
        elif rsi <= 30:
            return TechnicalSignals(name="RSI", value=str(rsi), signal="bullish")
        else:
            return TechnicalSignals(name="RSI", value=str(rsi), signal="neutral")
    
    def _analyze_macd(self, macd: Dict) -> TechnicalSignals:
        """分析 MACD"""
        macd_val = macd.get("macd", 0)
        signal_val = macd.get("signal", 0)
        histogram = macd.get("histogram", 0)
        
        if macd_val > signal_val and histogram > 0:
            return TechnicalSignals(name="MACD", value=f"M:{macd_val:.4f} S:{signal_val:.4f}", signal="bullish")
        elif macd_val < signal_val and histogram < 0:
            return TechnicalSignals(name="MACD", value=f"M:{macd_val:.4f} S:{signal_val:.4f}", signal="bearish")
        else:
            return TechnicalSignals(name="MACD", value=f"M:{macd_val:.4f} S:{signal_val:.4f}", signal="neutral")
    
    def _analyze_bollinger(self, bb: Dict, current_price: float) -> TechnicalSignals:
        """分析布林带"""
        upper = bb.get("upper", 0)
        middle = bb.get("middle", 0)
        lower = bb.get("lower", 0)
        
        if current_price >= upper:
            return TechnicalSignals(name="布林带", value=f"触顶", signal="bearish")
        elif current_price <= lower:
            return TechnicalSignals(name="布林带", value=f"触底", signal="bullish")
        elif current_price > middle:
            return TechnicalSignals(name="布林带", value=f"中上轨", signal="neutral")
        else:
            return TechnicalSignals(name="布林带", value=f"中下轨", signal="neutral")
    
    def _analyze_moving_averages(self, ma: Dict, current_price: float) -> List[TechnicalSignals]:
        """分析均线"""
        signals = []
        
        ma5 = ma.get("ma5", 0)
        ma10 = ma.get("ma10", 0)
        ma20 = ma.get("ma20", 0)
        ma60 = ma.get("ma60", 0)
        
        if ma5 and ma10:
            if ma5 > ma10:
                signals.append(TechnicalSignals(name="MA5>MA10", value=f"{ma5:.2f}>{ma10:.2f}", signal="bullish"))
            else:
                signals.append(TechnicalSignals(name="MA5<MA10", value=f"{ma5:.2f}<{ma10:.2f}", signal="bearish"))
        
        if ma20 and ma60:
            if current_price > ma20:
                signals.append(TechnicalSignals(name="价格>MA20", value=f"{current_price:.2f}>{ma20:.2f}", signal="bullish"))
            else:
                signals.append(TechnicalSignals(name="价格<MA20", value=f"{current_price:.2f}<{ma20:.2f}", signal="bearish"))
        
        # 多头排列
        if ma5 > ma10 > ma20 > ma60 and ma60:
            signals.append(TechnicalSignals(name="多头排列", value="5>10>20>60", signal="bullish"))
        elif ma5 < ma10 < ma20 < ma60 and ma60:
            signals.append(TechnicalSignals(name="空头排列", value="5<10<20<60", signal="bearish"))
        
        return signals
    
    def _generate_signals(self, indicators: Dict, current_price: float) -> List[TechnicalSignals]:
        """生成所有技术信号"""
        signals = []
        
        # RSI
        rsi = indicators.get("rsi", 50)
        signals.append(self._analyze_rsi(rsi))
        
        # MACD
        macd = indicators.get("macd", {})
        signals.append(self._analyze_macd(macd))
        
        # 布林带
        bb = indicators.get("bollinger_bands", {})
        signals.append(self._analyze_bollinger(bb, current_price))
        
        # 均线
        ma = indicators.get("moving_averages", {})
        signals.extend(self._analyze_moving_averages(ma, current_price))
        
        return signals
    
    def _calculate_signal_score(self, signals: List[TechnicalSignals]) -> float:
        """计算信号得分"""
        bullish = sum(1 for s in signals if s.signal == "bullish")
        bearish = sum(1 for s in signals if s.signal == "bearish")
        total = len(signals)
        
        if total == 0:
            return 50.0
        
        # 得分范围 0-100，50 为中性
        score = 50 + (bullish - bearish) * (50 / total)
        return max(0, min(100, score))
    
    async def run(self, input_data: TechnicalAgentInput) -> AgentOutput:
        """执行技术分析"""
        self.log(f"开始分析股票 {input_data.stock_code} 的技术指标")
        
        kline_data = input_data.kline_data
        
        if not kline_data:
            self.log("没有K线数据，返回空结果", "warning")
            return AgentOutput(
                agent_name=self.name,
                result={
                    "stock_code": input_data.stock_code,
                    "error": "没有K线数据"
                },
                confidence=0.3
            )
        
        # 1. 计算技术指标
        indicators = calculate_all_indicators(kline_data)
        
        if not indicators:
            self.log("技术指标计算失败", "error")
            return AgentOutput(
                agent_name=self.name,
                result={
                    "stock_code": input_data.stock_code,
                    "error": "技术指标计算失败"
                },
                confidence=0.3
            )
        
        # 2. 获取当前价格
        current_price = kline_data[-1]["close"] if kline_data else 0
        
        # 3. 生成技术信号
        signals = self._generate_signals(indicators, current_price)
        
        # 4. 计算信号得分
        signal_score = self._calculate_signal_score(signals)
        
        # 5. 生成趋势判断
        trend = indicators.get("trend", "unknown")
        
        # 6. 构建结果
        result = {
            "stock_code": input_data.stock_code,
            "stock_name": input_data.stock_name,
            "current_price": current_price,
            "indicators": {
                "rsi": indicators.get("rsi"),
                "macd": indicators.get("macd"),
                "bollinger_bands": indicators.get("bollinger_bands"),
                "moving_averages": indicators.get("moving_averages"),
            },
            "signals": [s.model_dump() for s in signals],
            "trend": trend,
            "signal_score": round(signal_score, 2),
            "signal": "超买" if signal_score > 70 else "超卖" if signal_score < 30 else "中性"
        }
        
        self.log(f"技术分析完成: 趋势={trend}, 信号得分={signal_score}")
        
        return AgentOutput(
            agent_name=self.name,
            result=result,
            confidence=0.8
        )


# 便捷函数
async def analyze_technical(
    stock_code: str,
    stock_name: str = "",
    kline_data: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """快速进行技术分析"""
    agent = TechnicalAgent()
    input_data = TechnicalAgentInput(
        stock_code=stock_code,
        stock_name=stock_name,
        kline_data=kline_data or []
    )
    output = await agent.run(input_data)
    return output.result
