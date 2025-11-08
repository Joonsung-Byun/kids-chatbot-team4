# services/weather_service.py
"""
Weather Service

외부 날씨 API 호출 및 날씨 정보 처리 담당
"""

from typing import Dict, Any

# TODO: 실제 날씨 API 호출 로직 구현
def get_weather(location: str) -> Dict[str, Any]:
    """
    지정한 위치의 현재 날씨 정보 반환 (플레이스홀더)
    
    Args:
      location: "서울특별시 중구" 등
    
    Returns:
      {
        "location": str,
        "status": str,  # 예: "sunny", "rainy"
        ...
      }
    """
    return {"location": location, "status": "sunny"}