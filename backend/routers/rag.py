from fastapi import APIRouter

router = APIRouter()


@router.get("")
def search_rag():
    """Placeholder RAG endpoint"""
    return {"results": []}
