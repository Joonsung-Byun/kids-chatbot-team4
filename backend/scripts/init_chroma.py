"""
ChromaDB 데이터 초기화 스크립트

CSV 파일을 읽어 ChromaDB에 벡터 데이터를 로드합니다.
로컬 개발 및 Docker 환경에서 모두 사용 가능합니다.
"""

import sys
import os
import pandas as pd
from pathlib import Path

# backend 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.vector_client import get_vector_client
from utils.logger import logger


def load_csv_to_chroma(csv_path: str, batch_size: int = 100):
    """
    CSV 파일을 ChromaDB에 로드
    
    Args:
        csv_path: CSV 파일 경로
        batch_size: 배치 크기 (메모리 효율성)
    """
    try:
        # CSV 로드
        logger.info(f"📂 CSV 파일 로딩: {csv_path}")
        df = pd.read_csv(csv_path)
        logger.info(f"✅ {len(df)}개 행 로드 완료")
        
        # 필수 컬럼 확인
        required_cols = ["facility_name", "description"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            raise ValueError(f"필수 컬럼 누락: {missing_cols}")
        
        # NaN 제거
        df = df.dropna(subset=required_cols)
        logger.info(f"🧹 정제 후: {len(df)}개 행")
        
        # VectorClient 초기화
        logger.info("🔗 ChromaDB 연결 중...")
        client = get_vector_client()
        
        # 배치 처리
        total_batches = (len(df) + batch_size - 1) // batch_size
        logger.info(f"📦 {total_batches}개 배치로 나누어 업로드")
        
        for i in range(0, len(df), batch_size):
            batch_df = df.iloc[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            
            logger.info(f"⏳ 배치 {batch_num}/{total_batches} 처리 중...")
            
            # 문서 및 메타데이터 준비
            documents = batch_df["description"].tolist()
            metadatas = batch_df.to_dict("records")
            ids = [f"facility_{idx}" for idx in batch_df.index]
            
            # ChromaDB에 추가
            client.add_documents(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"✅ 배치 {batch_num} 완료 ({len(documents)}개 문서)")
        
        # 최종 확인
        info = client.get_collection_info()
        logger.info(f"🎉 데이터 로드 완료!")
        logger.info(f"📊 총 문서 수: {info['count']}")
        logger.info(f"📊 컬렉션: {info['name']}")
        
        return True
    
    except FileNotFoundError:
        logger.error(f"❌ 파일을 찾을 수 없습니다: {csv_path}")
        return False
    
    except Exception as e:
        logger.error(f"❌ 데이터 로드 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_data():
    """데이터 로드 검증"""
    try:
        logger.info("🔍 데이터 검증 중...")
        
        client = get_vector_client()
        info = client.get_collection_info()
        
        logger.info(f"✅ 컬렉션: {info['name']}")
        logger.info(f"✅ 문서 수: {info['count']}")
        logger.info(f"✅ 환경: {info['environment']}")
        
        # 샘플 검색
        results = client.search("놀이터", n_results=3)
        
        logger.info(f"🔍 샘플 검색 결과: {len(results['ids'][0])}개")
        
        for i, (doc, meta) in enumerate(zip(
            results['documents'][0][:3],
            results['metadatas'][0][:3]
        ), 1):
            logger.info(f"  {i}. {meta.get('facility_name', 'N/A')}")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ 검증 실패: {e}")
        return False


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="CSV 데이터를 ChromaDB에 로드"
    )
    parser.add_argument(
        "csv_path",
        type=str,
        help="CSV 파일 경로"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="배치 크기 (기본값: 100)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="로드 후 검증"
    )
    
    args = parser.parse_args()
    
    # 데이터 로드
    success = load_csv_to_chroma(args.csv_path, args.batch_size)
    
    if not success:
        sys.exit(1)
    
    # 검증
    if args.verify:
        if not verify_data():
            sys.exit(1)
    
    logger.info("🎉 모든 작업 완료!")


if __name__ == "__main__":
    main()