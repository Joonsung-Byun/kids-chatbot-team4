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

# 🌿 Kids Activity Chatbot Backend

## 📖 개요
이 프로젝트는 **LangGraph + RAG + KakaoMap API** 를 이용한  
“아이와 함께할 활동 추천 챗봇”의 **백엔드 서버**입니다.

사용자가 “서울 한남동 근처 놀이터 추천해줘” 같은 문장을 입력하면  
서버는 다음과 같은 순서로 작동합니다 👇

1. **날씨 정보 조회** (`weather tool`)
2. **RAG 기반 장소 검색** (`rag tool`)
3. **KakaoMap 좌표 생성** (`map tool`)
4. **LLM이 최종 답변 생성** (`llm service`)

즉, 여러 도구를 순서대로 호출하는 **LangGraph 기반 의사결정 구조**를  
FastAPI 구조 안에 깔끔하게 녹여낸 형태입니다.

---

## 🏗️ 폴더 구조
backend/
├── main.py
├── routers/
│ ├── chat.py
│ ├── weather.py
│ ├── map.py
│ └── rag.py
├── services/
│ ├── llm_service.py
│ ├── map_service.py
│ ├── rag_service.py
│ └── weather_service.py
├── models/
│ ├── chat_schema.py
│ └── facility_schema.py
├── utils/
│ ├── logger.py
│ ├── config.py
│ └── vector_client.py
├── data/
│ └── embeddings/
├── tests/
│ └── test_chat.py
├── requirements.txt
└── .env



---

## 📦 폴더별 역할

| 폴더 | 설명 |
|-------|------|
| **`main.py`** | FastAPI 서버 진입점. 모든 라우터(router)를 등록하고 앱을 실행함. |
| **`routers/`** | 각 기능별 API 엔드포인트 정의. LangGraph에서 “도구(tool)” 역할을 함. |
| **`services/`** | 실제 데이터 처리 로직. 외부 API 호출, RAG 검색, KakaoMap 처리 등이 포함됨. |
| **`models/`** | Pydantic 스키마 정의. 요청(Request)과 응답(Response) 구조를 명시함. |
| **`utils/`** | 공통 함수(로깅, 환경변수, 벡터DB 연결 등). |
| **`data/`** | 전처리된 CSV, JSON, 임베딩 데이터 저장소. |
| **`tests/`** | 각 기능에 대한 단위 테스트 코드. |

---

## 🧠 LangGraph와의 관계

LangGraph는 **“LLM이 어떤 도구를 언제 사용할지”** 결정하는 프레임워크입니다.  
우리 구조는 LangGraph의 개념을 그대로 코드 구조로 표현합니다 👇

| LangGraph 개념 | 실제 코드 대응 |
|----------------|----------------|
| Node (Tool) | `routers/weather.py`, `routers/rag.py`, `routers/map.py` |
| Edge (연결) | `chat.py` 안의 도구 호출 순서 (weather → rag → map) |
| State (Memory) | `models/chat_schema.py` |
| Controller (Agent) | `routers/chat.py` |

즉, `chat.py`는 “도구를 언제 호출할지 판단하는 AI 라우터” 역할을 하고,  
각 `service`는 실제 작업을 수행하는 LangGraph 노드(node)에 해당합니다.

---

## ⚙️ 작동 흐름 요약
[사용자 요청]
↓
/chat → weather_service → rag_service → map_service → llm_service
↓
[AI 응답 + 지도 데이터 반환]

pgsql
코드 복사

**예시 응답**
```json
{
  "type": "map",
  "message": "한남동 근처 아이와 가기 좋은 공원이에요 🌳",
  "data": {
    "center": { "lat": 37.533, "lng": 127.002 },
    "markers": [
      { "name": "한남어린이공원", "lat": 37.5341, "lng": 127.0013 },
      { "name": "보광어린이공원", "lat": 37.5298, "lng": 127.0025 }
    ]
  }
}
💡 폴더 분리 이유
이유	설명
유지보수성	날씨, RAG, 지도 중 하나만 교체해도 전체 서비스에 영향 없음
LangGraph 호환성	각 도구(tool)가 독립 구조로 존재해 그래프 설계와 1:1 대응
협업 용이성	팀원이 기능별로 분담 가능 (예: A는 RAG, B는 KakaoMap 담당)
테스트 편리성	/tests에서 각 기능을 독립적으로 검증 가능
확장성	나중에 서버리스 구조(AWS Lambda 등)로 옮겨도 유연하게 적용 가능

🧩 간단 요약표
폴더	한 줄 요약	역할
routers/	API 입구	사용자 요청을 받고 service 호출
services/	두뇌(로직)	LLM, RAG, KakaoMap, 날씨 API 등 실제 처리
models/	데이터 설계자	요청/응답 구조 정의
utils/	비서	환경설정, 로깅, DB 연결
data/	자료실	벡터데이터 저장소
tests/	검증기	각 기능 단위 테스트

🔧 환경 변수 예시 (.env)
ini
코드 복사
OPENAI_API_KEY=sk-xxxxxx
KAKAO_REST_API_KEY=xxxxxx
WEATHER_API_KEY=xxxxxx
CHROMA_URL=http://localhost:8000
🧪 실행 방법
bash
코드 복사
# 패키지 설치
pip install -r requirements.txt

# 서버 실행
uvicorn main:app --reload

# (기본 포트: http://localhost:8000)
👥 팀원 참고 요약
LangGraph는 “AI가 어떤 도구를 호출할지 결정하는 뇌”

각 도구는 routers + services 로 나뉘어 구현됨

FastAPI 구조이지만 LangGraph의 노드 구조와 1:1 매칭

코드를 수정할 때는 service → router → main 순서로 확인하면 안전함

📘 Tip:
이 구조를 그대로 유지하면 나중에 OpenAI Function Call, LangChain Agent,
혹은 LangGraph Workflow로 쉽게 전환할 수 있습니다.