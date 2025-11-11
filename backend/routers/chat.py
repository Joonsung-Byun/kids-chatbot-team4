# routers/chat.py

"""
Chat Router - LangChain Agent 통합
"""

import uuid
from fastapi import APIRouter

from models.chat_schema import ChatRequest, ChatResponse
from services.agent_service import run_agent
from utils.session_manager import (
    get_history,
    save_history
)
from utils.logger import logger

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


@router.post(
    "/message",
    response_model=ChatResponse,
    summary="챗봇 메시지 처리 (LangChain Agent)",
    description="LangChain Agent로 자동 도구 선택 및 실행"
)
async def chat_message(request: ChatRequest) -> ChatResponse:
    """
    메인 챗봇 엔드포인트
    
    1. conversation_id 확인
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
        
        logger.info(f"✅ 응답 생성 완료 (타입: {result['response_type']})")
        
        # 5. 응답 타입에 따라 반환
        if result["response_type"] == "map":
            # 지도 응답
            return ChatResponse(
                role="ai",
                content=result["answer"],
                type="map",
                link=result.get("map_link"),
                data=result.get("map_data"),
                conversation_id=conversation_id
            )
        else:
            # 텍스트 응답
            return ChatResponse(
                role="ai",
                content=result["answer"],
                type="text",
                link=None,
                data=None,
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
            link=None,
            data=None,
            conversation_id=error_conversation_id
        )


@router.delete(
    "/history/{conversation_id}",
    summary="대화 히스토리 삭제"
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
    summary="활성 세션 수"
)
async def get_session_count():
    """활성 세션 개수 조회"""
    from utils.session_manager import get_session_count
    
    count = get_session_count()
    
    return {
        "active_sessions": count
    }