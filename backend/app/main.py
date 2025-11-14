"""
Presto Backtesting API
CSV 기반 백테스팅 전용 서버
"""
import logging
import sys
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .api import backtesting

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Presto Backtesting API",
    description="CSV 기반 백테스팅 전용 API",
    version="1.0.0"
)

# CORS 설정 (React 프론트엔드 연결용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 요청 로깅 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """모든 HTTP 요청 로깅"""
    start_time = datetime.now()
    
    # 요청 로그
    logger.info(f"➡️  {request.method} {request.url.path}")
    
    # 응답 처리
    response = await call_next(request)
    
    # 응답 로그
    duration = (datetime.now() - start_time).total_seconds()
    logger.info(f"⬅️  {request.method} {request.url.path} | Status: {response.status_code} | Duration: {duration:.3f}s")
    
    return response


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행"""
    logger.info("=" * 80)
    logger.info("🚀 Presto Backtesting API 시작")
    logger.info("=" * 80)
    logger.info(f"📍 API Docs: http://localhost:8000/docs")
    logger.info(f"📍 Health Check: http://localhost:8000/health")
    logger.info(f"📊 Backtesting API: http://localhost:8000/api/backtesting/*")
    logger.info("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 실행"""
    logger.info("=" * 80)
    logger.info("🛑 Presto Backtesting API 종료")
    logger.info("=" * 80)


# 백테스팅 API 라우터 등록
app.include_router(backtesting.router)


@app.get("/", tags=["system"])
async def root():
    """API 루트 엔드포인트"""
    logger.info("📌 Root endpoint accessed")
    return {
        "message": "Presto Backtesting API",
        "version": "1.0.0",
        "docs": "/docs",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", tags=["system"])
async def health_check():
    """헬스체크 엔드포인트"""
    logger.info("✅ Health check passed")
    return {
        "status": "healthy",
        "service": "backtesting-api",
        "timestamp": datetime.now().isoformat()
    }
