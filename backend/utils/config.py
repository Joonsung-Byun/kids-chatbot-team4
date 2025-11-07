"""Environment config loader"""
from functools import lru_cache
from pydantic import BaseModel
import os


class Settings(BaseModel):
    OPENAI_API_KEY: str | None = None
    KAKAO_REST_API_KEY: str | None = None
    WEATHER_API_KEY: str | None = None
    CHROMA_URL: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings(
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
        KAKAO_REST_API_KEY=os.getenv("KAKAO_REST_API_KEY"),
        WEATHER_API_KEY=os.getenv("WEATHER_API_KEY"),
        CHROMA_URL=os.getenv("CHROMA_URL"),
    )
