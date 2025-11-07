"""
Main FastAPI Application

키즈 액티비티 챗봇 백엔드 서버
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat, rag, weather, map
from utils.logger import logger
from utils.config import get_settings

# 설정 로드
settings = get_settings()

# FastAPI 앱 생성
app = FastAPI(
    title="키즈 액티비티 챗봇 API",
    description="LangGraph 기반 멀티에이전트 키즈 액티비티 추천 시스템",
    version="1.0.0",
    debug=settings.DEBUG
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # 프론트엔드 URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(chat.router)
app.include_router(rag.router)
app.include_router(weather.router)
app.include_router(map.router)


@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "키즈 액티비티 챗봇 API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """전체 시스템 헬스 체크"""
    try:
        # VectorDB 상태 확인
        from utils.vector_client import get_vector_client
        vector_client = get_vector_client()
        vector_info = vector_client.get_collection_info()
        
        return {
            "status": "healthy",
            "services": {
                "vector_db": {
                    "status": "connected",
                    "documents": vector_info.get("count", 0),
                    "environment": vector_info.get("environment", "unknown")
                },
                "rag_service": "ready",
                "llm_service": "ready"
            }
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 키즈 액티비티 챗봇 API 서버 시작")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )