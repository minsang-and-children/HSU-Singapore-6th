'''
백테스팅 프로그래밍 개발 계획
1. 테스트 기간은 2025년 1월 ~ 2025년 10월까지 10개월 데이터 사용
2. 수출 서프라이즈 데이터, 실제 일별 주가 데이터 사용 + 코스피 데이터 
3. 종목별 신호 생성 
4. 종목별 포지션 계산 
5. 수익률 계산 및 성과 분석
'''

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# 프로젝트 경로 설정
base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(base_path, 'src'))

from market import Market
from investor import Investor
from surprise_strategy_v2 import SurpriseStrategyV2
import config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
) 


def generate_time_slots():
    """
    장 시작부터 종료까지의 시간 슬롯 생성
    
    Returns:
        list: ['0900_0910', '0910_0920', ..., '1520_1530']
    """
    slots = []
    start_time = config.MARKET_OPEN_HOUR * 60 + config.MARKET_OPEN_MINUTE
    end_time = config.MARKET_CLOSE_HOUR * 60 + config.MARKET_CLOSE_MINUTE
    
    current = start_time
    while current < end_time:
        start_hour = current // 60
        start_min = current % 60
        
        next_time = current + config.TIME_SLOT_INTERVAL
        end_hour = next_time // 60
        end_min = next_time % 60
        
        slot = f'{start_hour:02d}{start_min:02d}_{end_hour:02d}{end_min:02d}'
        slots.append(slot)
        
        current = next_time
    
    return slots


def load_trading_days():
    """
    실제 거래일 목록을 분봉 데이터 파일에서 로드
    
    Returns:
        tuple: (거래일 목록, 최소 날짜, 최대 날짜)
    
    Raises:
        FileNotFoundError: 분봉 데이터 파일이 없는 경우
        ValueError: 데이터 형식이 잘못된 경우
    """
    # 분봉 데이터 파일에서 실제 거래일 추출
    price_file = os.path.join(config.MINUTELY_PRICE_DIR, 'close_0900_0910.csv')
    
    if not os.path.exists(price_file):
        raise FileNotFoundError(
            f"분봉 데이터 파일을 찾을 수 없습니다: {price_file}\n"
            f"데이터 디렉토리를 확인해주세요."
        )
    
    try:
        df = pd.read_csv(price_file)
        
        if df.empty:
            raise ValueError(f"분봉 데이터 파일이 비어있습니다: {price_file}")
        
        date_col = df.columns[0]  # 'Unnamed: 0'
        
        # 날짜를 datetime으로 변환
        trading_days = pd.to_datetime(df[date_col].astype(str), format='%Y%m%d')
        
        if len(trading_days) == 0:
            raise ValueError("유효한 거래일 데이터가 없습니다.")
        
        logging.info(f"거래일 로드 완료: {len(trading_days)}일 ({trading_days.min().date()} ~ {trading_days.max().date()})")
        
        return trading_days.tolist(), trading_days.min(), trading_days.max()
        
    except Exception as e:
        logging.error(f"거래일 로드 중 오류: {e}")
        raise


def create_timeline(start_date, end_date):
    """
    전체 백테스팅 기간의 타임라인을 DataFrame으로 생성
    
    Parameters:
    - start_date: 시작 날짜 ('2025-01-01' 또는 datetime)
    - end_date: 종료 날짜
    
    Returns:
        DataFrame: columns=['date', 'date_int', 'time_slot', 'is_month_first', 'is_signal_time']
    
    Note:
        - 데이터셋 범위 내: 실제 거래일 사용 (공휴일 제외)
        - 데이터셋 범위 외: 주말만 제외 (freq='B')
    """
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    # 실제 거래일 로드
    real_trading_days, data_min_date, data_max_date = load_trading_days()
    
    # 백테스팅 기간과 데이터셋 범위 비교
    if start_dt >= data_min_date and end_dt <= data_max_date:
        # 완전히 데이터셋 범위 내 → 실제 거래일 사용
        trading_days = [day for day in real_trading_days if start_dt <= day <= end_dt]
        print(f'   [INFO] 데이터셋 범위 내 → 실제 거래일 사용 (공휴일 제외)')
    elif start_dt > data_max_date or end_dt < data_min_date:
        # 완전히 데이터셋 범위 외 → 주말만 제외
        trading_days = pd.date_range(start=start_date, end=end_date, freq='B').tolist()
        print(f'   [INFO] 데이터셋 범위 외 → 주말만 제외 (공휴일 포함)')
    else:
        # 혼합: 데이터셋 내/외 구간 분리
        trading_days = []
        
        # 데이터셋 이전 구간
        if start_dt < data_min_date:
            before_days = pd.date_range(start=start_dt, end=data_min_date - timedelta(days=1), freq='B')
            trading_days.extend(before_days.tolist())
            print(f'   [INFO] 데이터셋 이전 구간: 주말만 제외')
        
        # 데이터셋 범위 내 구간
        overlap_start = max(start_dt, data_min_date)
        overlap_end = min(end_dt, data_max_date)
        real_days = [day for day in real_trading_days if overlap_start <= day <= overlap_end]
        trading_days.extend(real_days)
        print(f'   [INFO] 데이터셋 범위 내: 실제 거래일 사용')
        
        # 데이터셋 이후 구간
        if end_dt > data_max_date:
            after_days = pd.date_range(start=data_max_date + timedelta(days=1), end=end_dt, freq='B')
            trading_days.extend(after_days.tolist())
            print(f'   [INFO] 데이터셋 이후 구간: 주말만 제외')
        
        trading_days.sort()
    
    time_slots = generate_time_slots()
    
    # 날짜와 시간 슬롯의 모든 조합 생성
    timeline = []
    for day in trading_days:
        for slot in time_slots:
            # 시그널 발생 조건 확인
            is_signal_day = (day.day == config.SIGNAL_DAY_OF_MONTH)
            is_signal_time = (is_signal_day and slot == config.SIGNAL_TIME_SLOT)
            
            timeline.append({
                'date': day,
                'date_int': int(day.strftime('%Y%m%d')),
                'time_slot': slot,
                'datetime_str': f"{day.strftime('%Y-%m-%d')} {slot}",
                'is_signal_day': is_signal_day,
                'is_signal_time': is_signal_time
            })
    
    return pd.DataFrame(timeline)


class Backtesting:
    """
    수출 서프라이즈 기반 백테스팅 시스템
    """
    
    def __init__(self, start_date, end_date, 
                 initial_capital=None,
                 symbols=None, 
                 long_threshold=None, 
                 short_threshold=None,
                 enable_short=False,
                 zscore_type=None,
                 progress_interval=None):
        """
        Parameters:
        - start_date: 시작 날짜 ('2025-01-01')
        - end_date: 종료 날짜 ('2025-10-31')
        - initial_capital: 초기 자본금 (기본값: config.DEFAULT_INITIAL_CAPITAL)
        - symbols: 거래 대상 종목 리스트 (None이면 전체)
        - long_threshold: 매수 시그널 임계값 (기본값: config.DEFAULT_LONG_THRESHOLD)
        - short_threshold: 매도 시그널 임계값 (기본값: config.DEFAULT_SHORT_THRESHOLD)
        - enable_short: Short 전략 사용 여부 (기본값: False)
        - zscore_type: Z-score 타입 (기본값: config.DEFAULT_ZSCORE_TYPE)
        - progress_interval: 진행률 출력 간격 (기본값: config.PROGRESS_REPORT_INTERVAL)
        
        Raises:
        - ValueError: 입력 파라미터가 잘못된 경우
        """
        # 입력 파라미터 검증 및 기본값 설정
        self._validate_and_set_parameters(
            start_date, end_date, initial_capital, 
            long_threshold, short_threshold, enable_short,
            zscore_type, progress_interval
        )
        
        # 거래 대상 종목
        self.symbols = symbols if symbols is not None else self._load_all_symbols()
        
        if len(self.symbols) == 0:
            raise ValueError("거래 가능한 종목이 없습니다. 데이터를 확인해주세요.")
        
        # 타임라인 생성
        try:
            self.timeline = create_timeline(self.start_date, self.end_date)
            self.current_idx = 0
        except Exception as e:
            logging.error(f"타임라인 생성 실패: {e}")
            raise
        
        # 백테스팅 기록
        self.history = []
        
        # 클래스 초기화
        self.market = Market()
        self.strategy = SurpriseStrategyV2(
            base_long_threshold=self.long_threshold, 
            base_short_threshold=self.short_threshold,
            use_sensitivity=config.USE_SENSITIVITY,
            min_pvalue=config.MIN_PVALUE,
            min_sample_size=config.MIN_SAMPLE_SIZE
        )
        self.investor = Investor(initial_capital=self.initial_capital)
        
        self._print_initialization_info()
    
    
    def _validate_and_set_parameters(self, start_date, end_date, initial_capital,
                                     long_threshold, short_threshold, enable_short,
                                     zscore_type, progress_interval):
        """파라미터 검증 및 기본값 설정"""
        # 날짜 검증
        try:
            self.start_date = pd.to_datetime(start_date)
            self.end_date = pd.to_datetime(end_date)
        except Exception as e:
            raise ValueError(f"날짜 형식이 잘못되었습니다: {e}")
        
        if self.start_date >= self.end_date:
            raise ValueError(f"시작 날짜({start_date})가 종료 날짜({end_date})보다 늦습니다.")
        
        # 초기 자본금 검증
        self.initial_capital = initial_capital if initial_capital is not None else config.DEFAULT_INITIAL_CAPITAL
        if self.initial_capital <= 0:
            raise ValueError(f"초기 자본금은 0보다 커야 합니다: {self.initial_capital}")
        
        # 임계값 설정
        self.long_threshold = long_threshold if long_threshold is not None else config.DEFAULT_LONG_THRESHOLD
        self.short_threshold = short_threshold if short_threshold is not None else config.DEFAULT_SHORT_THRESHOLD
        
        # Short 전략 설정
        self.enable_short = enable_short
        
        # Z-score 타입 설정
        self.zscore_type = zscore_type if zscore_type is not None else config.DEFAULT_ZSCORE_TYPE
        if self.zscore_type not in ['mom', 'yoy', 'qoq']:
            raise ValueError(f"잘못된 zscore_type: {self.zscore_type}. 'mom', 'yoy', 'qoq' 중 하나를 선택하세요.")
        
        # 진행률 출력 간격
        self.progress_interval = progress_interval if progress_interval is not None else config.PROGRESS_REPORT_INTERVAL
    
    
    def _print_initialization_info(self):
        """초기화 정보 출력"""
        print(f'=' * 80)
        print(f'백테스팅 초기화')
        print(f'=' * 80)
        print(f'기간: {self.start_date.date()} ~ {self.end_date.date()}')
        print(f'거래일 수: {self.timeline["date"].nunique()}일')
        print(f'총 타임스탬프: {len(self.timeline):,}개')
        print(f'초기 자본금: {self.initial_capital:,}원')
        print(f'거래 대상 종목: {len(self.symbols)}개')
        print(f'Long 임계값: {self.long_threshold} (기본값)')
        print(f'Short 전략: {"사용" if self.enable_short else "미사용"}')
        print(f'Z-score 타입: {self.zscore_type}')
        
        # 민감도 기반 전략 정보
        if config.USE_SENSITIVITY:
            print(f'민감도 전략: 활성화 🎯')
            print(f'  - p-value 임계값: {config.MIN_PVALUE}')
            print(f'  - 최소 샘플: {config.MIN_SAMPLE_SIZE}개')
            print(f'  - 산업별 임계값 자동 조정')
        else:
            print(f'민감도 전략: 비활성화 (모든 종목 동일 임계값)')
        
        # 홀딩 기간 정보
        if config.HOLDING_PERIOD_ENABLED:
            unit_name = '분' if config.HOLDING_PERIOD_UNIT == 'minutes' else '일'
            print(f'홀딩 기간: {config.HOLDING_PERIOD_VALUE}{unit_name} (자동 매도)')
        else:
            print(f'홀딩 기간: 시그널 기반 (매월 리밸런싱)')
        
        print(f'=' * 80)
    
    
    def _load_all_symbols(self):
        """
        데이터에서 사용 가능한 모든 종목 로드
        
        Returns:
        - list: 종목 코드 리스트
        
        Raises:
        - FileNotFoundError: 데이터 파일이 없는 경우
        """
        # export_with_surprise.csv에서 종목 리스트 추출
        export_surprise_path = config.EXPORT_SURPRISE_PATH
        
        if not os.path.exists(export_surprise_path):
            raise FileNotFoundError(
                f"수출 서프라이즈 데이터 파일을 찾을 수 없습니다: {export_surprise_path}"
            )
        
        try:
            df = pd.read_csv(export_surprise_path)
            
            if config.SYMBOL_COLUMN not in df.columns:
                raise ValueError(f"'{config.SYMBOL_COLUMN}' 컬럼을 찾을 수 없습니다.")
            
            symbols = df[config.SYMBOL_COLUMN].unique().tolist()
            
            logging.info(f"종목 로드 완료: {len(symbols)}개")
            
            return symbols
            
        except Exception as e:
            logging.error(f"종목 로드 중 오류: {e}")
            raise
    
    
    def get_current_time(self):
        """현재 시간 반환"""
        if self.current_idx >= len(self.timeline):
            return None
        return self.timeline.iloc[self.current_idx]
    
    
    def run(self):
        """백테스팅 실행"""
        print(f'\n백테스팅 시작...\n')
        
        # 전체 타임라인을 순회
        for idx, row in self.timeline.iterrows():
            self.current_idx = idx
            
            date = row['date']
            date_int = row['date_int']
            time_slot = row['time_slot']
            is_signal_time = row['is_signal_time']
            
            # 시그널 시점 (매월 1일 10:20-10:30)
            if is_signal_time:
                self._generate_signals(date)
            
            # 홀딩 기간 체크 및 자동 매도
            if config.HOLDING_PERIOD_ENABLED:
                self._check_and_sell_by_holding_period(date_int, time_slot)
            
            # 포트폴리오 가치 평가
            self._update_portfolio_value(date_int, time_slot)
            
            # 진행 상황 표시
            if idx % self.progress_interval == 0:
                progress = (idx / len(self.timeline)) * 100
                print(f'   진행: {progress:.1f}% [{idx}/{len(self.timeline)}] - {date.strftime("%Y-%m-%d")} {time_slot}')
        
        print(f'\n백테스팅 완료!\n')
        self._print_results()
    
    
    def _check_and_sell_by_holding_period(self, date_int, time_slot):
        """
        홀딩 기간이 경과한 종목 자동 매도
        
        Parameters:
        - date_int: 현재 날짜 (정수)
        - time_slot: 현재 시간 슬롯
        """
        # 홀딩 기간 경과 종목 확인
        symbols_to_sell = self.investor.check_holding_period(
            date_int, 
            time_slot,
            config.HOLDING_PERIOD_VALUE,
            config.HOLDING_PERIOD_UNIT
        )
        
        if not symbols_to_sell:
            return
        
        # 경과 종목 매도
        logging.info(f'홀딩 기간 경과: {len(symbols_to_sell)}개 종목 매도')
        
        for symbol in symbols_to_sell:
            quantity = self.investor.get_position(symbol)
            if quantity <= 0:
                continue
            
            # 현재 가격 조회
            price = self.market.get_minutely_price(symbol, date_int, time_slot, price_type='close')
            
            # 가격이 유효하면 매도
            if price is not None and not pd.isna(price) and price > 0:
                success = self.investor.sell(symbol, quantity, price, date_int, time_slot)
                if success:
                    logging.info(f'  └─ {symbol}: {quantity}주 매도 (단가: {price:,.0f}원)')
            else:
                # 가격이 없으면 매도 불가 (강제 청산 옵션은 별도 구현 필요)
                logging.warning(f'  └─ {symbol}: 매도 불가 (가격 없음)')
    
    
    def _generate_signals(self, date):
        """
        시그널 생성 및 매매 실행
        
        Parameters:
        - date: 현재 날짜
        """
        print(f'   [시그널 생성] {date.strftime("%Y-%m-%d")} (매월 {config.SIGNAL_DAY_OF_MONTH}일 {config.SIGNAL_TIME_SLOT})')
        
        # 해당 월의 시그널 생성
        month_str = date.strftime('%Y-%m')
        
        try:
            signals_df = self.strategy.get_signals(self.symbols, month_str, zscore_type=self.zscore_type)
        except Exception as e:
            logging.error(f"시그널 생성 중 오류 ({month_str}): {e}")
            return
        
        if signals_df.empty:
            print(f'      └─ 시그널 없음 (데이터 부족: {month_str})')
            self._clear_all_positions()
            return
        
        print(f'      └─ 데이터 있음: {len(signals_df)}개 종목')
        
        # Z-score 범위 출력 (디버깅용)
        if len(signals_df) > 0:
            zscore_min = signals_df['zscore'].min()
            zscore_max = signals_df['zscore'].max()
            print(f'         Z-score 범위: {zscore_min:.2f} ~ {zscore_max:.2f}')
        
        # Long 및 Short 시그널 필터링
        long_signals = signals_df[signals_df['signal'] == 1]
        short_signals = signals_df[signals_df['signal'] == -1] if self.enable_short else pd.DataFrame()
        
        # 시그널 정보 출력
        n_long = len(long_signals)
        n_short = len(short_signals)
        
        if n_long == 0 and n_short == 0:
            print(f'      └─ 거래 시그널 없음 (Long 임계값: {self.long_threshold}, Short: {self.short_threshold})')
            self._clear_all_positions()
            return
        
        print(f'      └─ Long: {n_long}개, Short: {n_short}개')
        
        # 포트폴리오 가중치 계산
        target_weights = self._calculate_portfolio_weights(long_signals, short_signals)
        
        # 리밸런싱 실행
        self._execute_rebalancing(target_weights, date)
    
    
    def _clear_all_positions(self):
        """모든 포지션 청산"""
        current_time = self.get_current_time()
        if current_time is not None:
            date_int = current_time['date_int']
            time_slot = config.SIGNAL_TIME_SLOT
            try:
                self.investor.rebalance({}, self.market, date_int, time_slot)
            except Exception as e:
                logging.error(f"포지션 청산 중 오류: {e}")
    
    
    def _calculate_portfolio_weights(self, long_signals, short_signals):
        """
        포트폴리오 가중치 계산 (Long/Short 통합)
        
        Parameters:
        - long_signals: Long 시그널 DataFrame
        - short_signals: Short 시그널 DataFrame
        
        Returns:
        - dict: {symbol: weight} 형태의 가중치
        """
        target_weights = {}
        total_signals = len(long_signals) + len(short_signals)
        
        if total_signals == 0:
            return target_weights
        
        # 동일 가중 방식
        if config.PORTFOLIO_WEIGHTING == 'equal':
            weight_per_stock = 1.0 / total_signals
            
            # Long 포지션
            for symbol in long_signals.index:
                target_weights[symbol] = weight_per_stock
            
            # Short 포지션 (음수 가중치)
            if self.enable_short:
                for symbol in short_signals.index:
                    target_weights[symbol] = -weight_per_stock
        
        return target_weights
    
    
    def _execute_rebalancing(self, target_weights, date):
        """
        리밸런싱 실행
        
        Parameters:
        - target_weights: 목표 가중치 딕셔너리
        - date: 거래 날짜
        """
        if not target_weights:
            return
        
        # 시그널 요약 출력
        long_symbols = [s for s, w in target_weights.items() if w > 0]
        short_symbols = [s for s, w in target_weights.items() if w < 0]
        
        if long_symbols:
            weight = target_weights[long_symbols[0]] * 100
            print(f'         Long: {", ".join(long_symbols[:5])}{"..." if len(long_symbols) > 5 else ""} (각 {weight:.1f}%)')
        
        if short_symbols:
            weight = abs(target_weights[short_symbols[0]]) * 100
            print(f'         Short: {", ".join(short_symbols[:5])}{"..." if len(short_symbols) > 5 else ""} (각 {weight:.1f}%)')
        
        # 리밸런싱 실행
        current_time = self.get_current_time()
        if current_time is not None:
            date_int = current_time['date_int']
            time_slot = config.SIGNAL_TIME_SLOT
            
            try:
                self.investor.rebalance(target_weights, self.market, date_int, time_slot)
                logging.info(f"리밸런싱 완료: Long {len(long_symbols)}개, Short {len(short_symbols)}개")
            except Exception as e:
                logging.error(f"리밸런싱 실행 중 오류: {e}")
                raise
    
    
    def _update_portfolio_value(self, date_int, time_slot):
        """
        포트폴리오 가치 업데이트
        
        Parameters:
        - date_int: 날짜 (정수, 20250102)
        - time_slot: 시간 슬롯 ('0900_0910')
        """
        # 포트폴리오 총 가치 계산
        try:
            total_value = self.investor.get_portfolio_value(self.market, date_int, time_slot)
        except Exception as e:
            logging.warning(f"포트폴리오 가치 계산 중 오류 ({date_int} {time_slot}): {e}")
            total_value = self.investor.get_cash()  # 오류 시 현금만 계산
        
        # 기록 저장 (매일 장 마감 시간에만 저장)
        if time_slot == config.CLOSING_TIME_SLOT:
            self.history.append({
                'date': date_int,
                'date_str': pd.to_datetime(str(date_int), format='%Y%m%d').strftime('%Y-%m-%d'),
                'cash': self.investor.get_cash(),
                'stock_value': total_value - self.investor.get_cash(),
                'total_value': total_value,
                'portfolio': self.investor.get_portfolio().copy()
            })
    
    
    def _print_results(self):
        """백테스팅 결과 출력"""
        print(f'=' * 80)
        print(f'백테스팅 결과')
        print(f'=' * 80)
        
        if not self.history:
            print('기록된 데이터가 없습니다.')
            print(f'=' * 80)
            return
        
        # 최종 가치
        final_value = self.history[-1]['total_value']
        final_cash = self.history[-1]['cash']
        final_stock = self.history[-1]['stock_value']
        
        # 수익률 계산
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        
        # 일별 수익률 계산
        history_df = pd.DataFrame(self.history)
        history_df['daily_return'] = history_df['total_value'].pct_change(fill_method=None)
        
        # 샤프 비율 계산 (연율화)
        if len(history_df) > 1:
            daily_returns = history_df['daily_return'].dropna()
            excess_return = daily_returns.mean() - (config.RISK_FREE_RATE / config.ANNUAL_TRADING_DAYS)
            sharpe_ratio = np.sqrt(config.ANNUAL_TRADING_DAYS) * (excess_return / daily_returns.std()) if daily_returns.std() > 0 else 0
            
            # MDD (Maximum Drawdown) 계산
            cumulative = (1 + history_df['daily_return'].fillna(0)).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            mdd = drawdown.min() * 100
        else:
            sharpe_ratio = 0
            mdd = 0
        
        # 거래 통계
        total_trades = len(self.investor.trade_history)
        buy_trades = len([t for t in self.investor.trade_history if t['action'] == 'BUY'])
        sell_trades = len([t for t in self.investor.trade_history if t['action'] == 'SELL'])
        
        # 코스피 수익률 계산
        kospi_return = self._calculate_kospi_return()
        excess_return = total_return - kospi_return if kospi_return is not None else None
        
        # 결과 출력
        print(f'\n[성과 요약]')
        print(f'   초기 자본금:     {self.initial_capital:>15,}원')
        print(f'   최종 자산:       {final_value:>15,.0f}원')
        print(f'   └─ 현금:         {final_cash:>15,.0f}원')
        print(f'   └─ 주식:         {final_stock:>15,.0f}원')
        print(f'   총 수익률:       {total_return:>15.2f}%')
        if kospi_return is not None:
            print(f'   코스피 수익률:   {kospi_return:>15.2f}%')
            print(f'   초과 수익률:     {excess_return:>15.2f}%p')
        
        print(f'\n[위험 지표]')
        print(f'   샤프 비율:       {sharpe_ratio:>15.2f}')
        print(f'   MDD:             {mdd:>15.2f}%')
        
        print(f'\n[거래 통계]')
        print(f'   총 거래 횟수:    {total_trades:>15,}회')
        print(f'   └─ 매수:         {buy_trades:>15,}회')
        print(f'   └─ 매도:         {sell_trades:>15,}회')
        print(f'   거래 기간:       {len(history_df):>15,}일')
        
        print(f'\n[최종 포트폴리오]')
        final_portfolio = self.investor.get_portfolio()
        if final_portfolio:
            print(f'   보유 종목 수:    {len(final_portfolio):>15,}개')
            for i, (symbol, position) in enumerate(list(final_portfolio.items())[:5], 1):
                qty = position['quantity']
                avg_price = position['avg_price']
                print(f'   {i}. {symbol:<10} {qty:>10,}주 (평균 {avg_price:>10,.0f}원)')
            if len(final_portfolio) > 5:
                print(f'   ... 외 {len(final_portfolio) - 5}개 종목')
        else:
            print(f'   보유 종목 없음')
        
        print(f'\n' + '=' * 80)
    
    
    def _calculate_kospi_return(self):
        """
        백테스팅 기간 동안의 코스피 수익률 계산
        
        Returns:
        - float: 코스피 수익률 (%), None if 계산 실패
        """
        try:
            import pandas as pd
            import os
            
            # kospi.csv 파일 경로
            kospi_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'kospi.csv')
            logging.info(f'코스피 파일 경로: {kospi_path}')
            
            # 파일 존재 확인
            if not os.path.exists(kospi_path):
                logging.error(f'코스피 파일이 존재하지 않습니다: {kospi_path}')
                return None
            
            # 코스피 데이터 로드
            kospi_df = pd.read_csv(kospi_path)
            kospi_df.columns = kospi_df.columns.str.strip()  # 공백 제거
            logging.info(f'코스피 데이터 로드 완료: {len(kospi_df)}행')
            logging.info(f'코스피 컬럼: {kospi_df.columns.tolist()}')
            
            # 날짜를 정수로 변환
            if 'Unnamed: 0' in kospi_df.columns:
                kospi_df['date'] = kospi_df['Unnamed: 0'].astype(int)
            else:
                kospi_df['date'] = kospi_df.iloc[:, 0].astype(int)
            
            # 시작일과 종료일을 정수로 변환 (pandas Timestamp 객체 처리)
            if hasattr(self.start_date, 'strftime'):
                # pandas Timestamp 객체인 경우
                start_date_int = int(self.start_date.strftime('%Y%m%d'))
                end_date_int = int(self.end_date.strftime('%Y%m%d'))
            else:
                # 문자열인 경우
                start_date_int = int(str(self.start_date).replace('-', ''))
                end_date_int = int(str(self.end_date).replace('-', ''))
            logging.info(f'백테스팅 기간: {start_date_int} ~ {end_date_int}')
            
            # 시작일과 종료일의 코스피 지수 찾기
            start_kospi = kospi_df[kospi_df['date'] == start_date_int]['close']
            end_kospi = kospi_df[kospi_df['date'] == end_date_int]['close']
            
            # 정확한 날짜가 없으면 가장 가까운 날짜 찾기
            if len(start_kospi) == 0:
                # 시작일 이후 첫 거래일
                available_dates = kospi_df[kospi_df['date'] >= start_date_int]
                if len(available_dates) > 0:
                    start_kospi = available_dates.iloc[0]['close']
                    actual_start_date = available_dates.iloc[0]['date']
                    logging.info(f'시작일 {start_date_int} → 가장 가까운 날짜 {actual_start_date} 사용')
                else:
                    start_kospi = None
            else:
                start_kospi = start_kospi.values[0]
                logging.info(f'시작일 {start_date_int} 코스피: {start_kospi}')
            
            if len(end_kospi) == 0:
                # 종료일 이전 마지막 거래일
                available_dates = kospi_df[kospi_df['date'] <= end_date_int]
                if len(available_dates) > 0:
                    end_kospi = available_dates.iloc[-1]['close']
                    actual_end_date = available_dates.iloc[-1]['date']
                    logging.info(f'종료일 {end_date_int} → 가장 가까운 날짜 {actual_end_date} 사용')
                else:
                    end_kospi = None
            else:
                end_kospi = end_kospi.values[0]
                logging.info(f'종료일 {end_date_int} 코스피: {end_kospi}')
            
            # 수익률 계산
            if start_kospi is not None and end_kospi is not None and start_kospi > 0:
                kospi_return = ((end_kospi - start_kospi) / start_kospi) * 100
                logging.info(f'✅ 코스피 수익률 계산 완료: {kospi_return:.2f}%')
                return kospi_return
            else:
                logging.warning(f'❌ 코스피 데이터를 찾을 수 없습니다: start={start_kospi}, end={end_kospi}')
                return None
                
        except Exception as e:
            logging.error(f'❌ 코스피 수익률 계산 실패: {e}')
            import traceback
            logging.error(traceback.format_exc())
            return None
    
    
    def get_history_df(self):
        """
        백테스팅 히스토리를 DataFrame으로 반환
        
        Returns:
        - DataFrame: 날짜별 포트폴리오 가치 기록
        """
        if not self.history:
            return pd.DataFrame()
        
        history_df = pd.DataFrame(self.history)
        history_df['daily_return'] = history_df['total_value'].pct_change(fill_method=None)
        
        return history_df 