"""
달러 인덱스 및 환율 계산 서비스
"""
import streamlit as st
import yfinance as yf
import pandas as pd
from typing import Dict, Tuple
from config.settings import (
    DXY_INITIAL_CONSTANT,
    DXY_WEIGHTS,
    DXY_TICKERS,
    USD_KRW_TICKER,
    PERIOD_MAP
)


def fetch_period_data_and_current_rates(period_months: int = 12) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, float]]:
    """
    yfinance를 사용하여 지정된 기간의 OHLC 데이터와 현재 종가 가격을 가져옵니다.
    
    Args:
        period_months: 분석 기간 (개월 단위, 기본값 12개월)
        
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict]: 
            - df_close: 종가 데이터
            - df_high: 고가 데이터
            - df_low: 저가 데이터
            - current_rates: 현재 환율 딕셔너리
    """
    all_tickers = list(DXY_TICKERS.values()) + [USD_KRW_TICKER]
    period_str = PERIOD_MAP.get(period_months, '1y')
    
    with st.spinner(f"yfinance에서 {period_months}개월치 일별 OHLC 데이터를 가져오는 중..."):
        # 전체 OHLC 데이터 다운로드
        df_all = yf.download(all_tickers, period=period_str, interval='1d')
        
        # 컬럼 이름 매핑
        column_mapping = {v: k for k, v in DXY_TICKERS.items()}
        
        # Close 데이터
        df_close = df_all['Close'].copy()
        df_close.rename(columns=column_mapping, inplace=True)
        df_close.rename(columns={USD_KRW_TICKER: 'USD_KRW'}, inplace=True)
        
        # High 데이터 (52주 최고가용)
        df_high = df_all['High'].copy()
        df_high.rename(columns=column_mapping, inplace=True)
        df_high.rename(columns={USD_KRW_TICKER: 'USD_KRW'}, inplace=True)
        
        # Low 데이터 (52주 최저가용)
        df_low = df_all['Low'].copy()
        df_low.rename(columns=column_mapping, inplace=True)
        df_low.rename(columns={USD_KRW_TICKER: 'USD_KRW'}, inplace=True)
        
        # 결측치 제거
        df_close.dropna(inplace=True)
        df_high.dropna(inplace=True)
        df_low.dropna(inplace=True)
    
    # 현재 가격 가져오기
    current_rates = _fetch_current_rates(DXY_TICKERS, USD_KRW_TICKER, df_close)
    
    return df_close, df_high, df_low, current_rates


def _fetch_current_rates(dxy_tickers: Dict, usd_krw_ticker: str, df_close: pd.DataFrame) -> Dict[str, float]:
    """
    현재 환율 정보를 가져오는 내부 함수
    
    Args:
        dxy_tickers: DXY 티커 딕셔너리
        usd_krw_ticker: USD/KRW 티커
        df_close: 종가 데이터프레임 (fallback용)
        
    Returns:
        Dict[str, float]: 현재 환율 정보
    """
    current_rates = {}
    
    with st.spinner("각 통화쌍의 현재 종가를 가져오는 중..."):
        # DXY 통화쌍들
        for key, ticker_symbol in dxy_tickers.items():
            ticker = yf.Ticker(ticker_symbol)
            price = ticker.info.get('regularMarketPrice')
            
            if price is not None:
                current_rates[key] = price
            else:
                # 현재 가격을 가져오지 못하면 마지막 종가 사용
                current_rates[key] = df_close[key].iloc[-1]
        
        # USD/KRW
        ticker = yf.Ticker(usd_krw_ticker)
        price = ticker.info.get('regularMarketPrice')
        
        if price is not None:
            current_rates['USD_KRW'] = price
        else:
            current_rates['USD_KRW'] = df_close['USD_KRW'].iloc[-1]
        
        # JXY (일본 엔화 커런시 인덱스) - USD/JPY 역수로 계산
        usd_jpy_rate = current_rates.get('USD_JPY', df_close['USD_JPY'].iloc[-1])
        current_rates['JXY'] = 100 / usd_jpy_rate
        
        # JPY/KRW (엔/원 환율) - USD/KRW / USD/JPY로 계산
        usd_krw_rate = current_rates.get('USD_KRW', df_close['USD_KRW'].iloc[-1])
        current_rates['JPY_KRW'] = usd_krw_rate / usd_jpy_rate

    return current_rates


def calculate_dollar_index_series(df_close: pd.DataFrame) -> pd.Series:
    """
    환율 종가 데이터프레임을 사용하여 일별 달러 인덱스 시리즈를 계산합니다.
    
    Args:
        df_close: 종가 데이터프레임
        
    Returns:
        pd.Series: 달러 인덱스 시리즈
    """
    with st.spinner("달러 인덱스 (종가 기준) 계산 중..."):
        # 가중 기하평균 계산
        dxy_series = DXY_INITIAL_CONSTANT * (
            (df_close['EUR_USD'] ** DXY_WEIGHTS['EUR_USD']) *
            (df_close['USD_JPY'] ** DXY_WEIGHTS['USD_JPY']) *
            (df_close['GBP_USD'] ** DXY_WEIGHTS['GBP_USD']) *
            (df_close['USD_CAD'] ** DXY_WEIGHTS['USD_CAD']) *
            (df_close['USD_SEK'] ** DXY_WEIGHTS['USD_SEK']) *
            (df_close['USD_CHF'] ** DXY_WEIGHTS['USD_CHF'])
        )
    
    return dxy_series.rename('DXY_Close')


def calculate_current_dxy(current_rates: Dict[str, float]) -> float:
    """
    현재 종가 환율을 사용하여 달러 인덱스 단일 값을 계산합니다.
    
    Args:
        current_rates: 현재 환율 딕셔너리
        
    Returns:
        float: 현재 달러 인덱스 값
    """
    product = 1.0
    for key, weight in DXY_WEIGHTS.items():
        if key in current_rates:
            product *= (current_rates[key] ** weight)
        else:
            return 0.0
    
    return DXY_INITIAL_CONSTANT * product

