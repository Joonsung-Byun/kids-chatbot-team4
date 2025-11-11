# services/map_service.py
"""
Map Service

KakaoMap API 또는 내부 좌표 변환 로직 담당
"""

from typing import List, Dict, Any

# TODO: 실제 Kakao REST API 호출 로직 구현
def get_map_markers(query: str) -> Dict[str, Any]:
    """
    query 기반으로 지도 마커 정보 반환 (플레이스홀더)

    Returns:
      {
        "center": {"lat": float, "lng": float},
        "markers": [
          {"name": str, "lat": float, "lng": float, "desc": str}
        ]
      }
    """
    # 임시 더미 데이터
    # TODO: KakaoMap REST API 호출 후 실제 데이터 반환
    # link도 넣어줘야함
    return {
        "center": {"lat": 37.0, "lng": 127.0},
        "markers": []
    }
    
    
