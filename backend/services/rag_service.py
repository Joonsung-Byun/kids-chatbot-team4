# services/rag_service.py
"""
RAG Service

- 벡터 검색
- 크로스인코더 리랭킹
- MMR 다양성 필터링
"""
import os
from typing import List, Dict, Any, Optional

from utils.config import get_settings
from utils.logger import logger
from utils.vector_client import get_vector_client

class RAGService:
    """RAG 기반 문서/시설 검색 서비스"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = get_vector_client()
        self._cross_encoder = None
        self._use_gpu = self._detect_gpu()

        if self._use_gpu:
            self._load_reranker()

    def _detect_gpu(self) -> bool:
        """GPU 환경 감지"""
        try:
            import torch
            if torch.cuda.is_available():
                return True
        except ImportError:
            pass
        # Colab 환경 체크
        if "COLAB_RELEASE_TAG" in os.environ:
            return True
        return False

    def _load_reranker(self) -> None:
        """GPU 환경에서 CrossEncoder 모델 로드"""
        try:
            from sentence_transformers import CrossEncoder
            model_name = self.settings.RERANKER_MODEL
            logger.info(f"🔄 크로스인코더 로딩: {model_name}")
            self._cross_encoder = CrossEncoder(model_name, device="cuda")
            logger.info("✅ 크로스인코더 로드 완료")
        except Exception as e:
            logger.error(f"❌ 크로스인코더 로드 실패: {e}")
            self._cross_encoder = None

    def search_and_rerank(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        use_multi_query: bool = True,
        use_mmr: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        1) (선택) 멀티쿼리 확장
        2) 초기 벡터 검색
        3) 중복 제거
        4) (선택) 크로스인코더 리랭킹
        5) (선택) MMR 필터링
        """
        try:
            k = top_k or self.settings.MMR_TOP_K
            logger.info(f"🔍 RAG 검색 시작: '{query}' (GPU={self._use_gpu})")

            # 멀티쿼리
            queries = [query]
            if use_multi_query and self._use_gpu:
                # TODO: LLM 기반 쿼리 확장 구현
                pass

            # 초기 검색
            all_docs = []
            for q in queries:
                res = self.client.search(q, n_results=self.settings.TOP_K, where=filters)
                # res['documents'][0], res['metadatas'][0], res['distances'][0]
                formatted = self._format_results(res)
                all_docs.extend(formatted)

            # 중복 제거
            unique_docs = self._dedupe(all_docs)

            # 리랭킹
            if self._cross_encoder:
                reranked = self._rerank(query, unique_docs)
                if not reranked or len(reranked) == 0:
                    logger.warning("⚠️ 리랭킹 결과가 비어 있음 → 원본 상위 N개 유지")
                    unique_docs = unique_docs[: self.settings.RERANK_TOP_K]
                else:
                    unique_docs = reranked
            else:
                logger.info("💡 GPU 비활성화 환경 → 리랭킹 생략, 상위 N개 그대로 사용")
                unique_docs = unique_docs[: self.settings.RERANK_TOP_K]

            # MMR 필터링 (현재는 상위 N개 추출)
            final = unique_docs[:k] if use_mmr else unique_docs
            logger.info(f"✅ RAG 검색 완료: {len(final)}개 반환")
            return final

        except Exception as e:
            logger.error(f"❌ RAG 검색 오류: {e}")
            return []

    def _format_results(self, res: Dict[str, Any]) -> List[Dict[str, Any]]:
        """ChromaDB 결과 포맷 변환 (빈 문서 예외 처리)"""
        if not res or not res.get("documents") or not res["documents"][0]:
            return []

        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]

        formatted = []
        for doc, meta, dist in zip(docs, metas, dists):
            if not doc or doc.strip() == "":
                continue
            formatted.append({
                "content": doc.strip(),
                "metadata": meta or {},
                "distance": dist,
                "similarity": round(1 - float(dist), 4)
            })

        return formatted

    def _dedupe(self, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """시설명 기준 중복 제거 (facility_name / Name 대응)"""
        seen, unique = set(), []
        for d in docs:
            meta = d.get("metadata", {})
            name = meta.get("facility_name") or meta.get("Name")  # ✅ 핵심 수정
            if name and name not in seen:
                seen.add(name)
                unique.append(d)
        return unique
    
    def _rerank(self, query: str, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """크로스인코더로 리랭킹"""
        try:
            pairs = [(query, d["content"]) for d in docs]
            scores = self._cross_encoder.predict(pairs)
            scored = []
            for doc, score in zip(docs, scores):
                if score >= self.settings.SIMILARITY_THRESHOLD:
                    doc["score"] = float(score)
                    scored.append(doc)
            scored.sort(key=lambda x: x["score"], reverse=True)
            return scored[: self.settings.RERANK_TOP_K]
        except Exception as e:
            logger.error(f"❌ 리랭킹 실패: {e}")
            return docs


# 싱글톤 인스턴스
_rag_service: RAGService = None


def get_rag_service() -> RAGService:
    """RAGService 싱글톤 반환"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service