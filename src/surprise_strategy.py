
import pandas as pd
import numpy as np
import os

# 데이터 경로
data_path = os.path.join(os.path.dirname(__file__), '..', 'data')

class SurpriseStrategy:
    def __init__(self, long_threshold=2.0, short_threshold=-2.0):
        """
        수출 서프라이즈 기반 트레이딩 전략
        
        Parameters:
        - long_threshold: Long 포지션 진입 임계값 (z-score)
        - short_threshold: Short 포지션 진입 임계값 (z-score)
        """
        self.long_threshold = long_threshold
        self.short_threshold = short_threshold
        self.signals = None
        self.export_with_surprise_data_path = os.path.join(data_path, 'export_with_surprise.csv')
        self._cached_data = None  # 데이터 캐싱
        
        # CSV 파일의 실제 컬럼명 (대소문자 구분)
        self.COLUMNS = {
            'date': 'date',
            'symbol': 'symbol',
            'export_value': 'export_value',
            'mom': 'MoM',  # 대문자!
            'yoy': 'YoY',  # 대문자!
            'qoq': 'QoQ',  # 대문자!
            'zscore_mom': 'rolling_zscore_mom',
            'zscore_yoy': 'rolling_zscore_yoy',
            'zscore_qoq': 'rolling_zscore_qoq'
        }
    

    def _load_data(self):
        """
        CSV 파일을 로드하고 캐싱 (성능 최적화)
        """
        if self._cached_data is not None:
            return self._cached_data
        
        if not os.path.exists(self.export_with_surprise_data_path):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {self.export_with_surprise_data_path}")
        
        surprise_df = pd.read_csv(self.export_with_surprise_data_path)
        
        # Unnamed: 0 컬럼 제거
        if 'Unnamed: 0' in surprise_df.columns:
            surprise_df = surprise_df.drop(columns=['Unnamed: 0'])
        
        # date 컬럼을 datetime으로 변환
        surprise_df[self.COLUMNS['date']] = pd.to_datetime(surprise_df[self.COLUMNS['date']])
        
        # 캐싱
        self._cached_data = surprise_df
        return surprise_df
    
    
    def _get_export_with_surprise(self, symbols, month):
        """
        특정 월의 수출 서프라이즈 데이터 반환 (여러 종목 동시 처리)
        
        Parameters:
        - symbols: 종목 코드 리스트 또는 단일 종목 코드
        - month: 월 (예: '2020-01-31', '2020-01', 202001, 20200131)
        
        Returns:
        - DataFrame: 여러 종목의 수출 서프라이즈 정보 (symbol을 인덱스로)
                    또는 단일 종목인 경우 dict
        """
        # 캐싱된 데이터 사용
        surprise_df = self._load_data()
        
        # month를 datetime으로 변환 (다양한 형식 지원)
        month_str = str(month).replace('-', '')
        if len(month_str) == 6: 
            month_str = month_str + '01' 
        elif len(month_str) == 8: 
            pass
        else:
            month_str = str(month)
        
        month_dt = pd.to_datetime(month_str)
        target_date = month_dt + pd.offsets.MonthEnd(0)
        
        # symbols가 리스트인지 단일 값인지 확인
        if isinstance(symbols, (list, tuple, np.ndarray, pd.Series)):
            # 여러 종목 동시 처리
            surprise_rows = surprise_df[
                (surprise_df[self.COLUMNS['symbol']].isin(symbols)) & 
                (surprise_df[self.COLUMNS['date']] == target_date)
            ]
            
            if surprise_rows.empty:
                return pd.DataFrame()  # 빈 DataFrame 반환
            
            return surprise_rows.set_index(self.COLUMNS['symbol'])
        else:
            # 단일 종목 처리 (하위 호환성)
            surprise_row = surprise_df[
                (surprise_df[self.COLUMNS['symbol']] == symbols) & 
                (surprise_df[self.COLUMNS['date']] == target_date)
            ]
            
            if surprise_row.empty:
                return None
            
            surprise_data = surprise_row.iloc[0].to_dict()
            return surprise_data 

    
    def get_signals(self, symbols, month, zscore_type='mom'):
        """
        여러 종목의 시그널을 동시에 생성
        
        Parameters:
        - symbols: 종목 코드 리스트
        - month: 월 (예: '2020-01-31', '2020-01', 202001)
        - zscore_type: 사용할 z-score 타입 ('mom', 'yoy', 'qoq')
        
        Returns:
        - DataFrame: symbol을 인덱스로 하는 시그널 DataFrame
                    columns: ['date', 'zscore', 'signal', 'export_value', 'MoM', 'YoY', 'QoQ']
                    signal: 1 (long), -1 (short), 0 (neutral)
        """
        # 여러 종목의 서프라이즈 데이터 가져오기
        surprise_data = self._get_export_with_surprise(symbols, month)
        
        if surprise_data is None or (isinstance(surprise_data, pd.DataFrame) and surprise_data.empty):
            return pd.DataFrame()
        
        # z-score 컬럼 선택 (COLUMNS 딕셔너리 사용)
        zscore_col = self.COLUMNS[f'zscore_{zscore_type}']
        
        # 필요한 컬럼 선택
        cols_to_select = [
            self.COLUMNS['date'],
            self.COLUMNS['export_value'],
            self.COLUMNS['mom'],
            self.COLUMNS['yoy'],
            self.COLUMNS['qoq'],
            zscore_col
        ]
        
        # 시그널 생성
        signals_df = surprise_data[cols_to_select].copy()
        signals_df = signals_df.rename(columns={zscore_col: 'zscore'})
        
        # NaN이 아닌 z-score만 사용
        signals_df = signals_df.dropna(subset=['zscore'])
        
        # 시그널 생성: long(1), short(-1), neutral(0)
        signals_df['signal'] = 0
        signals_df.loc[signals_df['zscore'] >= self.long_threshold, 'signal'] = 1
        signals_df.loc[signals_df['zscore'] <= self.short_threshold, 'signal'] = -1
        
        return signals_df
    
    
    def get_signal(self, symbol, month, zscore_type='mom'): 
        """
        단일 종목의 시그널 생성 (하위 호환성)
        
        Parameters:
        - symbol: 종목 코드
        - month: 월
        - zscore_type: 사용할 z-score 타입 ('mom', 'yoy', 'qoq')
        
        Returns:
        - dict: {'symbol': symbol, 'zscore': float, 'signal': int, 'export_value': float, ...}
        """
        surprise_data = self._get_export_with_surprise(symbol, month)
        
        if surprise_data is None:
            return None
        
        # COLUMNS 딕셔너리 사용
        zscore_col = self.COLUMNS[f'zscore_{zscore_type}']
        zscore = surprise_data.get(zscore_col)
        
        if pd.isna(zscore):
            return None
        
        # 시그널 생성
        if zscore >= self.long_threshold:
            signal = 1  # Long
        elif zscore <= self.short_threshold:
            signal = -1  # Short
        else:
            signal = 0  # Neutral
        
        return {
            'symbol': symbol,
            'date': surprise_data.get(self.COLUMNS['date']),
            'zscore': zscore,
            'signal': signal,
            'export_value': surprise_data.get(self.COLUMNS['export_value']),
            'MoM': surprise_data.get(self.COLUMNS['mom']),
            'YoY': surprise_data.get(self.COLUMNS['yoy']),
            'QoQ': surprise_data.get(self.COLUMNS['qoq'])
        }
    
