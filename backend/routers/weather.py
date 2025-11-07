from fastapi import APIRouter

router = APIRouter()


@router.get("")
def get_weather():
    """Placeholder weather endpoint"""
    return {"weather": "sunny"}
