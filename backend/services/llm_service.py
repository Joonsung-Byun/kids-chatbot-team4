# services/llm_service.py
"""
LLM Service

- GPU 환경: 실제 모델 로딩 및 추론
- CPU/Mock 환경: 간단한 Mock 답변 반환
"""

import os
from typing import List, Dict, Any

from utils.config import get_settings
from utils.logger import logger

# GPU 전용 라이브러리 import 시도
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
except ImportError:
    torch = None
    AutoTokenizer = None
    AutoModelForCausalLM = None
    GenerationConfig = None


class LLMService:
    """LLM 기반 답변 생성 서비스"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._tokenizer = None
        self._model = None
        self._use_gpu = self._detect_gpu()

        if self._use_gpu:
            self._load_model()
        else:
            logger.info("🔄 GPU 미검출 또는 라이브러리 미설치 → Mock 모드로 동작")

    def _detect_gpu(self) -> bool:
        """GPU 환경 감지 (Colab, CUDA 등)"""
        if os.getenv("COLAB_RELEASE_TAG"):
            return True
        if AutoModelForCausalLM and torch and torch.cuda.is_available():
            return True
        return False

    def _load_model(self) -> None:
        """GPU 환경에서 실제 LLM 모델 및 토크나이저 로드"""
        try:
            model_name = self.settings.GENERATION_MODEL
            logger.info(f"🔄 LLM 모델 로딩: {model_name}")
            self._tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
            self._model = AutoModelForCausalLM.from_pretrained(
                model_name, device_map="auto", torch_dtype=torch.float16, trust_remote_code=True
            )
            self._model.eval()
            logger.info("✅ LLM 모델 로드 완료")
        except Exception as e:
            logger.error(f"❌ LLM 모델 로드 실패: {e}")
            self._use_gpu = False  # fallback to Mock
    
    # def generate_short_response(
    #     self,
    #     prompt: str,
    #     max_tokens: int = 100
    # ) -> str:
    #     """
    #     analyze_query_with_llm 에서 JSON 파싱용으로 호출하는 단문 생성기.
    #     """
    #     # GPU 환경 실제 모델 호출
    #     if self._use_gpu and self._model and self._tokenizer:
    #         from transformers import GenerationConfig
    #         inputs = self._tokenizer(
    #             prompt,
    #             return_tensors="pt",
    #             truncation=True,
    #             max_length=512
    #         ).to(self._model.device)
    #         gen_cfg = GenerationConfig(
    #             temperature=0.7,
    #             max_new_tokens=max_tokens,
    #             top_p=0.9
    #         )
    #         with torch.no_grad():
    #             out = self._model.generate(**inputs, generation_config=gen_cfg)
    #         return self._tokenizer.decode(out[0], skip_special_tokens=True).strip()

    #     # Mock 모드: 최소한 빈 JSON이라도 반환
    #     return "{}"
    
    def generate_answer(
        self,
        query: str,
        context_docs: List[Dict[str, Any]],
    ) -> str:
        """
        RAG 컨텍스트 기반 답변 생성
    
        Returns:
          - 실제 GPU 환경: 모델 추론 결과
          - Mock 환경: 간단한 추천 리스트
        """
        if self._use_gpu and self._model and self._tokenizer:
            try:
                # 1) Prompt 조합
                context = "\n".join(doc["content"] for doc in context_docs)
                prompt = f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
                
                # 2) 토크나이즈 및 Tensor 변환
                inputs = self._tokenizer(
                    prompt, return_tensors="pt", truncation=True, max_length=1024
                ).to(self._model.device)
                
                # 3) 생성 설정
                gen_cfg = GenerationConfig(temperature=0.7, max_new_tokens=256, top_p=0.9)
                
                # 4) 추론
                with torch.no_grad():
                    out = self._model.generate(**inputs, generation_config=gen_cfg)
                text = self._tokenizer.decode(out[0], skip_special_tokens=True)
                return text.split("Answer:")[-1].strip()
            except Exception as e:
                logger.error(f"❌ LLM 추론 중 오류: {e}")
                return self._mock_answer(query, context_docs)
        
        # Mock 모드
        return self._mock_answer(query, context_docs)

    def _mock_answer(
        self,
        query: str,
        context_docs: List[Dict[str, Any]],
    ) -> str:
        """개발용 Mock 답변 생성 (개선 버전)"""
        if not context_docs:
            return "관련 정보를 찾지 못했습니다. 다른 키워드로 검색해 보세요."
        
        # 상위 3개 시설 정보 추출
        recommendations = []
        for doc in context_docs[:3]:
            metadata = doc.get("metadata", {})
            name = metadata.get("facility_name", "Unknown")
            category = metadata.get("category1", "시설")
            location = metadata.get("region_gu", metadata.get("region_city", ""))
            price = metadata.get("price", "무료")
            
            recommendations.append(
                f"📍 **{name}** ({location})\n"
                f"   분류: {category} | 가격: {price}"
            )
        
        answer = f"추천 장소를 찾았어요! 🎉\n\n"
        answer += "\n\n".join(recommendations)
        answer += f"\n\n총 {len(context_docs)}개의 장소가 있어요. 더 궁금한 점이 있으시면 말씀해주세요! 😊"
        answer += "\n\n💡 *현재 Mock 모드로 작동 중입니다. GPU 환경에서는 더 자세한 답변을 제공합니다.*"
        
        return answer

    def generate_clarifying_question(
        self, query: str, missing_info: List[str]
    ) -> str:
        """
        사용자가 빠뜨린 정보에 대한 추가 질문 생성
        """
        if not missing_info:
            return "더 구체적인 정보를 알려주시면 더 정확한 추천을 드릴 수 있어요!"
        return f"추가로 {', '.join(missing_info)} 정보를 알려주실 수 있나요?"


# 싱글톤 인스턴스
_llm_service: LLMService = None


def get_llm_service() -> LLMService:
    """LLMService 싱글톤 반환"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service