"""Base Agent Class"""
from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel

from app.logging import get_logger

logger = get_logger(__name__)


class AgentInput(BaseModel):
    """Base input for agents"""
    stock_code: str
    stock_name: str = ""


class AgentOutput(BaseModel):
    """Base output for agents"""
    agent_name: str
    result: Dict[str, Any]
    confidence: float = 0.0


class BaseAgent(ABC):
    """Base class for all agents"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"agents.{name}")
    
    @abstractmethod
    async def run(self, input_data: AgentInput) -> AgentOutput:
        """Run the agent with given input"""
        pass
    
    def log(self, message: str, level: str = "info") -> None:
        """Log a message"""
        getattr(self.logger, level)(f"[{self.name}] {message}")
