"""Technical Indicators Tools - 技术指标计算"""
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from app.logging import get_logger

logger = get_logger(__name__)


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """计算 RSI 指标"""
    if len(prices) < period + 1:
        return 50.0
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)


def calculate_macd(prices: List[float]) -> Dict[str, float]:
    """计算 MACD 指标"""
    if len(prices) < 26:
        return {"macd": 0, "signal": 0, "histogram": 0}
    
    # EMA
    ema12 = pd.Series(prices).ewm(span=12, adjust=False).mean().values
    ema26 = pd.Series(prices).ewm(span=26, adjust=False).mean().values
    
    macd_line = ema12 - ema26
    signal_line = pd.Series(macd_line).ewm(span=9, adjust=False).mean().values
    histogram = macd_line - signal_line
    
    return {
        "macd": round(macd_line[-1], 4),
        "signal": round(signal_line[-1], 4),
        "histogram": round(histogram[-1], 4)
    }


def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: int = 2) -> Dict[str, float]:
    """计算布林带"""
    if len(prices) < period:
        return {"upper": 0, "middle": 0, "lower": 0}
    
    prices_series = pd.Series(prices)
    middle = prices_series.rolling(window=period).mean().values
    std = prices_series.rolling(window=period).std().values
    
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    
    return {
        "upper": round(upper[-1], 2),
        "middle": round(middle[-1], 2),
        "lower": round(lower[-1], 2)
    }


def calculate_moving_averages(prices: List[float]) -> Dict[str, float]:
    """计算均线"""
    if len(prices) < 60:
        return {}
    
    prices_series = pd.Series(prices)
    
    return {
        "ma5": round(prices_series.rolling(window=5).mean().values[-1], 2),
        "ma10": round(prices_series.rolling(window=10).mean().values[-1], 2),
        "ma20": round(prices_series.rolling(window=20).mean().values[-1], 2),
        "ma60": round(prices_series.rolling(window=60).mean().values[-1], 2)
    }


def analyze_trend(prices: List[float], moving_averages: Dict[str, float]) -> str:
    """分析趋势"""
    if not moving_averages:
        return "unknown"
    
    current_price = prices[-1]
    ma20 = moving_averages.get("ma20", current_price)
    ma60 = moving_averages.get("ma60", current_price)
    
    if current_price > ma20 > ma60:
        return "上涨趋势"
    elif current_price < ma20 < ma60:
        return "下跌趋势"
    else:
        return "震荡整理"


def calculate_all_indicators(kline_data: List[Dict]) -> Dict[str, Any]:
    """计算所有技术指标"""
    if not kline_data:
        return {}
    
    closes = [item["close"] for item in kline_data]
    
    return {
        "rsi": calculate_rsi(closes),
        "macd": calculate_macd(closes),
        "bollinger_bands": calculate_bollinger_bands(closes),
        "moving_averages": calculate_moving_averages(closes),
        "trend": analyze_trend(closes, calculate_moving_averages(closes))
    }
