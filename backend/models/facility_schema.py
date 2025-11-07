"""Facility model schemas"""
from pydantic import BaseModel


class Facility(BaseModel):
    name: str
    lat: float
    lng: float
