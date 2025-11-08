# models/chat_schema.py
"""Pydantic 스키마 정의 - 프론트엔드 Message 타입과 호환"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


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
    session_id: Optional[str] = Field(
        None, 
        description="대화 세션 ID (선택)"
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