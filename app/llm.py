"""LLM Configuration - 支持多种 LLM 提供商"""
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from app.config import get_settings
from app.logging import get_logger

logger = get_logger(__name__)


def get_llm():
    """获取 LLM 实例 - 支持 Ollama 和 OpenAI"""
    settings = get_settings()
    
    if settings.llm_provider == "ollama":
        logger.info(f"Using Ollama LLM: {settings.llm_model}")
        logger.info(f"Ollama Base URL: {settings.ollama_base_url}")
        return ChatOllama(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            base_url=settings.ollama_base_url,
        )
    elif settings.llm_provider == "openai":
        logger.info(f"Using OpenAI LLM: {settings.openai_model}")
        return ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.llm_temperature,
            api_key=settings.openai_api_key,
        )
    else:
        # Default to Ollama
        logger.warning(f"Unknown provider {settings.llm_provider}, defaulting to Ollama")
        return ChatOllama(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
        )


# Default LLM instance (singleton)
_llm_instance = None


def get_default_llm():
    """获取默认 LLM 实例 (单例)"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = get_llm()
    return _llm_instance
