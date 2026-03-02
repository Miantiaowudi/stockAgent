"""Stock Data Tools - 股票数据获取工具"""
import requests
from typing import Dict, Any, Optional
from app.logging import get_logger

logger = get_logger(__name__)

# 腾讯财经 API
TENCENT_API = "http://hq.sinajs.cn/list="
TENCENT_KLINE_API = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"


def get_stock_name(code: str) -> Optional[str]:
    """获取股票名称"""
    try:
        prefix = "sh" if code.startswith("6") else "sz"
        url = f"{TENCENT_API}{prefix}{code}"
        response = requests.get(url, headers={"Referer": "http://finance.sina.com.cn"}, timeout=5)
        response.encoding = "gbk"
        
        text = response.text
        match = text.split('="')[1].split(",")[0] if '="' in text else None
        return match if match else None
    except Exception as e:
        logger.error(f"获取股票名称失败: {e}")
        return None


def get_stock_price(code: str) -> Optional[Dict[str, Any]]:
    """获取股票实时价格"""
    try:
        prefix = "sh" if code.startswith("6") else "sz"
        url = f"{TENCENT_API}{prefix}{code}"
        response = requests.get(url, headers={"Referer": "http://finance.sina.com.cn"}, timeout=5)
        response.encoding = "gbk"
        
        text = response.text
        if '="' not in text:
            return None
            
        data = text.split('="')[1].split(",")
        
        if len(data) > 10:
            return {
                "name": data[0],
                "code": code,
                "current_price": float(data[3]) if data[3] else 0,
                "yesterday_close": float(data[2]) if data[2] else 0,
                "open_price": float(data[1]) if data[1] else 0,
                "high_price": float(data[4]) if data[4] else 0,
                "low_price": float(data[5]) if data[5] else 0,
                "volume": int(float(data[8])) if data[8] else 0,
                "amount": float(data[9]) if data[9] else 0,
            }
        return None
    except Exception as e:
        logger.error(f"获取股票价格失败: {e}")
        return None


def get_kline_data(code: str, days: int = 365) -> list:
    """获取K线数据"""
    try:
        prefix = "sh" if code.startswith("6") else "sz"
        symbol = f"{prefix}{code}"
        
        url = f"{TENCENT_KLINE_API}?_var=kline_day&param={symbol},day,,,{days},qfq"
        response = requests.get(url, timeout=10)
        text = response.text
        
        match = text.split("=")[1] if "=" in text else None
        if not match:
            return []
        
        import json
        data = json.loads(match)
        kline_array = data.get("data", {}).get(symbol, {}).get("qfqday", [])
        
        return [
            {
                "date": item[0],
                "open": float(item[1]),
                "close": float(item[2]),
                "high": float(item[3]),
                "low": float(item[4]),
                "volume": int(item[5])
            }
            for item in kline_array
        ]
    except Exception as e:
        logger.error(f"获取K线数据失败: {e}")
        return []
