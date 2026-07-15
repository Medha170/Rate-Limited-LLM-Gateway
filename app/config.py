from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Redis configuration defaults
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
    # Ollama configuration
    # Note: Ollama doesn't actually require a real API key, but the client library expects one. 
    # We can pass any dummy string like "ollama".
    LLM_API_KEY: str = "ollama"
    LLM_BASE_URL: str = "http://localhost:11434/v1" 
    LLM_MODEL: str = "llama3.1" 
    
    # Budget configuration
    DAILY_REQUEST_LIMIT: int = 20

    class Config:
        env_file = ".env"

settings = Settings()