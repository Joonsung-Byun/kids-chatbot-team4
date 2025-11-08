# models/facility_schema.py
"""시설 정보 Pydantic 스키마"""

from pydantic import BaseModel


class Facility(BaseModel):
    """단일 시설 정보 모델"""
    name: str     # 시설명
    lat: float    # 위도
    lng: float    # 경도