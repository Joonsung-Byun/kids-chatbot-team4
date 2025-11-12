"""
ChromaDB 데이터 초기화 스크립트 (안전형)
----------------------------------------
CSV의 컬럼 결측치를 자동 처리하고,
시설 정보를 자연어 description으로 변환해 ChromaDB에 업로드합니다.
"""

import sys
import os
import pandas as pd
from pathlib import Path

# backend 경로 인식
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.vector_client import get_vector_client
from utils.logger import logger


def safe_get(row, key):
    """결측값이나 None을 안전하게 가져오기"""
    val = row.get(key, "")
    if pd.isna(val) or str(val).strip() in ["", "nan", "None"]:
        return ""
    return str(val).strip()


def build_description(row: pd.Series) -> str:
    """CSV 한 행(row)에서 자연어 description을 생성"""
    parts = []

    name = safe_get(row, "Name")
    region = " ".join(filter(None, [safe_get(row, "CTPRVN_NM"), safe_get(row, "SIGNGU_NM")]))
    category = " ".join(
        filter(None, [safe_get(row, "Category1"), safe_get(row, "Category2"), safe_get(row, "Category3")])
    )

    if name:
        parts.append(f"{name}은(는)")
    if region:
        parts.append(f"{region}에 위치한")
    if category:
        parts.append(f"{category} 관련 시설입니다.")
    else:
        parts.append("가족 및 유아가 함께 즐길 수 있는 시설입니다.")

    # 추가 정보
    inout = safe_get(row, "in_out")
    cost = safe_get(row, "Cost")
    age = safe_get(row, "Age")
    time = safe_get(row, "Time")
    day = safe_get(row, "Day")
    note = safe_get(row, "Note")
    address = safe_get(row, "Address")

    if inout:
        parts.append(f"이 시설은 {inout} 장소이며,")
    if age:
        parts.append(f"이용 연령대는 {age}입니다.")
    if cost:
        parts.append(f"이용 요금은 {cost}입니다.")
    if time or day:
        parts.append(f"운영 시간은 {day} {time}입니다.")
    if address:
        parts.append(f"주소는 {address}입니다.")
    if note:
        parts.append(note)

    # 문장 결합 + 중복 조사 제거
    text = " ".join(filter(None, parts))
    text = text.replace("  ", " ").strip()

    return text


def load_csv_to_chroma(csv_path: str, batch_size: int = 100):
    """CSV 파일을 ChromaDB에 로드"""
    try:
        logger.info(f"📂 CSV 파일 로딩: {csv_path}")
        df = pd.read_csv(csv_path)
        logger.info(f"✅ {len(df)}개 행 로드 완료")

        # description 생성
        logger.info("🧩 description 컬럼 자동 생성 중...")
        df["description"] = df.apply(build_description, axis=1)

        # Name과 description이 비어 있는 행 제거
        df = df.dropna(subset=["Name", "description"])
        df = df[df["description"].str.strip() != ""]
        logger.info(f"🧹 정제 후 {len(df)}개 행 남음")

        # VectorClient 초기화
        client = get_vector_client()
        total_batches = (len(df) + batch_size - 1) // batch_size
        logger.info(f"📦 총 {total_batches}개 배치 업로드 예정")

        for i in range(0, len(df), batch_size):
            batch_df = df.iloc[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            
            logger.info(f"⏳ 배치 {batch_num}/{total_batches} 처리 중...")

            # NaN → None (JSON 직렬화 가능하도록)
            batch_df = batch_df.where(pd.notnull(batch_df), None)

            # 문서 및 메타데이터 준비
            documents = batch_df["description"].fillna("").astype(str).tolist()
            metadatas = batch_df.astype(str).to_dict("records")
            ids = [f"facility_{idx}" for idx in batch_df.index]

            client.add_documents(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"✅ 배치 {batch_num} 완료 ({len(documents)}개 문서)")

        logger.info("🎉 데이터 로드 완료!")
        info = client.get_collection_info()
        logger.info(f"📊 총 문서 수: {info['count']}")
        logger.info(f"📚 컬렉션 이름: {info['name']}")
        return True

    except Exception as e:
        logger.error(f"❌ 데이터 로드 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="CSV 데이터를 ChromaDB에 로드")
    parser.add_argument("csv_path", type=str, help="CSV 파일 경로")
    parser.add_argument("--batch-size", type=int, default=100, help="배치 크기 (기본값: 100)")
    args = parser.parse_args()

    success = load_csv_to_chroma(args.csv_path, args.batch_size)
    if not success:
        sys.exit(1)

    logger.info("🎉 모든 작업 완료!")


if __name__ == "__main__":
    main()