"""Application Configuration"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application Settings"""
    
    # LLM Provider
    llm_provider: str = "ollama"  # "openai" or "ollama"
    llm_model: str = "qwen2.5:14b"
    ollama_base_url: str = "http://localhost:11434"
    llm_temperature: float = 0.7
    
    # OpenAI (optional)
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    
    # LangChain
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings"""
    return Settings()
