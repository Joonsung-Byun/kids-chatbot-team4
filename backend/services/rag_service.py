"""
RAG Service - 로컬 모델 기반

VectorClient 기반의 고도화된 검색 서비스
- 크로스인코더 리랭킹 (sentence-transformers)
- MMR 다양성 필터링
- 멀티쿼리 확장 (로컬 LLM)
"""

from typing import List, Dict, Any, Optional
from utils.vector_client import get_vector_client
from utils.config import get_settings
from utils.logger import logger
import os


class RAGService:
    """
    고도화된 RAG 검색 서비스 (로컬 모델 기반)
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.vector_client = get_vector_client()
        self._cross_encoder = None
        self._llm_model = None
        self._is_gpu_environment = self._detect_gpu_environment()
        
        # GPU 환경에서만 모델 로드
        if self._is_gpu_environment:
            self._load_models()
    
    def _detect_gpu_environment(self) -> bool:
        """GPU 환경 감지"""
        try:
            # 코랩 환경 체크
            if 'COLAB_RELEASE_TAG' in os.environ:
                return True
            
            # GPU 가용성 체크
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def _load_models(self):
        """GPU 환경에서 모델 로드"""
        try:
            from sentence_transformers import CrossEncoder
            
            logger.info("🔄 크로스인코더 모델 로딩...")
            self._cross_encoder = CrossEncoder(
                self.settings.RERANKER_MODEL,
                device='cuda' if self._is_gpu_environment else 'cpu'
            )
            logger.info("✅ 크로스인코더 로드 완료")
            
            # TODO: LLM 모델 로딩 (코랩에서 구현 예정)
            # self._llm_model = AutoModelForCausalLM.from_pretrained(...)
            
        except Exception as e:
            logger.error(f"모델 로딩 실패: {e}")
            self._cross_encoder = None
    
    def search_and_rerank(
        self,
        query: str,
        top_k: int = None,
        filters: Optional[Dict[str, Any]] = None,
        use_multi_query: bool = True,
        use_mmr: bool = True
    ) -> List[Dict[str, Any]]:
        """완전한 RAG 검색 파이프라인"""
        try:
            top_k = top_k or self.settings.MMR_TOP_K
            
            logger.info(f"🔍 RAG 검색: '{query}' (환경: {'GPU' if self._is_gpu_environment else 'Mock'})")
            
            # 1. 멀티쿼리 확장 (GPU 환경에서만)
            queries = self._expand_query_multi(query) if use_multi_query else [query]
            
            # 2. 초기 검색 (많은 수)
            all_results = []
            for q in queries:
                results = self.vector_client.search(
                    q, 
                    n_results=self.settings.TOP_K,
                    where=filters
                )
                if results['documents']:
                    all_results.extend(self._format_search_results(results))
            
            # 중복 제거
            unique_results = self._remove_duplicates(all_results)
            
            # 3. 크로스인코더 리랭킹
            if self._cross_encoder and self._is_gpu_environment:
                reranked_docs = self._cross_encoder_rerank(query, unique_results)
            else:
                logger.info("🔄 Mock 리랭킹 사용 (GPU 환경 아님)")
                reranked_docs = unique_results[:self.settings.RERANK_TOP_K]
            
            # 4. MMR 다양성 필터링
            if use_mmr:
                final_docs = self._mmr_filtering(query, reranked_docs)
            else:
                final_docs = reranked_docs[:top_k]
            
            logger.info(f"✅ RAG 검색 완료: {len(final_docs)}개 결과")
            return final_docs
            
        except Exception as e:
            logger.error(f"RAG 검색 실패: {e}")
            return []
    
    def _expand_query_multi(self, query: str) -> List[str]:
        """멀티쿼리 확장"""
        if not self._is_gpu_environment:
            logger.info("🔄 Mock 쿼리 확장")
            return [query]  # Mock: 원본 쿼리만 반환
        
        # TODO: GPU 환경에서 LLM 기반 쿼리 확장
        # 코랩에서 구현 예정
        logger.info("🔄 LLM 쿼리 확장 (구현 예정)")
        return [query]
    
    def _cross_encoder_rerank(self, query: str, docs: List[Dict]) -> List[Dict]:
        """크로스인코더 리랭킹"""
        if not self._cross_encoder:
            return docs
        
        try:
            # 쿼리-문서 쌍 생성
            pairs = [(query, doc['content']) for doc in docs]
            
            # 크로스인코더 점수 계산
            scores = self._cross_encoder.predict(pairs)
            
            # 점수와 문서 매칭
            scored_docs = []
            for doc, score in zip(docs, scores):
                if score >= self.settings.SIMILARITY_THRESHOLD:
                    doc['rerank_score'] = float(score)
                    scored_docs.append(doc)
            
            # 점수 기준 정렬
            scored_docs.sort(key=lambda x: x['rerank_score'], reverse=True)
            
            return scored_docs[:self.settings.RERANK_TOP_K]
            
        except Exception as e:
            logger.error(f"리랭킹 실패: {e}")
            return docs
    
    def _mmr_filtering(self, query: str, docs: List[Dict]) -> List[Dict]:
        """MMR 다양성 필터링 (TODO: 구현)"""
        # TODO: Maximum Marginal Relevance 구현
        # 현재는 상위 N개만 반환
        return docs[:self.settings.MMR_TOP_K]
    
    def _format_search_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """검색 결과를 표준 형식으로 변환"""
        formatted = []
        for doc, meta, dist in zip(
            results['documents'],
            results['metadatas'],
            results['distances']
        ):
            formatted.append({
                'content': doc,
                'metadata': meta,
                'distance': dist,
                'similarity': 1 - dist  # 거리를 유사도로 변환
            })
        return formatted
    
    def _remove_duplicates(self, docs: List[Dict]) -> List[Dict]:
        """중복 문서 제거 (facility_name 기준)"""
        seen_names = set()
        unique_docs = []
        
        for doc in docs:
            name = doc['metadata'].get('facility_name', '')
            if name and name not in seen_names:
                seen_names.add(name)
                unique_docs.append(doc)
        
        return unique_docs


# 싱글톤 인스턴스
_rag_service_instance = None

def get_rag_service() -> RAGService:
    """RAG Service 싱글톤 반환"""
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance