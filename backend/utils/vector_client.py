"""
ChromaDB Cloud Vector Client

이 모듈은 ChromaDB Cloud와의 연결 및 벡터 검색을 담당합니다.
RAG 파이프라인에서 시설 정보를 검색할 때 사용됩니다.

주요 기능:
- ChromaDB Cloud 연결 관리
- 텍스트 기반 벡터 검색 (환경별 임베딩 처리)
- 메타데이터 필터링 지원
- 싱글톤 패턴으로 연결 재사용
- 로컬/코랩/RunPod 환경 자동 감지

환경별 임베딩 처리:
- 로컬 CPU: Mock 임베딩 (개발용)
- 코랩/RunPod GPU: 실제 모델 (sentence-transformers)

사용 예시:
    from utils.vector_client import get_vector_client
    
    client = get_vector_client()
    results = client.search("한남동 놀이터", n_results=5)
"""

import os
import hashlib
from typing import List, Dict, Any, Optional

import chromadb
import numpy as np

from utils.config import get_settings
from utils.logger import logger


class VectorClient:
    """
    ChromaDB Cloud 클라이언트
    
    이 클래스는 ChromaDB Cloud와의 연결을 관리하고 벡터 검색을 수행합니다.
    싱글톤 패턴을 사용하여 애플리케이션 전체에서 하나의 연결만 유지합니다.
    
    환경 감지 기능:
    - 로컬 개발: Mock 임베딩으로 테스트
    - 코랩/GPU: 실제 sentence-transformers 모델 사용
    
    Attributes:
        settings: 환경변수 설정 객체
        client: ChromaDB Cloud 클라이언트 인스턴스
        collection: 사용 중인 ChromaDB 컬렉션
        _embedding_model: 로드된 임베딩 모델 (GPU 환경에서만)
        _is_gpu_environment: GPU 환경 여부
    """
    
    def __init__(self):
        """
        VectorClient 초기화
        
        환경변수를 로드하고 ChromaDB Cloud에 자동으로 연결합니다.
        환경을 감지하여 적절한 임베딩 방식을 선택합니다.
        """
        self.settings = get_settings()
        self.client = None
        self.collection = None
        self._embedding_model = None
        self._is_gpu_environment = self._detect_environment()
        
        # ChromaDB 연결
        self._connect()
        
        # GPU 환경이면 임베딩 모델 로드
        if self._is_gpu_environment:
            self._load_embedding_model()
    
    def _detect_environment(self) -> bool:
        """
        현재 환경 감지 (GPU/코랩 vs 로컬 CPU)
        
        Returns:
            bool: GPU 환경이면 True, 로컬 CPU면 False
        """
        try:
            if "COLAB_RELEASE_TAG" in os.environ:
                logger.info("🔍 코랩 환경 감지됨")
                return True
            import torch
            if torch.cuda.is_available():
                logger.info("🔍 GPU 환경 감지됨")
                return True
        except ImportError:
            logger.info("🔍 torch 미설치 - 로컬 CPU 환경으로 판단")
        logger.info("🔍 CPU 환경 감지됨 (Mock 임베딩 사용)")
        return False
    
    def _connect(self):
        """
        ChromaDB Cloud 연결
        
        환경변수에 설정된 정보를 사용하여 ChromaDB Cloud에 연결하고,
        지정된 컬렉션을 로드합니다.
        
        연결 정보:
        - API Key: 인증용 키 (CHROMA_API_KEY)
        - Tenant: 테넌트 ID (CHROMA_TENANT)
        - Database: 데이터베이스 이름 (CHROMA_DATABASE)
        - Collection: 컬렉션 이름 (CHROMA_COLLECTION_NAME)
        
        Raises:
            Exception: 연결 실패 시 (잘못된 인증 정보, 네트워크 오류 등)
        """
        try:
            logger.info("ChromaDB Cloud 연결 시도...")
            self.client = chromadb.CloudClient(
                api_key=self.settings.CHROMA_API_KEY,
                tenant=self.settings.CHROMA_TENANT,
                database=self.settings.CHROMA_DATABASE,
            )
            self.collection = self.client.get_collection(
                name=self.settings.CHROMA_COLLECTION_NAME
            )
            logger.info(f"✅ ChromaDB 연결 성공: {self.collection.name} ({self.collection.count()}개)")
        except Exception as e:
            logger.error(f"❌ ChromaDB 연결 실패: {e}")
            raise
    
    def _load_embedding_model(self):
        """
        임베딩 모델 로드 (GPU 환경에서만)
        
        sentence-transformers를 사용하여 팀원이 사용한 것과 동일한 모델을 로드합니다.
        모델은 한 번만 로드되어 메모리에 캐시됩니다.
        """
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"🔄 임베딩 모델 로딩 중: {self.settings.EMBEDDING_MODEL}")
            
            # GPU에서 모델 로드
            self._embedding_model = SentenceTransformer(
                self.settings.EMBEDDING_MODEL,
                device='cuda' if self._is_gpu_environment else 'cpu'
            )
            
            logger.info("✅ 임베딩 모델 로드 완료")
            
        except Exception as e:
            logger.error(f"❌ 임베딩 모델 로드 실패: {e}")
            logger.warning("Mock 임베딩으로 대체합니다")
            self._is_gpu_environment = False
            self._embedding_model = None
    
    def search(
        self,
        query_text: str,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        벡터 검색 수행
        
        사용자의 텍스트 쿼리를 벡터로 변환하여 유사한 문서를 검색합니다.
        환경에 따라 실제 모델 또는 Mock 임베딩을 사용합니다.
        
        검색 과정:
        1. query_text를 임베딩 벡터로 변환 (환경별 처리)
        2. 저장된 벡터들과 코사인 유사도 계산
        3. 가장 유사한 n_results개 반환
        
        Args:
            query_text (str): 검색할 텍스트 쿼리
                예: "한남동 근처 놀이터", "아이와 갈만한 박물관"
            
            n_results (int, optional): 반환할 결과 개수. 기본값 10.
                TOP_K로 많이 가져온 후 Reranking하는 경우 크게 설정 (예: 30)
            
            where (Dict[str, Any], optional): 메타데이터 필터 조건
                예: {"category": "놀이터"}, {"region": "서울"}
                복합 조건: {"$and": [{"category": "놀이터"}, {"region": "서울"}]}
            
            where_document (Dict[str, Any], optional): 문서 내용 필터 조건
                예: {"$contains": "무료"}
        
        Returns:
            Dict[str, Any]: 검색 결과 딕셔너리
                {
                    'ids': [[문서ID1, 문서ID2, ...]],  # 각 결과의 고유 ID
                    'documents': [[문서1, 문서2, ...]],  # 실제 텍스트 내용
                    'metadatas': [[메타1, 메타2, ...]],  # 메타데이터 (name, address 등)
                    'distances': [[거리1, 거리2, ...]]  # 코사인 거리 (낮을수록 유사)
                }
                
                주의: 모든 값이 이중 리스트 [[...]] 형태
                첫 번째 리스트는 쿼리 개수, 두 번째는 결과 개수
        
        Raises:
            Exception: 검색 실패 시 (연결 끊김, 잘못된 필터 등)
        
        Examples:
            >>> client = get_vector_client()
            >>> 
            >>> # 기본 검색
            >>> results = client.search("놀이터", n_results=5)
            >>> 
            >>> # 메타데이터 필터 사용
            >>> results = client.search(
            ...     "놀이터",
            ...     n_results=5,
            ...     where={"region": "서울"}
            ... )
            >>> 
            >>> # 결과 접근
            >>> for doc, meta, dist in zip(
            ...     results['documents'][0],
            ...     results['metadatas'][0],
            ...     results['distances'][0]
            ... ):
            ...     print(f"이름: {meta['name']}, 거리: {dist}")
        """
        try:
            env_status = "GPU" if self._is_gpu_environment else "Mock"
            logger.info(f"🔍 검색 쿼리: '{query_text}' (n_results={n_results}, 환경={env_status})")
            
            # where 필터 로그 (디버깅용)
            if where:
                logger.info(f"   메타데이터 필터: {where}")
            
            # 쿼리를 임베딩 벡터로 변환
            query_embedding = self._encode_query(query_text)
            
            # ChromaDB 검색 실행
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=["documents", "metadatas", "distances"]  # 반환할 필드 지정
            )
            
            # 검색 완료 로그
            logger.info(f"✅ 검색 완료: {len(results['ids'][0])}개 결과")
            
            # 상위 3개 결과의 거리 출력 (품질 확인용)
            if results['distances'][0]:
                top_distances = results['distances'][0][:3]
                logger.info(f"   상위 3개 거리: {[f'{d:.4f}' for d in top_distances]}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 검색 실패: {e}")
            logger.error(f"   쿼리: '{query_text}'")
            logger.error(f"   필터: {where}")
            raise
    
    def _encode_query(self, query_text: str) -> List[float]:
        """
        쿼리 텍스트를 임베딩 벡터로 변환
        
        환경에 따라 다른 방식 사용:
        - GPU 환경: 실제 sentence-transformers 모델
        - CPU 환경: Mock 임베딩 (개발용)
        
        Args:
            query_text (str): 임베딩할 텍스트
            
        Returns:
            List[float]: 임베딩 벡터 (4096차원)
            
        Raises:
            Exception: 임베딩 생성 실패 시
        """
        try:
            if self._is_gpu_environment and self._embedding_model is not None:
                # GPU 환경: 실제 모델 사용
                return self._encode_with_real_model(query_text)
            else:
                # CPU 환경: Mock 사용
                return self._encode_with_mock(query_text)
                
        except Exception as e:
            logger.error(f"❌ 임베딩 생성 실패: {e}")
            logger.warning("Mock 임베딩으로 대체")
            return self._encode_with_mock(query_text)
    
    def _encode_with_real_model(self, query_text: str) -> List[float]:
        """
        실제 모델로 임베딩 생성 (코랩/RunPod용)
        
        sentence-transformers를 사용하여 고품질 임베딩을 생성합니다.
        팀원이 업로드할 때 사용한 것과 동일한 모델을 사용합니다.
        
        Args:
            query_text (str): 임베딩할 텍스트
            
        Returns:
            List[float]: 실제 임베딩 벡터
        """
        try:
            # 배치 형태로 인코딩 (단일 텍스트도 리스트로)
            embeddings = self._embedding_model.encode([query_text])
            
            # 첫 번째 (유일한) 결과 반환
            embedding_vector = embeddings[0].tolist()
            
            logger.debug(f"✅ 실제 모델 임베딩 생성: {len(embedding_vector)}차원")
            return embedding_vector
            
        except Exception as e:
            logger.error(f"실제 모델 임베딩 실패: {e}")
            raise
    
    def _encode_with_mock(self, query_text: str) -> List[float]:
        
        """
        Mock 임베딩 생성 (로컬 개발용)
        
        텍스트를 해시 기반으로 일관된 가짜 벡터를 생성합니다.
        같은 텍스트는 항상 같은 벡터를 반환하므로 개발/테스트에 유용합니다.
        
        Args:
            query_text (str): 임베딩할 텍스트
            
        Returns:
            List[float]: Mock 임베딩 벡터 (3584차원)
        """
    
        try:
            hash_obj = hashlib.md5(query_text.encode('utf-8'))
            seed = int(hash_obj.hexdigest(), 16) % (2**32)
            
            np.random.seed(seed)
            fake_embedding = np.random.normal(0, 1, 3584)  # 4096 → 3584로 변경!
            
            norm = np.linalg.norm(fake_embedding)
            if norm > 0:
                fake_embedding = fake_embedding / norm
            
            logger.debug(f"🔄 Mock 임베딩 생성: '{query_text[:30]}...' -> 3584차원")
            return fake_embedding.tolist()
            
        except Exception as e:
            logger.error(f"Mock 임베딩 생성 실패: {e}")
            return [0.0] * 3584  # 4096 → 3584로 변경!
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        컬렉션 정보 반환
        
        현재 연결된 컬렉션의 메타 정보를 반환합니다.
        디버깅이나 상태 확인에 유용합니다.
        
        Returns:
            Dict[str, Any]: 컬렉션 정보
                {
                    'name': 컬렉션 이름,
                    'count': 저장된 문서 개수,
                    'metadata': 컬렉션 메타데이터,
                    'environment': 현재 임베딩 환경,
                    'model_loaded': 모델 로드 상태
                }
        
        Examples:
            >>> client = get_vector_client()
            >>> info = client.get_collection_info()
            >>> print(f"컬렉션: {info['name']}, 문서 수: {info['count']}")
        """
        try:
            return {
                "name": self.collection.name,
                "count": self.collection.count(),
                "metadata": self.collection.metadata,
                "environment": "GPU" if self._is_gpu_environment else "CPU (Mock)",
                "model_loaded": self._embedding_model is not None,
                "embedding_model": self.settings.EMBEDDING_MODEL
            }
        except Exception as e:
            logger.error(f"컬렉션 정보 조회 실패: {e}")
            return {"error": str(e)}


# ============================================================
# 싱글톤 패턴
# ============================================================
# VectorClient는 DB 연결과 모델을 유지하므로 매번 생성하면 비효율적입니다.
# 전역 변수로 하나의 인스턴스만 생성하여 재사용합니다.
# ============================================================

_vector_client_instance = None  # 전역 인스턴스 저장 변수


def get_vector_client() -> VectorClient:
    """
    VectorClient 싱글톤 인스턴스 반환
    
    애플리케이션 전체에서 하나의 VectorClient 인스턴스만 사용합니다.
    처음 호출 시 인스턴스를 생성하고, 이후 호출 시 같은 인스턴스를 반환합니다.
    
    싱글톤 패턴을 사용하는 이유:
    - DB 연결은 비용이 큰 작업 (매번 생성하면 느림)
    - 임베딩 모델 로딩은 메모리 집약적 (한 번만 로드)
    - 하나의 연결을 재사용하여 성능 향상
    - 메모리 효율성
    
    Returns:
        VectorClient: 전역 VectorClient 인스턴스
    
    Examples:
        >>> # 첫 번째 호출: 새 인스턴스 생성 (모델 로딩 포함)
        >>> client1 = get_vector_client()
        >>> 
        >>> # 두 번째 호출: 같은 인스턴스 반환 (즉시 사용 가능)
        >>> client2 = get_vector_client()
        >>> 
        >>> # 두 변수는 같은 객체를 가리킴
        >>> assert client1 is client2  # True
    """
    global _vector_client_instance
    
    # 인스턴스가 없으면 생성
    if _vector_client_instance is None:
        logger.info("🔧 VectorClient 인스턴스 생성 중...")
        _vector_client_instance = VectorClient()
        
        # 환경 정보 로그
        info = _vector_client_instance.get_collection_info()
        logger.info(f"📊 환경: {info.get('environment')}")
        logger.info(f"📊 모델: {info.get('embedding_model')}")
        logger.info(f"📊 컬렉션: {info.get('name')} ({info.get('count')}개 문서)")
    
    return _vector_client_instance


# ============================================================
# 개발/테스트용 유틸리티 함수들
# ============================================================

def reset_vector_client():
    """
    VectorClient 인스턴스 초기화 (테스트용)
    
    주로 테스트나 개발 중에 설정을 변경한 후 
    새로운 인스턴스를 생성하고 싶을 때 사용합니다.
    """
    global _vector_client_instance
    _vector_client_instance = None
    logger.info("🔄 VectorClient 인스턴스가 초기화되었습니다")


def test_vector_search(query: str = "테스트 쿼리", n_results: int = 3) -> Dict[str, Any]:
    try:
        client = get_vector_client()
        results = client.search(query, n_results)
        
        print(f"🔍 테스트 검색: '{query}'")
        print(f"📊 결과: {len(results['documents'][0])}개")
        
        # 상위 결과 출력 (수정된 키 이름 사용)
        for i, (doc, meta, dist) in enumerate(zip(
            results['documents'][0][:3],
            results['metadatas'][0][:3], 
            results['distances'][0][:3]
        )):
            facility_name = meta.get('facility_name', 'N/A')
            region = f"{meta.get('region_city', '')}/{meta.get('region_gu', '')}"
            category = f"{meta.get('category1', '')}-{meta.get('category2', '')}"
            
            print(f"  {i+1}. {facility_name}")
            print(f"     위치: {region}")
            print(f"     분류: {category}")  
            print(f"     거리: {dist:.4f}")
        
        return results
        
    except Exception as e:
        logger.error(f"테스트 검색 실패: {e}")
        return {"error": str(e)}
if __name__ == "__main__":
    # 직접 실행 시 테스트
    print("🧪 VectorClient 테스트 시작")
    test_vector_search("놀이터", 3)