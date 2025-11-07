"""
RAG Router

RAG 검색 관련 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from services.rag_service import get_rag_service
from utils.logger import logger

router = APIRouter(prefix="/rag", tags=["RAG"])


class RAGSearchRequest(BaseModel):
    """RAG 검색 요청"""
    query: str = Field(..., description="검색 쿼리", example="서울 실내 놀이터")
    top_k: Optional[int] = Field(3, description="반환할 문서 수")
    region_city: Optional[str] = Field(None, description="지역 필터", example="서울특별시")
    category1: Optional[str] = Field(None, description="카테고리 필터", example="놀이")
    in_out: Optional[str] = Field(None, description="실내/실외", example="실내")


class RAGSearchResponse(BaseModel):
    """RAG 검색 응답"""
    success: bool
    query: str
    results: List[Dict[str, Any]]
    total_found: int


@router.post("/search", response_model=RAGSearchResponse)
async def rag_search(request: RAGSearchRequest):
    """
    RAG 기반 시설 검색
    
    고도화된 검색 기능:
    - 크로스인코더 리랭킹
    - MMR 다양성 필터링  
    - 메타데이터 기반 필터링
    """
    try:
        logger.info(f"🔍 RAG API 호출: '{request.query}'")
        
        # 필터 조건 구성
        filters = {}
        if request.region_city:
            filters['region_city'] = request.region_city
        if request.category1:
            filters['category1'] = request.category1
        if request.in_out:
            filters['in_out'] = request.in_out
        
        # RAG 검색 수행
        rag_service = get_rag_service()
        results = rag_service.search_and_rerank(
            query=request.query,
            top_k=request.top_k,
            filters=filters if filters else None
        )
        
        return RAGSearchResponse(
            success=True,
            query=request.query,
            results=results,
            total_found=len(results)
        )
        
    except Exception as e:
        logger.error(f"RAG API 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def rag_health():
    """RAG 서비스 상태 확인"""
    try:
        # VectorClient 연결 상태 확인
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
        return {
            "status": "unhealthy", 
            "error": str(e)
        }