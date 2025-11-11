"""
ChromaDB Vector Client (로컬 서버 지원)

ChromaDB Cloud → 로컬 ChromaDB 서버로 전환
Docker Compose 환경에서 chromadb 서비스와 연결
"""

import os
import hashlib
from typing import List, Dict, Any, Optional

import chromadb
import numpy as np

from utils.config import get_settings
from utils.logger import logger


class VectorClient:
    """ChromaDB 클라이언트 (로컬/클라우드 자동 감지)"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = None
        self.collection = None
        self._embedding_model = None
        self._is_gpu_environment = self._detect_environment()
        
        # ChromaDB 연결 (로컬 우선)
        self._connect()
        
        # GPU 환경이면 임베딩 모델 로드
        if self._is_gpu_environment:
            self._load_embedding_model()
    
    def _detect_environment(self) -> bool:
        """GPU 환경 감지"""
        # 환경변수로 명시적 설정
        use_gpu = os.getenv("USE_GPU", "false").lower() == "true"
        if use_gpu:
            logger.info("🔍 USE_GPU=true 환경변수 감지")
            return True
        
        # Colab 환경
        if "COLAB_RELEASE_TAG" in os.environ:
            logger.info("🔍 코랩 환경 감지됨")
            return True
        
        # CUDA 사용 가능 여부
        try:
            import torch
            if torch.cuda.is_available():
                logger.info("🔍 GPU 환경 감지됨")
                return True
        except ImportError:
            logger.info("🔍 torch 미설치 - 로컬 CPU 환경으로 판단")
        
        logger.info("🔍 CPU 환境 감지됨 (Mock 임베딩 사용)")
        return False
    
    def _connect(self):
        """ChromaDB 연결 (로컬 서버 우선, fallback to Cloud)"""
        try:
            # 1. 로컬 ChromaDB 서버 시도 (Docker Compose)
            chroma_host = os.getenv("CHROMA_HOST", "localhost")
            chroma_port = int(os.getenv("CHROMA_PORT", "8000"))
            
            if chroma_host != "localhost" or os.getenv("ENVIRONMENT") == "docker":
                logger.info(f"🔗 로컬 ChromaDB 서버 연결 시도: {chroma_host}:{chroma_port}")
                
                self.client = chromadb.HttpClient(
                    host=chroma_host,
                    port=chroma_port
                )
                
                # 컬렉션 가져오기 또는 생성
                try:
                    self.collection = self.client.get_collection(
                        name=self.settings.CHROMA_COLLECTION_NAME
                    )
                    logger.info(f"✅ 기존 컬렉션 로드: {self.collection.name}")
                except Exception:
                    logger.info(f"📦 새 컬렉션 생성: {self.settings.CHROMA_COLLECTION_NAME}")
                    self.collection = self.client.create_collection(
                        name=self.settings.CHROMA_COLLECTION_NAME,
                        metadata={"description": "Kids activity facilities"}
                    )
                
                logger.info(f"✅ 로컬 ChromaDB 연결 성공: {self.collection.count()}개 문서")
                return
            
        except Exception as e:
            logger.warning(f"⚠️ 로컬 ChromaDB 연결 실패: {e}")
        
        # 2. ChromaDB Cloud 시도 (fallback)
        try:
            if self.settings.CHROMA_API_KEY and self.settings.CHROMA_TENANT:
                logger.info("🔗 ChromaDB Cloud 연결 시도...")
                
                self.client = chromadb.CloudClient(
                    api_key=self.settings.CHROMA_API_KEY,
                    tenant=self.settings.CHROMA_TENANT,
                    database=self.settings.CHROMA_DATABASE,
                )
                
                self.collection = self.client.get_collection(
                    name=self.settings.CHROMA_COLLECTION_NAME
                )
                
                logger.info(f"✅ ChromaDB Cloud 연결 성공: {self.collection.count()}개 문서")
                return
        
        except Exception as e:
            logger.error(f"❌ ChromaDB Cloud 연결 실패: {e}")
        
        # 3. 모든 연결 실패 시 에러
        raise ConnectionError("ChromaDB 연결 실패: 로컬 서버와 Cloud 모두 연결할 수 없습니다.")
    
    def _load_embedding_model(self):
        """임베딩 모델 로드 (GPU 환경)"""
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"🔄 임베딩 모델 로딩 중: {self.settings.EMBEDDING_MODEL}")
            
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
        """벡터 검색"""
        try:
            env_status = "GPU" if self._is_gpu_environment else "Mock"
            logger.info(f"🔍 검색 쿼리: '{query_text}' (n_results={n_results}, 환경={env_status})")
            
            if where:
                logger.info(f"   메타데이터 필터: {where}")
            
            # 쿼리 임베딩
            query_embedding = self._encode_query(query_text)
            
            # ChromaDB 검색
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=["documents", "metadatas", "distances"]
            )
            
            logger.info(f"✅ 검색 완료: {len(results['ids'][0])}개 결과")
            
            if results['distances'][0]:
                top_distances = results['distances'][0][:3]
                logger.info(f"   상위 3개 거리: {[f'{d:.4f}' for d in top_distances]}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 검색 실패: {e}")
            raise
    
    def _encode_query(self, query_text: str) -> List[float]:
        """쿼리 텍스트 임베딩"""
        try:
            if self._is_gpu_environment and self._embedding_model is not None:
                return self._encode_with_real_model(query_text)
            else:
                return self._encode_with_mock(query_text)
                
        except Exception as e:
            logger.error(f"❌ 임베딩 생성 실패: {e}")
            logger.warning("Mock 임베딩으로 대체")
            return self._encode_with_mock(query_text)
    
    def _encode_with_real_model(self, query_text: str) -> List[float]:
        """실제 모델로 임베딩 생성"""
        try:
            embeddings = self._embedding_model.encode([query_text])
            embedding_vector = embeddings[0].tolist()
            
            logger.debug(f"✅ 실제 모델 임베딩 생성: {len(embedding_vector)}차원")
            return embedding_vector
            
        except Exception as e:
            logger.error(f"실제 모델 임베딩 실패: {e}")
            raise
    
    def _encode_with_mock(self, query_text: str) -> List[float]:
        """Mock 임베딩 생성 (개발용)"""
        try:
            hash_obj = hashlib.md5(query_text.encode('utf-8'))
            seed = int(hash_obj.hexdigest(), 16) % (2**32)
            
            np.random.seed(seed)
            fake_embedding = np.random.normal(0, 1, 3584)
            
            norm = np.linalg.norm(fake_embedding)
            if norm > 0:
                fake_embedding = fake_embedding / norm
            
            logger.debug(f"🔄 Mock 임베딩 생성: '{query_text[:30]}...' -> 3584차원")
            return fake_embedding.tolist()
            
        except Exception as e:
            logger.error(f"Mock 임베딩 생성 실패: {e}")
            return [0.0] * 3584
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> None:
        """문서 추가 (초기 데이터 로딩용)"""
        try:
            if ids is None:
                ids = [f"doc_{i}" for i in range(len(documents))]
            
            # 임베딩 생성
            if self._is_gpu_environment and self._embedding_model:
                embeddings = self._embedding_model.encode(documents).tolist()
            else:
                embeddings = [self._encode_with_mock(doc) for doc in documents]
            
            # ChromaDB에 추가
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
            
            logger.info(f"✅ {len(documents)}개 문서 추가 완료")
            
        except Exception as e:
            logger.error(f"❌ 문서 추가 실패: {e}")
            raise
    
    def get_collection_info(self) -> Dict[str, Any]:
        """컬렉션 정보 반환"""
        try:
            return {
                "name": self.collection.name,
                "count": self.collection.count(),
                "metadata": self.collection.metadata,
                "environment": "GPU" if self._is_gpu_environment else "CPU (Mock)",
                "model_loaded": self._embedding_model is not None,
                "embedding_model": self.settings.EMBEDDING_MODEL,
                "connection_type": "Local Server" if os.getenv("CHROMA_HOST") else "Cloud"
            }
        except Exception as e:
            logger.error(f"컬렉션 정보 조회 실패: {e}")
            return {"error": str(e)}


# 싱글톤 인스턴스
_vector_client_instance = None


def get_vector_client() -> VectorClient:
    """VectorClient 싱글톤 반환"""
    global _vector_client_instance
    
    if _vector_client_instance is None:
        logger.info("🔧 VectorClient 인스턴스 생성 중...")
        _vector_client_instance = VectorClient()
        
        info = _vector_client_instance.get_collection_info()
        logger.info(f"📊 환경: {info.get('environment')}")
        logger.info(f"📊 연결: {info.get('connection_type')}")
        logger.info(f"📊 모델: {info.get('embedding_model')}")
        logger.info(f"📊 컬렉션: {info.get('name')} ({info.get('count')}개 문서)")
    
    return _vector_client_instance


def reset_vector_client():
    """VectorClient 초기화 (테스트용)"""
    global _vector_client_instance
    _vector_client_instance = None
    logger.info("🔄 VectorClient 인스턴스가 초기화되었습니다")


if __name__ == "__main__":
    print("🧪 VectorClient 테스트 시작")
    client = get_vector_client()
    info = client.get_collection_info()
    print(f"연결 정보: {info}")