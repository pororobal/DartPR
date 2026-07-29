# DartPR — 실시간 DART 공시 분석 플랫폼

DartPR은 DART(전자공시시스템) 공시를 실시간으로 수집하여 규칙 엔진(DVI 0-100)과 AI(Groq LLM)로 분석하는 트레이딩 인사이트 플랫폼입니다.

## 핵심 기능

- **실시간 피드**: Supabase Realtime 기반 공시 실시간 스트리밍
- **DVI 스코어링**: 150+ 규칙 기반 점수 엔진 (0-100)
- **AI 요약**: Groq LLM으로 공시 핵심 요약 및 감성 분석
- **히스토리**: 과거 공시 검색/필터/점수 조회
- **프리미엄**: 실시간(무료 3분 지연), Pro(실시간 + API), Dev(API 키)

## 아키텍처

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Next.js    │────▶│  FastAPI     │────▶│  Supabase   │
│  (Vercel)   │     │  (Render)    │     │  (DB+Auth)  │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────┴───────┐
                    │  Groq LLM   │
                    │  (AI 분석)   │
                    └──────────────┘
```

### 백엔드 (`backend/`)
- **FastAPI** + Python 3.12
- DART OpenAPI 5분 간격 폴링
- 규칙 엔진: 카테고리 분류 → 서브룰 매칭 → DVI 스코어링 → LLM 라우팅
- 30~59점 모호 공시: Cerebras LLM 감성 분석 → 점수 피드백
- 사용자 플랜: free/pro/admin (Supabase Auth)

### 프론트엔드 (`frontend/`)
- **Next.js 16** + Tailwind CSS v4
- Supabase Auth (이메일/비밀번호)
- 실시간 피드, 히스토리, 어드민, 마이페이지
- 반응형 다크 테마

## 로컬 개발

### 백엔드
```bash
cd backend
cp .env.example .env  # API 키 입력
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 프론트엔드
```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

### 테스트
```bash
cd backend
pytest -v
```

## 배포

### 백엔드 (Render)
- `backend/render.yaml` 참고
- GitHub `main` 브랜치 푸시 시 자동 배포
- 또는 Docker: `docker build -t dartpr-backend ./backend`

### 프론트엔드 (Vercel)
- `frontend/vercel.json` 참고
- GitHub 연결로 자동 배포

## 환경 변수

| 변수 | 설명 |
|------|------|
| `OPENDART_API_KEY` | DART OpenAPI 키 |
| `GROQ_API_KEY` | Groq LLM API 키 |
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase 서비스 롤 키 |
| `JWT_SECRET` | JWT 서명 키 |
| `CORS_ORIGINS` | 허용 오리진 (콤마 구분) |

## DVI 점수 가이드

| 점수 | 의미 | 피드 노출 | AI 분석 |
|------|------|-----------|---------|
| 80-100 | 강한 시그널 (경영권분쟁, 자사주 소각, FDA 승인) | ✅ | ✅ 요약 |
| 60-79 | 중간 시그널 (합병, 유증, 계약 체결) | ✅ | ✅ 요약 |
| 30-59 | 모호/저신호 (선택적 Cerebras 분석) | 조건부 | 조건부 |
| 0-29 | 노이즈/행정/배당 | ❌ | ❌ |
