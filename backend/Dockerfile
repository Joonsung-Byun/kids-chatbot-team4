# Python 3.10 버전을 기반으로 환경 구성
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# requirements.txt를 먼저 복사하여 라이브러리 설치 (캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 현재 디렉토리(backend)의 모든 파일을 컨테이너 /app으로 복사
COPY . .

# 컨테이너 실행 시 uvicorn 서버 구동
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]