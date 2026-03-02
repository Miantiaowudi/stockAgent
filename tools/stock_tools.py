"""Stock Data Tools for LangChain"""
from typing import Optional, Dict, Any, List
from langchain_core.tools import tool

from tools.stock_data import get_stock_name, get_stock_price, get_kline_data
from app.logging import get_logger

logger = get_logger(__name__)


@tool
def get_stock_info(code: str) -> str:
    """
    获取股票的基本信息，包括当前价格、涨跌幅等。
    
    Args:
        code: 股票代码，如 '600000'
    
    Returns:
        股票信息 JSON 字符串
    """
    try:
        name = get_stock_name(code) or code
        price_data = get_stock_price(code)
        
        if not price_data:
            return f"无法获取股票 {code} 的信息"
        
        current = price_data.get("current_price", 0)
        yesterday = price_data.get("yesterday_close", 0)
        change = current - yesterday
        change_rate = (change / yesterday * 100) if yesterday > 0 else 0
        
        return f"""
股票: {name} ({code})
当前价格: {current:.2f}
昨收: {yesterday:.2f}
涨跌: {change:+.2f} ({change_rate:+.2f}%)
开盘: {price_data.get('open_price', 0):.2f}
最高: {price_data.get('high_price', 0):.2f}
最低: {price_data.get('low_price', 0):.2f}
成交量: {price_data.get('volume', 0):,}
成交额: {price_data.get('amount', 0):,.0f}
""".strip()
    except Exception as e:
        logger.error(f"获取股票信息失败: {e}")
        return f"获取股票信息失败: {str(e)}"


@tool
def get_historical_kline(code: str, days: int = 60) -> str:
    """
    获取股票的历史K线数据，用于技术分析。
    
    Args:
        code: 股票代码，如 '600000'
        days: 获取的天数，默认60天
    
    Returns:
        K线数据摘要 JSON 字符串
    """
    try:
        kline_data = get_kline_data(code, days)
        
        if not kline_data:
            return f"无法获取股票 {code} 的K线数据"
        
        # 取最近30条数据
        recent = kline_data[-30:] if len(kline_data) > 30 else kline_data
        
        name = get_stock_name(code) or code
        first = recent[0]
        last = recent[-1]
        
        return f"""
股票: {name} ({code})
数据范围: {first['date']} 至 {last['date']}
数据条数: {len(recent)}
最新收盘: {last['close']:.2f}
最高价: {max(k['high'] for k in recent):.2f}
最低价: {min(k['low'] for k in recent):.2f}
平均成交量: {sum(k['volume'] for k in recent) // len(recent):,}
""".strip()
    except Exception as e:
        logger.error(f"获取K线数据失败: {e}")
        return f"获取K线数据失败: {str(e)}"


def get_all_stock_tools() -> List:
    """获取所有股票数据工具"""
    return [get_stock_info, get_historical_kline]
