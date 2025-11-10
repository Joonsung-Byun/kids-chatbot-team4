"""
LangChain Agent Service (LangChain 1.0+ with LangGraph)

LangGraph의 create_react_agent를 사용한 도구 자동 선택 및 실행
langgraph 1.0.2 버전 호환 + MockChatModel Runnable 구현
"""

import json
from typing import List, Dict, Any, Iterator

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.runnables import Runnable
from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration

from services.llm_service import get_llm_service
from services.rag_service import get_rag_service
from services.weather_service import get_weather
from services.map_service import get_map_markers
from utils.logger import logger


# ============================================================
# Tool 정의 (LangGraph 방식)
# ============================================================

@tool
def weather_tool(location: str) -> str:
    """날씨 정보를 조회합니다. 입력: 지역명 (예: '서울', '강남')"""
    try:
        logger.info(f"[WeatherTool] 호출: {location}")
        result = get_weather(location=location, target_date=None)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[WeatherTool] 오류: {e}")
        return json.dumps({"error": str(e)})


@tool
def rag_search_tool(query: str) -> str:
    """문화/체육/교육 시설을 검색합니다. 입력: 검색 쿼리 (예: '서울 놀이터', '강남 키즈카페')"""
    try:
        logger.info(f"[RAGTool] 호출: {query}")
        rag_service = get_rag_service()
        results = rag_service.search_and_rerank(query=query, top_k=5)
        
        formatted = []
        for doc in results[:3]:
            metadata = doc.get("metadata", {})
            formatted.append({
                "name": metadata.get("facility_name", "Unknown"),
                "category": metadata.get("category1", "시설"),
                "location": metadata.get("region_gu", ""),
                "price": metadata.get("price", "무료")
            })
        return json.dumps(formatted, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[RAGTool] 오류: {e}")
        return json.dumps({"error": str(e)})


@tool
def map_tool(query: str) -> str:
    """지도를 생성합니다. 입력: 시설 정보"""
    try:
        logger.info(f"[MapTool] 호출: {query}")
        # TODO: 실제 카카오맵 API 연동
        return json.dumps({
            "status": "success",
            "message": "지도 생성 완료 (Mock)"
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[MapTool] 오류: {e}")
        return json.dumps({"error": str(e)})


# ============================================================
# Tools 리스트
# ============================================================

def get_tools():
    """사용 가능한 도구 목록 반환"""
    return [weather_tool, rag_search_tool, map_tool]


# ============================================================
# Mock LLM (CPU 환경용) - Runnable 구현
# ============================================================

class MockChatModel(BaseChatModel):
    """
    LangGraph 호환 Mock ChatModel
    BaseChatModel을 상속하여 Runnable 인터페이스 구현
    """
    
    model_name: str = "mock-chat-model"
    
    def _generate(self, messages: List[BaseMessage], stop=None, **kwargs) -> ChatResult:
        """필수 메서드: 메시지 생성"""
        # 마지막 사용자 메시지 추출
        user_input = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_input = msg.content
                break
        
        # 룰 베이스 응답
        if any(k in user_input for k in ["지역", "어디", "위치"]):
            response_text = "어느 지역을 생각하고 계신가요? 🗺️ (서울, 부산, 대구 등)"
        elif any(k in user_input for k in ["고마워", "감사", "좋아"]):
            response_text = "천만에요! 😊 더 도움이 필요하시면 언제든 말씀해주세요!"
        else:
            response_text = "Mock 모드입니다. 실제 LLM을 사용하려면 OpenAI API 키를 설정하거나 GPU 환경에서 실행해주세요."
        
        # ChatResult 반환
        message = AIMessage(content=response_text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])
    
    @property
    def _llm_type(self) -> str:
        """필수 속성: LLM 타입"""
        return "mock-chat-model"
    
    def bind_tools(self, tools, **kwargs):
        """도구 바인딩 (Mock에서는 self 반환)"""
        return self
    
    def _stream(self, messages: List[BaseMessage], stop=None, **kwargs) -> Iterator[ChatResult]:
        """선택 메서드: 스트리밍 (미구현)"""
        result = self._generate(messages, stop=stop, **kwargs)
        yield result
    
    async def _agenerate(self, messages: List[BaseMessage], stop=None, **kwargs) -> ChatResult:
        """선택 메서드: 비동기 생성 (동기 버전 재사용)"""
        return self._generate(messages, stop=stop, **kwargs)


# ============================================================
# Agent 생성
# ============================================================

def create_langchain_agent():
    """LangGraph create_react_agent를 사용한 Agent 생성"""
    logger.info("🔧 LangGraph Agent 생성 중...")
    
    try:
        from langgraph.prebuilt import create_react_agent
    except ImportError:
        logger.error("❌ langgraph 패키지가 설치되지 않았습니다. pip install langgraph 로 설치하세요.")
        return None
    
    tools = get_tools()
    
    # System prompt 정의
    system_prompt = """당신은 아이와 함께할 수 있는 활동을 추천하는 전문 챗봇입니다.

**중요 규칙:**

1. **위치 확인이 최우선입니다:**
   - 사용자 질문에 지역명이 없으면 먼저 "어느 지역을 생각하고 계신가요? 🗺️" 질문
   - 이전 대화에 지역이 있으면 그것을 사용

2. **위치가 확인되면 다음 순서로 진행:**
   - Step 1: weather_tool로 날씨 확인
   - Step 2: rag_search_tool로 추천 시설 검색
   - Step 3: 결과를 종합해서 친절하게 답변

3. **감정 표현("고마워", "좋아요" 등):**
   - 도구 사용 없이 바로 친절하게 응답

4. **답변 스타일:**
   - 이모지 사용 (🎨, 🏃‍♂️, 📍)
   - 구체적인 정보 제공
   - 추가 질문 유도

사용 가능한 도구를 활용하여 최선의 답변을 제공하세요."""
    
    # LLM 로드
    llm_service = get_llm_service()
    
    # OpenAI API 키가 있으면 OpenAI 사용
    import os
    if os.getenv("OPENAI_API_KEY"):
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
            logger.info("✅ OpenAI LLM 사용")
        except ImportError:
            logger.warning("⚠️ langchain-openai 미설치 → Mock 모드")
            llm = MockChatModel()
    elif llm_service._use_gpu and llm_service._model:
        try:
            from langchain_huggingface import HuggingFacePipeline
            llm = HuggingFacePipeline(
                pipeline=llm_service._model,
                model_kwargs={"temperature": 0.7, "max_new_tokens": 512}
            )
            logger.info("✅ GPU 모드: HuggingFace LLM 사용")
        except ImportError:
            logger.warning("⚠️ langchain-huggingface 미설치 → Mock 모드")
            llm = MockChatModel()
    else:
        logger.info("✅ CPU 모드: Mock LLM 사용")
        llm = MockChatModel()
    
    # ============================================================
    # langgraph 버전별 호환성 처리
    # ============================================================
    
    # langgraph 1.0.2는 파라미터가 거의 없음!
    # 공식 문서: create_react_agent(model, tools, checkpointer=None)
    
    try:
        logger.info("🔧 Agent 생성 시작...")
        
        # ✅ 기본 방법 (langgraph 1.0.2)
        agent = create_react_agent(
            model=llm,
            tools=tools
        )
        
        logger.info("✅ LangGraph ReAct Agent 생성 완료")
        logger.warning("⚠️ System prompt는 messages에 직접 추가해야 합니다")
        return agent
        
    except Exception as e:
        logger.error(f"❌ Agent 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================
# 대화 히스토리 변환
# ============================================================

def convert_history_to_messages(history: List[Dict[str, str]]) -> List:
    """대화 히스토리를 LangChain Message 형식으로 변환"""
    messages = []
    for msg in history[-5:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "ai":
            messages.append(AIMessage(content=msg["content"]))
    return messages


# ============================================================
# Agent 실행 (System Prompt 포함)
# ============================================================

def run_agent(user_query: str, conversation_id: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """LangGraph Agent 실행"""
    logger.info(f"🚀 Agent 실행: conversation_id={conversation_id}")
    
    agent = create_langchain_agent()
    
    if agent is None:
        return {
            "answer": "죄송합니다. Agent 시스템을 초기화할 수 없습니다. langgraph 패키지를 확인해주세요.",
            "conversation_history": conversation_history or [],
            "tools_used": []
        }
    
    # System prompt를 첫 메시지로 추가
    from langchain_core.messages import SystemMessage
    
    system_prompt = """당신은 아이와 함께할 수 있는 활동을 추천하는 전문 챗봇입니다.

**중요 규칙:**
1. 위치 확인이 최우선입니다
2. 위치가 확인되면 weather_tool과 rag_search_tool 사용
3. 감정 표현은 도구 없이 바로 응답

사용 가능한 도구를 활용하여 최선의 답변을 제공하세요."""
    
    # 메시지 구성
    chat_history = convert_history_to_messages(conversation_history or [])
    
    # System prompt를 맨 앞에 추가
    all_messages = [SystemMessage(content=system_prompt)] + chat_history + [HumanMessage(content=user_query)]
    
    try:
        result = agent.invoke({"messages": all_messages})
        answer = ""
        tools_used = []
        
        if "messages" in result:
            # 마지막 AI 메시지 찾기
            for msg in reversed(result["messages"]):
                if isinstance(msg, AIMessage) and msg.content:
                    answer = msg.content
                    break
            
            # 사용된 도구 추출
            for msg in result["messages"]:
                if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        if isinstance(tool_call, dict) and "name" in tool_call:
                            tools_used.append(tool_call["name"])
        
        if not answer:
            answer = "응답을 생성할 수 없습니다."
        
        new_history = (conversation_history or []) + [
            {"role": "user", "content": user_query},
            {"role": "ai", "content": answer},
        ]
        
        logger.info(f"✅ Agent 완료 (사용된 도구: {list(set(tools_used))})")
        return {
            "answer": answer,
            "conversation_history": new_history,
            "tools_used": list(set(tools_used))
        }
    
    except Exception as e:
        logger.error(f"❌ Agent 실행 오류: {e}", exc_info=True)
        fallback_answer = "죄송합니다. 일시적인 오류가 발생했습니다. 다시 시도해주세요. 🙏"
        new_history = (conversation_history or []) + [
            {"role": "user", "content": user_query},
            {"role": "ai", "content": fallback_answer},
        ]
        return {
            "answer": fallback_answer,
            "conversation_history": new_history,
            "tools_used": []
        }