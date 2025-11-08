# routers/chat.py
"""
Chat Router - LangGraph Agent 역할
"""

from fastapi import APIRouter
from typing import List, Dict, Any, Optional

from models.chat_schema import ChatRequest, ChatResponse, MapData, MapMarker
from services.rag_service import get_rag_service
from services.llm_service import get_llm_service
from utils.logger import logger

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


@router.post(
    "/message",
    response_model=ChatResponse,
    summary="챗봇 메시지 처리",
    description="사용자 메시지를 받아 RAG 검색 → LLM 답변 생성 → (필요 시) 지도 데이터 포함 응답"
)
async def chat_message(request: ChatRequest) -> ChatResponse:
    """
    메인 챗봇 엔드포인트

    1. RAG 검색  
    2. LLM 답변 생성  
    3. 검색 결과 중 좌표가 있으면 MapData 생성  
    4. ChatResponse 반환
    """
    try:
        logger.info(f"💬 사용자 메시지: '{request.message}'")

        # 1) RAG 검색
        rag_service = get_rag_service()
        search_results = rag_service.search_and_rerank(request.message)

        # 2) LLM 답변 생성
        llm_service = get_llm_service()
        answer = llm_service.generate_answer(request.message, search_results)

        # 3) 지도 데이터 생성 (있으면)

        # TODO: 카카오맵 API 연동 후 아래 로직을 활성화하세요.
        # raw_map = get_map_markers(request.message)
        # map_data = MapData(**raw_map)
        # return ChatResponse(
        #     role="ai",
        #     content=answer,
        #     type="map",
        #     data=map_data
        # )


        # 일반 텍스트 응답
        return ChatResponse(
            role="ai",
            content=answer,
            type="text"
        )

    except Exception as e:
        logger.error(f"챗봇 처리 중 오류 발생: {e}")
        # 에러 발생 시에도 ChatResponse 포맷 유지
        return ChatResponse(
            role="ai",
            content="죄송합니다. 일시적인 오류가 발생했습니다.",
            type="text"
        )

'''
------------------------------------------------------------
아래 함수는 카카오맵 연동 전에 사용하던 임시 MapData 생성 로직입니다.
실제 API 연동 시에는 이 전체 블록을 활성화하거나 완전히 제거하세요.
------------------------------------------------------------

def _create_map_data_if_needed(
    search_results: List[Dict[str, Any]]
) -> Optional[MapData]:
    """
    검색 결과(metadata)에서 위도·경도 정보가 있으면 MapData 생성

    - 최대 5개 문서 검사
    - 평균 좌표를 중심으로 MapData 구성
    """
    if not search_results:
        return None

    locations = []
    for doc in search_results[:5]:
        meta = doc.get("metadata", {})
        lat = meta.get("latitude")
        lng = meta.get("longitude")
        name = meta.get("facility_name")

        if lat is None or lng is None or not name:
            continue

        try:
            locations.append({
                "name": str(name),
                "lat": float(lat),
                "lng": float(lng),
                "desc": f"{meta.get('category1','')} - {meta.get('category2','')}"
            })
        except (ValueError, TypeError):
            continue

    center_lat = sum(loc["lat"] for loc in locations) / len(locations)
    center_lng = sum(loc["lng"] for loc in locations) / len(locations)

    markers = [MapMarker(**loc) for loc in locations]

    return MapData(center={"lat": center_lat, "lng": center_lng}, markers=markers)

'''
