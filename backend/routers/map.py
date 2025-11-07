from fastapi import APIRouter

router = APIRouter()


@router.get("")
def get_map():
    """Placeholder map endpoint"""
    return {"center": {"lat": 0, "lng": 0}, "markers": []}
