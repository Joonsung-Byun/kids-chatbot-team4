# Kids Chatbot Team 4 Project

이 프로젝트는 아이들을 위한 챗봇 애플리케이션입니다.

## 프로젝트 구조

```
kids-chatbot-team4/
├── frontend/          # 프론트엔드 코드
├── backend/           # 백엔드 코드
├── .gitignore        # Git에서 제외할 파일 목록
└── README.md         # 프로젝트 설명서
```

## 시작하기

### 사전 요구사항

- Node.js (v14 이상)
- npm 또는 yarn
- Python (백엔드용)

### 설치

1. 프로젝트 클론
```bash
git clone <repository-url>
cd kids-chatbot-team4
```

2. Frontend 설정
```bash
cd frontend
npm install
```

3. Backend 설정
```bash
cd backend
pip install -r requirements.txt
```

### 환경 변수 설정

각 폴더(frontend, backend)에 `.env` 파일을 생성하여 환경 변수를 설정하세요.

**주의: .env 파일은 민감한 정보를 포함하므로 Git에 커밋하지 마세요.**

### 실행

Frontend:
```bash
cd frontend
npm start
```

Backend:
```bash
cd backend
python app.py
```

## 기여하기

1. 이 저장소를 포크하세요
2. 기능 브랜치를 생성하세요 (`git checkout -b feature/새로운기능`)
3. 변경사항을 커밋하세요 (`git commit -am '새로운 기능 추가'`)
4. 브랜치에 푸시하세요 (`git push origin feature/새로운기능`)
5. Pull Request를 생성하세요

## 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다.