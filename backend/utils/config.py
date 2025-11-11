"""Environment config loader"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """환경변수 관리"""
    
    # API Keys
    HUGGINGFACE_API_KEY: str
    OPENAI_API_KEY: Optional[str] = None
    KAKAO_REST_API_KEY: Optional[str] = None
    WEATHER_API_KEY: Optional[str] = None
    
    # Models
    EMBEDDING_MODEL: str = "Alibaba-NLP/gte-Qwen2-7B-instruct"
    GENERATION_MODEL: str = "Qwen/Qwen2.5-7B-Instruct"
    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
    
    # Vector DB - 로컬/클라우드 자동 감지
    # 로컬 ChromaDB (Docker Compose)
    CHROMA_HOST: Optional[str] = None  # 예: "chromadb" (docker) or "localhost"
    CHROMA_PORT: int = 8000
    
    # ChromaDB Cloud (fallback)
    CHROMA_API_KEY: Optional[str] = None
    CHROMA_TENANT: Optional[str] = None
    CHROMA_DATABASE: str = "kids_chatbot_4team"
    
    # Collection
    CHROMA_COLLECTION_NAME: str = "kid_program_collection"
    
    # RAG Settings
    TOP_K: int = 30  # 초기 검색 개수
    RERANK_TOP_K: int = 10  # Reranking 후 최종 개수
    MMR_DIVERSITY: float = 0.3  # MMR 다양성 (0~1)
    MMR_TOP_K: int = 5  # MMR 최종 결과 개수
    SIMILARITY_THRESHOLD: float = 0.3  # 유사도 임계값
    
    # Multi-Query Settings
    MULTI_QUERY_ENABLED: bool = True
    NUM_SUB_QUERIES: int = 3
    
    # 실행 환경
    ENVIRONMENT: str = "local"  # local, docker, colab, runpod
    USE_GPU: bool = False  # GPU 사용 여부
    
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