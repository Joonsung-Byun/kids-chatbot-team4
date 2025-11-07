"""
LLM Service - 로컬 모델 기반

로컬/GPU 환경에서 직접 모델 로딩
"""

from typing import List, Dict, Any
from utils.config import get_settings
from utils.logger import logger
import os


class LLMService:
    """LLM 기반 답변 생성 서비스 (로컬 모델)"""
    
    def __init__(self):
        self.settings = get_settings()
        self._llm_model = None
        self._tokenizer = None
        self._is_gpu_environment = self._detect_gpu_environment()
        
        if self._is_gpu_environment:
            self._load_llm_model()
    
    def _detect_gpu_environment(self) -> bool:
        """GPU 환경 감지"""
        try:
            if 'COLAB_RELEASE_TAG' in os.environ:
                return True
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def _load_llm_model(self):
        """LLM 모델 로드 (GPU 환경에서만)"""
        try:
            # TODO: 코랩/RunPod에서 구현 예정
            # from transformers import AutoTokenizer, AutoModelForCausalLM
            # 
            # self._tokenizer = AutoTokenizer.from_pretrained(self.settings.GENERATION_MODEL)
            # self._llm_model = AutoModelForCausalLM.from_pretrained(
            #     self.settings.GENERATION_MODEL,
            #     device_map="auto",
            #     torch_dtype=torch.float16
            # )
            
            logger.info("🔄 LLM 모델 로딩 준비됨 (코랩에서 구현 예정)")
            
        except Exception as e:
            logger.error(f"LLM 모델 로딩 실패: {e}")
    
    def generate_answer(self, query: str, context_docs: List[Dict[str, Any]]) -> str:
        """RAG 컨텍스트 기반 답변 생성"""
        try:
            if not self._is_gpu_environment:
                # Mock 답변 (로컬 개발용)
                return self._generate_mock_answer(query, context_docs)
            
            # TODO: GPU 환경에서 실제 LLM 추론
            # 코랩/RunPod에서 구현 예정
            logger.info(f"🤖 LLM 답변 생성 (구현 예정): '{query}'")
            return "GPU 환경에서 LLM 답변 생성 구현 예정입니다."
            
        except Exception as e:
            logger.error(f"답변 생성 실패: {e}")
            return "죄송합니다. 답변 생성 중 오류가 발생했습니다."
    
    def _generate_mock_answer(self, query: str, context_docs: List[Dict[str, Any]]) -> str:
        """Mock 답변 생성 (로컬 개발용)"""
        if not context_docs:
            return "관련 정보를 찾지 못했습니다. 다른 키워드로 검색해보세요."
        
        # 간단한 템플릿 기반 답변
        facilities = [doc['metadata'].get('facility_name', 'Unknown') for doc in context_docs[:3]]
        
        return f"""
{query}에 대한 추천 결과입니다:

🎯 추천 시설:
{chr(10).join([f"• {facility}" for facility in facilities])}

총 {len(context_docs)}개의 관련 시설을 찾았습니다.
더 자세한 정보는 각 시설에 직접 문의해보세요!

(참고: 현재 Mock 답변입니다. GPU 환경에서 고품질 답변이 생성됩니다.)
        """.strip()
    
    def generate_clarifying_question(self, query: str, missing_info: List[str]) -> str:
        """역질문 생성"""
        if not missing_info:
            return "더 구체적인 정보를 알려주시면 더 정확한 추천을 드릴 수 있어요!"
        
        return f"더 정확한 추천을 위해 {', '.join(missing_info)}에 대해 알려주세요."


# 싱글톤 인스턴스  
_llm_service_instance = None

def get_llm_service() -> LLMService:
    """LLM Service 싱글톤 반환"""
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    return _llm_service_instance