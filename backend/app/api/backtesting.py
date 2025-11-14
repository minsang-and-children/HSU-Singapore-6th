"""
백테스팅 API
- 기존 src/ 모듈 사용 (CSV 기반)
- 한투 API 사용 안 함
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import sys
import os
import asyncio
import logging

# src 모듈 임포트를 위한 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.backtesting import Backtesting
from src.market import Market
from src.investor import Investor
import src.config as bt_config

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backtesting", tags=["backtesting"])

# ============ Request/Response 스키마 ============

class BacktestConfig(BaseModel):
    """백테스팅 설정"""
    start_date: str = Field(..., example="2024-01-04")
    end_date: str = Field(..., example="2024-12-31")
    initial_capital: int = Field(100_000_000, gt=0)
    long_threshold: float = Field(0.4, ge=0)
    short_threshold: float = Field(-0.4, le=0)
    enable_short: bool = False
    zscore_type: str = Field("mom", pattern="^(mom|yoy|qoq)$")
    holding_period_enabled: bool = False
    holding_period_value: int = Field(30, gt=0)
    holding_period_unit: str = Field("days", pattern="^(days|minutes)$")

class PortfolioPosition(BaseModel):
    """포트폴리오 포지션"""
    ticker: str
    shares: float
    current_price: Optional[float]
    current_value: Optional[float]
    buy_price: float
    cost_basis: float
    pnl: Optional[float]
    pnl_percent: Optional[float]
    purchase_date: Optional[int]
    purchase_time: Optional[str]

class PortfolioSummary(BaseModel):
    """포트폴리오 요약"""
    cash: float
    stock_value: float
    total_value: float
    initial_capital: float
    total_pnl: float
    total_pnl_percent: float
    positions_count: int
    positions: List[PortfolioPosition]

class TradeRecord(BaseModel):
    """거래 기록"""
    date: int
    time_slot: Optional[str] = None  # 거래 시간 (예: '1020_1030')
    symbol: str
    action: str
    quantity: float
    price: float
    total: float
    buy_price: Optional[float] = None  # 매수 평균가 (매도 시에만)
    profit_loss: Optional[float] = None  # 손익 금액 (매도 시에만)
    profit_loss_percent: Optional[float] = None  # 손익률 (매도 시에만)

class BacktestStatus(BaseModel):
    """백테스팅 상태"""
    status: str  # idle, running, completed, error
    progress: float
    current_date: Optional[str]
    current_time_slot: Optional[str]
    message: Optional[str]

class BacktestResults(BaseModel):
    """백테스팅 최종 결과"""
    initial_capital: float
    final_value: float
    total_return: float
    kospi_return: Optional[float] = None  # 코스피 수익률
    excess_return: Optional[float] = None  # 초과 수익률
    sharpe_ratio: float
    mdd: float
    total_trades: int
    buy_trades: int
    sell_trades: int
    trading_days: int

# ============ 백테스팅 상태 관리 ============

class BacktestingState:
    """백테스팅 진행 상태 관리 (In-Memory)"""
    def __init__(self):
        self.backtest: Optional[Backtesting] = None
        self.is_running: bool = False
        self.status: str = "idle"
        self.error_message: Optional[str] = None
        self.results_cache: Optional[dict] = None

backtest_state = BacktestingState()

# ============ 백그라운드 태스크 ============

def run_backtest_task():
    """백테스팅을 백그라운드에서 실행"""
    try:
        logger.info("=" * 80)
        logger.info("📊 백테스팅 시작")
        logger.info("=" * 80)
        
        backtest_state.status = "running"
        
        # 백테스팅 실행
        logger.info(f"⏱️  기간: {backtest_state.backtest.start_date} ~ {backtest_state.backtest.end_date}")
        logger.info(f"💰 초기 자본: {backtest_state.backtest.initial_capital:,}원")
        logger.info(f"📈 Long 임계값: {backtest_state.backtest.strategy.base_long_threshold}")
        logger.info(f"🎯 민감도 전략: {'활성화' if backtest_state.backtest.strategy.use_sensitivity else '비활성화'}")
        logger.info(f"🔄 백테스팅 실행 중...")
        
        backtest_state.backtest.run()
        
        logger.info("✅ 백테스팅 완료!")
        backtest_state.status = "completed"
        
        # 결과 캐싱
        logger.info("📊 결과 계산 중...")
        history_df = backtest_state.backtest.get_history_df()
        final_value = history_df['total_value'].iloc[-1]
        initial_capital = backtest_state.backtest.initial_capital
        
        # Sharpe Ratio 계산
        returns = history_df['daily_return'].dropna()
        if len(returns) > 0:
            sharpe = (returns.mean() / returns.std()) * (252 ** 0.5) if returns.std() > 0 else 0
        else:
            sharpe = 0
        
        # MDD 계산
        cummax = history_df['total_value'].cummax()
        drawdown = (history_df['total_value'] - cummax) / cummax
        mdd = drawdown.min() * 100
        
        # 거래 통계
        trades = backtest_state.backtest.investor.trade_history
        buy_trades = len([t for t in trades if t['action'] == 'BUY'])
        sell_trades = len([t for t in trades if t['action'] == 'SELL'])
        total_return = ((final_value - initial_capital) / initial_capital) * 100
        
        # 코스피 수익률 계산
        kospi_return = backtest_state.backtest._calculate_kospi_return()
        excess_return = total_return - kospi_return if kospi_return is not None else None
        
        backtest_state.results_cache = {
            "initial_capital": float(initial_capital),
            "final_value": float(final_value),
            "total_return": float(total_return),
            "kospi_return": float(kospi_return) if kospi_return is not None else None,
            "excess_return": float(excess_return) if excess_return is not None else None,
            "sharpe_ratio": float(sharpe),
            "mdd": float(mdd),
            "total_trades": len(trades),
            "buy_trades": buy_trades,
            "sell_trades": sell_trades,
            "trading_days": len(history_df)
        }
        
        # 결과 로그 출력
        logger.info("=" * 80)
        logger.info("📊 백테스팅 최종 결과")
        logger.info("=" * 80)
        logger.info(f"💰 초기 자본: {initial_capital:,.0f}원")
        logger.info(f"💵 최종 자산: {final_value:,.0f}원")
        logger.info(f"📈 총 수익률: {total_return:+.2f}%")
        if kospi_return is not None:
            logger.info(f"🏦 코스피 수익률: {kospi_return:+.2f}%")
            logger.info(f"✨ 초과 수익률 (알파): {excess_return:+.2f}%p")
        logger.info(f"📊 Sharpe Ratio: {sharpe:.2f}")
        logger.info(f"📉 MDD: {mdd:.2f}%")
        logger.info(f"🔄 총 거래: {len(trades)}회 (매수: {buy_trades}, 매도: {sell_trades})")
        logger.info(f"📅 거래일: {len(history_df)}일")
        logger.info("=" * 80)
        
    except Exception as e:
        backtest_state.status = "error"
        backtest_state.error_message = str(e)
        import traceback
        error_msg = traceback.format_exc()
        logger.error("=" * 80)
        logger.error("❌ 백테스팅 오류 발생")
        logger.error("=" * 80)
        logger.error(f"오류 메시지: {str(e)}")
        logger.error(f"상세 정보:\n{error_msg}")
        logger.error("=" * 80)
    finally:
        backtest_state.is_running = False
        logger.info("🏁 백테스팅 프로세스 종료")

# ============ API 엔드포인트 ============

@router.post("/start")
async def start_backtest(config: BacktestConfig, background_tasks: BackgroundTasks):
    """
    백테스팅 시작
    - 기존 CSV 데이터 사용
    - 백그라운드에서 실행
    """
    logger.info("🚀 백테스팅 시작 요청 받음")
    logger.info(f"   - 기간: {config.start_date} ~ {config.end_date}")
    logger.info(f"   - 초기 자본: {config.initial_capital:,}원")
    logger.info(f"   - Z-score 타입: {config.zscore_type}")
    logger.info(f"   - 보유 기간: {config.holding_period_value} {config.holding_period_unit}")
    
    if backtest_state.is_running:
        logger.warning("⚠️  백테스팅이 이미 실행 중입니다")
        raise HTTPException(
            status_code=400, 
            detail="백테스팅이 이미 실행 중입니다."
        )
    
    try:
        # 설정 적용
        bt_config.HOLDING_PERIOD_ENABLED = config.holding_period_enabled
        bt_config.HOLDING_PERIOD_VALUE = config.holding_period_value
        bt_config.HOLDING_PERIOD_UNIT = config.holding_period_unit
        
        logger.info("⚙️  백테스팅 인스턴스 생성 중...")
        
        # 백테스팅 인스턴스 생성
        backtest = Backtesting(
            start_date=config.start_date,
            end_date=config.end_date,
            initial_capital=config.initial_capital,
            long_threshold=config.long_threshold,
            short_threshold=config.short_threshold,
            enable_short=config.enable_short,
            zscore_type=config.zscore_type
        )
        
        backtest_state.backtest = backtest
        backtest_state.is_running = True
        backtest_state.status = "initializing"
        backtest_state.error_message = None
        backtest_state.results_cache = None
        
        logger.info("✅ 백테스팅 인스턴스 생성 완료")
        logger.info("🔄 백그라운드 태스크 시작...")
        
        # 백그라운드 실행
        background_tasks.add_task(run_backtest_task)
        
        return {
            "status": "started",
            "message": "백테스팅이 시작되었습니다.",
            "config": config.dict()
        }
    
    except Exception as e:
        import traceback
        error_detail = f"백테스팅 시작 실패: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"❌ 백테스팅 시작 실패: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)

@router.get("/status", response_model=BacktestStatus)
async def get_backtest_status():
    """백테스팅 진행 상태 조회"""
    if not backtest_state.backtest:
        return BacktestStatus(
            status="idle",
            progress=0,
            current_date=None,
            current_time_slot=None,
            message="백테스팅이 시작되지 않았습니다."
        )
    
    backtest = backtest_state.backtest
    current_time = backtest.get_current_time()
    
    if current_time is None:
        progress = 100.0 if backtest_state.status == "completed" else 0.0
        current_date_str = None
        current_time_slot = None
    else:
        progress = (backtest.current_idx / len(backtest.timeline)) * 100
        current_date_str = current_time['date'].strftime('%Y-%m-%d')
        current_time_slot = current_time['time_slot']
    
    return BacktestStatus(
        status=backtest_state.status,
        progress=progress,
        current_date=current_date_str,
        current_time_slot=current_time_slot,
        message=backtest_state.error_message
    )

@router.get("/portfolio", response_model=PortfolioSummary)
async def get_current_portfolio():
    """
    현재 포트폴리오 조회
    - CSV 기반 가격 조회 사용
    """
    if not backtest_state.backtest:
        raise HTTPException(
            status_code=404, 
            detail="백테스팅 세션이 없습니다."
        )
    
    backtest = backtest_state.backtest
    investor = backtest.investor
    market = backtest.market
    
    # 현재 시점 정보
    current_time = backtest.get_current_time()
    if current_time is None:
        # 백테스팅 완료 후 마지막 시점 사용
        current_time = backtest.timeline.iloc[-1]
    
    date_int = current_time['date_int']
    time_slot = current_time['time_slot']
    
    # 포트폴리오 데이터 생성 (CSV 기반)
    positions = investor.get_portfolio_for_api(market, date_int, time_slot)
    summary = investor.get_portfolio_summary(market, date_int, time_slot)
    
    return PortfolioSummary(
        **summary,
        positions=[PortfolioPosition(**pos) for pos in positions]
    )

@router.get("/trades", response_model=List[TradeRecord])
async def get_trade_history():
    """거래 히스토리 조회"""
    if not backtest_state.backtest:
        raise HTTPException(
            status_code=404,
            detail="백테스팅 세션이 없습니다."
        )
    
    investor = backtest_state.backtest.investor
    trades = investor.get_trade_history_for_api()
    
    return [TradeRecord(**trade) for trade in trades]

@router.get("/results", response_model=BacktestResults)
async def get_backtest_results():
    """백테스팅 최종 결과 조회"""
    if not backtest_state.backtest:
        raise HTTPException(
            status_code=404,
            detail="백테스팅 세션이 없습니다."
        )
    
    if backtest_state.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"백테스팅이 아직 완료되지 않았습니다. 현재 상태: {backtest_state.status}"
        )
    
    if backtest_state.results_cache:
        # 캐시된 결과 반환
        return BacktestResults(**backtest_state.results_cache)
    
    # 결과 계산 (캐시 없을 때)
    backtest = backtest_state.backtest
    history_df = backtest.get_history_df()
    
    final_value = history_df['total_value'].iloc[-1]
    initial_capital = backtest.initial_capital
    total_return = ((final_value - initial_capital) / initial_capital) * 100
    
    # 거래 통계
    trades = backtest.investor.trade_history
    buy_trades = len([t for t in trades if t['action'] == 'BUY'])
    sell_trades = len([t for t in trades if t['action'] == 'SELL'])
    
    # Sharpe Ratio 계산
    returns = history_df['daily_return'].dropna()
    if len(returns) > 0:
        sharpe = (returns.mean() / returns.std()) * (252 ** 0.5) if returns.std() > 0 else 0
    else:
        sharpe = 0
    
    # MDD 계산
    cummax = history_df['total_value'].cummax()
    drawdown = (history_df['total_value'] - cummax) / cummax
    mdd = drawdown.min() * 100
    
    # 코스피 수익률 계산
    kospi_return = backtest._calculate_kospi_return()
    excess_return = total_return - kospi_return if kospi_return is not None else None
    
    return BacktestResults(
        initial_capital=float(initial_capital),
        final_value=float(final_value),
        total_return=float(total_return),
        kospi_return=float(kospi_return) if kospi_return is not None else None,
        excess_return=float(excess_return) if excess_return is not None else None,
        sharpe_ratio=float(sharpe),
        mdd=float(mdd),
        total_trades=len(trades),
        buy_trades=buy_trades,
        sell_trades=sell_trades,
        trading_days=len(history_df)
    )

@router.post("/stop")
async def stop_backtest():
    """백테스팅 중지 (현재 구조에서는 제한적)"""
    if not backtest_state.is_running:
        raise HTTPException(
            status_code=400,
            detail="실행 중인 백테스팅이 없습니다."
        )
    
    # Note: 백그라운드 태스크는 중간에 멈추기 어려움
    # 추후 개선 필요 (thread/async 제어)
    backtest_state.is_running = False
    
    return {
        "status": "stopped",
        "message": "중지 요청이 전송되었습니다."
    }

@router.delete("/reset")
async def reset_backtest():
    """백테스팅 상태 초기화"""
    backtest_state.backtest = None
    backtest_state.is_running = False
    backtest_state.status = "idle"
    backtest_state.error_message = None
    backtest_state.results_cache = None
    
    return {
        "status": "reset",
        "message": "백테스팅 상태가 초기화되었습니다."
    }

