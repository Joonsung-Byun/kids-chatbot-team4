# services/map_service.py

"""
Map Service

KakaoMap API 연동 및 지도 마커 생성
"""

from typing import List, Dict, Any
import json
from utils.logger import logger


def get_map_markers(markers_json: str) -> Dict[str, Any]:
    """
    마커 리스트를 받아서 카카오맵 데이터 생성
    
    Args:
        markers_json: JSON 형식의 마커 리스트
        예: '[{"name": "공원", "lat": 37.5, "lng": 127.0}, ...]'
    
    Returns:
        {
            "center": {"lat": float, "lng": float},
            "markers": [
                {"name": str, "lat": float, "lng": float, "desc": str}
            ],
            "link": str  # 카카오맵 링크
        }
    """
    try:
        # JSON 파싱
        markers = json.loads(markers_json)
        
        if not markers:
            logger.warning("⚠️ 마커가 비어있습니다")
            return {
                "center": {"lat": 37.5665, "lng": 126.9780},  # 서울 시청 기본값
                "markers": [],
                "link": ""
            }
        
        # 중심점 계산 (모든 마커의 평균 좌표)
        avg_lat = sum(m["lat"] for m in markers) / len(markers)
        avg_lng = sum(m["lng"] for m in markers) / len(markers)
        
        # 마커 데이터 구성 (desc 필드 추가 가능)
        formatted_markers = []
        for marker in markers:
            formatted_markers.append({
                "name": marker.get("name", "Unknown"),
                "lat": marker["lat"],
                "lng": marker["lng"],
                "desc": marker.get("desc", "")  # 설명 (선택사항)
            })
        
        # 카카오맵 링크 생성
        # 첫 번째 마커를 기준으로 링크 생성
        first_marker = markers[0]
        kakao_link = f"https://map.kakao.com/link/to/{first_marker['name']},{first_marker['lat']},{first_marker['lng']}"
        
        result = {
            "center": {
                "lat": round(avg_lat, 4),
                "lng": round(avg_lng, 4)
            },
            "markers": formatted_markers,
            "link": kakao_link
        }
        
        logger.info(f"🗺️ 지도 데이터 생성 완료: {len(formatted_markers)}개 마커, 중심({avg_lat:.4f}, {avg_lng:.4f})")
        
        return result
    
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON 파싱 오류: {e}")
        return {
            "center": {"lat": 37.5665, "lng": 126.9780},
            "markers": [],
            "link": "",
            "error": "JSON 파싱 실패"
        }
    
    except Exception as e:
        logger.error(f"❌ 지도 생성 오류: {e}")
        return {
            "center": {"lat": 37.5665, "lng": 126.9780},
            "markers": [],
            "link": "",
            "error": str(e)
        }