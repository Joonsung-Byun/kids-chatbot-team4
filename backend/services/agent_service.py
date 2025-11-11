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
"""
개선된 LangChain Agent Service
3단계 의사결정 로직 명확히 구현:
1. 감정 표현 → 즉시 응답
2. 위치 정보 없음 → Multi-turn 질문
3. 위치 정보 있음 → Weather + RAG 호출
"""

import json
import re
from typing import List, Dict, Any, Optional

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration

from services.llm_service import get_llm_service
from services.rag_service import get_rag_service
from services.weather_service import get_weather
from utils.logger import logger


# ============================================================
# 1단계: 쿼리 분석 (감정/위치 감지)
# ============================================================

def analyze_user_query(query: str, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    사용자 쿼리를 3단계로 분류
    
    Returns:
        {
            "type": "emotion" | "need_location" | "ready",
            "location": str or None,
            "date": str or None,
            "has_emotion": bool
        }
    """
    query_lower = query.lower()
    
    # 1단계: 감정 표현 감지
    emotion_keywords = [
        "고마워", "감사", "좋아", "최고", "완벽", "훌륭",
        "thank", "thanks", "great", "awesome", "perfect"
    ]
    has_emotion = any(keyword in query_lower for keyword in emotion_keywords)
    
    # 2단계: 위치 정보 추출
    location = extract_location(query)
    
    # 이전 대화에서 위치 찾기
    if not location:
        location = extract_location_from_history(conversation_history)
    
    # 3단계: 날짜 정보 추출
    date_info = extract_date(query)
    
    # 쿼리 타입 결정
    if has_emotion and not any(k in query_lower for k in ["추천", "찾아", "어디", "뭐해", "갈만한"]):
        return {"type": "emotion", "location": None, "date": None, "has_emotion": True}
    
    if not location:
        return {"type": "need_location", "location": None, "date": date_info, "has_emotion": False}
    
    return {"type": "ready", "location": location, "date": date_info, "has_emotion": False}


def extract_location(text: str) -> Optional[str]:
    """텍스트에서 위치 정보 추출"""
    # 시/도 패턴
    cities = [
        "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
        "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"
    ]
    
    # 구/동 패턴
    districts = [
        "강남", "서초", "송파", "강동", "마포", "용산", "성동", "광진",
        "중구", "종로", "은평", "서대문", "동대문", "성북", "강북", "도봉",
        "노원", "동작", "관악", "금천", "구로", "영등포", "양천", "강서"
    ]
    
    for city in cities:
        if city in text:
            # 구까지 있는지 확인
            for district in districts:
                if district in text:
                    return f"{city} {district}"
            return city
    
    for district in districts:
        if district in text:
            return f"서울 {district}"  # 기본값으로 서울 추가
    
    return None


def extract_location_from_history(history: List[Dict[str, str]]) -> Optional[str]:
    """대화 히스토리에서 위치 정보 찾기"""
    for msg in reversed(history[-10:]):  # 최근 10개 메시지만
        if msg["role"] == "user":
            location = extract_location(msg["content"])
            if location:
                logger.info(f"📍 히스토리에서 위치 발견: {location}")
                return location
    return None


def extract_date(text: str) -> Optional[str]:
    """날짜 정보 추출"""
    date_keywords = {
        "오늘": "today",
        "내일": "tomorrow",
        "모레": "day_after_tomorrow",
        "이번주": "this_week",
        "다음주": "next_week",
        "주말": "weekend"
    }
    
    for keyword, value in date_keywords.items():
        if keyword in text:
            return value
    
    # YYYY-MM-DD 형식 찾기
    date_pattern = r'\d{4}-\d{2}-\d{2}'
    match = re.search(date_pattern, text)
    if match:
        return match.group()
    
    return None


# ============================================================
# 2단계: Tool 정의
# ============================================================

@tool
def weather_tool(location: str) -> str:
    """날씨 정보를 조회합니다."""
    try:
        logger.info(f"[WeatherTool] 호출: {location}")
        result = get_weather(location=location, target_date=None)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[WeatherTool] 오류: {e}")
        return json.dumps({"error": str(e)})


@tool
def rag_search_tool(query: str, location: Optional[str] = None) -> str:
    """문화/체육/교육 시설을 검색합니다."""
    try:
        logger.info(f"[RAGTool] 호출: query='{query}', location='{location}'")
        rag_service = get_rag_service()
        
        # 위치 기반 필터 구성
        filters = {}
        if location:
            # "서울 강남" → region_city="서울", region_gu="강남"
            parts = location.split()
            if len(parts) >= 2:
                filters["region_city"] = parts[0]
                filters["region_gu"] = parts[1]
            elif len(parts) == 1:
                filters["region_city"] = parts[0]
        
        results = rag_service.search_and_rerank(
            query=query, 
            top_k=5,
            filters=filters if filters else None
        )
        
        formatted = []
        for doc in results[:3]:
            metadata = doc.get("metadata", {})
            formatted.append({
                "name": metadata.get("facility_name", "Unknown"),
                "category": f"{metadata.get('category1', '')}-{metadata.get('category2', '')}",
                "location": f"{metadata.get('region_city', '')}/{metadata.get('region_gu', '')}",
                "price": metadata.get("price", "무료"),
                "in_out": metadata.get("in_out", ""),
                "target_age": metadata.get("target_age", "")
            })
        return json.dumps(formatted, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[RAGTool] 오류: {e}")
        return json.dumps({"error": str(e)})


# ============================================================
# 3단계: Mock LLM (CPU 환경용)
# ============================================================

class MockChatModel(BaseChatModel):
    """CPU 환경용 Mock ChatModel"""
    
    model_name: str = "mock-chat-model"
    
    def _generate(self, messages: List[BaseMessage], stop=None, **kwargs) -> ChatResult:
        user_input = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_input = msg.content
                break
        
        # 쿼리 분석
        analysis = analyze_user_query(user_input, [])
        
        if analysis["type"] == "emotion":
            response_text = "천만에요! 😊 더 도움이 필요하시면 언제든 말씀해주세요!"
        elif analysis["type"] == "need_location":
            response_text = "어느 지역을 생각하고 계신가요? 🗺️ (서울, 부산, 대구 등)"
        else:
            response_text = f"Mock 모드입니다. 위치({analysis['location']})와 날짜({analysis['date']})를 확인했습니다."
        
        message = AIMessage(content=response_text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])
    
    @property
    def _llm_type(self) -> str:
        return "mock-chat-model"
    
    def bind_tools(self, tools, **kwargs):
        return self


# ============================================================
# 4단계: Agent 실행 함수 (3단계 로직 구현)
# ============================================================

def run_agent(
    user_query: str, 
    conversation_id: str, 
    conversation_history: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    개선된 Agent 실행 로직
    
    1단계: 쿼리 분석
    2단계: 타입별 처리
        - emotion: 즉시 응답
        - need_location: 위치 질문
        - ready: Weather + RAG 호출 후 LLM 답변 생성
    """
    logger.info(f"🚀 Agent 실행: '{user_query}'")
    
    history = conversation_history or []
    
    # 1단계: 쿼리 분석
    analysis = analyze_user_query(user_query, history)
    logger.info(f"📊 쿼리 분석 결과: {analysis}")
    
    # 2단계: 타입별 처리
    if analysis["type"] == "emotion":
        # 감정 표현 → 즉시 응답
        answer = generate_emotion_response(user_query)
        tools_used = []
    
    elif analysis["type"] == "need_location":
        # 위치 정보 없음 → 질문
        answer = "어느 지역을 생각하고 계신가요? 🗺️\n(예: 서울 강남, 부산 해운대)"
        tools_used = []
    
    else:  # type == "ready"
        # 위치 정보 있음 → Weather + RAG 실행
        location = analysis["location"]
        date_info = analysis["date"]
        
        # Tool 실행
        weather_result = call_weather_tool(location, date_info)
        rag_result = call_rag_tool(user_query, location)
        
        # LLM으로 최종 답변 생성
        answer = generate_final_answer(
            query=user_query,
            location=location,
            weather=weather_result,
            facilities=rag_result
        )
        tools_used = ["weather_tool", "rag_search_tool"]
    
    # 히스토리 업데이트
    new_history = history + [
        {"role": "user", "content": user_query},
        {"role": "ai", "content": answer}
    ]
    
    logger.info(f"✅ Agent 완료 (도구: {tools_used})")
    
    return {
        "answer": answer,
        "conversation_history": new_history,
        "tools_used": tools_used,
        "query_analysis": analysis
    }


# ============================================================
# 헬퍼 함수들
# ============================================================

def generate_emotion_response(query: str) -> str:
    """감정 표현에 대한 응답"""
    responses = {
        "고마": "천만에요! 😊 더 궁금한 점이 있으시면 언제든 말씀해주세요!",
        "감사": "도움이 되었다니 기쁩니다! 🎉 또 필요하신 게 있으시면 말씀해주세요!",
        "좋아": "마음에 드셨다니 정말 기쁩니다! 😄 즐거운 시간 보내세요!",
        "최고": "감사합니다! 😊 항상 최선을 다하겠습니다!",
        "완벽": "완벽하다는 말씀 감사합니다! ✨ 즐거운 시간 되세요!"
    }
    
    for keyword, response in responses.items():
        if keyword in query:
            return response
    
    return "말씀해주셔서 감사합니다! 😊 더 도와드릴 것이 있을까요?"


def call_weather_tool(location: str, date_info: Optional[str]) -> Dict[str, Any]:
    """날씨 도구 호출"""
    try:
        result = get_weather(location=location, target_date=date_info)
        logger.info(f"🌤️ 날씨 조회 완료: {location}")
        return result
    except Exception as e:
        logger.error(f"❌ 날씨 조회 실패: {e}")
        return {"location": location, "status": "sunny", "error": str(e)}


def call_rag_tool(query: str, location: str) -> List[Dict[str, Any]]:
    """RAG 도구 호출"""
    try:
        rag_service = get_rag_service()
        
        # 필터 구성
        filters = {}
        parts = location.split()
        if len(parts) >= 2:
            filters["region_city"] = parts[0]
            filters["region_gu"] = parts[1]
        elif len(parts) == 1:
            filters["region_city"] = parts[0]
        
        results = rag_service.search_and_rerank(
            query=query,
            top_k=5,
            filters=filters if filters else None
        )
        
        logger.info(f"🔍 RAG 검색 완료: {len(results)}개 시설")
        return results
    except Exception as e:
        logger.error(f"❌ RAG 검색 실패: {e}")
        return []


def generate_final_answer(
    query: str,
    location: str,
    weather: Dict[str, Any],
    facilities: List[Dict[str, Any]]
) -> str:
    """최종 답변 생성"""
    llm_service = get_llm_service()
    
    # GPU 환경: 실제 LLM 사용
    if llm_service._use_gpu and llm_service._model:
        try:
            # 컨텍스트 구성
            context = f"위치: {location}\n"
            context += f"날씨: {weather.get('status', '알 수 없음')}\n\n"
            context += "추천 시설:\n"
            
            for i, doc in enumerate(facilities[:3], 1):
                meta = doc.get("metadata", {})
                context += f"{i}. {meta.get('facility_name', 'N/A')}\n"
                context += f"   - 위치: {meta.get('region_gu', '')}\n"
                context += f"   - 분류: {meta.get('category1', '')}\n"
                context += f"   - 가격: {meta.get('price', '무료')}\n\n"
            
            # LLM 프롬프트
            prompt = f"""아래 정보를 바탕으로 사용자 질문에 친절하게 답변해주세요.

{context}

사용자 질문: {query}

답변 작성 가이드:
- 날씨 정보를 먼저 언급
- 추천 시설 3개를 구체적으로 소개
- 이모지 사용 (🎨, 🏃‍♂️, 📍)
- 따뜻하고 친근한 톤

답변:"""
            
            # 토크나이징 및 생성
            from transformers import GenerationConfig
            inputs = llm_service._tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=1024
            ).to(llm_service._model.device)
            
            gen_cfg = GenerationConfig(
                temperature=0.7,
                max_new_tokens=300,
                top_p=0.9
            )
            
            import torch
            with torch.no_grad():
                out = llm_service._model.generate(**inputs, generation_config=gen_cfg)
            
            answer = llm_service._tokenizer.decode(out[0], skip_special_tokens=True)
            answer = answer.split("답변:")[-1].strip()
            
            return answer
        
        except Exception as e:
            logger.error(f"❌ LLM 생성 실패: {e}")
            # fallback to mock
    
    # Mock 모드 답변
    weather_status = weather.get("status", "맑음")
    weather_emoji = {"sunny": "☀️", "rainy": "🌧️", "cloudy": "☁️"}.get(weather_status, "🌤️")
    
    answer = f"{weather_emoji} {location} 날씨는 {weather_status}이에요!\n\n"
    answer += "추천 장소를 찾았어요! 🎉\n\n"
    
    for i, doc in enumerate(facilities[:3], 1):
        meta = doc.get("metadata", {})
        name = meta.get("facility_name", "Unknown")
        category = meta.get("category1", "시설")
        gu = meta.get("region_gu", "")
        price = meta.get("price", "무료")
        
        answer += f"{i}. 📍 **{name}** ({gu})\n"
        answer += f"   분류: {category} | 가격: {price}\n\n"
    
    answer += "즐거운 시간 보내세요! 😊"
    
    return answer


# ============================================================
# get_tools 함수 (호환성)
# ============================================================

def get_tools():
    """사용 가능한 도구 목록"""
    return [weather_tool, rag_search_tool]


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