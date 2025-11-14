import React, { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000';

interface PortfolioSummary {
  cash: number;
  stock_value: number;
  total_value: number;
  initial_capital: number;
  total_pnl: number;
  total_pnl_percent: number;
  positions_count: number;
  positions: PortfolioPosition[];
}

interface PortfolioPosition {
  ticker: string;
  shares: number;
  current_price: number | null;
  current_value: number | null;
  buy_price: number;
  cost_basis: number;
  pnl: number | null;
  pnl_percent: number | null;
  purchase_date: number | null;
  purchase_time: string | null;
}

interface BacktestStatus {
  status: string;
  progress: number;
  current_date: string | null;
  current_time_slot: string | null;
  message: string | null;
}

interface BacktestResults {
  initial_capital: number;
  final_value: number;
  total_return: number;
  kospi_return?: number | null;  // 코스피 수익률
  excess_return?: number | null;  // 초과 수익률
  sharpe_ratio: number;
  mdd: number;
  total_trades: number;
  buy_trades: number;
  sell_trades: number;
  trading_days: number;
}

interface TradeRecord {
  date: number;
  time_slot?: string | null;  // 거래 시간
  symbol: string;
  action: string;
  quantity: number;
  price: number;
  total: number;
  buy_price?: number | null;  // 매수 평균가 (매도 시에만)
  profit_loss?: number | null;  // 손익 금액 (매도 시에만)
  profit_loss_percent?: number | null;  // 손익률 (매도 시에만)
}

export const BacktestingDashboard: React.FC = () => {
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [status, setStatus] = useState<BacktestStatus | null>(null);
  const [results, setResults] = useState<BacktestResults | null>(null);
  const [tradeHistory, setTradeHistory] = useState<TradeRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // 상태 폴링 (1초마다)
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;

    if (status?.status === 'running' || status?.status === 'initializing') {
      interval = setInterval(async () => {
        await fetchStatus();
        await fetchPortfolio();
      }, 1000);
    } else if (status?.status === 'completed' && !results) {
      // 완료되면 결과 및 거래 이력 가져오기
      fetchResults();
      fetchTradeHistory();
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [status?.status]);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/backtesting/status`);
      const data = await res.json();
      setStatus(data);
    } catch (error) {
      console.error('Status fetch error:', error);
    }
  };

  const fetchPortfolio = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/backtesting/portfolio`);
      if (res.ok) {
        const data = await res.json();
        setPortfolio(data);
      }
    } catch (error) {
      console.error('Portfolio fetch error:', error);
    }
  };

  const fetchResults = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/backtesting/results`);
      if (res.ok) {
        const data = await res.json();
        console.log('📊 백테스팅 결과 받음:', data);
        console.log('🏦 코스피 수익률:', data.kospi_return);
        console.log('📈 초과 수익률:', data.excess_return);
        setResults(data);
      }
    } catch (error) {
      console.error('Results fetch error:', error);
    }
  };

  const fetchTradeHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/backtesting/trades`);
      if (res.ok) {
        const data = await res.json();
        setTradeHistory(data);
      }
    } catch (error) {
      console.error('Trade history fetch error:', error);
    }
  };

  const startBacktest = async () => {
    setIsLoading(true);
    setResults(null);
    setPortfolio(null);
    
    try {
      const res = await fetch(`${API_BASE}/api/backtesting/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_date: '2024-01-04',
          end_date: '2024-12-31',
          initial_capital: 100000000,
          long_threshold: 0.4,
          short_threshold: -0.4,
          enable_short: false,
          zscore_type: 'mom',
          holding_period_enabled: true,
          holding_period_value: 30,
          holding_period_unit: 'days'
        })
      });
      
      if (res.ok) {
        await fetchStatus();
      } else {
        const error = await res.json();
        alert(`백테스팅 시작 실패: ${error.detail}`);
      }
    } catch (error) {
      console.error('Start error:', error);
      alert('백테스팅 시작 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const resetBacktest = async () => {
    try {
      await fetch(`${API_BASE}/api/backtesting/reset`, {
        method: 'DELETE'
      });
      setPortfolio(null);
      setStatus(null);
      setResults(null);
      setTradeHistory([]);
    } catch (error) {
      console.error('Reset error:', error);
    }
  };

  const formatNumber = (num: number | null | undefined): string => {
    if (num === null || num === undefined) return '-';
    return num.toLocaleString('ko-KR');
  };

  const formatPercent = (num: number | null | undefined): string => {
    if (num === null || num === undefined) return '-';
    return `${num.toFixed(2)}%`;
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'running': return '#4CAF50';
      case 'completed': return '#2196F3';
      case 'error': return '#F44336';
      case 'initializing': return '#FF9800';
      default: return '#9E9E9E';
    }
  };

  const getStatusText = (status: string): string => {
    switch (status) {
      case 'idle': return '대기 중';
      case 'initializing': return '초기화 중';
      case 'running': return '실행 중';
      case 'completed': return '완료';
      case 'error': return '오류';
      default: return status;
    }
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial', maxWidth: '1400px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '30px' }}>📊 백테스팅 대시보드</h1>
      
      {/* 컨트롤 패널 */}
      <div style={{ 
        marginBottom: '30px', 
        padding: '20px', 
        backgroundColor: '#f5f5f5', 
        borderRadius: '8px',
        display: 'flex',
        alignItems: 'center',
        gap: '15px'
      }}>
        <button 
          onClick={startBacktest} 
          disabled={isLoading || status?.status === 'running' || status?.status === 'initializing'}
          style={{ 
            padding: '10px 20px', 
            fontSize: '16px',
            backgroundColor: '#4CAF50',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer',
            opacity: (isLoading || status?.status === 'running' || status?.status === 'initializing') ? 0.5 : 1
          }}
        >
          {isLoading ? '초기화 중...' : '백테스팅 시작'}
        </button>
        
        <button 
          onClick={resetBacktest}
          style={{ 
            padding: '10px 20px', 
            fontSize: '16px',
            backgroundColor: '#f44336',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer'
          }}
        >
          초기화
        </button>
        
        {status && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1 }}>
            <span style={{ 
              padding: '5px 10px', 
              backgroundColor: getStatusColor(status.status), 
              color: 'white',
              borderRadius: '5px',
              fontWeight: 'bold'
            }}>
              {getStatusText(status.status)}
            </span>
            
            {(status.status === 'running' || status.status === 'initializing') && (
              <>
                <div style={{ flex: 1, backgroundColor: '#e0e0e0', borderRadius: '10px', height: '20px', position: 'relative' }}>
                  <div style={{ 
                    width: `${status.progress}%`, 
                    height: '100%', 
                    backgroundColor: '#4CAF50', 
                    borderRadius: '10px',
                    transition: 'width 0.3s'
                  }} />
                  <span style={{ 
                    position: 'absolute', 
                    top: '50%', 
                    left: '50%', 
                    transform: 'translate(-50%, -50%)',
                    fontSize: '12px',
                    fontWeight: 'bold'
                  }}>
                    {status.progress.toFixed(1)}%
                  </span>
                </div>
                
                {status.current_date && (
                  <span style={{ fontSize: '14px', color: '#666' }}>
                    {status.current_date} {status.current_time_slot}
                  </span>
                )}
              </>
            )}
            
            {status.status === 'error' && status.message && (
              <span style={{ color: '#F44336', fontSize: '14px' }}>
                오류: {status.message}
              </span>
            )}
          </div>
        )}
      </div>

      {/* 최종 결과 */}
      {results && (
        <div style={{ marginBottom: '30px' }}>
          <h2>✅ 백테스팅 최종 결과</h2>
          
          {/* 코스피 비교 섹션 */}
          {results.kospi_return !== null && results.kospi_return !== undefined && (
            <div style={{ 
              padding: '20px', 
              backgroundColor: '#f8f9fa', 
              borderRadius: '8px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
              marginBottom: '20px'
            }}>
              <h3 style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '16px', color: '#333' }}>
                📊 벤치마크 비교 (KOSPI)
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
                <div style={{ textAlign: 'center', padding: '15px', backgroundColor: 'white', borderRadius: '8px' }}>
                  <div style={{ color: '#666', fontSize: '12px', marginBottom: '8px' }}>내 수익률</div>
                  <div style={{ 
                    fontSize: '24px', 
                    fontWeight: 'bold', 
                    color: results.total_return >= 0 ? '#4CAF50' : '#F44336' 
                  }}>
                    {results.total_return >= 0 ? '+' : ''}{results.total_return.toFixed(2)}%
                  </div>
                </div>
                <div style={{ textAlign: 'center', padding: '15px', backgroundColor: 'white', borderRadius: '8px' }}>
                  <div style={{ color: '#666', fontSize: '12px', marginBottom: '8px' }}>코스피 수익률</div>
                  <div style={{ 
                    fontSize: '24px', 
                    fontWeight: 'bold', 
                    color: results.kospi_return >= 0 ? '#2196F3' : '#FF9800' 
                  }}>
                    {results.kospi_return >= 0 ? '+' : ''}{results.kospi_return.toFixed(2)}%
                  </div>
                </div>
                <div style={{ textAlign: 'center', padding: '15px', backgroundColor: 'white', borderRadius: '8px' }}>
                  <div style={{ color: '#666', fontSize: '12px', marginBottom: '8px' }}>초과 수익률 (알파)</div>
                  <div style={{ 
                    fontSize: '24px', 
                    fontWeight: 'bold', 
                    color: results.excess_return && results.excess_return >= 0 ? '#4CAF50' : '#F44336' 
                  }}>
                    {results.excess_return && results.excess_return >= 0 ? '+' : ''}
                    {results.excess_return?.toFixed(2)}%p
                  </div>
                </div>
              </div>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '15px' }}>
            {[
              { label: '초기 자본', value: formatNumber(results.initial_capital) + '원' },
              { label: '최종 자산', value: formatNumber(results.final_value) + '원' },
              { label: '총 수익률', value: formatPercent(results.total_return), color: results.total_return >= 0 ? 'green' : 'red' },
              { label: 'Sharpe Ratio', value: results.sharpe_ratio.toFixed(2) },
              { label: 'MDD', value: formatPercent(results.mdd), color: 'red' },
              { label: '총 거래', value: formatNumber(results.total_trades) + '회' },
              { label: '매수 거래', value: formatNumber(results.buy_trades) + '회' },
              { label: '매도 거래', value: formatNumber(results.sell_trades) + '회' },
            ].map((item, idx) => (
              <div key={idx} style={{ 
                border: '1px solid #ddd', 
                padding: '15px', 
                borderRadius: '8px',
                backgroundColor: 'white'
              }}>
                <div style={{ fontSize: '14px', color: '#666', marginBottom: '5px' }}>{item.label}</div>
                <div style={{ 
                  fontSize: '18px', 
                  fontWeight: 'bold', 
                  color: item.color || '#333' 
                }}>
                  {item.value}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 포트폴리오 요약 */}
      {portfolio && (
        <div style={{ marginBottom: '30px' }}>
          <h2>💼 포트폴리오 요약</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '15px' }}>
            {[
              { label: '총 자산', value: formatNumber(portfolio.total_value) + '원' },
              { label: '현금', value: formatNumber(portfolio.cash) + '원' },
              { label: '주식 평가액', value: formatNumber(portfolio.stock_value) + '원' },
              { label: '손익', value: formatNumber(portfolio.total_pnl) + '원', color: portfolio.total_pnl >= 0 ? 'green' : 'red' },
              { label: '수익률', value: formatPercent(portfolio.total_pnl_percent), color: portfolio.total_pnl_percent >= 0 ? 'green' : 'red' },
              { label: '보유 종목', value: portfolio.positions_count + '개' },
            ].map((item, idx) => (
              <div key={idx} style={{ 
                border: '1px solid #ddd', 
                padding: '15px', 
                borderRadius: '8px',
                backgroundColor: 'white'
              }}>
                <div style={{ fontSize: '14px', color: '#666', marginBottom: '5px' }}>{item.label}</div>
                <div style={{ 
                  fontSize: '18px', 
                  fontWeight: 'bold', 
                  color: item.color || '#333' 
                }}>
                  {item.value}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 포지션 테이블 */}
      {portfolio && portfolio.positions.length > 0 && (
        <div>
          <h2>📈 보유 종목 ({portfolio.positions.length}개)</h2>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ 
              width: '100%', 
              borderCollapse: 'collapse',
              backgroundColor: 'white',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}>
              <thead>
                <tr style={{ backgroundColor: '#f5f5f5' }}>
                  <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'left' }}>종목</th>
                  <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>수량</th>
                  <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>매수가</th>
                  <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>현재가</th>
                  <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>평가액</th>
                  <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>매입금액</th>
                  <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>손익</th>
                  <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>수익률</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.positions.map((pos, idx) => (
                  <tr key={idx} style={{ backgroundColor: idx % 2 === 0 ? 'white' : '#fafafa' }}>
                    <td style={{ border: '1px solid #ddd', padding: '12px', fontWeight: 'bold' }}>
                      {pos.ticker}
                    </td>
                    <td style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>
                      {formatNumber(pos.shares)}
                    </td>
                    <td style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>
                      {formatNumber(pos.buy_price)}원
                    </td>
                    <td style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>
                      {formatNumber(pos.current_price)}원
                    </td>
                    <td style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>
                      {formatNumber(pos.current_value)}원
                    </td>
                    <td style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>
                      {formatNumber(pos.cost_basis)}원
                    </td>
                    <td style={{ 
                      border: '1px solid #ddd', 
                      padding: '12px', 
                      textAlign: 'right',
                      color: pos.pnl && pos.pnl >= 0 ? 'green' : 'red',
                      fontWeight: 'bold'
                    }}>
                      {formatNumber(pos.pnl)}원
                    </td>
                    <td style={{ 
                      border: '1px solid #ddd', 
                      padding: '12px', 
                      textAlign: 'right',
                      color: pos.pnl_percent && pos.pnl_percent >= 0 ? 'green' : 'red',
                      fontWeight: 'bold'
                    }}>
                      {formatPercent(pos.pnl_percent)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 포지션 없음 메시지 */}
      {portfolio && portfolio.positions.length === 0 && (
        <div style={{ 
          padding: '40px', 
          textAlign: 'center', 
          backgroundColor: '#f5f5f5', 
          borderRadius: '8px',
          color: '#666'
        }}>
          현재 보유 중인 종목이 없습니다.
        </div>
      )}

      {/* 거래 이력 */}
      {tradeHistory.length > 0 && (
        <div style={{ marginTop: '30px' }}>
          <h2>📋 거래 이력 ({tradeHistory.length}건)</h2>
          <div style={{ overflowX: 'auto', maxHeight: '600px', overflowY: 'auto' }}>
            <table style={{ 
              width: '100%', 
              borderCollapse: 'collapse',
              backgroundColor: 'white',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}>
              <thead style={{ position: 'sticky', top: 0, backgroundColor: '#f5f5f5', zIndex: 1 }}>
                <tr>
                  <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'left' }}>날짜 / 시간</th>
                  <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'left' }}>종목</th>
                  <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'center' }}>구분</th>
                  <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>수량</th>
                  <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>매수가</th>
                  <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>매도가</th>
                  <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>총 금액</th>
                  <th style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>손익</th>
                </tr>
              </thead>
              <tbody>
                {tradeHistory.slice().reverse().map((trade, idx) => {
                  const dateStr = String(trade.date);
                  const formattedDate = dateStr.length === 8 
                    ? `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
                    : dateStr;
                  
                  // 시간 포맷팅 (0900_0910 -> 09:00-09:10)
                  const formattedTime = trade.time_slot 
                    ? `${trade.time_slot.slice(0, 2)}:${trade.time_slot.slice(2, 4)}-${trade.time_slot.slice(5, 7)}:${trade.time_slot.slice(7, 9)}`
                    : '';
                  
                  const isBuy = trade.action === 'BUY';
                  const actionColor = isBuy ? '#4CAF50' : '#F44336';
                  const actionBg = isBuy ? '#E8F5E9' : '#FFEBEE';
                  
                  return (
                    <tr key={idx} style={{ 
                      backgroundColor: idx % 2 === 0 ? 'white' : '#fafafa',
                      borderBottom: '1px solid #eee'
                    }}>
                      <td style={{ border: '1px solid #ddd', padding: '12px' }}>
                        <div style={{ fontWeight: 'bold' }}>{formattedDate}</div>
                        {formattedTime && (
                          <div style={{ fontSize: '12px', color: '#666', marginTop: '2px' }}>
                            {formattedTime}
                          </div>
                        )}
                      </td>
                      <td style={{ border: '1px solid #ddd', padding: '12px', fontWeight: 'bold' }}>
                        {trade.symbol}
                      </td>
                      <td style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'center' }}>
                        <span style={{ 
                          padding: '4px 12px', 
                          borderRadius: '4px', 
                          backgroundColor: actionBg,
                          color: actionColor,
                          fontWeight: 'bold',
                          fontSize: '13px'
                        }}>
                          {isBuy ? '매수' : '매도'}
                        </span>
                      </td>
                      <td style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>
                        {formatNumber(trade.quantity)}
                      </td>
                      <td style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>
                        {isBuy ? formatNumber(trade.price) + '원' : (trade.buy_price ? formatNumber(trade.buy_price) + '원' : '-')}
                      </td>
                      <td style={{ border: '1px solid #ddd', padding: '12px', textAlign: 'right' }}>
                        {isBuy ? '-' : formatNumber(trade.price) + '원'}
                      </td>
                      <td style={{ 
                        border: '1px solid #ddd', 
                        padding: '12px', 
                        textAlign: 'right',
                        fontWeight: 'bold',
                        color: actionColor
                      }}>
                        {isBuy ? '-' : '+'}{formatNumber(trade.total)}원
                      </td>
                      <td style={{ 
                        border: '1px solid #ddd', 
                        padding: '12px', 
                        textAlign: 'right',
                        fontWeight: 'bold',
                        color: trade.profit_loss && trade.profit_loss >= 0 ? '#4CAF50' : '#F44336'
                      }}>
                        {isBuy ? '-' : (
                          trade.profit_loss !== null && trade.profit_loss !== undefined ? (
                            <>
                              {trade.profit_loss >= 0 ? '+' : ''}{formatNumber(trade.profit_loss)}원
                              <br />
                              <span style={{ fontSize: '12px' }}>
                                ({trade.profit_loss_percent && trade.profit_loss_percent >= 0 ? '+' : ''}
                                {trade.profit_loss_percent?.toFixed(2)}%)
                              </span>
                            </>
                          ) : '-'
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          
          {/* 거래 이력 요약 */}
          <div style={{ 
            marginTop: '15px', 
            padding: '15px', 
            backgroundColor: '#f5f5f5', 
            borderRadius: '8px',
            display: 'flex',
            gap: '30px',
            flexWrap: 'wrap'
          }}>
            <div>
              <span style={{ color: '#666', fontSize: '14px' }}>총 거래: </span>
              <span style={{ fontWeight: 'bold', fontSize: '16px' }}>{tradeHistory.length}건</span>
            </div>
            <div>
              <span style={{ color: '#666', fontSize: '14px' }}>매수: </span>
              <span style={{ fontWeight: 'bold', fontSize: '16px', color: '#4CAF50' }}>
                {tradeHistory.filter(t => t.action === 'BUY').length}건
              </span>
            </div>
            <div>
              <span style={{ color: '#666', fontSize: '14px' }}>매도: </span>
              <span style={{ fontWeight: 'bold', fontSize: '16px', color: '#F44336' }}>
                {tradeHistory.filter(t => t.action === 'SELL').length}건
              </span>
            </div>
            <div>
              <span style={{ color: '#666', fontSize: '14px' }}>총 매수액: </span>
              <span style={{ fontWeight: 'bold', fontSize: '16px', color: '#F44336' }}>
                {formatNumber(tradeHistory.filter(t => t.action === 'BUY').reduce((sum, t) => sum + t.total, 0))}원
              </span>
            </div>
            <div>
              <span style={{ color: '#666', fontSize: '14px' }}>총 매도액: </span>
              <span style={{ fontWeight: 'bold', fontSize: '16px', color: '#4CAF50' }}>
                {formatNumber(tradeHistory.filter(t => t.action === 'SELL').reduce((sum, t) => sum + t.total, 0))}원
              </span>
            </div>
            <div>
              <span style={{ color: '#666', fontSize: '14px' }}>총 시세차익: </span>
              <span style={{ 
                fontWeight: 'bold', 
                fontSize: '18px', 
                color: (() => {
                  const totalProfit = tradeHistory.filter(t => t.action === 'SELL' && t.profit_loss !== null).reduce((sum, t) => sum + (t.profit_loss || 0), 0);
                  return totalProfit >= 0 ? '#4CAF50' : '#F44336';
                })()
              }}>
                {(() => {
                  const totalProfit = tradeHistory.filter(t => t.action === 'SELL' && t.profit_loss !== null).reduce((sum, t) => sum + (t.profit_loss || 0), 0);
                  return (totalProfit >= 0 ? '+' : '') + formatNumber(totalProfit) + '원';
                })()}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

