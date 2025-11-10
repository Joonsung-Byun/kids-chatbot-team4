# models/chat_schema.py
"""Pydantic 스키마 정의 - 프론트엔드 Message 타입과 호환"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, TypedDict


# ============================================================
# 기존 Pydantic 스키마 (FastAPI용)
# ============================================================

class MapMarker(BaseModel):
    """지도 마커 하나를 나타내는 모델"""
    name: str                         # 마커 이름
    lat: float                        # 위도
    lng: float                        # 경도
    desc: Optional[str] = None        # 설명 (선택)


class MapData(BaseModel):
    """지도 전체 데이터를 묶는 모델"""
    center: Dict[str, float]          # 중심 좌표: {"lat": float, "lng": float}
    markers: List[MapMarker]          # 지도에 표시할 마커 목록


class ChatRequest(BaseModel):
    """클라이언트 → 서버 채팅 요청 모델"""
    message: str = Field(
        ..., 
        description="사용자가 입력한 메시지"
    )
    conversation_id: Optional[str] = Field(
        None, 
        description="대화 세션 ID (UUID)"
    )


class ChatResponse(BaseModel):
    """서버 → 클라이언트 채팅 응답 모델"""
    role: str = Field(
        "ai", 
        description="메시지 역할 (user | ai)"
    )
    content: str = Field(
        ..., 
        description="AI가 생성한 메시지 텍스트"
    )
    type: Optional[str] = Field(
        "text", 
        description="응답 타입 (text | map)"
    )
    data: Optional[MapData] = Field(
        None, 
        description="지도 데이터 (type='map'일 때 포함)"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="대화 세션 ID (클라이언트에 반환)"
    )


# ============================================================
# LangGraph용 TypedDict 스키마
# ============================================================

class ChatState(TypedDict):
    """
    LangGraph Agent 상태 관리
    
    이 상태는 Agent의 모든 노드(Node)에서 공유되며,
    각 노드는 이 상태를 읽고 수정합니다.
    """
    # 대화 관리
    messages: List[Dict[str, str]]    # [{"role": "user", "content": "..."}, ...]
    conversation_id: str              # UUID
    user_query: str                   # 현재 사용자 입력
    
    # 추출된 정보
    location: Optional[str]           # 지역명 (예: "서울", "강남", "부산")
    date: Optional[str]               # 날짜 (예: "오늘", "내일", "2024-01-01")
    
    # Tool 선택 및 실행 결과
    selected_tools: List[str]         # 선택된 도구 목록 (예: ["weather", "rag"])
    needs_location: bool              # 위치 정보 필요 여부
    
    weather_results: Optional[Dict[str, Any]]  # 날씨 API 결과
    rag_results: Optional[List[Dict[str, Any]]]  # RAG 검색 결과
    map_results: Optional[Dict[str, Any]]      # 지도 정보
    
    # 최종 응답
    final_answer: str                 # LLM이 생성한 최종 답변