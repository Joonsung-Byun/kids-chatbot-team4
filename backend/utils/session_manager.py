# utils/session_manager.py
"""
Session History Manager

대화 히스토리를 메모리에 저장하고 관리합니다.
conversation_id 기반으로 멀티턴 대화를 지원합니다.
"""

from typing import Dict, List, Optional
from utils.logger import logger


# 전역 세션 저장소 (In-memory)
# 실제 배포 시에는 Redis 등으로 교체 권장
_sessions: Dict[str, List[Dict[str, str]]] = {}

# 위치 정보 캐시 (대화별)
_location_cache: Dict[str, str] = {}


def get_history(conversation_id: str) -> List[Dict[str, str]]:
    """
    대화 히스토리 조회
    
    Args:
        conversation_id: 대화 세션 ID (UUID)
    
    Returns:
        메시지 리스트: [{"role": "user", "content": "..."}, ...]
    """
    history = _sessions.get(conversation_id, [])
    logger.debug(f"📜 히스토리 조회: {conversation_id} ({len(history)}개 메시지)")
    return history


def save_history(conversation_id: str, messages: List[Dict[str, str]]):
    """
    대화 히스토리 저장
    
    Args:
        conversation_id: 대화 세션 ID
        messages: 저장할 메시지 리스트
    """
    _sessions[conversation_id] = messages
    logger.debug(f"💾 히스토리 저장: {conversation_id} ({len(messages)}개 메시지)")


def add_message(conversation_id: str, role: str, content: str):
    """
    메시지 추가
    
    Args:
        conversation_id: 대화 세션 ID
        role: "user" 또는 "ai"
        content: 메시지 내용
    """
    history = get_history(conversation_id)
    history.append({"role": role, "content": content})
    save_history(conversation_id, history)


def clear_history(conversation_id: str):
    """
    특정 대화의 히스토리 삭제
    
    Args:
        conversation_id: 대화 세션 ID
    """
    if conversation_id in _sessions:
        del _sessions[conversation_id]
        logger.info(f"🗑️  히스토리 삭제: {conversation_id}")
    
    if conversation_id in _location_cache:
        del _location_cache[conversation_id]


def get_cached_location(conversation_id: str) -> Optional[str]:
    """
    대화에서 추출한 위치 정보 조회
    
    Args:
        conversation_id: 대화 세션 ID
    
    Returns:
        위치 문자열 또는 None
    """
    return _location_cache.get(conversation_id)


def save_cached_location(conversation_id: str, location: str):
    """
    위치 정보 캐시 저장
    
    Args:
        conversation_id: 대화 세션 ID
        location: 위치 문자열
    """
    _location_cache[conversation_id] = location
    logger.debug(f"📍 위치 캐시 저장: {conversation_id} -> {location}")


def get_session_count() -> int:
    """활성 세션 개수 반환"""
    return len(_sessions)


def cleanup_old_sessions(max_sessions: int = 100):
    """
    오래된 세션 정리 (메모리 관리)
    
    Args:
        max_sessions: 최대 유지 세션 수
    """
    if len(_sessions) > max_sessions:
        # 가장 오래된 세션부터 삭제
        sessions_to_delete = list(_sessions.keys())[:-max_sessions]
        for session_id in sessions_to_delete:
            clear_history(session_id)
        
        logger.info(f"🧹 오래된 세션 정리: {len(sessions_to_delete)}개 삭제")