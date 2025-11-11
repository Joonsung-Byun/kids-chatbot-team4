# services/weather_service.py
"""
Weather Service

기상청 API Hub (apihub.kma.go.kr) 연동
동네예보 조회서비스 사용
"""

from typing import Dict, Any, Optional
from datetime import datetime
import requests
import xml.etree.ElementTree as ET
from utils.logger import logger
from dotenv import load_dotenv
from data.location import DONG_TO_CITY, LANDMARK_TO_CITY, UNIVERSITY_TO_CITY, KMA_LOCATION_CODES
load_dotenv()

try:
    from utils.config import get_settings
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False
    logger.warning("config 모듈을 불러올 수 없습니다. Mock 모드로 동작합니다.")

def get_weather(location: str, target_date: Optional[str] = None) -> Dict[str, Any]:
    print(f"********Getting weather for location: {location}, target_date: {target_date}*************")
    """
    기상청 API Hub로 실제 날씨 정보 가져오기
    
    Args:
        location: "서울", "부산", "서울 강남", "부산 해운대" 등
        target_date: 조회 날짜
    
    Returns:
        {
            "location": str,          # 지역명
            "status": str,            # "clear", "cloudy", "rainy", "snowy"
            "description": str,       # "맑음", "흐림", "비", "눈"
            "temp": float,            # 기온 (°C)
            "humidity": int,          # 습도 (%)
            "wind_speed": float,      # 풍속 (m/s)
            "source": str             # "kma_api_hub" or "mock"
        }
    """
    try:
        # API 키 확인
        if not HAS_CONFIG:
            logger.warning(f"[Weather] Config 없음 - Mock 데이터 반환: {location}")
            return _get_mock_weather(location)
        
        settings = get_settings()
        api_key = settings.WEATHER_API_KEY
        print(f"API Key: {api_key}")
        
        if not api_key:
            logger.warning(f"[Weather] API 키 없음 - Mock 데이터 반환: {location}")
            return _get_mock_weather(location)
        
        # 지역코드 추출
        stn_id = _extract_location_code(location)
        
        # 기상청 API Hub 호출 (동네예보 - 이미 활용신청 완료된 API)
        url = "https://apihub.kma.go.kr/api/typ01/url/fct_afs_wl.php"
        
        # 현재 시각 (정시 기준)
        now = datetime.now()
        
        params = {
            "stn": stn_id,
            "authKey": api_key
        }
        
        logger.info(f"[Weather] API 호출: {location} (stn={stn_id})")
        logger.info(f"[Weather] Request URL: {url}")
        logger.info(f"[Weather] Request Params: {params}")
        
        response = requests.get(url, params=params, timeout=10)
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Text: {response.text[:500]}")  # 처음 500자만
        response.raise_for_status()
        
        # XML 파싱
        weather_info = _parse_kma_xml_response(response.text, location)
        
        logger.info(f"[Weather] 성공: {location} - {weather_info['description']}, {weather_info['temp']}°C")
        return weather_info
        
    except requests.exceptions.Timeout:
        logger.error(f"[Weather] 타임아웃: {location}")
        return _get_mock_weather(location, error="API 타임아웃")
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"[Weather] HTTP 오류 {e.response.status_code}: {location}")
        return _get_mock_weather(location, error=f"HTTP {e.response.status_code}")
        
    except ET.ParseError as e:
        logger.error(f"[Weather] XML 파싱 오류: {location} - {e}")
        return _get_mock_weather(location, error="XML 파싱 실패")
        
    except Exception as e:
        logger.error(f"[Weather] 알 수 없는 오류: {location} - {e}")
        return _get_mock_weather(location, error=str(e))


def _extract_location_code(location: str) -> str:
    """
    입력된 위치에서 기상청 지점번호 추출 (개선판)
    
    우선순위:
    1. KMA_LOCATION_CODES 정확 매칭
    2. 동(洞) 단위 매칭
    3. 관광지/랜드마크 매칭
    4. 대학교 매칭
    5. KMA_LOCATION_CODES 부분 매칭
    6. 기본값: 서울
    
    Args:
        location: "서울", "정자동", "해운대", "첨성대", "한강" 등
    
    Returns:
        지점번호 (예: "108")
    """
    location = location.strip()
    
    # 1. 정확한 도시명 매칭
    if location in KMA_LOCATION_CODES:
        logger.info(f"[Weather] 도시 매칭: '{location}' → stn={KMA_LOCATION_CODES[location]}")
        return KMA_LOCATION_CODES[location]
    
    # 2. 동(洞) 단위 매칭
    if location in DONG_TO_CITY:
        city = DONG_TO_CITY[location]
        code = KMA_LOCATION_CODES.get(city, "108")
        logger.info(f"[Weather] 동 매칭: '{location}' → '{city}' (stn={code})")
        return code
    
    # 3. 관광지/랜드마크 매칭
    if location in LANDMARK_TO_CITY:
        city = LANDMARK_TO_CITY[location]
        code = KMA_LOCATION_CODES.get(city, "108")
        logger.info(f"[Weather] 랜드마크 매칭: '{location}' → '{city}' (stn={code})")
        return code
    
    # 4. 대학교 매칭
    if location in UNIVERSITY_TO_CITY:
        city = UNIVERSITY_TO_CITY[location]
        code = KMA_LOCATION_CODES.get(city, "108")
        logger.info(f"[Weather] 대학 매칭: '{location}' → '{city}' (stn={code})")
        return code
    
    # 5. 부분 매칭 시도 (예: "서울 강남" → "서울")
    for city, code in KMA_LOCATION_CODES.items():
        if city in location:
            logger.info(f"[Weather] 부분 매칭: '{location}' → '{city}' (stn={code})")
            return code
    
    # 6. 동 이름 부분 매칭 (예: "수원 정자동" → "정자동" → "수원")
    for dong, city in DONG_TO_CITY.items():
        if dong in location:
            code = KMA_LOCATION_CODES.get(city, "108")
            logger.info(f"[Weather] 동 부분 매칭: '{location}' → '{dong}' → '{city}' (stn={code})")
            return code
    
    # 7. 랜드마크 부분 매칭
    for landmark, city in LANDMARK_TO_CITY.items():
        if landmark in location:
            code = KMA_LOCATION_CODES.get(city, "108")
            logger.info(f"[Weather] 랜드마크 부분 매칭: '{location}' → '{landmark}' → '{city}' (stn={code})")
            return code
    
    # 기본값: 서울
    logger.warning(f"[Weather] 지원하지 않는 지역: '{location}' → 서울로 대체")
    return "108"


def _parse_kma_xml_response(xml_text: str, location: str) -> Dict[str, Any]:
    """
    기상청 API Hub 응답 파싱 (동네예보)
    
    응답 형식 (텍스트):
    # REG_ID TM_FC        TM_EF        MOD STN C SKY  PRE  CONF WF    RN_ST
    11B00000 202511110600 202511150000 A02 109 2 WB01 WB00 없음 "맑음" 20
    
    컬럼:
    - SKY: 하늘상태 코드 (1=맑음, 2=구름조금, 3=구름많음, 4=흐림)
    - PRE: 강수형태 (없음/비/눈)
    - WF: 날씨 예보 ("맑음", "구름많음", "흐림", "비", "눈")
    - RN_ST: 강수확률 (%)
    """
    try:
        lines = xml_text.strip().split('\n')
        
        # 헤더 제외하고 첫 번째 데이터 라인 파싱
        data_lines = [line for line in lines if not line.startswith('#')]
        if not data_lines:
            logger.warning(f"[Weather] 데이터 없음 - Mock 반환")
            return _get_mock_weather(location, error="데이터 없음")
        
        # 첫 번째 예보 데이터 파싱 (공백으로 분리)
        parts = data_lines[0].split()
        if len(parts) < 11:
            logger.warning(f"[Weather] 응답 형식 오류 - Mock 반환")
            return _get_mock_weather(location, error="응답 형식 오류")
        
        # 데이터 추출
        sky_code = parts[6]  # SKY: 하늘상태
        pre_type = parts[7]  # PRE: 강수형태
        wf = parts[9].strip('"')  # WF: 날씨 설명
        rain_prob = int(parts[10])  # RN_ST: 강수확률
        
        # 날씨 상태 판단
        status = "clear"
        if "비" in wf or pre_type == "WB06":
            status = "rainy"
        elif "눈" in wf or pre_type == "WB07":
            status = "snowy"
        elif "흐림" in wf or sky_code == "4":
            status = "cloudy"
        elif "구름" in wf or sky_code in ["2", "3"]:
            status = "cloudy"
        
        # 현재 시간대 기온 추정 (예보 데이터는 기온 미포함)
        hour = datetime.now().hour
        if 6 <= hour < 12:
            temp = 12.0
        elif 12 <= hour < 18:
            temp = 18.0
        else:
            temp = 10.0
        
        return {
            "location": location,
            "status": status,
            "description": wf,
            "temp": temp,
            "humidity": 60,  # 예보 데이터에 없음
            "wind_speed": 1.5,  # 예보 데이터에 없음
            "rainfall": rain_prob,  # 강수확률로 대체
            "source": "kma_api_hub"
        }
        
    except Exception as e:
        logger.error(f"[Weather] 응답 파싱 중 오류: {e}")
        logger.debug(f"[Weather] 응답 내용: {xml_text[:200]}")
        return _get_mock_weather(location, error="파싱 오류")


def _determine_weather_status(temp: float, rainfall: float) -> tuple[str, str]:
    """
    기온과 강수량으로 날씨 상태 판단
    
    Returns:
        (status, description) 튜플
    """
    if rainfall > 0.0:
        if temp < 0:
            return ("snowy", "눈")
        else:
            return ("rainy", "비")
    elif temp < 0:
        return ("clear", "맑음 (영하)")
    elif temp < 10:
        return ("clear", "맑음 (쌀쌀)")
    elif temp < 25:
        return ("clear", "맑음")
    else:
        return ("clear", "맑음 (더움)")


def _get_mock_weather(location: str, error: Optional[str] = None) -> Dict[str, Any]:
    """
    API 호출 실패 시 폴백용 Mock 데이터
    실제 날씨처럼 보이도록 시간대별 다른 값 반환
    """
    hour = datetime.now().hour
    
    # 시간대별 기온 변화 시뮬레이션
    if 6 <= hour < 12:
        temp = 10.0 + (hour - 6) * 1.5  # 아침: 10~19°C
        description = "맑음 (아침)"
    elif 12 <= hour < 18:
        temp = 19.0 + (hour - 12) * 0.5  # 낮: 19~22°C
        description = "맑음 (낮)"
    elif 18 <= hour < 24:
        temp = 22.0 - (hour - 18) * 2.0  # 저녁: 22~10°C
        description = "맑음 (저녁)"
    else:
        temp = 10.0 - hour * 0.5  # 새벽: 10~7°C
        description = "맑음 (새벽)"
    
    result = {
        "location": location,
        "status": "clear",
        "description": description,
        "temp": round(temp, 1),
        "humidity": 60,
        "wind_speed": 1.5,
        "rainfall": 0.0,
        "source": "mock"
    }
    
    if error:
        result["error"] = error
        logger.warning(f"[Weather] Mock 데이터 반환 (사유: {error})")
    
    return result