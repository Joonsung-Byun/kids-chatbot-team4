# services/supervisor_service.py
"""
Supervisor Service (룰베이스)

LLM 없이 키워드 매칭과 정규식으로 판단합니다.
- 위치 추출
- 날짜 추출  
- 필요한 도구 선택
"""

import re
from typing import Dict, List, Optional, Any
from utils.logger import logger
from services.llm_service import get_llm_service


class SupervisorService:
    """룰베이스 Supervisor - 키워드 기반 판단"""
    
    # 한국 주요 지역 키워드
    LOCATION_KEYWORDS = [
        # 서울
        "서울", "강남", "강북", "강서", "강동", "서초", "송파", "광진",
        "마포", "용산", "성동", "동대문", "성북", "도봉", "노원", "은평",
        "종로", "중구", "중랑", "양천", "영등포", "구로", "금천", "관악",
        "동작", "서대문","광진",
        # 경기
        "수원", "성남", "고양", "용인", "부천", "안산", "안양", "남양주",
        "화성", "평택", "의정부", "시흥", "파주", "김포", "광명", "광주",
        "군포", "오산", "이천", "양주", "안성", "구리", "포천", "의왕",
        "하남", "여주", "양평", "동두천", "과천", "가평", "연천",
        # 광역시
        "부산", "인천", "대구", "대전", "광주", "울산", "세종",
        # 기타 주요 도시
        "제주", "춘천", "원주", "강릉", "청주", "천안", "전주", "포항",
        "창원", "진주", "순천", "여수", "목포"
    ]
    
    # 감정 표현 키워드
    EMOTION_KEYWORDS = [
        "고마워", "감사", "좋아", "괜찮아", "네", "응", "알겠어", "완벽",
        "최고", "멋져", "훌륭", "great", "thanks", "thank you", "ok", "okay"
    ]
    
    # 날씨 관련 키워드
    WEATHER_KEYWORDS = [
        "날씨", "기온", "온도", "맑", "흐림", "비", "눈", "바람",
        "춥", "덥", "따뜻", "시원", "weather"
    ]
    
    # 지도 관련 키워드
    MAP_KEYWORDS = [
        "지도", "위치", "어디", "찾아가", "가는법", "map", "location"
    ]
    
    def __init__(self):
        logger.info("🔧 SupervisorService 초기화 (룰베이스)")


    def analyze_query(
        self,
        user_query: str,
        conversation_context: List[Dict[str, str]],
        current_location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        사용자 쿼리 분석 (룰베이스)
        
        Args:
            user_query: 현재 사용자 입력
            conversation_context: 이전 대화 히스토리
            current_location: 이전에 추출된 위치 정보
        
        Returns:
            {
                "location": str,
                "date": str,
                "selected_tools": list,
                "needs_location": bool,
                "reasoning": str
            }
        """
        query_lower = user_query.lower().strip()
        
        # 1. 감정 표현인지 체크
        if self._is_emotional_response(query_lower):
            return {
                "location": current_location,
                "date": None,
                "selected_tools": [],
                "needs_location": False,
                "reasoning": "감정 표현 - 도구 불필요"
            }
        
        # 2. 위치 추출
        location = self._extract_location(user_query)
        if not location and current_location:
            location = current_location  # 이전 대화에서 추출한 위치 사용
        
        # 3. 날짜 추출
        date = self._extract_date(user_query)
        
        # 4. 위치가 없으면 역질문 필요
        if not location:
            return {
                "location": None,
                "date": date,
                "selected_tools": [],
                "needs_location": True,
                "reasoning": "위치 정보 없음 - 사용자에게 질문 필요"
            }
        
        # 5. 도구 선택
        selected_tools = self._select_tools(user_query, location, date)
        
        logger.info(f"[Supervisor] 위치={location}, 날짜={date}, 도구={selected_tools}")
        
        return {
            "location": location,
            "date": date,
            "selected_tools": selected_tools,
            "needs_location": False,
            "reasoning": f"위치={location}, 도구={selected_tools}"
        }
    
    def _is_emotional_response(self, query: str) -> bool:
        """감정 표현인지 판단"""
        # 짧은 문장 + 감정 키워드
        if len(query) < 20:
            for keyword in self.EMOTION_KEYWORDS:
                if keyword in query:
                    return True
        return False
    
    def _extract_location(self, query: str) -> Optional[str]:
        """위치 추출 (키워드 매칭)"""
        for location in self.LOCATION_KEYWORDS:
            if location in query:
                logger.debug(f"[Supervisor] 위치 발견: {location}")
                return location
        
        # "근처", "주변" 등의 상대적 위치 표현
        relative_keywords = ["근처", "주변", "여기", "이곳"]
        for keyword in relative_keywords:
            if keyword in query:
                logger.debug(f"[Supervisor] 상대적 위치 표현 발견: {keyword}")
                # 이전 대화에서 위치를 가져와야 함
                return None
        
        return None
    
    def _extract_date(self, query: str) -> Optional[str]:
        """날짜 추출 (정규식)"""
        # 패턴: 오늘, 내일, 이번주, 다음주, 토요일, 일요일 등
        date_patterns = [
            r"오늘",
            r"내일",
            r"모레",
            r"이번\s?주",
            r"다음\s?주",
            r"(월|화|수|목|금|토|일)요일",
            r"\d{1,2}월\s?\d{1,2}일",
            r"\d{4}-\d{2}-\d{2}",
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, query)
            if match:
                date_str = match.group(0)
                logger.debug(f"[Supervisor] 날짜 발견: {date_str}")
                return date_str
        
        return None
    
    def _select_tools(
        self,
        query: str,
        location: Optional[str],
        date: Optional[str]
    ) -> List[str]:
        """필요한 도구 선택"""
        tools = []
        query_lower = query.lower()
        
        # 1. 지도 요청인지 체크
        if any(keyword in query for keyword in self.MAP_KEYWORDS):
            tools.append("map")
            return tools  # 지도만 필요
        
        # 2. 위치 정보가 있으면 기본적으로 RAG 사용
        if location:
            tools.append("rag")
        
        # 3. 날씨 정보 필요 여부
        # - 날씨 키워드가 있거나
        # - 날짜 정보가 있으면 (미래 날씨 확인)
        needs_weather = (
            any(keyword in query for keyword in self.WEATHER_KEYWORDS)
            or date is not None
        )
        
        if needs_weather and location:
            tools.insert(0, "weather")  # 날씨를 먼저 조회
        
        # 4. RAG 결과가 있으면 지도도 생성
        if "rag" in tools:
            tools.append("map")
        
        return tools


# 싱글톤 인스턴스
_supervisor_service: Optional[SupervisorService] = None


def get_supervisor_service() -> SupervisorService:
    """SupervisorService 싱글톤 반환"""
    global _supervisor_service
    if _supervisor_service is None:
        _supervisor_service = SupervisorService()
    return _supervisor_service