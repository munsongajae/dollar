"""
캐시된 환율 데이터 수집 서비스 (데이터베이스 활용)
"""
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Tuple, Dict
from database.exchange_history_db import exchange_history_db
from services.index_calculator import fetch_period_data_and_current_rates


@st.cache_data(ttl=3600, show_spinner=False)  # 1시간 캐시, spinner 비활성화
def fetch_period_data_with_cache(period_months=12) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, float]]:
    """
    데이터베이스 캐시를 활용하여 환율 데이터를 가져옵니다.
    DB에 있는 데이터는 재사용하고, 없는 부분만 yfinance에서 가져옵니다.
    네트워크 오류 시 기존 방식으로 폴백합니다.
    
    Streamlit 캐시(TTL 1시간)로 세션 내 반복 호출을 방지합니다.
    
    Args:
        period_months: 분석 기간 (개월 단위, 기본값 12개월)
        
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, float]]: 
            (Close 데이터, High 데이터, Low 데이터, 현재 환율 딕셔너리)
    """
    try:
        return _fetch_with_db_cache(period_months)
    except Exception as e:
        # UI 요소 제거 - 캐시된 함수 내에서 사용 불가
        return fetch_period_data_and_current_rates(period_months)


def _fetch_with_db_cache(period_months=12) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, float]]:
    # 통화쌍 정의
    dxy_tickers = {
        'EUR_USD': 'EURUSD=X', 
        'USD_JPY': 'JPY=X', 
        'GBP_USD': 'GBPUSD=X',
        'USD_CAD': 'CAD=X', 
        'USD_SEK': 'SEK=X', 
        'USD_CHF': 'CHF=X'
    }
    usd_krw_ticker = 'USDKRW=X'
    all_currency_pairs = list(dxy_tickers.keys()) + ['USD_KRW']
    
    # 필요한 날짜 범위 계산
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_months * 30 + 7)  # 여유있게
    
    # 1. 데이터베이스에서 기존 데이터 조회
    try:
        df_close_db, df_high_db, df_low_db = exchange_history_db.load_history_data(
            all_currency_pairs, start_date, end_date
        )
    except Exception as e:
        df_close_db = pd.DataFrame()
        df_high_db = pd.DataFrame()
        df_low_db = pd.DataFrame()
    
    # 2. 각 통화쌍별 최근 날짜 확인
    try:
        latest_dates = exchange_history_db.get_all_latest_dates(all_currency_pairs)
    except Exception as e:
        latest_dates = {pair: None for pair in all_currency_pairs}
    
    # 3. 업데이트가 필요한지 확인 (모든 통화쌍이 최신이면 스킵)
    needs_update = []
    all_up_to_date = True
    
    for pair, latest_date in latest_dates.items():
        if latest_date is None:
            needs_update.append(pair)
            all_up_to_date = False
        else:
            days_since_update = (datetime.now() - latest_date).days
            if days_since_update >= 1:  # 1일 이상 지난 경우만 업데이트
                needs_update.append(pair)
                all_up_to_date = False
    
    # 4. DB에 충분한 데이터가 있고 최신이면 바로 사용
    if all_up_to_date and not df_close_db.empty:
        df_close = df_close_db
        df_high = df_high_db
        df_low = df_low_db
        # Toast 제거 - 캐시된 함수 내에서 UI 요소 사용 불가
    # 5. 업데이트가 필요하거나 DB가 비어있으면 yfinance에서 가져오기
    elif needs_update or df_close_db.empty:
        period_map = {1: '1mo', 3: '3mo', 6: '6mo', 12: '1y'}
        period_str = period_map.get(period_months, '1y')
        
        # yfinance에서 데이터 가져오기
        ticker_list = list(dxy_tickers.values()) + [usd_krw_ticker]
        
        # Spinner 제거 - 캐시된 함수 내에서 UI 요소 사용 불가
        df_all = yf.download(ticker_list, period=period_str, interval='1d', progress=False)
        
        # 컬럼 이름 변경
        column_mapping = {v: k for k, v in dxy_tickers.items()}
        
        df_close_new = df_all['Close'].copy()
        df_close_new.rename(columns=column_mapping, inplace=True)
        df_close_new.rename(columns={usd_krw_ticker: 'USD_KRW'}, inplace=True)
        
        df_high_new = df_all['High'].copy()
        df_high_new.rename(columns=column_mapping, inplace=True)
        df_high_new.rename(columns={usd_krw_ticker: 'USD_KRW'}, inplace=True)
        
        df_low_new = df_all['Low'].copy()
        df_low_new.rename(columns=column_mapping, inplace=True)
        df_low_new.rename(columns={usd_krw_ticker: 'USD_KRW'}, inplace=True)
        
        df_open_new = df_all['Open'].copy()
        df_open_new.rename(columns=column_mapping, inplace=True)
        df_open_new.rename(columns={usd_krw_ticker: 'USD_KRW'}, inplace=True)
        
        # 결측치 제거
        df_close_new.dropna(inplace=True)
        df_high_new.dropna(inplace=True)
        df_low_new.dropna(inplace=True)
        df_open_new.dropna(inplace=True)
        
        # JPY/KRW 및 JXY 계산
        if 'USD_JPY' in df_close_new.columns and 'USD_KRW' in df_close_new.columns:
            df_close_new['JPY_KRW'] = df_close_new['USD_KRW'] / df_close_new['USD_JPY']
            df_close_new['JXY'] = 100 / df_close_new['USD_JPY']
            
            df_high_new['JPY_KRW'] = df_high_new['USD_KRW'] / df_high_new['USD_JPY']
            df_high_new['JXY'] = 100 / df_high_new['USD_JPY']
            
            df_low_new['JPY_KRW'] = df_low_new['USD_KRW'] / df_low_new['USD_JPY']
            df_low_new['JXY'] = 100 / df_low_new['USD_JPY']
            
            df_open_new['JPY_KRW'] = df_open_new['USD_KRW'] / df_open_new['USD_JPY']
            df_open_new['JXY'] = 100 / df_open_new['USD_JPY']
        
        # 6. 데이터베이스에 저장 (실패해도 계속 진행)
        try:
            success = exchange_history_db.save_history_data(
                df_close_new, df_high_new, df_low_new, df_open_new
            )
            # Toast 제거 - 캐시된 함수 내에서 UI 요소 사용 불가
        except Exception as e:
            # 에러 무시 - 데이터는 정상 사용 가능
            pass
        
        # 7. DB 데이터와 병합 (DB가 비어있지 않은 경우)
        if not df_close_db.empty:
            df_close = pd.concat([df_close_db, df_close_new]).sort_index()
            df_high = pd.concat([df_high_db, df_high_new]).sort_index()
            df_low = pd.concat([df_low_db, df_low_new]).sort_index()
            
            # 중복 제거 (최신 데이터 우선)
            df_close = df_close[~df_close.index.duplicated(keep='last')]
            df_high = df_high[~df_high.index.duplicated(keep='last')]
            df_low = df_low[~df_low.index.duplicated(keep='last')]
        else:
            df_close = df_close_new
            df_high = df_high_new
            df_low = df_low_new
    
    # 8. 현재 가격 가져오기
    current_rates = {}
    # Spinner 제거 - 캐시된 함수 내에서 UI 요소 사용 불가
    for key, ticker_symbol in dxy_tickers.items():
        ticker = yf.Ticker(ticker_symbol)
        price = ticker.info.get('regularMarketPrice')
        
        if price is not None:
            current_rates[key] = price
        else:
            current_rates[key] = df_close[key].iloc[-1]
    
    # USD/KRW
    ticker = yf.Ticker(usd_krw_ticker)
    price = ticker.info.get('regularMarketPrice')
    
    if price is not None:
        current_rates['USD_KRW'] = price
    else:
        current_rates['USD_KRW'] = df_close['USD_KRW'].iloc[-1]
    
    # JXY와 JPY/KRW 계산
    usd_jpy_rate = current_rates.get('USD_JPY', df_close['USD_JPY'].iloc[-1])
    current_rates['JXY'] = 100 / usd_jpy_rate
    
    usd_krw_rate = current_rates.get('USD_KRW', df_close['USD_KRW'].iloc[-1])
    current_rates['JPY_KRW'] = usd_krw_rate / usd_jpy_rate
    
    return df_close, df_high, df_low, current_rates

