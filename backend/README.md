# 🚀 Presto Backtesting API

CSV 기반 백테스팅 전용 FastAPI 서버

## 📦 의존성

```bash
pip install -r requirements.txt
```

**핵심 패키지:**
- FastAPI 0.115.5
- Pandas 2.2.0
- Uvicorn 0.30.6

## 🎯 실행 방법

```bash
# 개발 서버
uvicorn app.main:app --reload

# 프로덕션
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 🔗 엔드포인트

- **API 문서**: http://localhost:8000/docs
- **헬스체크**: http://localhost:8000/health

## 📊 백테스팅 API

- `POST /api/backtesting/start` - 백테스팅 시작
- `GET /api/backtesting/status` - 진행 상태
- `GET /api/backtesting/portfolio` - 포트폴리오
- `GET /api/backtesting/results` - 최종 결과

## 🗂️ 구조

```
backend/
├── app/
│   ├── main.py           # FastAPI 앱
│   ├── config.py         # 설정
│   └── api/
│       └── backtesting.py  # 백테스팅 API
└── requirements.txt      # 의존성
```

## ⚙️ 설정

`.env` 파일 (선택):
```env
DEBUG=true
```

---

**Presto Backtesting System v1.0.0**
