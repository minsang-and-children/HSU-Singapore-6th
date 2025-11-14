"""
백테스팅 실행 메인 스크립트
"""
from backtesting import Backtesting

# ==================== 백테스팅 설정 ====================
# 통계적 임계값 가이드:
#   - 2σ (±2.0): 상위/하위 2.5% (극단값, 매우 보수적)
#   - 1σ (±1.0): 상위/하위 16% (보수적)
#   - 0.5σ (±0.5): 상위/하위 31% (중간)
#
# 실제 데이터 분석 결과 (2021년):
#   최대 Z-score: 0.94
#   최소 Z-score: -1.85

# 백테스팅 초기화
backtest = Backtesting(
    start_date='2024-01-04',
    end_date='2024-12-31',
    initial_capital=100_000_000,  # 1억원
    symbols=None,  # 전체 종목 (None이면 전체)
    long_threshold=0.4,  # Long 임계값
    short_threshold=-0.4,  # Short 임계값
    enable_short=False,  # Short 전략 사용 여부
    zscore_type='mom',  # 'mom', 'yoy', 'qoq' 중 선택
    progress_interval=100  # 진행률 출력 간격
)

# 백테스팅 실행
import time
start_time = time.time()

backtest.run()

end_time = time.time()
elapsed_time = end_time - start_time

# 성능 정보 출력
print('\n' + '=' * 80)
print('성능 정보')
print('=' * 80)
print(f'백테스팅 소요 시간: {elapsed_time:.2f}초')
print(f'캐시 정보: {backtest.market.get_cache_info()}')
print('=' * 80)

# 결과 DataFrame 확인
history_df = backtest.get_history_df()

# 상세 결과 출력 (선택사항)
print('\n' + '=' * 80)
print('상세 히스토리')
print('=' * 80)
if len(history_df) > 0:
    print(history_df[['date_str', 'total_value', 'cash', 'stock_value', 'daily_return']].head(20))
    print(f'\n... (총 {len(history_df)}일)')
else:
    print('히스토리 데이터가 없습니다.')
print('=' * 80)