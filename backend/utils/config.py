"""Environment config loader"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """환경변수 관리"""
    
    # API Keys
    HUGGINGFACE_API_KEY: str
    OPENAI_API_KEY: Optional[str] = None  # 비교용
    KAKAO_REST_API_KEY: Optional[str] = None
    WEATHER_API_KEY: Optional[str] = None
    
    # Models
    EMBEDDING_MODEL: str = "Alibaba-NLP/gte-Qwen2-7B-instruct"
    GENERATION_MODEL: str = "Qwen/Qwen2.5-7B-Instruct"
    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
    
    # Vector DB (ChromaDB Cloud)
    CHROMA_API_KEY: Optional[str] = None
    CHROMA_TENANT: Optional[str] = None
    CHROMA_DATABASE: str = "kids_chatbot_4team"
    CHROMA_COLLECTION_NAME: str = "kid_program_collection"
    
    # RAG Settings
    TOP_K: int = 30  # 초기 검색 개수 (3584차원 벡터 기반)
    RERANK_TOP_K: int = 10  # Reranking 후 최종 개수
    MMR_DIVERSITY: float = 0.3  # MMR 다양성 (0~1)
    MMR_TOP_K: int = 5  # MMR 최종 결과 개수
    
    # Multi-Query Settings
    MULTI_QUERY_ENABLED: bool = True  # 멀티쿼리 사용 여부
    NUM_SUB_QUERIES: int = 3  # 서브쿼리 개수
    
    # Server
    DEBUG: bool = True
    PORT: int = 3001
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """싱글톤 패턴으로 Settings 반환"""
    return Settings()