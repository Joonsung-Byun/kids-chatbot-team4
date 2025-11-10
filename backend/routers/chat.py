# routers/chat.py
"""
Chat Router - LangGraph Agent 통합

LangGraph Agent를 FastAPI에 연결합니다.
- 멀티턴 대화 지원 (conversation_id 기반)
- 세션 히스토리 관리
- Agent 실행 및 응답 반환
"""

import uuid
from fastapi import APIRouter

from models.chat_schema import ChatRequest, ChatResponse, MapData, MapMarker
from services.agent_service import run_agent
from utils.session_manager import (
    get_history,
    save_history,
    get_cached_location,
    save_cached_location,
    add_message
)
from utils.logger import logger

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


@router.post(
    "/message",
    response_model=ChatResponse,
    summary="챗봇 메시지 처리 (LangGraph Agent)",
    description="LangGraph Agent로 멀티턴 대화 처리. conversation_id로 세션 관리."
)
async def chat_message(request: ChatRequest) -> ChatResponse:
    """
    메인 챗봇 엔드포인트 (LangGraph Agent 사용)
    
    워크플로우:
    1. conversation_id 확인 (없으면 생성)
    2. 세션 히스토리 로드
    3. Agent 실행
    4. 히스토리 저장
    5. 응답 반환
    """
    try:
        # 1. conversation_id 처리
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            logger.info(f"🆕 새 대화 생성: {conversation_id}")
        else:
            logger.info(f"📖 기존 대화 계속: {conversation_id}")
        
        # 2. 히스토리 로드
        conversation_history = get_history(conversation_id)
        
        # 3. Agent 실행
        logger.info(f"💬 사용자 메시지: '{request.message}'")
        
        result = run_agent(
            user_query=request.message,
            conversation_id=conversation_id,
            conversation_history=conversation_history
        )
        
        # 4. 히스토리 저장
        save_history(conversation_id, result["conversation_history"])
        
        # 위치 정보 캐싱
        if result.get("location"):
            save_cached_location(conversation_id, result["location"])
        
        # 5. 응답 생성
        response_type = "text"
        map_data = None
        
        # 지도 데이터가 있으면 포함
        if result.get("map_data") and result["map_data"].get("markers"):
            response_type = "map"
            map_data = MapData(
                center=result["map_data"]["center"],
                markers=[
                    MapMarker(**marker)
                    for marker in result["map_data"]["markers"]
                ]
            )
        
        logger.info(f"✅ 응답 생성 완료: type={response_type}, tools={result['tools_used']}")
        
        return ChatResponse(
            role="ai",
            content=result["answer"],
            type=response_type,
            data=map_data,
            conversation_id=conversation_id
        )
    
    except Exception as e:
        logger.error(f"❌ 챗봇 처리 중 오류: {e}", exc_info=True)
        
        # 에러 시에도 conversation_id 반환
        error_conversation_id = request.conversation_id or str(uuid.uuid4())
        
        return ChatResponse(
            role="ai",
            content="죄송합니다. 일시적인 오류가 발생했습니다. 다시 시도해주세요.",
            type="text",
            conversation_id=error_conversation_id
        )


@router.delete(
    "/history/{conversation_id}",
    summary="대화 히스토리 삭제",
    description="특정 conversation_id의 히스토리를 삭제합니다."
)
async def clear_conversation(conversation_id: str):
    """대화 히스토리 삭제"""
    from utils.session_manager import clear_history
    
    clear_history(conversation_id)
    
    return {
        "status": "success",
        "message": f"Conversation {conversation_id} cleared"
    }


@router.get(
    "/sessions/count",
    summary="활성 세션 수",
    description="현재 활성화된 대화 세션 수를 반환합니다."
)
async def get_session_count():
    """활성 세션 개수 조회"""
    from utils.session_manager import get_session_count
    
    count = get_session_count()
    
    return {
        "active_sessions": count
    }