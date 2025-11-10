# services/agent_service.py
"""
LangGraph Agent Service

LangGraph를 사용한 멀티턴 대화 관리
- Supervisor: 룰베이스로 도구 선택
- Tools: Weather, RAG, Map
- Answer Generation: Qwen2.5-7B-Instruct
"""

from typing import Literal
from langgraph.graph import StateGraph, END

from models.chat_schema import ChatState
from services.supervisor_service import get_supervisor_service
from services.llm_service import get_llm_service
from services.rag_service import get_rag_service
from services.weather_service import get_weather
from services.map_service import get_map_markers
from utils.logger import logger


# ============================================================
# LangGraph Nodes
# ============================================================

def supervisor_node(state: ChatState) -> ChatState:
    """
    Supervisor Node: 쿼리 분석 및 도구 선택
    
    룰베이스로 다음을 수행:
    - 위치 추출
    - 날짜 추출
    - 필요한 도구 선택 (weather, rag, map)
    - 위치 없으면 needs_location=True
    """
    logger.info(f"[Supervisor] 분석 시작: '{state['user_query']}'")
    
    # 이전 대화에서 위치 정보 가져오기
    current_location = state.get("location")
    
    # 대화 컨텍스트 (최근 5개 메시지)
    conversation_context = state["messages"][-5:] if state["messages"] else []
    
    # Supervisor 분석
    supervisor = get_supervisor_service()
    result = supervisor.analyze_query(
        user_query=state["user_query"],
        conversation_context=conversation_context,
        current_location=current_location
    )
    
    # 상태 업데이트
    state["location"] = result.get("location")
    state["date"] = result.get("date")
    state["selected_tools"] = result.get("selected_tools", [])
    state["needs_location"] = result.get("needs_location", False)
    
    logger.info(f"[Supervisor] 결과: location={state['location']}, tools={state['selected_tools']}, needs_location={state['needs_location']}")
    
    return state


def check_location_node(state: ChatState) -> ChatState:
    """
    위치 확인 Node
    
    위치가 필요한데 없으면 역질문 생성
    """
    if state["needs_location"]:
        state["final_answer"] = "어느 지역을 생각하고 계신가요? 🗺️"
        logger.info("[CheckLocation] 위치 질문 생성")
    
    return state


def weather_tool_node(state: ChatState) -> ChatState:
    """
    Weather Tool Node
    
    날씨 API 호출 (선택된 경우에만)
    """
    if "weather" not in state["selected_tools"]:
        return state
    
    try:
        logger.info(f"[WeatherTool] 날씨 조회: {state['location']}")
        
        weather_info = get_weather(
            location=state["location"],
            target_date=state.get("date")
        )
        
        state["weather_results"] = weather_info
        logger.info(f"[WeatherTool] 결과: {weather_info}")
        
    except Exception as e:
        logger.error(f"[WeatherTool] 오류: {e}")
        state["weather_results"] = None
    
    return state


def rag_tool_node(state: ChatState) -> ChatState:
    """
    RAG Tool Node
    
    벡터 검색으로 시설 찾기
    """
    if "rag" not in state["selected_tools"]:
        return state
    
    try:
        logger.info(f"[RAGTool] 검색: {state['user_query']}")
        
        # 메타데이터 필터 구성
        filters = {}
        if state.get("location"):
            # 위치 기반 필터링 (필요시 추가)
            pass
        
        # RAG 검색
        rag_service = get_rag_service()
        results = rag_service.search_and_rerank(
            query=state["user_query"],
            top_k=5,
            filters=filters or None
        )
        
        state["rag_results"] = results
        logger.info(f"[RAGTool] 결과: {len(results)}개 시설")
        
    except Exception as e:
        logger.error(f"[RAGTool] 오류: {e}")
        state["rag_results"] = []
    
    return state


def map_tool_node(state: ChatState) -> ChatState:
    """
    Map Tool Node
    
    카카오맵 데이터 생성 (RAG 결과 기반)
    """
    if "map" not in state["selected_tools"]:
        return state
    
    try:
        # RAG 결과에서 좌표 추출
        facilities = state.get("rag_results", [])
        
        if not facilities:
            logger.warning("[MapTool] RAG 결과 없음 - 지도 생성 스킵")
            return state
        
        logger.info(f"[MapTool] 지도 생성: {len(facilities)}개 시설")
        
        # TODO: 실제 카카오맵 API 연동 시 사용
        # map_data = get_map_markers(state["user_query"])
        # state["map_results"] = map_data
        
        # 임시: RAG 결과를 지도 형식으로 변환
        state["map_results"] = {
            "center": {"lat": 37.5665, "lng": 126.9780},  # 서울 기본
            "markers": [
                {
                    "name": f["metadata"].get("facility_name", "Unknown"),
                    "lat": 37.5665 + i * 0.01,  # Mock 좌표
                    "lng": 126.9780 + i * 0.01
                }
                for i, f in enumerate(facilities[:5])
            ]
        }
        
    except Exception as e:
        logger.error(f"[MapTool] 오류: {e}")
        state["map_results"] = None
    
    return state


def generate_answer_node(state: ChatState) -> ChatState:
    """
    Answer Generation Node
    
    Qwen2.5-7B-Instruct로 최종 답변 생성
    """
    # 1. 위치 질문이 이미 생성된 경우
    if state.get("final_answer"):
        logger.info("[GenerateAnswer] 위치 질문 사용")
        return state
    
    # 2. 도구 없음 (일반 대화)
    if not state["selected_tools"]:
        logger.info("[GenerateAnswer] 일반 대화 응답")
        llm_service = get_llm_service()
        
        # 간단한 Mock 응답 (GPU 환경에서는 실제 LLM 사용)
        state["final_answer"] = llm_service._mock_answer(
            state["user_query"],
            []
        )
        return state
    
    # 3. Tool 결과 기반 응답 생성
    try:
        logger.info("[GenerateAnswer] Tool 결과 기반 응답 생성")
        
        llm_service = get_llm_service()
        rag_results = state.get("rag_results", [])
        
        # 컨텍스트 문서 포맷 변환
        context_docs = []
        for doc in rag_results:
            context_docs.append({
                "content": doc.get("content", ""),
                "metadata": doc.get("metadata", {})
            })
        
        # LLM 답변 생성
        answer = llm_service.generate_answer(
            query=state["user_query"],
            context_docs=context_docs
        )
        
        # 날씨 정보 추가 (있으면)
        if state.get("weather_results"):
            weather = state["weather_results"]
            answer = f"🌤️ 날씨: {weather}\n\n{answer}"
        
        state["final_answer"] = answer
        logger.info(f"[GenerateAnswer] 완료: {len(answer)}자")
        
    except Exception as e:
        logger.error(f"[GenerateAnswer] 오류: {e}")
        state["final_answer"] = "죄송합니다. 응답 생성 중 오류가 발생했습니다."
    
    return state


# ============================================================
# Routing Functions
# ============================================================

def should_ask_location(state: ChatState) -> Literal["ask_location", "execute_tools"]:
    """
    조건부 라우팅: 위치 질문 vs 도구 실행
    """
    if state["needs_location"]:
        return "ask_location"
    return "execute_tools"


def should_run_weather(state: ChatState) -> Literal["weather", "rag"]:
    """
    조건부 라우팅: 날씨 도구 실행 여부
    """
    if "weather" in state["selected_tools"]:
        return "weather"
    return "rag"


def should_run_rag(state: ChatState) -> Literal["rag", "map"]:
    """
    조건부 라우팅: RAG 도구 실행 여부
    """
    if "rag" in state["selected_tools"]:
        return "rag"
    return "map"


def should_run_map(state: ChatState) -> Literal["map", "generate"]:
    """
    조건부 라우팅: Map 도구 실행 여부
    """
    if "map" in state["selected_tools"]:
        return "map"
    return "generate"


# ============================================================
# Graph Creation
# ============================================================

def create_agent_graph():
    """
    LangGraph Agent 생성
    
    워크플로우:
    START → Supervisor → [위치 질문 OR 도구 실행] → 답변 생성 → END
    """
    logger.info("🔧 LangGraph Agent 생성 중...")
    
    workflow = StateGraph(ChatState)
    
    # Nodes 추가
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("check_location", check_location_node)
    workflow.add_node("weather_tool", weather_tool_node)
    workflow.add_node("rag_tool", rag_tool_node)
    workflow.add_node("map_tool", map_tool_node)
    workflow.add_node("generate_answer", generate_answer_node)
    
    # Entry point
    workflow.set_entry_point("supervisor")
    
    # 조건부 라우팅: Supervisor → 위치 질문 OR 도구 실행
    workflow.add_conditional_edges(
        "supervisor",
        should_ask_location,
        {
            "ask_location": "check_location",
            "execute_tools": "weather_tool"
        }
    )
    
    # 위치 질문 → 종료
    workflow.add_edge("check_location", END)
    
    # 도구 실행 체인 (조건부)
    workflow.add_conditional_edges(
        "weather_tool",
        should_run_rag,
        {
            "rag": "rag_tool",
            "map": "map_tool"
        }
    )
    
    workflow.add_conditional_edges(
        "rag_tool",
        should_run_map,
        {
            "map": "map_tool",
            "generate": "generate_answer"
        }
    )
    
    workflow.add_edge("map_tool", "generate_answer")
    workflow.add_edge("generate_answer", END)
    
    logger.info("✅ LangGraph Agent 생성 완료")
    
    return workflow.compile()


# ============================================================
# Main Chat Function
# ============================================================

def run_agent(
    user_query: str,
    conversation_id: str,
    conversation_history: list = None
) -> dict:
    """
    Agent 실행
    
    Args:
        user_query: 사용자 입력
        conversation_id: 대화 세션 ID
        conversation_history: 이전 대화 히스토리
    
    Returns:
        {
            "answer": str,
            "conversation_history": list,
            "location": str,
            "tools_used": list
        }
    """
    logger.info(f"🚀 Agent 실행: conversation_id={conversation_id}")
    
    # Graph 생성
    graph = create_agent_graph()
    
    # 초기 상태
    initial_state = ChatState(
        messages=conversation_history or [],
        conversation_id=conversation_id,
        user_query=user_query,
        location=None,
        date=None,
        selected_tools=[],
        needs_location=False,
        weather_results=None,
        rag_results=None,
        map_results=None,
        final_answer=""
    )
    
    # 이전 히스토리에서 위치 추출 시도
    if conversation_history:
        supervisor = get_supervisor_service()
        for msg in reversed(conversation_history):
            if msg["role"] == "user":
                location = supervisor._extract_location(msg["content"])
                if location:
                    initial_state["location"] = location
                    logger.info(f"[Agent] 히스토리에서 위치 추출: {location}")
                    break
    
    # 사용자 메시지 추가
    initial_state["messages"].append({"role": "user", "content": user_query})
    
    # Graph 실행
    result = graph.invoke(initial_state)
    
    # AI 응답 추가
    if result["final_answer"]:
        result["messages"].append({"role": "ai", "content": result["final_answer"]})
    
    logger.info(f"✅ Agent 완료: tools={result['selected_tools']}")
    
    return {
        "answer": result["final_answer"],
        "conversation_history": result["messages"],
        "location": result.get("location"),
        "tools_used": result["selected_tools"],
        "map_data": result.get("map_results")
    }
    
    
    