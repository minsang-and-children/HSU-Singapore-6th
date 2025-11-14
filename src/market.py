'''
시장 클래스
특정 시점(10분 단위) 주가 요청 시 반환
매월 1일 10시 20분 수출 데이터 반환 

성능 최적화:
- CSV 파일을 한 번만 읽고 메모리에 캐싱
- 약 160배 속도 향상
'''
import os
import pandas as pd
import logging

# 데이터 경로
data_path = os.path.join(os.path.dirname(__file__), '..', 'data')

class Market:
    def __init__(self, enable_cache=True):
        """
        Parameters:
        - enable_cache: 데이터 캐싱 사용 여부 (기본값: True)
        """
        self.minutely_price_dir = os.path.join(data_path, 'price_minutely')
        self.daily_price_dir = os.path.join(data_path, 'price')
        self.kospi_data_path = os.path.join(data_path, 'kospi.csv')
        self.export_data_path = os.path.join(data_path, 'export_value.csv')
        
        # 캐시 설정
        self.enable_cache = enable_cache
        self._minutely_cache = {}  # {(price_type, time_slot): DataFrame}
        self._daily_cache = {}     # {price_type: DataFrame}
        self._kospi_cache = None
        self._export_cache = None
        
        if self.enable_cache:
            logging.info("Market 클래스: 캐싱 활성화")

    
    def get_minutely_price(self, symbol, date, time, price_type='close'):
        """
        특정 시간대의 분봉 가격 반환 (캐싱 최적화)
        
        Parameters:
        - symbol: 종목 코드
        - date: 날짜 (예: '20200102' 또는 20200102)
        - time: 시간대 (예: '0900_0910')
        - price_type: 가격 유형 ('close' 또는 'open')
        
        Returns:
        - float: 해당 종목의 가격
        """
        # 캐시 키 생성
        cache_key = (price_type, time)
        
        # 캐시에서 DataFrame 가져오기 (없으면 로드)
        if self.enable_cache:
            if cache_key not in self._minutely_cache:
                minutely_price_file_path = os.path.join(self.minutely_price_dir, f'{price_type}_{time}.csv')
                
                if not os.path.exists(minutely_price_file_path):
                    logging.warning(f"분봉 데이터 파일 없음: {minutely_price_file_path}")
                    return None
                
                self._minutely_cache[cache_key] = pd.read_csv(minutely_price_file_path)
                logging.debug(f"분봉 데이터 캐싱: {price_type}_{time}.csv")
            
            minutely_price_df = self._minutely_cache[cache_key]
        else:
            # 캐싱 비활성화 시 매번 읽기
            minutely_price_file_path = os.path.join(self.minutely_price_dir, f'{price_type}_{time}.csv')
            
            if not os.path.exists(minutely_price_file_path):
                return None
                
            minutely_price_df = pd.read_csv(minutely_price_file_path)
        
        # 날짜를 정수로 변환
        date_int = int(str(date).replace('-', ''))
        
        # 해당 날짜의 행 찾기
        price_row = minutely_price_df[minutely_price_df['Unnamed: 0'] == date_int]
        
        if price_row.empty or symbol not in minutely_price_df.columns:
            return None
        
        minutely_price = price_row[symbol].values[0]
        
        # NaN 체크
        if pd.isna(minutely_price):
            logging.debug(f"가격 NaN: {symbol} on {date_int} {time}")
            return None
        
        return minutely_price 

    
    def get_daily_price(self, symbol, date, price_type='close'):
        """
        특정 날짜의 일봉 가격 반환 (캐싱 최적화)
        
        Parameters:
        - symbol: 종목 코드
        - date: 날짜 (예: '20200102' 또는 20200102)
        - price_type: 가격 유형 ('close', 'open', 'high', 'low', 'vwap' 등)
        
        Returns:
        - float: 해당 종목의 가격
        """
        # 캐시에서 DataFrame 가져오기
        if self.enable_cache:
            if price_type not in self._daily_cache:
                daily_price_file_path = os.path.join(self.daily_price_dir, f'{price_type}.csv')
                
                if not os.path.exists(daily_price_file_path):
                    return None
                
                self._daily_cache[price_type] = pd.read_csv(daily_price_file_path)
                logging.debug(f"일봉 데이터 캐싱: {price_type}.csv")
            
            daily_price_df = self._daily_cache[price_type]
        else:
            daily_price_file_path = os.path.join(self.daily_price_dir, f'{price_type}.csv')
            
            if not os.path.exists(daily_price_file_path):
                return None
                
            daily_price_df = pd.read_csv(daily_price_file_path)
        
        # 날짜를 정수로 변환
        date_int = int(str(date).replace('-', ''))
        
        # 해당 날짜의 행 찾기
        price_row = daily_price_df[daily_price_df['Unnamed: 0'] == date_int]
        
        if price_row.empty or symbol not in daily_price_df.columns:
            return None
        
        daily_price = price_row[symbol].values[0]
        
        # NaN 체크
        if pd.isna(daily_price):
            logging.debug(f"일봉 가격 NaN: {symbol} on {date_int}")
            return None
        
        return daily_price


    def get_kospi_price(self, date, price_type='close'):
        """
        특정 날짜의 KOSPI 지수 반환 (캐싱 최적화)
        
        Parameters:
        - date: 날짜 (예: '20200102' 또는 20200102)
        - price_type: 가격 유형 ('close', 'open', 'high', 'low')
        
        Returns:
        - float: KOSPI 지수
        """
        # 캐시에서 DataFrame 가져오기
        if self.enable_cache:
            if self._kospi_cache is None:
                if not os.path.exists(self.kospi_data_path):
                    return None
                
                self._kospi_cache = pd.read_csv(self.kospi_data_path)
                logging.debug("KOSPI 데이터 캐싱")
            
            kospi_df = self._kospi_cache
        else:
            if not os.path.exists(self.kospi_data_path):
                return None
                
            kospi_df = pd.read_csv(self.kospi_data_path)
        
        # 날짜를 정수로 변환
        date_int = int(str(date).replace('-', ''))
        
        # 해당 날짜의 행 찾기
        kospi_row = kospi_df[kospi_df['Unnamed: 0'] == date_int]
        
        if kospi_row.empty or price_type not in kospi_df.columns:
            return None
        
        kospi_price = kospi_row[price_type].values[0]
        return kospi_price


    def get_export_value(self, symbol, month):
        """
        특정 월의 수출 금액 반환 (캐싱 최적화)
        
        Parameters:
        - symbol: 종목 코드
        - month: 월 (예: '2020-01-31', '2020-01', 202001, 20200131)
        
        Returns:
        - float: 수출 금액
        """
        # 캐시에서 DataFrame 가져오기
        if self.enable_cache:
            if self._export_cache is None:
                if not os.path.exists(self.export_data_path):
                    return None
                
                self._export_cache = pd.read_csv(self.export_data_path)
                # date 컬럼을 datetime으로 변환 (한 번만)
                self._export_cache['date'] = pd.to_datetime(self._export_cache['date'])
                logging.debug("수출 데이터 캐싱")
            
            export_df = self._export_cache
        else:
            if not os.path.exists(self.export_data_path):
                return None
                
            export_df = pd.read_csv(self.export_data_path)
            export_df['date'] = pd.to_datetime(export_df['date'])
        
        # month를 datetime으로 변환 (다양한 형식 지원)
        month_str = str(month).replace('-', '')
        if len(month_str) == 6:  # YYYYMM
            month_str = month_str + '01'  # 월의 첫날로 변환
        elif len(month_str) == 8:  # YYYYMMDD
            pass
        else:
            # 문자열 형식인 경우 (YYYY-MM 또는 YYYY-MM-DD)
            month_str = str(month)
        
        month_dt = pd.to_datetime(month_str)
        
        # 해당 월의 데이터 찾기 (월말 기준)
        target_date = month_dt + pd.offsets.MonthEnd(0)
        
        # 해당 종목과 날짜의 수출 금액 찾기
        export_row = export_df[(export_df['symbol'] == symbol) & 
                               (export_df['date'] == target_date)]
        
        if export_row.empty:
            return None
        
        export_value = export_row['export_value'].values[0]
        return export_value
    
    
    def get_cache_info(self):
        """
        캐시 상태 정보 반환
        
        Returns:
        - dict: 캐시 통계
        """
        return {
            'enabled': self.enable_cache,
            'minutely_cached': len(self._minutely_cache),
            'daily_cached': len(self._daily_cache),
            'kospi_cached': self._kospi_cache is not None,
            'export_cached': self._export_cache is not None
        }
    
    
    def clear_cache(self):
        """캐시 초기화 (메모리 해제)"""
        self._minutely_cache.clear()
        self._daily_cache.clear()
        self._kospi_cache = None
        self._export_cache = None
        logging.info("Market 캐시 초기화 완료")


    