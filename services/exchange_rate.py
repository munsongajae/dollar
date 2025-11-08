"""
환율 데이터 수집 서비스
"""
import streamlit as st
import requests
from bs4 import BeautifulSoup
from typing import Optional, Tuple, Dict
import pandas as pd
import yfinance as yf
from config.settings import BITHUMB_USDT_URL


@st.cache_data(ttl=120)
def fetch_usdt_krw_price() -> Optional[float]:
    """
    Bithumb 공개 API에서 USDT/KRW 현재가(종가)를 가져옵니다.
    
    Returns:
        float | None: USDT 가격, 실패 시 None
    """
    try:
        resp = requests.get(BITHUMB_USDT_URL, timeout=5)
        resp.raise_for_status()
        payload = resp.json()
        price_str = payload.get("data", {}).get("closing_price")
        return float(price_str) if price_str is not None else None
    except Exception as e:
        print(f"USDT 가격 조회 실패: {e}")
        return None


@st.cache_data(ttl=180)
def fetch_hana_usd_krw_rate() -> Optional[float]:
    """
    네이버 환율 메인 페이지에서 USD/KRW 값을 파싱합니다.
    
    Returns:
        float | None: 하나은행 달러 환율, 실패 시 None
    """
    url = "https://finance.naver.com/marketindex/"
    try:
        resp = requests.get(url, timeout=7, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        node = soup.select_one("#exchangeList .head_info .value")
        if not node:
            return None
        text = node.get_text(strip=True)
        num = text.replace(",", "").replace("원", "")
        return float(num)
    except Exception as e:
        print(f"하나은행 환율 조회 실패: {e}")
        return None


@st.cache_data(ttl=180)
def fetch_investing_usd_krw_rate() -> Optional[float]:
    """
    인베스팅닷컴 환율 테이블에서 USD/KRW을 파싱합니다.
    
    Returns:
        float | None: 인베스팅닷컴 USD/KRW 환율, 실패 시 None
    """
    url = "https://kr.investing.com/currencies/exchange-rates-table"
    try:
        resp = requests.get(url, timeout=7, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        cell = soup.find("td", {"class": "pid-650-last", "id": "last_12_28"})
        if not cell:
            return None
        text = cell.get_text(strip=True)
        num = text.replace(",", "").replace("원", "")
        return float(num)
    except Exception as e:
        print(f"인베스팅닷컴 USD/KRW 조회 실패: {e}")
        return None


@st.cache_data(ttl=180)
def fetch_investing_jpy_krw_rate() -> Optional[float]:
    """
    인베스팅닷컴 환율 테이블에서 JPY/KRW(원/엔) 값을 파싱합니다.
    
    Returns:
        float | None: 인베스팅닷컴 JPY/KRW 환율, 실패 시 None
    """
    url = "https://kr.investing.com/currencies/exchange-rates-table"
    try:
        resp = requests.get(url, timeout=7, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        cell = soup.find("td", {"id": "last_2_28"})
        if not cell:
            return None
        text = cell.get_text(strip=True)
        num = text.replace(",", "").replace("원", "")
        return float(num)
    except Exception as e:
        print(f"인베스팅닷컴 JPY/KRW 조회 실패: {e}")
        return None


@st.cache_data(ttl=60)
def get_investing_usd_krw_for_portfolio() -> Optional[float]:
    """
    포트폴리오 수익 계산용 인베스팅닷컴 USD/KRW 실시간 환율
    
    Returns:
        float | None: USD/KRW 환율
    """
    return fetch_investing_usd_krw_rate()


@st.cache_data(ttl=60)
def get_investing_jpy_krw_for_portfolio() -> Optional[float]:
    """
    포트폴리오 수익 계산용 인베스팅닷컴 JPY/KRW 실시간 환율
    
    Returns:
        float | None: JPY/KRW 환율
    """
    return fetch_investing_jpy_krw_rate()


@st.cache_data(ttl=300)
def fetch_period_data_and_current_rates(period_months=12) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, float]]:
    """
    yfinance를 사용하여 지정된 기간의 OHLC 데이터와 현재 종가 가격을 가져옵니다.
    
    Args:
        period_months: 분석 기간 (개월 단위, 기본값 12개월)
        
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, float]]: 
            (Close 데이터, High 데이터, Low 데이터, 현재 환율 딕셔너리)
    """
    # 달러 인덱스 공식에 필요한 6개 통화쌍의 야후 티커
    dxy_tickers = {
        'EUR_USD': 'EURUSD=X', 
        'USD_JPY': 'JPY=X', 
        'GBP_USD': 'GBPUSD=X',
        'USD_CAD': 'CAD=X', 
        'USD_SEK': 'SEK=X', 
        'USD_CHF': 'CHF=X'
    }
    
    # USD/KRW 추가 (원달러 환율)
    usd_krw_ticker = 'USDKRW=X'
    all_tickers = list(dxy_tickers.values()) + [usd_krw_ticker]
    
    # 기간 설정
    period_map = {1: '1mo', 3: '3mo', 6: '6mo', 12: '1y'}
    period_str = period_map.get(period_months, '1y')
    
    with st.spinner(f"yfinance에서 {period_months}개월치 일별 OHLC 데이터를 가져오는 중..."):
        # 전체 OHLC 데이터를 가져옵니다.
        df_all = yf.download(all_tickers, period=period_str, interval='1d')
        
        # 컬럼 이름을 달러 인덱스 키에 맞게 변경
        column_mapping = {v: k for k, v in dxy_tickers.items()}
        
        # Close 데이터
        df_close = df_all['Close'].copy()
        df_close.rename(columns=column_mapping, inplace=True)
        df_close.rename(columns={usd_krw_ticker: 'USD_KRW'}, inplace=True)
        
        # High 데이터 (52주 최고가용)
        df_high = df_all['High'].copy()
        df_high.rename(columns=column_mapping, inplace=True)
        df_high.rename(columns={usd_krw_ticker: 'USD_KRW'}, inplace=True)
        
        # Low 데이터 (52주 최저가용)
        df_low = df_all['Low'].copy()
        df_low.rename(columns=column_mapping, inplace=True)
        df_low.rename(columns={usd_krw_ticker: 'USD_KRW'}, inplace=True)
        
        # 결측치 제거
        df_close.dropna(inplace=True)
        df_high.dropna(inplace=True)
        df_low.dropna(inplace=True)
    
    # 현재 가격 (종가 기준) 가져오기
    current_rates = {}
    with st.spinner("각 통화쌍의 현재 종가를 가져오는 중..."):
        # DXY 통화쌍들
        for key, ticker_symbol in dxy_tickers.items():
            ticker = yf.Ticker(ticker_symbol)
            price = ticker.info.get('regularMarketPrice')
            
            if price is not None:
                current_rates[key] = price
            else:
                # 현재 가격을 가져오지 못하면 52주 데이터의 마지막 종가를 사용
                current_rates[key] = df_close[key].iloc[-1]
                st.warning(f"{key}의 현재 가격을 찾을 수 없어, 마지막 종가({current_rates[key]:.4f})를 사용합니다.")
        
        # USD/KRW
        ticker = yf.Ticker(usd_krw_ticker)
        price = ticker.info.get('regularMarketPrice')
        
        if price is not None:
            current_rates['USD_KRW'] = price
        else:
            current_rates['USD_KRW'] = df_close['USD_KRW'].iloc[-1]
            st.warning(f"USD/KRW의 현재 가격을 찾을 수 없어, 마지막 종가({current_rates['USD_KRW']:.2f})를 사용합니다.")
        
        # JXY (일본 엔화 커런시 인덱스) - USD/JPY 역수로 계산
        usd_jpy_rate = current_rates.get('USD_JPY', df_close['USD_JPY'].iloc[-1])
        current_rates['JXY'] = 100 / usd_jpy_rate
        
        # JPY/KRW (엔/원 환율) - USD/KRW / USD/JPY로 계산
        usd_krw_rate = current_rates.get('USD_KRW', df_close['USD_KRW'].iloc[-1])
        current_rates['JPY_KRW'] = usd_krw_rate / usd_jpy_rate
    
    # DataFrame에도 JPY/KRW 및 JXY 컬럼 추가
    if 'USD_JPY' in df_close.columns and 'USD_KRW' in df_close.columns:
        df_close['JPY_KRW'] = df_close['USD_KRW'] / df_close['USD_JPY']
        df_close['JXY'] = 100 / df_close['USD_JPY']
        
        df_high['JPY_KRW'] = df_high['USD_KRW'] / df_high['USD_JPY']
        df_high['JXY'] = 100 / df_high['USD_JPY']
        
        df_low['JPY_KRW'] = df_low['USD_KRW'] / df_low['USD_JPY']
        df_low['JXY'] = 100 / df_low['USD_JPY']

    return df_close, df_high, df_low, current_rates

