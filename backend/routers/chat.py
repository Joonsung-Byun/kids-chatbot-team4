"""
Chat Router

메인 챗봇 API - LangGraph Agent 통합 예정
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from services.rag_service import get_rag_service
from services.llm_service import get_llm_service
from utils.logger import logger

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    """채팅 요청"""
    message: str = Field(..., description="사용자 메시지")
    session_id: Optional[str] = Field(None, description="세션 ID")


class ChatResponse(BaseModel):
    """채팅 응답"""
    message: str
    type: str = Field(description="응답 타입: text, map, clarification")
    data: Optional[Dict[str, Any]] = None


@router.post("/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest):
    """
    메인 챗봇 엔드포인트
    
    TODO: LangGraph Agent 통합 예정
    - 멀티 에이전트 (RAG + Weather + Map)
    - 조건부 도구 호출
    - 멀티턴 대화 관리
    """
    try:
        logger.info(f"💬 챗봇 메시지: '{request.message}'")
        
        # TODO: LangGraph Agent 구현 예정
        # 현재는 기본 RAG만 사용
        
        # 1. RAG 검색
        rag_service = get_rag_service()
        search_results = rag_service.search_and_rerank(request.message)
        
        # 2. LLM 답변 생성
        llm_service = get_llm_service()
        answer = llm_service.generate_answer(request.message, search_results)
        
        return ChatResponse(
            message=answer,
            type="text",
            data={"search_results": len(search_results)}
        )
        
    except Exception as e:
        logger.error(f"챗봇 오류: {e}")
        return ChatResponse(
            message="죄송합니다. 일시적인 오류가 발생했습니다.",
            type="error"
        )


# TODO: LangGraph 통합 예정
# - Agent workflow 정의
# - State 관리
# - Tool 호출 순서 결정
# - 멀티턴 대화 처리