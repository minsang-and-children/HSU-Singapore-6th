import React from 'react';
import { BacktestingDashboard } from './components/BacktestingDashboard';

function App() {
  return (
    <div style={{ 
      minHeight: '100vh', 
      backgroundColor: '#f8fafc',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>
      <div style={{ maxWidth: '1600px', margin: '0 auto', padding: '20px' }}>
        {/* 헤더 */}
        <header style={{
          backgroundColor: 'white',
          borderRadius: '12px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          padding: '32px',
          marginBottom: '24px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{
              width: '60px',
              height: '60px',
              backgroundColor: '#3b82f6',
              borderRadius: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '32px'
            }}>
              📊
            </div>
            <div>
              <h1 style={{ 
                fontSize: '2.5rem', 
                fontWeight: 'bold', 
                margin: '0 0 8px 0', 
                color: '#1a202c',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent'
              }}>
                Presto Backtesting
              </h1>
              <p style={{ 
                color: '#718096', 
                margin: 0,
                fontSize: '1.1rem'
              }}>
                CSV 기반 백테스팅 시스템 • Export Surprise Strategy
              </p>
            </div>
          </div>
        </header>

        {/* 백테스팅 대시보드 */}
        <BacktestingDashboard />

        {/* 푸터 */}
        <footer style={{
          marginTop: '48px',
          padding: '24px',
          textAlign: 'center',
          color: '#9ca3af',
          fontSize: '14px'
        }}>
          <p style={{ margin: 0 }}>
            Presto Backtesting System v1.0.0
          </p>
          <p style={{ margin: '8px 0 0 0' }}>
            Powered by FastAPI + React + Pandas
          </p>
        </footer>
      </div>
    </div>
  );
}

export default App;
