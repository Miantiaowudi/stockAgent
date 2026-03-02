"""Fundamental Data Tools - 基本面数据获取"""
import requests
from typing import Optional, Dict, Any
from app.logging import get_logger

logger = get_logger(__name__)


def get_fundamental_data(code: str) -> Dict[str, Any]:
    """
    获取股票基本面数据（从东方财富获取）
    
    Args:
        code: 股票代码
    
    Returns:
        基本面数据字典
    """
    try:
        # 东方财富基本面数据 API
        url = f"https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "invt": "2",
            "fltt": "2",
            "fields": "f57,f58,f84,f85,f127,f128,f162,f163,f164,f167,f168,f169,f170,f171,f173,f177,f178,f187,f188,f189,f190,f191,f192",
            "secid": f"1.{code}" if code.startswith("6") else f"0.{code}"
        }
        
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if not data.get("data"):
            return {}
        
        f = data["data"]
        
        return {
            "pe": f.get("f162"),      # 市盈率
            "pb": f.get("f167"),      # 市净率
            "market_cap": f.get("f84"),  # 总市值（万元）
            "circulating_cap": f.get("f85"),  # 流通市值（万元）
            "dividend": f.get("f173"),  # 股息率
            "fvr": f.get("f127"),     # 净资产收益率
            "gross_margin": f.get("f164"),  # 毛利率
            "net_margin": f.get("f170"),  # 净利率
            "debt_ratio": f.get("f189"),  # 资产负债率
        }
    except Exception as e:
        logger.error(f"获取基本面数据失败: {e}")
        return {}


def get_financial_data(code: str) -> Dict[str, Any]:
    """
    获取股票财务数据
    
    Args:
        code: 股票代码
    
    Returns:
        财务数据字典
    """
    try:
        # 东方财富财务指标 API
        url = "https://push2.eastmoney.com/api/qt/stock/fin指标的/get"
        params = {
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fields": "f570,f571,f572,f573,f574,f575,f576,f577,f578,f579,f580,f581,f582,f583,f584,f585,f586,f587,f588,f589,f590,f591,f592,f593,f594,f595,f596,f597,f598,f599,f600",
            "secid": f"1.{code}" if code.startswith("6") else f"0.{code}"
        }
        
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if not data.get("data"):
            return {}
        
        f = data["data"]
        
        return {
            "total_revenue": f.get("f580"),      # 营业总收入
            "revenue_growth": f.get("f581"),     # 营业总收入同比增长
            "net_profit": f.get("f570"),        # 净利润
            "profit_growth": f.get("f571"),      # 净利润同比增长
            "gross_profit_margin": f.get("f573"),  # 毛利率
            "net_profit_margin": f.get("f574"),  # 净利率
            "roe": f.get("f575"),               # 净资产收益率
            "eps": f.get("f578"),               # 每股收益
            "bps": f.get("f579"),               # 每股净资产
        }
    except Exception as e:
        logger.error(f"获取财务数据失败: {e}")
        return {}


def format_market_cap(cap: float) -> str:
    """格式化市值显示"""
    if cap >= 10000:  # 万亿
        return f"{cap / 10000:.2f}万亿"
    elif cap >= 10000:  # 亿
        return f"{cap / 10000:.2f}亿"
    else:
        return f"{cap:.0f}万"
