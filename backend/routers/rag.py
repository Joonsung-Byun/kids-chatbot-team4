# routers/rag.py
"""
RAG Router - 시설 검색 API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from services.rag_service import get_rag_service
from utils.logger import logger

router = APIRouter(
    prefix="/rag",
    tags=["RAG"]
)


class RAGSearchRequest(BaseModel):
    """RAG 검색 요청 모델"""
    query: str = Field(..., description="검색 키워드", example="서울 실내 놀이터")
    top_k: Optional[int] = Field(3, description="반환할 문서 수")
    region_city: Optional[str] = Field(None, description="시/도 필터", example="서울특별시")
    category1: Optional[str] = Field(None, description="대분류 필터", example="놀이")
    in_out: Optional[str] = Field(None, description="실내/실외 필터", example="실내")


class RAGSearchResponse(BaseModel):
    """RAG 검색 응답 모델"""
    success: bool
    query: str
    results: List[Dict[str, Any]]
    total_found: int


@router.post(
    "/search",
    response_model=RAGSearchResponse,
    summary="RAG 기반 시설 검색",
    description="크로스 인코더 리랭킹 · MMR 다양성 필터링 지원"
)
async def rag_search(request: RAGSearchRequest) -> RAGSearchResponse:
    """
    RAG 검색 엔드포인트

    - 메타데이터 필터 구성  
    - search_and_rerank 호출  
    - 결과 반환
    """
    try:
        logger.info(f"🔍 RAG 요청: '{request.query}'")

        # 필터 조립
        filters: Dict[str, str] = {}
        if request.region_city:
            filters["region_city"] = request.region_city
        if request.category1:
            filters["category1"] = request.category1
        if request.in_out:
            filters["in_out"] = request.in_out

        rag_service = get_rag_service()
        results = rag_service.search_and_rerank(
            query=request.query,
            top_k=request.top_k,
            filters=filters or None
        )

        return RAGSearchResponse(
            success=True,
            query=request.query,
            results=results,
            total_found=len(results)
        )

    except Exception as e:
        logger.error(f"RAG API 오류: {e}")
        # 내부 서버 에러로 HTTP 500 반환
        raise HTTPException(status_code=500, detail="RAG 검색 중 오류가 발생했습니다.")


@router.get(
    "/health",
    summary="RAG 서비스 헬스 체크",
    description="Vector DB 연결 및 컬렉션 정보 반환"
)
async def rag_health():
    try:
        from utils.vector_client import get_vector_client
        client = get_vector_client()
        info = client.get_collection_info()

        return {
            "status": "healthy",
            "vector_db": {
                "connected": True,
                "document_count": info.get("count", 0),
                "environment": info.get("environment", "unknown")
            }
        }
    except Exception as e:
        logger.error(f"RAG 헬스 체크 실패: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }