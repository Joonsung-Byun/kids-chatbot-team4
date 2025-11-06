# Backend

아이들을 위한 챗봇 애플리케이션의 백엔드 API 서버입니다.

## 기술 스택

- Python
- Flask/FastAPI (추후 선택)
- SQLAlchemy (데이터베이스 ORM)
- PostgreSQL/SQLite

## 설치 및 실행

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 가상환경 활성화 (Mac/Linux)
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python app.py
```

## 환경 변수

`.env` 파일을 생성하고 다음과 같이 설정하세요:

```
DATABASE_URL=sqlite:///chatbot.db
SECRET_KEY=your-secret-key-here
DEBUG=True
PORT=3001
OPENAI_API_KEY=your-openai-api-key
```

**중요: 실제 API 키와 비밀 키는 절대 Git에 커밋하지 마세요!**