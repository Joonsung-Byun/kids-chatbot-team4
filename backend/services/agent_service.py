"""
LangChain Agent Service (Simplified 3-Step Logic)

3단계 의사결정 로직:
1. 감정 표현 → 즉시 응답
2. 위치 정보 없음 → Multi-turn 질문
3. 위치 정보 있음 → Weather + RAG 호출
4. 지도 요청 → 히스토리에서 RAG 결과 추출 후 지도 생성
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple

from langchain_core.tools import tool

from services.llm_service import get_llm_service
from services.rag_service import get_rag_service
from services.weather_service import get_weather
from services.map_service import get_map_markers
from data.location import KMA_LOCATION_CODES, DONG_TO_CITY, LANDMARK_TO_CITY, UNIVERSITY_TO_CITY, LOCATION_MAP
from utils.logger import logger


# ============================================================
# Tool 정의
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
def rag_search_tool(query: str, location: Optional[str] = None) -> str:
    """문화/체육/교육 시설을 검색합니다. 입력: 검색 쿼리와 위치 (예: '놀이터', '서울 강남')"""
    try:
        logger.info(f"[RAGTool] 호출: query='{query}', location='{location}'")
        rag_service = get_rag_service()
        
        # 필터 구성
        filters = None
        if location:
            parts = location.split()
            if len(parts) >= 2:
                filters = {
                    "$and": [
                        {"ctprvn_nm": {"$eq": parts[0]}},
                        {"signgu_nm": {"$eq": parts[1]}}
                    ]
                }
            elif len(parts) == 1:
                filters = {"ctprvn_nm": {"$eq": parts[0]}}
        
        results = rag_service.search_and_rerank(
            query=query,
            top_k=5,
            filters=filters
        )
        
        formatted = []
        for doc in results[:3]:
            metadata = doc.get("metadata", {})
            formatted.append({
                "name": metadata.get("facility_name", "Unknown"),
                "category": f"{metadata.get('category1', '')}-{metadata.get('category2', '')}",
                "location": f"{metadata.get('ctprvn_nm', '')}/{metadata.get('signgu_nm', '')}",
                "price": metadata.get("price", "무료"),
                "in_out": metadata.get("in_out", ""),
                "target_age": metadata.get("target_age", "")
            })
        return json.dumps(formatted, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[RAGTool] 오류: {e}")
        return json.dumps({"error": str(e)})


@tool
def map_tool(markers_json: str) -> str:
    """
    지도를 생성합니다. 
    입력: JSON 형식의 마커 리스트 
    예: '[{"name": "공원", "lat": 37.5, "lng": 127.0}, ...]'
    """
    try:
        logger.info(f"[MapTool] 호출")
        result = get_map_markers(markers_json)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[MapTool] 오류: {e}")
        return json.dumps({"error": str(e)})


def get_tools():
    """사용 가능한 도구 목록 반환"""
    return [weather_tool, rag_search_tool, map_tool]


# ============================================================
# 1단계: 쿼리 분석 (감정/위치 감지)
# ============================================================

def analyze_user_query(query: str, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    사용자 쿼리를 4가지 타입으로 분류
    
    Returns:
        {
            "type": "emotion" | "need_location" | "ready" | "show_map",
            "location": str or None,
            "date": str or None,
            "has_emotion": bool
        }
    """
    query_lower = query.lower()
    
    # 0단계: 지도 요청 감지
    map_keywords = ["지도", "맵", "map", "위치", "보여줘", "보여주세요", "표시"]
    if any(keyword in query_lower for keyword in map_keywords):
        if has_rag_results_in_history(conversation_history):
            return {"type": "show_map", "location": None, "date": None, "has_emotion": False}
    
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


def has_rag_results_in_history(history: List[Dict[str, str]]) -> bool:
    """히스토리에 RAG 결과가 있는지 확인"""
    for msg in reversed(history[-10:]):
        if msg.get("role") == "system":
            try:
                content = json.loads(msg["content"])
                if "rag_results" in content and content["rag_results"]:
                    return True
            except:
                pass
    return False


def get_rag_results_from_history(history: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """히스토리에서 가장 최근 RAG 결과 추출"""
    for msg in reversed(history[-10:]):
        if msg.get("role") == "system":
            try:
                content = json.loads(msg["content"])
                if "rag_results" in content:
                    return content["rag_results"]
            except:
                pass
    return []


def extract_location(text: str) -> Optional[str]:
    """
    사용자가 입력한 텍스트에서 도시/구/동/명소 등 위치를 최대한 정밀하게 인식해
    대표 도시명(예: 서울, 부산, 제주 등)으로 반환.
    """

    text = text.strip().replace(" ", "")  # 공백 제거 (예: "한 남 동" → "한남동")

    # 1️⃣ KMA 지역코드 기반: 도시/군/구 단위 직접 매칭
    for city in KMA_LOCATION_CODES.keys():
        if city in text:
            return city

    # 2️⃣ DONG_TO_CITY: 동(洞) → 도시 매핑
    for dong, city in DONG_TO_CITY.items():
        if dong in text:
            return city

    # 3️⃣ LANDMARK_TO_CITY: 명소/관광지 → 도시 매핑
    for landmark, city in LANDMARK_TO_CITY.items():
        if landmark in text:
            return city

    # 4️⃣ UNIVERSITY_TO_CITY: 대학교 → 도시 매핑
    for univ, city in UNIVERSITY_TO_CITY.items():
        if univ in text:
            return city

    # 5️⃣ LOCATION_MAP: 추가 확장명소/상권 등
    for city, names in LOCATION_MAP.items():
        for name in names:
            if name in text:
                return city

    # 6️⃣ 보정 규칙 (자주 등장하는 표현)
    keyword_city_map = {
        "한강": "서울", "청계천": "서울", "남산": "서울", "광안리": "부산",
        "감천문화마을": "부산", "남이섬": "가평", "설악산": "속초", "에버랜드": "용인",
        "롯데월드": "서울", "경주월드": "경주", "전주한옥마을": "전주",
        "한라산": "제주", "성심당": "대전"
    }
    for kw, city in keyword_city_map.items():
        if kw in text:
            return city

    # 7️⃣ 패턴기반 추론 (예: ~카페거리, ~해수욕장, ~시장)
    if "카페거리" in text:
        if "성수" in text or "홍대" in text or "연남" in text:
            return "서울"
        if "애월" in text:
            return "제주"
        if "온천천" in text:
            return "부산"
    if "해수욕장" in text:
        if "광안" in text or "해운대" in text or "송정" in text:
            return "부산"
        if "함덕" in text or "협재" in text:
            return "제주"
        if "낙산" in text or "경포" in text:
            return "강릉"
        if "대천" in text:
            return "보령"
    if "시장" in text:
        if "남대문" in text or "광장" in text or "통인" in text:
            return "서울"
        if "서문" in text:
            return "대구"
        if "자갈치" in text or "국제시장" in text:
            return "부산"

    return None


def extract_location_from_history(history: List[Dict[str, str]]) -> Optional[str]:
    """대화 히스토리에서 위치 정보 찾기"""
    for msg in reversed(history[-10:]):
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
    
    date_pattern = r'\d{4}-\d{2}-\d{2}'
    match = re.search(date_pattern, text)
    if match:
        return match.group()
    
    return None


# ============================================================
# 2단계: Agent 실행 함수 (4단계 로직 구현)
# ============================================================

def run_agent(
    user_query: str, 
    conversation_id: str, 
    conversation_history: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    개선된 Agent 실행 로직
    
    Returns:
        {
            "answer": str,
            "conversation_history": List[Dict],
            "tools_used": List[str],
            "query_analysis": Dict,
            "response_type": str,  # "text" or "map"
            "map_data": Dict (optional),
            "map_link": str (optional)
        }
    """
    logger.info(f"🚀 Agent 실행: '{user_query}'")
    
    history = conversation_history or []
    
    # 1단계: 쿼리 분석
    analysis = analyze_user_query(user_query, history)
    logger.info(f"📊 쿼리 분석 결과: {analysis}")
    
    # 초기화
    answer = ""
    tools_used = []
    map_data = None
    map_link = None
    rag_results = []
    response_type = "text"
    
    # 2단계: 타입별 처리
    if analysis["type"] == "emotion":
        answer = _generate_emotion_response(user_query)
        response_type = "text"
    
    elif analysis["type"] == "show_map":
        # 지도 요청 → map 응답 (4개 값 반환)
        result_tuple = _handle_map_request(history)
        answer, tools_used, map_data, map_link = result_tuple
        response_type = "map" if map_data else "text"
    
    elif analysis["type"] == "need_location":
        answer = "어느 지역을 생각하고 계신가요? 🗺️\n(예: 서울 강남, 부산 해운대)"
        response_type = "text"
    
    else:  # type == "ready"
        answer, tools_used, rag_results = _handle_location_query(
            user_query, 
            analysis["location"], 
            analysis["date"]
        )
        response_type = "text"
    
    # 히스토리 업데이트
    new_history = history + [
        {"role": "user", "content": user_query},
        {"role": "ai", "content": answer}
    ]
    
    # RAG 결과를 system 메시지로 저장 (지도 요청 대비)
    if analysis["type"] == "ready" and rag_results:
        new_history = _append_rag_metadata(new_history, rag_results)
    
    logger.info(f"✅ Agent 완료 (도구: {tools_used}, 응답 타입: {response_type})")
    
    # 결과 구성
    result = {
        "answer": answer,
        "conversation_history": new_history,
        "tools_used": tools_used,
        "query_analysis": analysis,
        "response_type": response_type
    }
    
    # 지도 데이터가 있으면 추가
    if response_type == "map" and map_data:
        result["map_data"] = map_data
        result["map_link"] = map_link
    
    return result


# ============================================================
# 헬퍼 함수들
# ============================================================

def _generate_emotion_response(query: str) -> str:
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


def _handle_map_request(
    history: List[Dict[str, str]]
) -> Tuple[str, List[str], Optional[Dict[str, Any]], Optional[str]]:
    """
    지도 요청 처리
    
    Returns:
        (answer, tools_used, map_data, map_link)
    """
    rag_results = get_rag_results_from_history(history)
    
    if not rag_results:
        return (
            "먼저 장소를 추천받아야 지도를 볼 수 있어요! 😊\n어떤 곳을 찾고 계신가요?", 
            [], 
            None,
            None
        )
    
    # 좌표 정보 추출 및 마커 데이터 구성
    markers = []
    for result in rag_results:
        meta = result.get("metadata", {})
        
        lat = meta.get("latitude") or meta.get("lat")
        lng = meta.get("longitude") or meta.get("lon") or meta.get("lng")
        name = meta.get("facility_name", "Unknown")
        
        if lat and lng:
            try:
                markers.append({
                    "name": name,
                    "lat": float(lat),
                    "lng": float(lng),
                    "desc": meta.get("description", "")
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"⚠️ 좌표 변환 실패: {name} - lat={lat}, lng={lng} ({e})")
                continue
    
    if not markers:
        return (
            "죄송해요, 좌표 정보가 없어서 지도를 표시할 수 없어요. 😢", 
            [], 
            None,
            None
        )
    
    # get_map_markers 호출
    try:
        map_result = get_map_markers(json.dumps(markers, ensure_ascii=False))
        
        answer = f"🗺️ 지도 정보를 불러왔어요! {len(markers)}개의 위치를 지도에 표시했습니다.\n\n"
        answer += "📍 표시된 장소:\n"
        
        for i, marker in enumerate(markers[:5], 1):
            answer += f"{i}. {marker['name']}\n"
        
        map_data = {
            "center": map_result["center"],
            "markers": map_result["markers"]
        }
        
        map_link = map_result.get("link", "")
        
        logger.info(f"🗺️ 지도 생성 완료: {len(markers)}개 마커")
        
        return answer, ["map_tool"], map_data, map_link
    
    except Exception as e:
        logger.error(f"❌ 지도 생성 실패: {e}")
        return (
            "죄송해요, 지도를 생성하는 중에 오류가 발생했습니다. 😢",
            [],
            None,
            None
        )


def _handle_location_query(
    query: str, 
    location: str, 
    date_info: Optional[str]
) -> Tuple[str, List[str], List[Dict[str, Any]]]:
    """
    위치 정보가 있는 쿼리 처리
    
    Returns:
        (answer, tools_used, rag_results)
    """
    weather_result = _call_weather_tool(location, date_info)
    rag_results = _call_rag_tool(query, location)
    
    if not rag_results:
        logger.warning("⚠️ RAG 결과 없음 - Mock 데이터 사용")
        rag_results = _get_mock_rag_results(location)
    
    answer = _generate_final_answer(
        query=query,
        location=location,
        weather=weather_result,
        facilities=rag_results
    )
    
    return answer, ["weather_tool", "rag_search_tool"], rag_results


def _call_weather_tool(location: str, date_info: Optional[str]) -> Dict[str, Any]:
    """날씨 도구 호출"""
    try:
        result = get_weather(location=location, target_date=date_info)
        logger.info(f"🌤️ 날씨 조회 완료: {location}")
        return result
    except Exception as e:
        logger.error(f"❌ 날씨 조회 실패: {e}")
        return {
            "location": location, 
            "status": "clear", 
            "description": "맑음",
            "temp": 15.0,
            "error": str(e)
        }


def _call_rag_tool(query: str, location: str) -> List[Dict[str, Any]]:
    """RAG 도구 호출"""
    try:
        rag_service = get_rag_service()
        
        filters = None
        parts = location.split()
        
        if len(parts) >= 2:
            filters = {
                "$and": [
                    {"ctprvn_nm": {"$eq": parts[0]}},
                    {"signgu_nm": {"$eq": parts[1]}}
                ]
            }
            logger.info(f"🔍 필터 적용: {parts[0]} + {parts[1]}")
        elif len(parts) == 1:
            filters = {"ctprvn_nm": {"$eq": parts[0]}}
            logger.info(f"🔍 필터 적용: {parts[0]}")
        
        results = rag_service.search_and_rerank(
            query=query,
            top_k=5,
            filters=filters
        )
        
        logger.info(f"🔍 RAG 검색 완료: {len(results)}개 시설")
        return results
    except Exception as e:
        logger.error(f"❌ RAG 검색 실패: {e}")
        return []


def _get_mock_rag_results(location: str) -> List[Dict[str, Any]]:
    """Mock RAG 결과 생성"""
    parts = location.split()
    city = parts[0] if parts else "서울"
    district = parts[1] if len(parts) > 1 else "강남구"
    
    return [
        {
            "metadata": {
                "facility_name": f"{district} 어린이공원",
                "ctprvn_nm": city,
                "signgu_nm": district,
                "category1": "문화/체육",
                "category2": "공원",
                "price": "무료",
                "in_out": "실외",
                "target_age": "전체",
                "lat": 37.4979,
                "lon": 127.0276
            }
        },
        {
            "metadata": {
                "facility_name": f"{district} 키즈카페",
                "ctprvn_nm": city,
                "signgu_nm": district,
                "category1": "문화/체육",
                "category2": "실내놀이터",
                "price": "15,000원",
                "in_out": "실내",
                "target_age": "3-10세",
                "lat": 37.5012,
                "lon": 127.0396
            }
        },
        {
            "metadata": {
                "facility_name": f"{district} 도서관",
                "ctprvn_nm": city,
                "signgu_nm": district,
                "category1": "교육",
                "category2": "도서관",
                "price": "무료",
                "in_out": "실내",
                "target_age": "전체",
                "lat": 37.5172,
                "lon": 127.0473
            }
        }
    ]


def _generate_final_answer(
    query: str,
    location: str,
    weather: Dict[str, Any],
    facilities: List[Dict[str, Any]]
) -> str:
    """최종 답변 생성"""
    llm_service = get_llm_service()
    
    if llm_service._use_gpu and llm_service._model:
        try:
            return _generate_with_llm(query, location, weather, facilities, llm_service)
        except Exception as e:
            logger.error(f"❌ LLM 생성 실패: {e}")
    
    return _generate_mock_answer(location, weather, facilities)


def _generate_with_llm(query, location, weather, facilities, llm_service) -> str:
    """실제 LLM으로 답변 생성"""
    context = f"위치: {location}\n"
    context += f"날씨: {weather.get('description', '알 수 없음')} ({weather.get('temp', 0)}°C)\n\n"
    context += "추천 시설:\n"
    
    for i, doc in enumerate(facilities[:3], 1):
        meta = doc.get("metadata", {})
        context += f"{i}. {meta.get('facility_name', 'N/A')}\n"
        context += f"   - 위치: {meta.get('signgu_nm', '')}\n"
        context += f"   - 분류: {meta.get('category1', '')}\n"
        context += f"   - 가격: {meta.get('price', '무료')}\n\n"
    
    prompt = f"""아래 정보를 바탕으로 사용자 질문에 친절하게 답변해주세요.

{context}

사용자 질문: {query}

답변 작성 가이드:
- 날씨 정보를 먼저 언급
- 추천 시설 3개를 구체적으로 소개
- 이모지 사용 (🎨, 🏃‍♂️, 📍)
- 따뜻하고 친근한 톤

답변:"""
    
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


def _generate_mock_answer(location: str, weather: Dict[str, Any], facilities: List[Dict[str, Any]]) -> str:
    """Mock 답변 생성"""
    weather_desc = weather.get("description", "맑음")
    temp = weather.get("temp", 15)
    weather_emoji = {"맑음": "☀️", "비": "🌧️", "흐림": "☁️", "눈": "❄️"}.get(weather_desc, "🌤️")
    
    answer = f"{weather_emoji} {location} 날씨는 {weather_desc}이고, 기온은 {temp}°C예요!\n\n"
    answer += "추천 장소를 찾았어요! 🎉\n\n"
    
    if not facilities:
        answer += "죄송해요, 검색 결과가 없습니다. 다른 지역을 시도해보세요! 😢"
        return answer
    
    for i, doc in enumerate(facilities[:3], 1):
        meta = doc.get("metadata", {})
        name = meta.get("facility_name", "Unknown")
        category = meta.get("category1", "시설")
        gu = meta.get("signgu_nm", "")
        price = meta.get("price", "무료")
        
        answer += f"{i}. 📍 **{name}** ({gu})\n"
        answer += f"   분류: {category} | 가격: {price}\n\n"
    
    answer += "즐거운 시간 보내세요! 😊"
    
    return answer


def _append_rag_metadata(
    history: List[Dict[str, str]], 
    rag_results: List[Dict[str, Any]]
) -> List[Dict[str, str]]:
    """RAG 결과를 system 메시지로 추가"""
    try:
        rag_metadata = []
        for doc in rag_results[:5]:
            meta = doc.get("metadata", {})
            
            lat = meta.get("lat") or meta.get("latitude")
            lon = meta.get("lon") or meta.get("lng") or meta.get("longitude")
            
            rag_metadata.append({
                "metadata": {
                    "facility_name": meta.get("facility_name", "Unknown"),
                    "latitude": lat,
                    "longitude": lon,
                    "region_city": meta.get("ctprvn_nm"),
                    "region_gu": meta.get("signgu_nm"),
                    "category1": meta.get("category1"),
                }
            })
        
        if rag_metadata:
            history.append({
                "role": "system",
                "content": json.dumps({"rag_results": rag_metadata}, ensure_ascii=False)
            })
            logger.info(f"📌 RAG 결과 {len(rag_metadata)}개를 system 메시지로 저장")
    
    except Exception as e:
        logger.error(f"❌ RAG 메타데이터 추가 실패: {e}")
    
    return history