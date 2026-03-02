"""FastAPI Application Entry Point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging import setup_logging, get_logger
from api.routes import analysis

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="StockAgent API",
    description="股票交易分析 Agent - 结合基本面、技术面和用户买卖点提供交易建议",
    version="0.1.0",
    debug=settings.debug,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    """Application startup"""
    logger.info("StockAgent API starting...")
    logger.info(f"Model: {settings.openai_model}")
    logger.info(f"Debug: {settings.debug}")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Application shutdown"""
    logger.info("StockAgent API shutting down...")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "StockAgent API",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# Include routers
app.include_router(analysis.router, prefix="/api", tags=["analysis"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
