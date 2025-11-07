from fastapi import APIRouter

router = APIRouter()


@router.post("")
def chat_endpoint():
    """Placeholder chat endpoint"""
    return {"message": "chat stub"}
