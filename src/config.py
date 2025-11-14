"""
백테스팅 시스템 설정 파일
모든 상수와 설정값을 중앙에서 관리
"""
import os

# ==================== 경로 설정 ====================
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_PATH, 'data')
DAILY_PRICE_DIR = os.path.join(DATA_PATH, 'price')
MINUTELY_PRICE_DIR = os.path.join(DATA_PATH, 'price_minutely')
EXPORT_SURPRISE_PATH = os.path.join(DATA_PATH, 'export_with_surprise.csv')
EXPORT_VALUE_PATH = os.path.join(DATA_PATH, 'export_value.csv')
KOSPI_PATH = os.path.join(DATA_PATH, 'kospi.csv')


# ==================== 시장 시간 설정 ====================
MARKET_OPEN_HOUR = 9        # 장 시작 시간 (09:00)
MARKET_OPEN_MINUTE = 0
MARKET_CLOSE_HOUR = 15      # 장 마감 시간 (15:30)
MARKET_CLOSE_MINUTE = 30
TIME_SLOT_INTERVAL = 10     # 시간 슬롯 간격 (분)


# ==================== 시그널 설정 ====================
SIGNAL_DAY_OF_MONTH = 1            # 시그널 발생 날짜 (매월 1일)
SIGNAL_TIME_SLOT = '1020_1030'     # 시그널 발생 시간 (10:20-10:30)
CLOSING_TIME_SLOT = '1520_1530'    # 포트폴리오 평가 시간 (15:20-15:30)


# ==================== 백테스팅 설정 ====================
DEFAULT_INITIAL_CAPITAL = 100_000_000   # 기본 초기 자본금 (1억원)
DEFAULT_LONG_THRESHOLD = 0.3            # 기본 Long 임계값 (0.4 → 0.3으로 낮춤)
DEFAULT_SHORT_THRESHOLD = -0.3          # 기본 Short 임계값
PROGRESS_REPORT_INTERVAL = 100          # 진행률 출력 간격 (타임스탬프 단위)


# ==================== 전략 설정 ====================
DEFAULT_ZSCORE_TYPE = 'mom'             # 기본 Z-score 타입 (mom, yoy, qoq)
PORTFOLIO_WEIGHTING = 'equal'           # 포트폴리오 가중 방식 (equal, value_weighted)

# 민감도 기반 전략 설정
USE_SENSITIVITY = True                  # 민감도 기반 임계값 조정 활성화
MIN_PVALUE = 0.5                        # 최대 p-value (0.2 → 0.5로 완화)
MIN_SAMPLE_SIZE = 20                    # 최소 샘플 크기 (30 → 20으로 완화)
# 참고:
#   - 보수적: MIN_PVALUE=0.05, MIN_SAMPLE_SIZE=100 → 유의미한 종목만
#   - 공격적: MIN_PVALUE=0.5, MIN_SAMPLE_SIZE=20 → 더 많은 종목 (현재 설정)
#   - 균형: MIN_PVALUE=0.1, MIN_SAMPLE_SIZE=50

# 홀딩 기간 설정
HOLDING_PERIOD_ENABLED = True          # 홀딩 기간 규칙 사용 여부
HOLDING_PERIOD_UNIT = 'days'            # 'minutes' 또는 'days'
HOLDING_PERIOD_VALUE = 30               # 홀딩 기간 (분 또는 일)
# 예시:
#   - HOLDING_PERIOD_UNIT='minutes', VALUE=60 → 매수 후 60분(1시간) 후 매도
#   - HOLDING_PERIOD_UNIT='days', VALUE=30 → 매수 후 30일 후 매도


# ==================== 성과 분석 설정 ====================
RISK_FREE_RATE = 0.0                    # 무위험 수익률 (샤프비율 계산용)
ANNUAL_TRADING_DAYS = 252               # 연간 거래일 수 (연율화 계산용)


# ==================== 데이터 컬럼명 ====================
DATE_COLUMN = 'Unnamed: 0'              # CSV 파일의 날짜 컬럼명
SYMBOL_COLUMN = 'symbol'                # 종목 코드 컬럼명

