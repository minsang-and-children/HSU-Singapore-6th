'''
투자자 클래스 
- 포트폴리오 관리  
- 매매 실행
- 포지션 관리
'''

class Investor:
    def __init__(self, initial_capital=1_000_000): 
        """
        Parameters:
        - initial_capital: 초기 자본금
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.portfolio = {}  # {symbol: {'quantity': int, 'avg_price': float, 'purchase_date': int, 'purchase_time': str}}
        self.strategy = None
        
        # 거래 기록
        self.trade_history = []
    
    
    def get_cash(self):
        """현금 잔액 반환"""
        return self.cash
    
    
    def get_portfolio(self):
        """포트폴리오 반환"""
        return self.portfolio
    
    
    def get_position(self, symbol):
        """특정 종목의 보유 수량 반환"""
        if symbol not in self.portfolio:
            return 0
        return self.portfolio[symbol]['quantity']
    
    
    def buy(self, symbol, quantity, price, date, time_slot=None):
        """
        매수 실행 (가격 검증 + 매수 시점 기록)
        
        Parameters:
        - symbol: 종목 코드
        - quantity: 수량
        - price: 가격
        - date: 거래 날짜 (정수, 예: 20240101)
        - time_slot: 거래 시간 (문자열, 예: '1020_1030', 생략 가능)
        
        Returns:
        - bool: 성공 여부
        """
        import pandas as pd
        
        # 가격 유효성 검증
        if price is None or pd.isna(price) or price <= 0:
            print(f'[매수 거부] {symbol}: 유효하지 않은 가격 ({price})')
            return False
        
        # 수량 검증
        if quantity <= 0:
            print(f'[매수 거부] {symbol}: 유효하지 않은 수량 ({quantity})')
            return False
        
        total_cost = quantity * price
        
        # 현금 부족 체크
        if total_cost > self.cash:
            print(f'[매수 실패] {symbol}: 현금 부족 (필요: {total_cost:,.0f}원, 보유: {self.cash:,.0f}원)')
            return False
        
        # 현금 차감
        self.cash -= total_cost
        
        # 포트폴리오 업데이트
        if symbol not in self.portfolio:
            self.portfolio[symbol] = {
                'quantity': 0, 
                'avg_price': 0,
                'purchase_date': date,  # 매수 날짜 기록
                'purchase_time': time_slot  # 매수 시간 기록
            }
        
        # 평균 단가 계산
        current_qty = self.portfolio[symbol]['quantity']
        current_avg = self.portfolio[symbol]['avg_price']
        
        new_qty = current_qty + quantity
        new_avg = ((current_qty * current_avg) + (quantity * price)) / new_qty
        
        self.portfolio[symbol]['quantity'] = new_qty
        self.portfolio[symbol]['avg_price'] = new_avg
        
        # 추가 매수 시에도 최초 매수 시점은 유지
        if 'purchase_date' not in self.portfolio[symbol]:
            self.portfolio[symbol]['purchase_date'] = date
            self.portfolio[symbol]['purchase_time'] = time_slot
        
        # 거래 기록
        self.trade_history.append({
            'date': date,
            'symbol': symbol,
            'action': 'BUY',
            'quantity': quantity,
            'price': price,
            'total': total_cost
        })
        
        return True
    
    
    def sell(self, symbol, quantity, price, date):
        """
        매도 실행 (가격 검증 추가)
        
        Parameters:
        - symbol: 종목 코드
        - quantity: 수량
        - price: 가격
        - date: 거래 날짜
        
        Returns:
        - bool: 성공 여부
        """
        import pandas as pd
        
        # 가격 유효성 검증
        if price is None or pd.isna(price) or price <= 0:
            print(f'[매도 거부] {symbol}: 유효하지 않은 가격 ({price}) - 보유 유지')
            return False
        
        # 수량 검증
        if quantity <= 0:
            print(f'[매도 거부] {symbol}: 유효하지 않은 수량 ({quantity})')
            return False
        
        # 보유 수량 체크
        if symbol not in self.portfolio or self.portfolio[symbol]['quantity'] < quantity:
            print(f'[매도 실패] {symbol}: 보유 수량 부족')
            return False
        
        total_revenue = quantity * price
        
        # 현금 증가
        self.cash += total_revenue
        
        # 포트폴리오 업데이트
        self.portfolio[symbol]['quantity'] -= quantity
        
        # 수량이 0이면 제거
        if self.portfolio[symbol]['quantity'] == 0:
            del self.portfolio[symbol]
        
        # 거래 기록
        self.trade_history.append({
            'date': date,
            'symbol': symbol,
            'action': 'SELL',
            'quantity': quantity,
            'price': price,
            'total': total_revenue
        })
        
        return True
    
    
    def get_portfolio_value(self, market, date_int, time_slot):
        """
        현재 포트폴리오의 총 가치 계산
        
        Parameters:
        - market: Market 객체
        - date_int: 날짜 (정수, 20250102)
        - time_slot: 시간 슬롯 ('0900_0910')
        
        Returns:
        - float: 총 자산 가치 (현금 + 주식)
        """
        import pandas as pd
        
        stock_value = 0
        
        for symbol, position in self.portfolio.items():
            quantity = position['quantity']
            
            # 현재 가격 조회
            current_price = market.get_minutely_price(symbol, date_int, time_slot, price_type='close')
            
            # NaN이 아니고 유효한 가격일 때만 계산
            if current_price is not None and not pd.isna(current_price) and current_price > 0:
                stock_value += quantity * current_price
        
        total_value = self.cash + stock_value
        return total_value
    
    
    def check_holding_period(self, current_date_int, current_time_slot, holding_period_value, holding_period_unit):
        """
        홀딩 기간이 경과한 종목 확인
        
        Parameters:
        - current_date_int: 현재 날짜 (정수, 예: 20240101)
        - current_time_slot: 현재 시간 슬롯 (문자열, 예: '1020_1030')
        - holding_period_value: 홀딩 기간 값 (예: 30)
        - holding_period_unit: 홀딩 기간 단위 ('minutes' 또는 'days')
        
        Returns:
        - list: 홀딩 기간이 경과한 종목 리스트
        """
        import pandas as pd
        from datetime import datetime, timedelta
        
        symbols_to_sell = []
        
        for symbol, position in self.portfolio.items():
            purchase_date = position.get('purchase_date')
            purchase_time = position.get('purchase_time')
            
            # 매수 시점 정보가 없으면 스킵
            if purchase_date is None:
                continue
            
            # 날짜 문자열로 변환
            purchase_date_str = str(purchase_date)
            purchase_datetime = pd.to_datetime(purchase_date_str)
            current_datetime = pd.to_datetime(str(current_date_int))
            
            # 홀딩 기간 계산
            if holding_period_unit == 'days':
                # 일 단위: 날짜 차이 계산
                days_held = (current_datetime - purchase_datetime).days
                
                if days_held >= holding_period_value:
                    symbols_to_sell.append(symbol)
            
            elif holding_period_unit == 'minutes':
                # 분 단위: 시간 슬롯까지 고려
                if purchase_time is None or current_time_slot is None:
                    continue
                
                # 시간 슬롯을 datetime으로 변환 (예: '1020_1030' → 10:20)
                try:
                    purchase_hour = int(purchase_time[:2])
                    purchase_minute = int(purchase_time[2:4])
                    
                    current_hour = int(current_time_slot[:2])
                    current_minute = int(current_time_slot[2:4])
                    
                    # datetime 객체 생성
                    purchase_dt = purchase_datetime.replace(hour=purchase_hour, minute=purchase_minute)
                    current_dt = current_datetime.replace(hour=current_hour, minute=current_minute)
                    
                    # 분 단위 차이 계산
                    minutes_held = (current_dt - purchase_dt).total_seconds() / 60
                    
                    if minutes_held >= holding_period_value:
                        symbols_to_sell.append(symbol)
                
                except (ValueError, AttributeError):
                    # 시간 파싱 실패 시 스킵
                    continue
        
        return symbols_to_sell
    
    
    def rebalance(self, target_weights, market, date_int, time_slot):
        """
        포트폴리오 리밸런싱 (거래 불가능한 종목 자동 제외)
        
        Parameters:
        - target_weights: {symbol: weight} 딕셔너리 (weight 합이 1.0)
        - market: Market 객체
        - date_int: 날짜 (정수)
        - time_slot: 시간 슬롯
        
        Returns:
        - bool: 성공 여부
        """
        import pandas as pd
        
        # 현재 총 자산 가치
        total_value = self.get_portfolio_value(market, date_int, time_slot)
        
        # 거래 가능한 종목만 필터링
        tradable_weights = {}
        excluded_symbols = []
        
        for symbol, weight in target_weights.items():
            # 현재 가격 조회 (거래 가능 여부 확인)
            current_price = market.get_minutely_price(symbol, date_int, time_slot, price_type='close')
            
            # NaN, None, 0 모두 체크
            if current_price is None or pd.isna(current_price) or current_price <= 0:
                excluded_symbols.append(symbol)
                continue
            
            tradable_weights[symbol] = weight
        
        # 제외된 종목 출력
        if excluded_symbols:
            print(f'\n⚠️  거래 불가 종목 제외 ({len(excluded_symbols)}개): {", ".join(excluded_symbols[:5])}{"..." if len(excluded_symbols) > 5 else ""}')
        
        # 거래 가능한 종목이 없으면 전량 청산
        if not tradable_weights:
            print(f'\n⚠️  거래 가능한 종목이 없습니다. 현금 보유.')
            # 기존 포지션 전량 매도
            for symbol in list(self.portfolio.keys()):
                quantity = self.portfolio[symbol]['quantity']
                # 매도 시도 (가격을 찾을 수 없으면 스킵)
                price = market.get_minutely_price(symbol, date_int, time_slot, price_type='close')
                if price is not None and price > 0:
                    self.sell(symbol, quantity, price, date_int)
            return False
        
        # 가중치 재조정 (제외된 종목 비율만큼 나머지에 분배)
        total_tradable_weight = sum(tradable_weights.values())
        if total_tradable_weight > 0:
            normalized_weights = {
                symbol: weight / total_tradable_weight 
                for symbol, weight in tradable_weights.items()
            }
        else:
            return False
        
        # 목표 포지션 계산
        target_positions = {}
        for symbol, weight in normalized_weights.items():
            target_value = total_value * weight
            
            # 가격 재조회 (이미 확인했지만 안전을 위해)
            current_price = market.get_minutely_price(symbol, date_int, time_slot, price_type='close')
            
            if current_price is None or pd.isna(current_price) or current_price <= 0:
                continue
            
            target_qty = int(target_value / current_price)
            target_positions[symbol] = {'quantity': target_qty, 'price': current_price}
        
        # 현재 보유 종목 중 목표에 없는 종목 전량 매도
        for symbol in list(self.portfolio.keys()):
            if symbol not in target_positions:
                quantity = self.portfolio[symbol]['quantity']
                price = market.get_minutely_price(symbol, date_int, time_slot, price_type='close')
                
                # 가격을 조회할 수 없으면 매도 불가 (거래 정지/상장 폐지 등)
                if price is None or pd.isna(price) or price <= 0:
                    print(f'   ⚠️  매도 불가 (가격 없음): {symbol} (보유: {quantity}주) - 보유 유지')
                    continue
                
                self.sell(symbol, quantity, price, date_int)
        
        # 목표 포지션으로 조정
        for symbol, target in target_positions.items():
            current_qty = self.get_position(symbol)
            target_qty = target['quantity']
            price = target['price']
            
            # 안전 체크: 가격이 유효한지 재확인
            if price is None or pd.isna(price) or price <= 0:
                print(f'   ⚠️  거래 불가 (유효하지 않은 가격): {symbol} (가격: {price})')
                continue
            
            if target_qty > current_qty:
                # 매수
                buy_qty = target_qty - current_qty
                if buy_qty > 0:
                    success = self.buy(symbol, buy_qty, price, date_int, time_slot)
                    # buy()에서 이미 실패 메시지 출력
            elif target_qty < current_qty:
                # 매도
                sell_qty = current_qty - target_qty
                if sell_qty > 0:
                    success = self.sell(symbol, sell_qty, price, date_int)
                    # sell()에서 이미 실패 메시지 출력
        
        return True
    
    
    # ============ API 친화적 메서드 (Backend 연동용) ============
    
    def get_portfolio_for_api(self, market, current_date_int, current_time_slot):
        """
        API 응답용 포트폴리오 데이터 생성 (CSV 기반 Market 사용)
        
        Parameters:
        - market: Market 객체 (CSV 기반)
        - current_date_int: 현재 날짜 (예: 20240101)
        - current_time_slot: 현재 시간 (예: '1020_1030')
        
        Returns:
        - list[dict]: 포트폴리오 포지션 리스트
        
        Example:
        >>> positions = investor.get_portfolio_for_api(market, 20240101, '1020_1030')
        >>> print(positions)
        [
            {
                'ticker': 'SYMBOL',
                'shares': 100.0,
                'current_price': 10500.0,
                'current_value': 1050000.0,
                'buy_price': 10000.0,
                'cost_basis': 1000000.0,
                'pnl': 50000.0,
                'pnl_percent': 5.0,
                'purchase_date': 20240101,
                'purchase_time': '1020_1030'
            }
        ]
        """
        import pandas as pd
        
        portfolio_list = []
        
        for symbol, position in self.portfolio.items():
            # CSV에서 현재 가격 조회
            current_price = market.get_minutely_price(
                symbol, current_date_int, current_time_slot, 'close'
            )
            
            quantity = position['quantity']
            avg_price = position['avg_price']
            cost_basis = quantity * avg_price
            
            # NaN 체크 및 손익 계산
            if current_price is not None and not pd.isna(current_price) and current_price > 0:
                current_value = quantity * current_price
                pnl = current_value - cost_basis
                pnl_percent = (pnl / cost_basis) * 100
            else:
                current_price = None
                current_value = None
                pnl = None
                pnl_percent = None
            
            portfolio_list.append({
                'ticker': symbol,
                'shares': float(quantity),
                'current_price': float(current_price) if current_price else None,
                'current_value': float(current_value) if current_value else None,
                'buy_price': float(avg_price),
                'cost_basis': float(cost_basis),
                'pnl': float(pnl) if pnl else None,
                'pnl_percent': float(pnl_percent) if pnl_percent else None,
                'purchase_date': position.get('purchase_date'),
                'purchase_time': position.get('purchase_time')
            })
        
        return portfolio_list
    
    
    def get_portfolio_summary(self, market, current_date_int, current_time_slot):
        """
        전체 포트폴리오 요약 정보
        
        Parameters:
        - market: Market 객체
        - current_date_int: 현재 날짜
        - current_time_slot: 현재 시간
        
        Returns:
        - dict: 전체 자산 요약
        
        Example:
        >>> summary = investor.get_portfolio_summary(market, 20240101, '1020_1030')
        >>> print(summary)
        {
            'cash': 50000000.0,
            'stock_value': 50000000.0,
            'total_value': 100000000.0,
            'initial_capital': 100000000.0,
            'total_pnl': 0.0,
            'total_pnl_percent': 0.0,
            'positions_count': 5
        }
        """
        total_value = self.get_portfolio_value(market, current_date_int, current_time_slot)
        stock_value = total_value - self.cash
        
        return {
            'cash': float(self.cash),
            'stock_value': float(stock_value),
            'total_value': float(total_value),
            'initial_capital': float(self.initial_capital),
            'total_pnl': float(total_value - self.initial_capital),
            'total_pnl_percent': float(((total_value - self.initial_capital) / self.initial_capital) * 100),
            'positions_count': len(self.portfolio)
        }
    
    
    def get_trade_history_for_api(self):
        """
        거래 히스토리를 API 응답용으로 변환
        
        Returns:
        - list[dict]: 거래 기록 리스트
        
        Example:
        >>> trades = investor.get_trade_history_for_api()
        >>> print(trades)
        [
            {
                'date': 20240101,
                'symbol': 'SYMBOL',
                'action': 'BUY',
                'quantity': 100.0,
                'price': 10000.0,
                'total': 1000000.0
            }
        ]
        """
        return [
            {
                'date': trade['date'],
                'symbol': trade['symbol'],
                'action': trade['action'],
                'quantity': float(trade['quantity']),
                'price': float(trade['price']),
                'total': float(trade['total'])
            }
            for trade in self.trade_history
        ]
