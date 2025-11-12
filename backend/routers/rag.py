# routers/rag.py
"""
RAG Router - 시설 검색 API (개선 + 로그 진단 포함 버전)
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


# ============================================================
# 📘 Request / Response 모델
# ============================================================

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


# ============================================================
# 🔍 /rag/search - RAG 기반 시설 검색
# ============================================================

@router.post(
    "/search",
    response_model=RAGSearchResponse,
    summary="RAG 기반 시설 검색",
    description="로컬 ChromaDB 기반 RAG 검색 (필터 자동 매핑 + 로그 진단 지원)"
)
async def rag_search(request: RAGSearchRequest) -> RAGSearchResponse:
    """
    RAG 검색 엔드포인트
    - 컬럼명 자동 매핑 (region_city → CTPRVN_NM, category1 → Category1 등)
    - $eq 구조로 필터 정확도 향상
    - 결과 0개 시 실제 메타데이터 샘플 로그 출력
    """
    try:
        logger.info(f"🔍 RAG 요청: '{request.query}'")

        # 1️⃣ 필터 구성
        filters = {}
        if request.region_city:
            filters["CTPRVN_NM"] = request.region_city
        if request.category1:
            filters["Category1"] = request.category1
        if request.in_out:
            filters["in_out"] = request.in_out

        filters = filters if filters else None  # ✅ 빈 dict 방지

        # 2️⃣ 필터 조합 ($and 구조)
        where_clause = {"$and": filters} if filters else None
        logger.info(f"🧩 필터 구조: {where_clause}")

        # 3️⃣ RAG 서비스 호출
        rag_service = get_rag_service()
        results = rag_service.search_and_rerank(
            query=request.query,
            top_k=request.top_k,
            filters=filters  # ✅ where_clause → filters
        )

        logger.info(f"📊 RAG 결과 수: {len(results)}")

        # 4️⃣ 결과가 없을 경우 → 샘플 메타데이터 출력
        if len(results) == 0:
            try:
                from utils.vector_client import get_vector_client
                client = get_vector_client()
                sample = client.collection.get(limit=3)
                if sample and "metadatas" in sample:
                    logger.warning(f"🧩 샘플 메타데이터 예시: {sample['metadatas'][0]}")
                else:
                    logger.warning("⚠️ 샘플 메타데이터를 가져오지 못했습니다.")
            except Exception as e:
                logger.error(f"❌ 샘플 조회 실패: {e}")

        # 5️⃣ 응답 반환
        return RAGSearchResponse(
            success=True,
            query=request.query,
            results=results,
            total_found=len(results)
        )

    except Exception as e:
        logger.error(f"❌ RAG API 오류: {e}")
        raise HTTPException(status_code=500, detail="RAG 검색 중 오류가 발생했습니다.")


# ============================================================
# 💚 /rag/health - 벡터DB 헬스체크
# ============================================================

@router.get(
    "/health",
    summary="RAG 서비스 헬스 체크",
    description="Vector DB 연결 상태 및 컬렉션 정보 반환"
)
async def rag_health():
    """ChromaDB 연결 및 컬렉션 상태 확인"""
    try:
        from utils.vector_client import get_vector_client
        client = get_vector_client()
        info = client.get_collection_info()

        return {
            "status": "healthy",
            "vector_db": {
                "connected": True,
                "document_count": info.get("count", 0),
                "environment": info.get("environment", "unknown"),
                "collection": info.get("name", "unknown")
            }
        }
    except Exception as e:
        logger.error(f"❌ RAG 헬스 체크 실패: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }