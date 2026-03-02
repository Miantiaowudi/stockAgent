"""Analysis API Routes"""
from fastapi import APIRouter, HTTPException
from typing import List

from schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    BatchAnalysisRequest,
    ReviewResponse,
)
from agents.master_agent import MasterAgent, MasterAgentInput, UserTrade, CurrentPosition
from app.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/analysis")
async def analyze_stock(request: AnalysisRequest):
    """分析单只股票 - 完整综合分析"""
    logger.info(f"收到分析请求: {request.stock_code}")
    
    try:
        # 转换用户交易记录
        user_trades = []
        if request.user_trades:
            for t in request.user_trades:
                user_trades.append(UserTrade(
                    direction=t.direction,
                    price=t.price,
                    quantity=t.quantity,
                    trade_time=t.trade_time
                ))
        
        # 转换持仓
        position = None
        if request.current_position:
            position = CurrentPosition(
                hold_quantity=request.current_position.hold_quantity,
                avg_cost=request.current_position.avg_cost,
                current_price=request.current_position.current_price
            )
        
        # 使用 Master Agent 进行分析
        agent = MasterAgent()
        input_data = MasterAgentInput(
            stock_code=request.stock_code,
            user_trades=user_trades,
            current_position=position
        )
        
        result = await agent.run(input_data)
        
        if result.result.get("error"):
            raise HTTPException(status_code=400, detail=result.result.get("error"))
        
        return result.result
        
    except Exception as e:
        logger.error(f"分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analysis/batch")
async def batch_analyze(request: BatchAnalysisRequest):
    """批量分析股票"""
    logger.info(f"收到批量分析请求: {len(request.stocks)} 只股票")
    
    results = []
    for stock_code in request.stocks:
        try:
            agent = MasterAgent()
            input_data = MasterAgentInput(stock_code=stock_code)
            result = await agent.run(input_data)
            results.append(result.result)
        except Exception as e:
            logger.error(f"分析 {stock_code} 失败: {e}")
            results.append({
                "stock_code": stock_code,
                "error": str(e)
            })
    
    return {"results": results}


@router.get("/analysis/review")
async def review_positions(type: str = "cleared"):
    """复盘已清仓股票"""
    logger.info(f"收到复盘请求: type={type}")
    
    # TODO: 实现从数据库获取已清仓股票进行复盘
    return {
        "summary": {
            "total_trades": 0,
            "win_rate": 0,
            "total_profit": 0,
            "avg_holding_days": 0
        },
        "positions": [],
        "message": "复盘功能待实现，需集成数据库"
    }
