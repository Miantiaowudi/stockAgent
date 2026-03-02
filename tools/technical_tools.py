"""Technical Analysis Tools for LangChain"""
from typing import List, Dict, Any
from langchain_core.tools import tool

from tools.indicators import calculate_all_indicators
from app.logging import get_logger

logger = get_logger(__name__)


@tool
def calculate_technical_indicators(kline_data: List[Dict]) -> str:
    """
    计算股票的技术指标，用于技术分析。
    
    Args:
        kline_data: K线数据列表，每条包含 date, open, close, high, low, volume
    
    Returns:
        技术指标分析结果 JSON 字符串
    """
    try:
        if not kline_data:
            return "没有K线数据"
        
        indicators = calculate_all_indicators(kline_data)
        
        if not indicators:
            return "技术指标计算失败"
        
        rsi = indicators.get("rsi", 0)
        macd = indicators.get("macd", {})
        bb = indicators.get("bollinger_bands", {})
        ma = indicators.get("moving_averages", {})
        trend = indicators.get("trend", "unknown")
        
        # 生成分析
        analysis = []
        
        # RSI 分析
        if rsi >= 70:
            analysis.append(f"- RSI={rsi:.1f}，超买区域，注意回调风险")
        elif rsi <= 30:
            analysis.append(f"- RSI={rsi:.1f}，超卖区域，可能存在反弹机会")
        else:
            analysis.append(f"- RSI={rsi:.1f}，中性区域")
        
        # MACD 分析
        macd_val = macd.get("macd", 0)
        signal_val = macd.get("signal", 0)
        if macd_val > signal_val:
            analysis.append(f"- MACD 金叉，看涨信号")
        elif macd_val < signal_val:
            analysis.append(f"- MACD 死叉，看跌信号")
        else:
            analysis.append(f"- MACD 盘整，等待方向")
        
        # 均线分析
        if ma:
            ma5 = ma.get("ma5")
            ma20 = ma.get("ma20")
            if ma5 and ma20:
                if ma5 > ma20:
                    analysis.append(f"- 均线多头排列，短期强势")
                else:
                    analysis.append(f"- 均线空头排列，短期弱势")
        
        # 趋势
        analysis.append(f"- 当前趋势: {trend}")
        
        result = f"""
技术指标分析:
{chr(10).join(analysis)}

详细数据:
- RSI: {rsi:.2f}
- MACD: {macd_val:.4f} (signal: {signal_val:.4f})
- 布林带: 上轨 {bb.get('upper', 0):.2f}, 中轨 {bb.get('middle', 0):.2f}, 下轨 {bb.get('lower', 0):.2f}
- MA5: {ma.get('ma5', 'N/A')}
- MA10: {ma.get('ma10', 'N/A')}
- MA20: {ma.get('ma20', 'N/A')}
- MA60: {ma.get('ma60', 'N/A')}
""".strip()
        
        return result
    except Exception as e:
        logger.error(f"技术指标计算失败: {e}")
        return f"技术指标计算失败: {str(e)}"


@tool
def analyze_stock_trend(kline_data: List[Dict]) -> str:
    """
    分析股票趋势，只返回简单的趋势判断。
    
    Args:
        kline_data: K线数据列表
    
    Returns:
        趋势判断结果
    """
    try:
        if not kline_data or len(kline_data) < 20:
            return "数据不足，无法判断趋势"
        
        closes = [k["close"] for k in kline_data]
        
        # 简单趋势判断
        ma20 = sum(closes[-20:]) / 20
        ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else ma20
        
        current = closes[-1]
        
        if current > ma20 > ma60:
            return "上涨趋势"
        elif current < ma20 < ma60:
            return "下跌趋势"
        elif ma20 > ma60:
            return "震荡上行"
        else:
            return "震荡下行"
    except Exception as e:
        logger.error(f"趋势分析失败: {e}")
        return f"趋势分析失败: {str(e)}"


def get_all_technical_tools() -> List:
    """获取所有技术分析工具"""
    return [calculate_technical_indicators, analyze_stock_trend]
