"""
수출 서프라이즈 기반 트레이딩 전략 (민감도 개선 버전)
- 산업별 민감도를 고려한 임계값 조정
- 통계적 유의성 필터링
"""
import pandas as pd
import numpy as np
import os

# 데이터 경로
data_path = os.path.join(os.path.dirname(__file__), '..', 'data')

class SurpriseStrategyV2:
    def __init__(self, 
                 base_long_threshold=0.4, 
                 base_short_threshold=-0.4,
                 use_sensitivity=True,
                 min_pvalue=0.1,
                 min_sample_size=50):
        """
        수출 서프라이즈 기반 트레이딩 전략 (민감도 개선)
        
        Parameters:
        - base_long_threshold: 기본 Long 임계값 (민감도 조정 전)
        - base_short_threshold: 기본 Short 임계값
        - use_sensitivity: 민감도 기반 조정 활성화
        - min_pvalue: 최대 p-value (이보다 크면 제외)
        - min_sample_size: 최소 샘플 크기
        """
        self.base_long_threshold = base_long_threshold
        self.base_short_threshold = base_short_threshold
        self.use_sensitivity = use_sensitivity
        self.min_pvalue = min_pvalue
        self.min_sample_size = min_sample_size
        
        # 데이터 경로
        self.export_with_surprise_data_path = os.path.join(data_path, 'export_with_surprise.csv')
        self.sensitivity_data_path = os.path.join(data_path, 'part3_result.csv')
        
        # 캐시
        self._cached_export_data = None
        self._cached_sensitivity = None
        
        # CSV 파일의 실제 컬럼명
        self.COLUMNS = {
            'date': 'date',
            'symbol': 'symbol',
            'export_value': 'export_value',
            'mom': 'MoM',
            'yoy': 'YoY',
            'qoq': 'QoQ',
            'zscore_mom': 'rolling_zscore_mom',
            'zscore_yoy': 'rolling_zscore_yoy',
            'zscore_qoq': 'rolling_zscore_qoq',
            'industry_group': 'industry_group'  # 산업 그룹
        }
        
        # 민감도 데이터 로드
        if self.use_sensitivity:
            self._load_sensitivity_data()
    
    
    def _load_sensitivity_data(self):
        """
        산업별 민감도 데이터 로드 및 처리
        """
        if self._cached_sensitivity is not None:
            return self._cached_sensitivity
        
        if not os.path.exists(self.sensitivity_data_path):
            print(f"⚠️  민감도 파일을 찾을 수 없습니다: {self.sensitivity_data_path}")
            print(f"   기본 임계값을 사용합니다.")
            self.use_sensitivity = False
            return None
        
        # CSV 로드
        sensitivity_df = pd.read_csv(self.sensitivity_data_path)
        
        # 데이터 전처리
        sensitivity_df['industry_group'] = sensitivity_df['industry_group'].astype(float)
        
        # zscore 타입별로 분리
        self.sensitivity_mom = sensitivity_df[sensitivity_df['surprise_metric'] == 'rolling_zscore_mom'].copy()
        self.sensitivity_yoy = sensitivity_df[sensitivity_df['surprise_metric'] == 'rolling_zscore_yoy'].copy()
        self.sensitivity_qoq = sensitivity_df[sensitivity_df['surprise_metric'] == 'rolling_zscore_qoq'].copy()
        
        # 산업별 임계값 계산
        self._calculate_industry_thresholds()
        
        self._cached_sensitivity = True
        
        print(f"✅ 민감도 데이터 로드 완료")
        print(f"   - 산업 그룹 수: {sensitivity_df['industry_group'].nunique()}개")
        print(f"   - 민감도 기반 임계값 조정 활성화")
        
        return True
    
    
    def _calculate_industry_thresholds(self):
        """
        산업별 임계값 자동 계산
        
        로직:
        1. slope(베타) 절대값이 클수록 → 임계값 낮춤 (민감도 높음)
        2. p_value가 클수록 → 임계값 높임 (불확실성 높음)
        3. sample_size가 작을수록 → 임계값 높임 (신뢰도 낮음)
        """
        self.industry_thresholds = {}
        
        for zscore_type in ['mom', 'yoy', 'qoq']:
            if zscore_type == 'mom':
                sensitivity_df = self.sensitivity_mom
            elif zscore_type == 'yoy':
                sensitivity_df = self.sensitivity_yoy
            else:
                sensitivity_df = self.sensitivity_qoq
            
            thresholds = {}
            
            for _, row in sensitivity_df.iterrows():
                industry = row['industry_group']
                slope = abs(row['slope'])
                p_value = row['p_value']
                sample_size = row['sample_size']
                
                # 기본 조정 배수
                adjustment = 1.0
                
                # 1. Slope 기반 조정 (베타가 클수록 임계값 낮춤)
                if slope > 0.003:
                    adjustment *= 0.5  # 매우 민감 → 임계값 50% 감소
                elif slope > 0.002:
                    adjustment *= 0.7  # 민감 → 30% 감소
                elif slope > 0.001:
                    adjustment *= 0.85  # 약간 민감 → 15% 감소
                elif slope < 0.0005:
                    adjustment *= 1.5  # 매우 둔감 → 임계값 50% 증가
                
                # 2. P-value 기반 조정 (유의미하지 않으면 임계값 높임)
                if p_value > 0.1:
                    adjustment *= 1.8  # 통계적으로 유의미하지 않음
                elif p_value > 0.05:
                    adjustment *= 1.3  # 약간 유의미하지 않음
                
                # 3. Sample size 기반 조정 (샘플이 적으면 임계값 높임)
                if sample_size < 50:
                    adjustment *= 1.5
                elif sample_size < 100:
                    adjustment *= 1.2
                
                # 최종 임계값 계산
                long_threshold = self.base_long_threshold * adjustment
                short_threshold = self.base_short_threshold * adjustment
                
                # 임계값 범위 제한 (0.1 ~ 2.0)
                long_threshold = max(0.1, min(2.0, long_threshold))
                short_threshold = max(-2.0, min(-0.1, short_threshold))
                
                thresholds[industry] = {
                    'long': long_threshold,
                    'short': short_threshold,
                    'slope': row['slope'],
                    'p_value': p_value,
                    'sample_size': sample_size,
                    'R': row['R']
                }
            
            self.industry_thresholds[zscore_type] = thresholds
    
    
    def _should_exclude_industry(self, industry, zscore_type='mom'):
        """
        산업이 거래 제외 대상인지 판단
        
        제외 조건:
        1. p_value > min_pvalue (통계적으로 유의미하지 않음)
        2. sample_size < min_sample_size (샘플이 너무 적음)
        """
        if not self.use_sensitivity:
            return False
        
        thresholds = self.industry_thresholds.get(zscore_type, {})
        industry_data = thresholds.get(industry)
        
        if industry_data is None:
            # 민감도 데이터 없음 → 보수적으로 제외
            return True
        
        # 제외 조건 체크
        if industry_data['p_value'] > self.min_pvalue:
            return True
        
        if industry_data['sample_size'] < self.min_sample_size:
            return True
        
        return False
    
    
    def _get_industry_threshold(self, industry, zscore_type='mom'):
        """
        산업별 임계값 반환
        """
        if not self.use_sensitivity:
            return {
                'long': self.base_long_threshold,
                'short': self.base_short_threshold
            }
        
        thresholds = self.industry_thresholds.get(zscore_type, {})
        industry_data = thresholds.get(industry)
        
        if industry_data is None:
            # 민감도 데이터 없음 → 기본 임계값 사용
            return {
                'long': self.base_long_threshold,
                'short': self.base_short_threshold
            }
        
        return {
            'long': industry_data['long'],
            'short': industry_data['short']
        }
    
    
    def _load_export_data(self):
        """
        CSV 파일을 로드하고 캐싱
        """
        if self._cached_export_data is not None:
            return self._cached_export_data
        
        if not os.path.exists(self.export_with_surprise_data_path):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {self.export_with_surprise_data_path}")
        
        surprise_df = pd.read_csv(self.export_with_surprise_data_path)
        
        # Unnamed: 0 컬럼 제거
        if 'Unnamed: 0' in surprise_df.columns:
            surprise_df = surprise_df.drop(columns=['Unnamed: 0'])
        
        # date 컬럼을 datetime으로 변환
        surprise_df[self.COLUMNS['date']] = pd.to_datetime(surprise_df[self.COLUMNS['date']])
        
        # industry_group 컬럼 확인
        if self.COLUMNS['industry_group'] not in surprise_df.columns:
            print(f"⚠️  {self.COLUMNS['industry_group']} 컬럼이 없습니다. 민감도 기반 필터링을 사용할 수 없습니다.")
            self.use_sensitivity = False
        
        # 캐싱
        self._cached_export_data = surprise_df
        return surprise_df
    
    
    def _get_export_with_surprise(self, symbols, month):
        """
        특정 월의 수출 서프라이즈 데이터 반환
        """
        surprise_df = self._load_export_data()
        
        # month를 datetime으로 변환
        month_str = str(month).replace('-', '')
        if len(month_str) == 6: 
            month_str = month_str + '01' 
        
        month_dt = pd.to_datetime(month_str)
        target_date = month_dt + pd.offsets.MonthEnd(0)
        
        # 여러 종목 또는 단일 종목 처리
        if isinstance(symbols, (list, tuple, np.ndarray, pd.Series)):
            surprise_rows = surprise_df[
                (surprise_df[self.COLUMNS['symbol']].isin(symbols)) & 
                (surprise_df[self.COLUMNS['date']] == target_date)
            ]
            
            if surprise_rows.empty:
                return pd.DataFrame()
            
            return surprise_rows.set_index(self.COLUMNS['symbol'])
        else:
            surprise_row = surprise_df[
                (surprise_df[self.COLUMNS['symbol']] == symbols) & 
                (surprise_df[self.COLUMNS['date']] == target_date)
            ]
            
            if surprise_row.empty:
                return None
            
            return surprise_row.iloc[0].to_dict()
    
    
    def get_signals(self, symbols, month, zscore_type='mom'):
        """
        여러 종목의 시그널 생성 (민감도 기반)
        
        Parameters:
        - symbols: 종목 코드 리스트
        - month: 월 (예: '2020-01-31', '2020-01', 202001)
        - zscore_type: 사용할 z-score 타입 ('mom', 'yoy', 'qoq')
        
        Returns:
        - DataFrame: symbol을 인덱스로 하는 시그널 DataFrame
        """
        # 서프라이즈 데이터 가져오기
        surprise_data = self._get_export_with_surprise(symbols, month)
        
        if surprise_data is None or (isinstance(surprise_data, pd.DataFrame) and surprise_data.empty):
            return pd.DataFrame()
        
        # z-score 컬럼 선택
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
        
        # industry_group 컬럼 추가 (있는 경우)
        if self.use_sensitivity and self.COLUMNS['industry_group'] in surprise_data.columns:
            cols_to_select.append(self.COLUMNS['industry_group'])
        
        # 시그널 생성
        signals_df = surprise_data[cols_to_select].copy()
        signals_df = signals_df.rename(columns={zscore_col: 'zscore'})
        
        # NaN이 아닌 z-score만 사용
        signals_df = signals_df.dropna(subset=['zscore'])
        
        # 민감도 기반 필터링 및 시그널 생성
        signals_df['signal'] = 0
        signals_df['threshold_long'] = self.base_long_threshold
        signals_df['threshold_short'] = self.base_short_threshold
        signals_df['excluded'] = False
        
        if self.use_sensitivity and self.COLUMNS['industry_group'] in signals_df.columns:
            # 산업별로 임계값 적용
            for idx, row in signals_df.iterrows():
                industry = row[self.COLUMNS['industry_group']]
                
                # 제외 대상 산업 체크
                if self._should_exclude_industry(industry, zscore_type):
                    signals_df.at[idx, 'excluded'] = True
                    signals_df.at[idx, 'signal'] = 0
                    continue
                
                # 산업별 임계값 가져오기
                threshold = self._get_industry_threshold(industry, zscore_type)
                signals_df.at[idx, 'threshold_long'] = threshold['long']
                signals_df.at[idx, 'threshold_short'] = threshold['short']
                
                # 시그널 생성
                zscore = row['zscore']
                if zscore >= threshold['long']:
                    signals_df.at[idx, 'signal'] = 1  # Long
                elif zscore <= threshold['short']:
                    signals_df.at[idx, 'signal'] = -1  # Short
            
            # 제외된 종목 필터링
            signals_df = signals_df[signals_df['excluded'] == False].copy()
            signals_df = signals_df.drop(columns=['excluded'])
        else:
            # 민감도 미사용 시 기본 임계값 적용
            signals_df.loc[signals_df['zscore'] >= self.base_long_threshold, 'signal'] = 1
            signals_df.loc[signals_df['zscore'] <= self.base_short_threshold, 'signal'] = -1
        
        return signals_df
    
    
    def get_signal(self, symbol, month, zscore_type='mom'):
        """
        단일 종목의 시그널 생성 (하위 호환성)
        """
        surprise_data = self._get_export_with_surprise(symbol, month)
        
        if surprise_data is None:
            return None
        
        zscore_col = self.COLUMNS[f'zscore_{zscore_type}']
        zscore = surprise_data.get(zscore_col)
        
        if pd.isna(zscore):
            return None
        
        # 산업별 임계값 적용
        if self.use_sensitivity and self.COLUMNS['industry_group'] in surprise_data:
            industry = surprise_data.get(self.COLUMNS['industry_group'])
            
            # 제외 대상 산업 체크
            if self._should_exclude_industry(industry, zscore_type):
                return None
            
            threshold = self._get_industry_threshold(industry, zscore_type)
        else:
            threshold = {
                'long': self.base_long_threshold,
                'short': self.base_short_threshold
            }
        
        # 시그널 생성
        if zscore >= threshold['long']:
            signal = 1
        elif zscore <= threshold['short']:
            signal = -1
        else:
            signal = 0
        
        return {
            'symbol': symbol,
            'date': surprise_data.get(self.COLUMNS['date']),
            'zscore': zscore,
            'signal': signal,
            'threshold_long': threshold['long'],
            'threshold_short': threshold['short'],
            'export_value': surprise_data.get(self.COLUMNS['export_value']),
            'MoM': surprise_data.get(self.COLUMNS['mom']),
            'YoY': surprise_data.get(self.COLUMNS['yoy']),
            'QoQ': surprise_data.get(self.COLUMNS['qoq'])
        }
    
    
    def get_sensitivity_summary(self, zscore_type='mom'):
        """
        민감도 요약 정보 출력
        """
        if not self.use_sensitivity:
            print("민감도 기반 전략이 비활성화되어 있습니다.")
            return
        
        print(f"\n" + "=" * 80)
        print(f"민감도 요약 ({zscore_type.upper()})")
        print(f"=" * 80)
        
        thresholds = self.industry_thresholds.get(zscore_type, {})
        
        if not thresholds:
            print("민감도 데이터가 없습니다.")
            return
        
        # DataFrame으로 변환
        summary_data = []
        for industry, data in thresholds.items():
            summary_data.append({
                'industry_group': industry,
                'threshold_long': data['long'],
                'threshold_short': data['short'],
                'slope': data['slope'],
                'R': data['R'],
                'p_value': data['p_value'],
                'sample_size': data['sample_size'],
                'excluded': self._should_exclude_industry(industry, zscore_type)
            })
        
        summary_df = pd.DataFrame(summary_data)
        summary_df = summary_df.sort_values('slope', key=abs, ascending=False)
        
        print(f"\n상위 5개 민감도 높은 산업:")
        print(summary_df.head(5).to_string(index=False))
        
        print(f"\n하위 5개 민감도 낮은 산업:")
        print(summary_df.tail(5).to_string(index=False))
        
        print(f"\n제외된 산업 수: {summary_df['excluded'].sum()}개")
        print(f"거래 가능 산업 수: {(~summary_df['excluded']).sum()}개")
        print("=" * 80)

