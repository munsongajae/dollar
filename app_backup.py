import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, Tuple, List
import datetime
import requests
from bs4 import BeautifulSoup
import uuid
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# --- Supabase 클라이언트 초기화 ---

@st.cache_resource
def init_supabase() -> Client:
    """Supabase 클라이언트 초기화"""
    # .env 파일 로드
    load_dotenv()
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    
    if not url or not key:
        st.warning("⚠️ Supabase 설정이 필요합니다. .env 파일에 SUPABASE_URL과 SUPABASE_ANON_KEY를 설정해주세요.")
        return None
    
    try:
        supabase = create_client(url, key)
        return supabase
    except Exception as e:
        st.error(f"Supabase 연결 실패: {e}")
        return None

# --- 1. 데이터 가져오기 및 처리 ---

def fetch_period_data_and_current_rates(period_months=12) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, float]]:
    """
    yfinance를 사용하여 지정된 기간의 OHLC 데이터와 현재 종가 가격을 가져옵니다.
    period_months: 분석 기간 (개월 단위, 기본값 12개월)
    """
    # 달러 인덱스 공식에 필요한 6개 통화쌍의 야후 티커
    dxy_tickers = {
        'EUR_USD': 'EURUSD=X', 'USD_JPY': 'JPY=X', 'GBP_USD': 'GBPUSD=X',
        'USD_CAD': 'CAD=X', 'USD_SEK': 'SEK=X', 'USD_CHF': 'CHF=X'
    }
    
    # USD/KRW 추가 (원달러 환율)
    usd_krw_ticker = 'USDKRW=X'
    # JXY는 USD/JPY 역수로 계산하므로 별도 티커 불필요
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

    return df_close, df_high, df_low, current_rates


# --- 2. 달러 인덱스 계산 로직 ---

def calculate_dollar_index_series(df_close: pd.DataFrame) -> pd.Series:
    """
    환율 종가 데이터프레임(52주치)을 사용하여 일별 달러 인덱스 시리즈를 계산합니다.
    """
    INITIAL_CONSTANT = 50.143432

    # 달러 인덱스 공식에 사용되는 가중치 (EUR/USD, GBP/USD는 음수 지수)
    weights = {
        'EUR_USD': -0.576, 'USD_JPY': 0.136, 'GBP_USD': -0.119,
        'USD_CAD': 0.091, 'USD_SEK': 0.042, 'USD_CHF': 0.036
    }
    
    with st.spinner("52주치 달러 인덱스 (종가 기준) 계산 중..."):
        # 가중 기하평균 계산
        dxy_series = INITIAL_CONSTANT * (
            (df_close['EUR_USD'] ** weights['EUR_USD']) *
            (df_close['USD_JPY'] ** weights['USD_JPY']) *
            (df_close['GBP_USD'] ** weights['GBP_USD']) *
            (df_close['USD_CAD'] ** weights['USD_CAD']) *
            (df_close['USD_SEK'] ** weights['USD_SEK']) *
            (df_close['USD_CHF'] ** weights['USD_CHF'])
        )
    
    return dxy_series.rename('DXY_Close')

def calculate_current_dxy(current_rates: Dict[str, float]) -> float:
    """현재 종가 환율을 사용하여 달러 인덱스 단일 값을 계산합니다."""
    weights = {
        'EUR_USD': -0.576, 'USD_JPY': 0.136, 'GBP_USD': -0.119,
        'USD_CAD': 0.091, 'USD_SEK': 0.042, 'USD_CHF': 0.036
    }
    INITIAL_CONSTANT = 50.143432
    
    product = 1.0
    for key, weight in weights.items():
        if key in current_rates:
            product *= (current_rates[key] ** weight)
        else:
            return 0.0 
    
    return INITIAL_CONSTANT * product


# --- 3. 대시보드 함수들 ---

def create_jxy_position_indicator(current_jxy, jxy_52w_high, jxy_52w_low, jxy_52w_mid):
    """JXY (일본 엔화 커런시 인덱스) 위치 표시 - 시각화만"""
    st.markdown("### 💴 엔화지수")
    
    # O/X 표시 로직 (현재값이 중간값보다 높으면 X, 낮으면 O)
    is_above_mid = current_jxy > jxy_52w_mid
    ox_symbol = "X" if is_above_mid else "O"
    ox_color = "#dc3545" if is_above_mid else "#28a745"
    
    # 위치 계산 (0-100%)
    position_percent = ((current_jxy - jxy_52w_low) / (jxy_52w_high - jxy_52w_low)) * 100
    position_percent = max(0, min(100, position_percent))  # 0-100% 범위 제한
    
    # 커스텀 HTML/CSS로 시각화 (O/X 표시를 상태바 왼쪽에 추가)
    st.markdown(f"""
    <div style="
        display: flex;
        align-items: center;
        gap: 20px;
        margin: 20px 0;
    ">
        <div style="
            font-size: 48px;
            color: {ox_color};
            flex-shrink: 0;
        ">
            {ox_symbol}
        </div>
        <div style="
            background: linear-gradient(to right, #44ff44 0%, #ffaa00 50%, #ff4444 100%);
            height: 40px;
            border-radius: 20px;
            position: relative;
            flex-grow: 1;
            border: 2px solid #333;
        ">
            <!-- 중간값 역삼각형 -->
            <div style="
                position: absolute;
                left: 50%;
                top: -5px;
                width: 0;
                height: 0;
                border-left: 8px solid transparent;
                border-right: 8px solid transparent;
                border-top: 15px solid #ff0000;
                transform: translateX(-50%);
            "></div>
            <!-- 현재값 역삼각형 -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: -5px;
                width: 0;
                height: 0;
                border-left: 8px solid transparent;
                border-right: 8px solid transparent;
                border-top: 15px solid #000;
                transform: translateX(-50%);
            "></div>
            <div style="
                position: absolute;
                left: 0%;
                top: 45px;
                font-size: 12px;
                color: #666;
            ">최저<br>{jxy_52w_low*100:.2f}</div>
            <div style="
                position: absolute;
                left: 50%;
                top: 45px;
                font-size: 12px;
                color: #666;
                transform: translateX(-50%);
            ">중간<br><br>{jxy_52w_mid*100:.2f}</div>
            <div style="
                position: absolute;
                right: 0%;
                top: 45px;
                font-size: 12px;
                color: #666;
            ">최고<br>{jxy_52w_high*100:.2f}</div>
            <!-- 현재값 라벨 (화살표 위에) -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: -25px;
                font-size: 12px;
                font-weight: bold;
                color: #000;
                transform: translateX(-50%);
            ">현재</div>
            <!-- 현재값 수치 (그라데이션 바 중앙) -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: 50%;
                font-size: 14px;
                font-weight: bold;
                color: #000;
                transform: translate(-50%, -50%);
            ">{current_jxy*100:.2f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_jpy_position_indicator(current_jpy_krw, jpy_krw_52w_high, jpy_krw_52w_low, jpy_krw_52w_mid):
    """엔화(JPY/KRW) 위치 표시 - 시각화만"""
    st.markdown("### 💴 엔화환율")
    
    # O/X 표시 로직 (현재값이 중간값보다 낮으면 O, 높으면 X)
    is_below_mid = current_jpy_krw < jpy_krw_52w_mid
    ox_symbol = "O" if is_below_mid else "X"
    ox_color = "#28a745" if is_below_mid else "#dc3545"
    
    # 위치 계산 (0-100%)
    position_percent = ((current_jpy_krw - jpy_krw_52w_low) / (jpy_krw_52w_high - jpy_krw_52w_low)) * 100
    position_percent = max(0, min(100, position_percent))  # 0-100% 범위 제한
    
    # 커스텀 HTML/CSS로 시각화 (O/X 표시를 상태바 왼쪽에 추가)
    st.markdown(f"""
    <div style="
        display: flex;
        align-items: center;
        gap: 20px;
        margin: 20px 0;
    ">
        <div style="
            font-size: 48px;
            color: {ox_color};
            flex-shrink: 0;
        ">
            {ox_symbol}
        </div>
        <div style="
            background: linear-gradient(to right, #44ff44 0%, #ffaa00 50%, #ff4444 100%);
            height: 40px;
            border-radius: 20px;
            position: relative;
            flex-grow: 1;
            border: 2px solid #333;
        ">
            <!-- 중간값 역삼각형 -->
            <div style="
                position: absolute;
                left: 50%;
                top: -5px;
                width: 0;
                height: 0;
                border-left: 8px solid transparent;
                border-right: 8px solid transparent;
                border-top: 15px solid #ff0000;
                transform: translateX(-50%);
            "></div>
            <!-- 현재값 역삼각형 -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: -5px;
                width: 0;
                height: 0;
                border-left: 8px solid transparent;
                border-right: 8px solid transparent;
                border-top: 15px solid #000;
                transform: translateX(-50%);
            "></div>
            <div style="
                position: absolute;
                left: 0%;
                top: 45px;
                font-size: 12px;
                color: #666;
            ">최저<br>{jpy_krw_52w_low*100:.2f}</div>
            <div style="
                position: absolute;
                left: 50%;
                top: 45px;
                font-size: 12px;
                color: #666;
                transform: translateX(-50%);
            ">중간<br><br>{jpy_krw_52w_mid*100:.2f}</div>
            <div style="
                position: absolute;
                right: 0%;
                top: 45px;
                font-size: 12px;
                color: #666;
            ">최고<br>{jpy_krw_52w_high*100:.2f}</div>
            <!-- 현재값 라벨 (화살표 위에) -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: -25px;
                font-size: 12px;
                font-weight: bold;
                color: #000;
                transform: translateX(-50%);
            ">현재</div>
            <!-- 현재값 수치 (그라데이션 바 중앙) -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: 50%;
                font-size: 14px;
                font-weight: bold;
                color: #000;
                transform: translate(-50%, -50%);
            ">{current_jpy_krw*100:.2f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_jpy_gap_indicator(current_jxy, current_jpy_krw, jxy_52w_mid, jpy_krw_52w_mid):
    """엔화 갭 비율 계산 및 표시"""
    st.markdown("### 📊 엔화 갭 비율")
    
    # 현재 엔화 갭 비율 계산 (엔화지수*100 / 엔화환율*100)
    current_jpy_gap_ratio = (current_jxy * 100) / (current_jpy_krw * 100)
    
    # 52주 중간 엔화 갭 비율 계산
    mid_jpy_gap_ratio = (jxy_52w_mid * 100) / (jpy_krw_52w_mid * 100)
    
    # O/X 표시 로직 (현재 갭 비율이 중간 갭 비율보다 크면 O)
    is_above_mid = current_jpy_gap_ratio > mid_jpy_gap_ratio
    ox_symbol = "O" if is_above_mid else "X"
    ox_color = "#28a745" if is_above_mid else "#dc3545"
    
    # 범위 설정 (±20%)
    min_jpy_gap_ratio = mid_jpy_gap_ratio * 0.8
    max_jpy_gap_ratio = mid_jpy_gap_ratio * 1.2
    
    # 위치 계산
    if current_jpy_gap_ratio <= min_jpy_gap_ratio:
        position_percent = 0
    elif current_jpy_gap_ratio >= max_jpy_gap_ratio:
        position_percent = 100
    else:
        position_percent = ((current_jpy_gap_ratio - min_jpy_gap_ratio) / (max_jpy_gap_ratio - min_jpy_gap_ratio)) * 100
    
    # 중간 갭 비율 위치 (50%)
    mid_position_percent = 50
    
    # 커스텀 HTML/CSS로 시각화 (O/X 표시를 상태바 왼쪽에 추가)
    st.markdown(f"""
    <div style="
        display: flex;
        align-items: center;
        gap: 20px;
        margin: 20px 0;
    ">
        <div style="
            font-size: 48px;
            color: {ox_color};
            flex-shrink: 0;
        ">
            {ox_symbol}
        </div>
        <div style="
            background: linear-gradient(to right, #44ff44 0%, #ffaa00 50%, #ff4444 100%);
            height: 40px;
            border-radius: 20px;
            position: relative;
            flex-grow: 1;
            border: 2px solid #333;
        ">
            <!-- 중간 갭 비율 표시 라인 -->
            <div style="
                position: absolute;
                left: {mid_position_percent}%;
                top: -5px;
                width: 0;
                height: 0;
                border-left: 8px solid transparent;
                border-right: 8px solid transparent;
                border-top: 15px solid #ff0000;
                transform: translateX(-50%);
            "></div>
            <!-- 현재 갭 비율 표시 라인 -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: -5px;
                width: 0;
                height: 0;
                border-left: 8px solid transparent;
                border-right: 8px solid transparent;
                border-top: 15px solid #000;
                transform: translateX(-50%);
            "></div>
            <!-- 최소값 라벨 -->
            <div style="
                position: absolute;
                left: 0%;
                top: 45px;
                font-size: 12px;
                color: #666;
            ">최소<br>{min_jpy_gap_ratio*100:.2f}%</div>
            <!-- 중간값 라벨 -->
            <div style="
                position: absolute;
                left: 50%;
                top: 45px;
                font-size: 12px;
                color: #666;
                transform: translateX(-50%);
            ">중간<br><br>{mid_jpy_gap_ratio*100:.2f}%</div>
            <!-- 최대값 라벨 -->
            <div style="
                position: absolute;
                right: 0%;
                top: 45px;
                font-size: 12px;
                color: #666;
            ">최대<br>{max_jpy_gap_ratio*100:.2f}%</div>
            <!-- 현재값 라벨 (화살표 위에) -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: -25px;
                font-size: 12px;
                font-weight: bold;
                color: #000;
                transform: translateX(-50%);
            ">현재</div>
            <!-- 현재값 수치 (그라데이션 바 중앙) -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: 50%;
                font-size: 14px;
                font-weight: bold;
                color: #000;
                transform: translate(-50%, -50%);
            ">{current_jpy_gap_ratio*100:.2f}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_jpy_fair_exchange_rate_indicator(current_jxy, current_jpy_krw, jxy_52w_mid, jpy_krw_52w_mid):
    """엔화 적정 환율 계산 및 표시"""
    st.markdown("### ⚖️ 엔화 적정 환율")
    
    # 52주 중간 엔화 갭 비율 계산
    mid_jpy_gap_ratio = (jxy_52w_mid ) / (jpy_krw_52w_mid )
    
    # 엔화 적정 환율 계산 (현재 엔화지수*100 / 52주 중간 엔화 갭 비율)
    fair_jpy_exchange_rate = (current_jxy ) / mid_jpy_gap_ratio
    
    # O/X 표시 로직 (현재 엔화 환율이 적정 환율보다 낮으면 O, 높으면 X)
    is_below_fair = current_jpy_krw < fair_jpy_exchange_rate
    ox_symbol = "O" if is_below_fair else "X"
    ox_color = "#28a745" if is_below_fair else "#dc3545"
    
    # 범위 설정 (±10%)
    min_fair_rate = fair_jpy_exchange_rate * 0.9
    max_fair_rate = fair_jpy_exchange_rate * 1.1
    
    # 위치 계산
    if current_jpy_krw <= min_fair_rate:
        position_percent = 0
    elif current_jpy_krw >= max_fair_rate:
        position_percent = 100
    else:
        position_percent = ((current_jpy_krw - min_fair_rate) / (max_fair_rate - min_fair_rate)) * 100
    
    # 적정값 위치 (50%)
    fair_position_percent = 50
    
    # 커스텀 HTML/CSS로 시각화 (O/X 표시를 상태바 왼쪽에 추가)
    st.markdown(f"""
    <div style="
        display: flex;
        align-items: center;
        gap: 20px;
        margin: 20px 0;
    ">
        <div style="
            font-size: 48px;
            color: {ox_color};
            flex-shrink: 0;
        ">
            {ox_symbol}
        </div>
        <div style="
            background: linear-gradient(to right, #44ff44 0%, #ffaa00 50%, #ff4444 100%);
            height: 40px;
            border-radius: 20px;
            position: relative;
            flex-grow: 1;
            border: 2px solid #333;
        ">
            <!-- 적정 환율 표시 라인 -->
            <div style="
                position: absolute;
                left: {fair_position_percent}%;
                top: -5px;
                width: 0;
                height: 0;
                border-left: 8px solid transparent;
                border-right: 8px solid transparent;
                border-top: 15px solid #ff0000;
                transform: translateX(-50%);
            "></div>
            <!-- 현재 환율 표시 라인 -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: -5px;
                width: 0;
                height: 0;
                border-left: 8px solid transparent;
                border-right: 8px solid transparent;
                border-top: 15px solid #000;
                transform: translateX(-50%);
            "></div>
            <!-- 최소 환율 라벨 -->
            <div style="
                position: absolute;
                left: 0%;
                top: 45px;
                font-size: 12px;
                color: #666;
            ">최소<br>{min_fair_rate*100:.2f}</div>
            <!-- 적정 환율 라벨 -->
            <div style="
                position: absolute;
                left: 50%;
                top: 45px;
                font-size: 12px;
                color: #666;
                transform: translateX(-50%);
            ">적정<br><br>{fair_jpy_exchange_rate*100:.2f}</div>
            <!-- 최대 환율 라벨 -->
            <div style="
                position: absolute;
                right: 0%;
                top: 45px;
                font-size: 12px;
                color: #666;
            ">최대<br>{max_fair_rate*100:.2f}</div>
            <!-- 현재값 라벨 (화살표 위에) -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: -25px;
                font-size: 12px;
                font-weight: bold;
                color: #000;
                transform: translateX(-50%);
            ">현재</div>
            <!-- 현재값 수치 (그라데이션 바 중앙) -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: 50%;
                font-size: 14px;
                font-weight: bold;
                color: #000;
                transform: translate(-50%, -50%);
            ">{current_jpy_krw*100:.2f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_fair_exchange_rate_indicator(current_dxy: float, current_usd_krw: float, dxy_52w_mid: float, usd_krw_52w_mid: float):
    """적정 환율을 시각적으로 표시하는 인디케이터를 생성합니다."""
    
    # 52주 중간 달러 갭 비율 계산
    mid_gap_ratio = (dxy_52w_mid / usd_krw_52w_mid) * 100
    
    # 적정 환율 계산 (현재 달러지수 / 52주 중간 달러 갭 비율 * 100)
    fair_exchange_rate = (current_dxy / mid_gap_ratio) * 100
    
    # 현재 환율과 적정 환율 비교하여 O/X 표시 결정
    if current_usd_krw < fair_exchange_rate:
        ox_symbol = "O"  # O 표시 (현재 환율이 적정 환율보다 낮음)
        ox_color = "#28a745"  # 초록색
    else:
        ox_symbol = "X"  # X 표시 (현재 환율이 적정 환율보다 높음)
        ox_color = "#dc3545"  # 빨간색
    
    # 범위 계산을 위해 최소/최대 환율 계산 (적정 환율 기준으로 대칭 범위 설정)
    # 적정 환율에서 ±10% 범위로 설정 (환율 특성상 좁은 범위)
    range_percent = 10  # 적정 환율에서 ±10%
    min_fair_rate = fair_exchange_rate * (1 - range_percent / 100)
    max_fair_rate = fair_exchange_rate * (1 + range_percent / 100)
    
    # 현재 환율의 위치 계산
    if current_usd_krw <= min_fair_rate:
        position_percent = 0
    elif current_usd_krw >= max_fair_rate:
        position_percent = 100
    else:
        position_percent = ((current_usd_krw - min_fair_rate) / (max_fair_rate - min_fair_rate)) * 100
    
    # 적정 환율 위치 (항상 50%)
    fair_position_percent = 50
    
    # 시각적 범위 표시
    st.markdown("### 💰 적정 환율")
    
    # 범위 기반 시각화 (달러 갭 비율과 같은 스타일)
    st.markdown(f"""
    <div style="
        display: flex;
        align-items: center;
        gap: 20px;
        margin: 20px 0;
    ">
        <div style="
            font-size: 48px;
            color: {ox_color};
            flex-shrink: 0;
        ">
            {ox_symbol}
        </div>
        <div style="
            background: linear-gradient(to right, #44ff44 0%, #ffaa00 50%, #ff4444 100%);
            height: 40px;
            border-radius: 20px;
            position: relative;
            flex-grow: 1;
            border: 2px solid #333;
        ">
            <!-- 적정 환율 표시 라인 -->
            <div style="
                position: absolute;
                left: {fair_position_percent}%;
                top: -5px;
                width: 0;
                height: 0;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 12px solid #ff0000;
                transform: translateX(-50%);
            "></div>
            <!-- 현재 환율 표시 라인 -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: -8px;
                width: 0;
                height: 0;
                border-left: 8px solid transparent;
                border-right: 8px solid transparent;
                border-top: 15px solid #000;
                transform: translateX(-50%);
            "></div>
            <!-- 최소 환율 라벨 -->
            <div style="
                position: absolute;
                left: 0%;
                top: 45px;
                font-size: 12px;
                color: #666;
            ">최소<br>{min_fair_rate:.0f}원</div>
            <!-- 적정 환율 라벨 -->
            <div style="
                position: absolute;
                left: 50%;
                top: 45px;
                font-size: 12px;
                color: #666;
                transform: translateX(-50%);
            ">적정<br>{fair_exchange_rate:.0f}원</div>
            <!-- 최대 환율 라벨 -->
            <div style="
                position: absolute;
                right: 0%;
                top: 45px;
                font-size: 12px;
                color: #666;
            ">최대<br>{max_fair_rate:.0f}원</div>
            <!-- 현재 환율 라벨 (화살표 위에) -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: -25px;
                font-size: 12px;
                font-weight: bold;
                color: #000;
                transform: translateX(-50%);
            ">현재</div>
            <!-- 현재 환율 수치 (그라데이션 바 중앙) -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: 50%;
                font-size: 14px;
                font-weight: bold;
                color: #000;
                transform: translate(-50%, -50%);
            ">{current_usd_krw:.0f}원</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_dollar_gap_indicator(current_dxy: float, current_usd_krw: float, dxy_52w_mid: float, usd_krw_52w_mid: float):
    """달러 갭 비율을 시각적으로 표시하는 인디케이터를 생성합니다."""
    
    # 현재 달러 갭 비율 계산 (달러지수/원달러환율 * 100)
    current_gap_ratio = (current_dxy / current_usd_krw) * 100
    
    # 52주 중간 달러 갭 비율 계산
    mid_gap_ratio = (dxy_52w_mid / usd_krw_52w_mid) * 100
    
    # 중간 갭 비율 대비 O/X 표시 결정
    if current_gap_ratio > mid_gap_ratio:
        ox_symbol = "O"  # O 표시 (중간 갭 비율보다 높음)
        ox_color = "#28a745"  # 초록색
    else:
        ox_symbol = "X"  # X 표시 (중간 갭 비율보다 낮거나 같음)
        ox_color = "#dc3545"  # 빨간색
    
    # 범위 계산을 위해 최소/최대 갭 비율 계산 (중간값 기준으로 대칭 범위 설정)
    # 중간값에서 ±20% 범위로 설정 (실제 데이터 범위에 따라 조정 가능)
    range_percent = 20  # 중간값에서 ±20%
    min_gap_ratio = mid_gap_ratio * (1 - range_percent / 100)
    max_gap_ratio = mid_gap_ratio * (1 + range_percent / 100)
    
    # 현재 갭 비율의 위치 계산
    if current_gap_ratio <= min_gap_ratio:
        position_percent = 0
    elif current_gap_ratio >= max_gap_ratio:
        position_percent = 100
    else:
        position_percent = ((current_gap_ratio - min_gap_ratio) / (max_gap_ratio - min_gap_ratio)) * 100
    
    # 중간값 위치 (항상 50%)
    mid_position_percent = 50
    
    # 시각적 범위 표시
    st.markdown("### 📊 달러 갭 비율")
    
    # 범위 기반 시각화 (달러지수/원달러환율과 같은 스타일)
    st.markdown(f"""
    <div style="
        display: flex;
        align-items: center;
        gap: 20px;
        margin: 20px 0;
    ">
        <div style="
            font-size: 48px;
            color: {ox_color};
            flex-shrink: 0;
        ">
            {ox_symbol}
        </div>
        <div style="
            background: linear-gradient(to right, #44ff44 0%, #ffaa00 50%, #ff4444 100%);
            height: 40px;
            border-radius: 20px;
            position: relative;
            flex-grow: 1;
            border: 2px solid #333;
        ">
            <!-- 중간값 표시 라인 -->
            <div style="
                position: absolute;
                left: {mid_position_percent}%;
                top: -5px;
                width: 0;
                height: 0;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 12px solid #ff0000;
                transform: translateX(-50%);
            "></div>
            <!-- 현재값 표시 라인 -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: -8px;
                width: 0;
                height: 0;
                border-left: 8px solid transparent;
                border-right: 8px solid transparent;
                border-top: 15px solid #000;
                transform: translateX(-50%);
            "></div>
            <!-- 최소값 라벨 -->
            <div style="
                position: absolute;
                left: 0%;
                top: 45px;
                font-size: 12px;
                color: #666;
            ">최소<br>{min_gap_ratio:.2f}%</div>
            <!-- 중간값 라벨 -->
            <div style="
                position: absolute;
                left: 50%;
                top: 45px;
                font-size: 12px;
                color: #666;
                transform: translateX(-50%);
            ">중간<br>{mid_gap_ratio:.2f}%</div>
            <!-- 최대값 라벨 -->
            <div style="
                position: absolute;
                right: 0%;
                top: 45px;
                font-size: 12px;
                color: #666;
            ">최대<br>{max_gap_ratio:.2f}%</div>
            <!-- 현재값 라벨 (화살표 위에) -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: -25px;
                font-size: 12px;
                font-weight: bold;
                color: #000;
                transform: translateX(-50%);
            ">현재</div>
            <!-- 현재값 수치 (그라데이션 바 중앙) -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: 50%;
                font-size: 14px;
                font-weight: bold;
                color: #000;
                transform: translate(-50%, -50%);
            ">{current_gap_ratio:.2f}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_usd_krw_position_indicator(current_usd_krw: float, usd_krw_52w_high: float, usd_krw_52w_low: float, usd_krw_52w_mid: float):
    """원달러 환율의 현재 위치를 시각적으로 표시하는 인디케이터를 생성합니다."""
    
    # 범위 계산
    range_diff = usd_krw_52w_high - usd_krw_52w_low
    position_percent = (current_usd_krw - usd_krw_52w_low) / range_diff * 100 if range_diff > 0 else 0
    
    # 중간값 대비 O/X 표시 결정
    if current_usd_krw > usd_krw_52w_mid:
        ox_symbol = "X"  # X 표시 (중간값보다 높음)
        ox_color = "#dc3545"  # 빨간색
    else:
        ox_symbol = "O"  # O 표시 (중간값보다 낮거나 같음)
        ox_color = "#28a745"  # 초록색
    
    # 시각적 범위 표시
    st.markdown("### 💴 원달러 환율")
    
    # 프로그레스 바 스타일의 시각화 (O/X 표시 포함)
    progress_value = position_percent / 100
    
    # 색상 결정 (중간값 기준)
    if position_percent > 50:
        progress_color = "#ff4444"  # 빨간색 (중간값 위)
    elif position_percent < 50:
        progress_color = "#4444ff"  # 파란색 (중간값 아래)
    else:
        progress_color = "#ffaa00"  # 노란색 (중간값과 같음)
    
    # 커스텀 HTML/CSS로 시각화 (O/X 표시를 상태바 왼쪽에 추가)
    st.markdown(f"""
    <div style="
        display: flex;
        align-items: center;
        gap: 20px;
        margin: 20px 0;
    ">
        <div style="
            font-size: 48px;
            color: {ox_color};
            flex-shrink: 0;
        ">
            {ox_symbol}
        </div>
        <div style="
            background: linear-gradient(to right, #44ff44 0%, #ffaa00 50%, #ff4444 100%);
            height: 40px;
            border-radius: 20px;
            position: relative;
            flex-grow: 1;
            border: 2px solid #333;
        ">
            <!-- 중간값 역삼각형 -->
            <div style="
                position: absolute;
                left: 50%;
                top: -5px;
                width: 0;
                height: 0;
                border-left: 8px solid transparent;
                border-right: 8px solid transparent;
                border-top: 15px solid #ff0000;
                transform: translateX(-50%);
            "></div>
            <!-- 현재값 역삼각형 -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: -5px;
                width: 0;
                height: 0;
                border-left: 8px solid transparent;
                border-right: 8px solid transparent;
                border-top: 15px solid #000;
                transform: translateX(-50%);
            "></div>
            <div style="
                position: absolute;
                left: 0%;
                top: 45px;
                font-size: 12px;
                color: #666;
            ">최저<br>{usd_krw_52w_low:.0f}</div>
            <div style="
                position: absolute;
                left: 50%;
                top: 45px;
                font-size: 12px;
                color: #666;
                transform: translateX(-50%);
            ">중간 {usd_krw_52w_mid:.0f}</div>
            <div style="
                position: absolute;
                right: 0%;
                top: 45px;
                font-size: 12px;
                color: #666;
            ">최고<br>{usd_krw_52w_high:.0f}</div>
            <!-- 현재값 라벨 (화살표 위에) -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: -25px;
                font-size: 12px;
                font-weight: bold;
                color: #000;
                transform: translateX(-50%);
            ">현재</div>
            <!-- 현재값 수치 (그라데이션 바 중앙) -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: 50%;
                font-size: 14px;
                font-weight: bold;
                color: #000;
                transform: translate(-50%, -50%);
            ">{current_usd_krw:.0f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_position_indicator(current_dxy: float, dxy_52w_high: float, dxy_52w_low: float, dxy_52w_mid: float):
    """현재 DXY 위치를 시각적으로 표시하는 인디케이터를 생성합니다."""
    
    # 범위 계산
    range_diff = dxy_52w_high - dxy_52w_low
    position_percent = (current_dxy - dxy_52w_low) / range_diff * 100 if range_diff > 0 else 0
    
    # 중간값 대비 O/X 표시 결정
    if current_dxy > dxy_52w_mid:
        ox_symbol = "X"  # X 표시 (중간값보다 높음)
        ox_color = "#dc3545"  # 빨간색
    else:
        ox_symbol = "O"  # O 표시 (중간값보다 낮거나 같음)
        ox_color = "#28a745"  # 초록색
    
    # 시각적 범위 표시
    st.markdown("### 💵 달러지수")
    
    # 프로그레스 바 스타일의 시각화 (O/X 표시 포함)
    progress_value = position_percent / 100
    
    # 색상 결정 (중간값 기준)
    if position_percent > 50:
        progress_color = "#ff4444"  # 빨간색 (중간값 위)
    elif position_percent < 50:
        progress_color = "#4444ff"  # 파란색 (중간값 아래)
    else:
        progress_color = "#ffaa00"  # 노란색 (중간값과 같음)
    
    # 커스텀 HTML/CSS로 시각화 (O/X 표시를 상태바 왼쪽에 추가)
    st.markdown(f"""
    <div style="
        display: flex;
        align-items: center;
        gap: 20px;
        margin: 20px 0;
    ">
        <div style="
            font-size: 48px;
            color: {ox_color};
            flex-shrink: 0;
        ">
            {ox_symbol}
        </div>
        <div style="
            background: linear-gradient(to right, #44ff44 0%, #ffaa00 50%, #ff4444 100%);
            height: 40px;
            border-radius: 20px;
            position: relative;
            flex-grow: 1;
            border: 2px solid #333;
        ">
            <!-- 중간값 역삼각형 -->
            <div style="
                position: absolute;
                left: 50%;
                top: -5px;
                width: 0;
                height: 0;
                border-left: 8px solid transparent;
                border-right: 8px solid transparent;
                border-top: 15px solid #ff0000;
                transform: translateX(-50%);
            "></div>
            <!-- 현재값 역삼각형 -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: -5px;
                width: 0;
                height: 0;
                border-left: 8px solid transparent;
                border-right: 8px solid transparent;
                border-top: 15px solid #000;
                transform: translateX(-50%);
            "></div>
            <div style="
                position: absolute;
                left: 0%;
                top: 45px;
                font-size: 12px;
                color: #666;
            ">최저<br>{dxy_52w_low:.2f}</div>
            <div style="
                position: absolute;
                left: 50%;
                top: 45px;
                font-size: 12px;
                color: #666;
                transform: translateX(-50%);
            ">중간 {dxy_52w_mid:.2f}</div>
            <div style="
                position: absolute;
                right: 0%;
                top: 45px;
                font-size: 12px;
                color: #666;
            ">최고<br>{dxy_52w_high:.2f}</div>
            <!-- 현재값 라벨 (화살표 위에) -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: -25px;
                font-size: 12px;
                font-weight: bold;
                color: #000;
                transform: translateX(-50%);
            ">현재</div>
            <!-- 현재값 수치 (그라데이션 바 중앙) -->
            <div style="
                position: absolute;
                left: {position_percent}%;
                top: 50%;
                font-size: 14px;
                font-weight: bold;
                color: #000;
                transform: translate(-50%, -50%);
            ">{current_dxy:.2f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_dxy_chart(dxy_close: pd.Series, current_dxy: float, dxy_52w_high: float, dxy_52w_low: float, dxy_52w_mid: float, period_name: str = "1년"):
    """달러 인덱스 차트를 생성합니다."""
    fig = go.Figure()
    
    # 52주 달러 인덱스 라인
    fig.add_trace(go.Scatter(
        x=dxy_close.index,
        y=dxy_close.values,
        mode='lines',
        name='DXY (52주)',
        line=dict(color='blue', width=2)
    ))
    
    # 현재 가격 라인
    fig.add_hline(
        y=current_dxy,
        line_dash="dash",
        line_color="red",
        annotation_text=f"현재: {current_dxy:.2f}",
        annotation_position="bottom right"
    )
    
    # 52주 최고가 라인
    fig.add_hline(
        y=dxy_52w_high,
        line_dash="dot",
        line_color="green",
        annotation_text=f"52주 최고: {dxy_52w_high:.2f}",
        annotation_position="top right"
    )
    
    # 52주 최저가 라인
    fig.add_hline(
        y=dxy_52w_low,
        line_dash="dot",
        line_color="orange",
        annotation_text=f"52주 최저: {dxy_52w_low:.2f}",
        annotation_position="bottom right"
    )
    
    # 52주 중간값 라인
    fig.add_hline(
        y=dxy_52w_mid,
        line_dash="dashdot",
        line_color="purple",
        annotation_text=f"52주 중간: {dxy_52w_mid:.2f}",
        annotation_position="top left"
    )
    
    fig.update_layout(
        title=f"달러 인덱스 (DXY) {period_name} 차트",
        xaxis_title="날짜",
        yaxis_title="DXY",
        hovermode='x unified',
        height=500
    )
    # DXY y축은 데이터 기반으로 유연하게 표시 (고정 해제)
    
    return fig

def create_usd_jpy_chart(usd_jpy_series: pd.Series, current_usd_jpy: float, usd_jpy_52w_high: float, usd_jpy_52w_low: float, usd_jpy_52w_mid: float):
    """엔화 환율 차트를 생성합니다."""
    fig = go.Figure()
    
    # 52주 USD/JPY 라인
    fig.add_trace(go.Scatter(
        x=usd_jpy_series.index,
        y=usd_jpy_series.values,
        mode='lines',
        name='USD/JPY (52주)',
        line=dict(color='blue', width=2)
    ))
    
    # 현재 가격 라인
    fig.add_hline(
        y=current_usd_jpy,
        line_dash="dash",
        line_color="red",
        annotation_text=f"현재: {current_usd_jpy:.2f}",
        annotation_position="bottom right"
    )
    
    # 52주 최고가 라인
    fig.add_hline(
        y=usd_jpy_52w_high,
        line_dash="dot",
        line_color="green",
        annotation_text=f"52주 최고: {usd_jpy_52w_high:.2f}",
        annotation_position="top right"
    )
    
    # 52주 최저가 라인
    fig.add_hline(
        y=usd_jpy_52w_low,
        line_dash="dot",
        line_color="orange",
        annotation_text=f"52주 최저: {usd_jpy_52w_low:.2f}",
        annotation_position="bottom right"
    )
    
    # 52주 중간값 라인
    fig.add_hline(
        y=usd_jpy_52w_mid,
        line_dash="dashdot",
        line_color="purple",
        annotation_text=f"52주 중간: {usd_jpy_52w_mid:.2f}",
        annotation_position="top left"
    )
    
    fig.update_layout(
        title="엔화 환율 (USD/JPY) 52주 차트",
        xaxis_title="날짜",
        yaxis_title="USD/JPY",
        hovermode='x unified',
        height=500
    )
    
    return fig

def create_jpy_krw_chart(jpy_krw_series: pd.Series, current_jpy_krw: float, jpy_krw_52w_high: float, jpy_krw_52w_low: float, jpy_krw_52w_mid: float, period_name: str = "1년"):
    """JPY/KRW 차트를 생성합니다."""
    fig = go.Figure()
    
    # 52주 JPY/KRW 라인
    fig.add_trace(go.Scatter(
        x=jpy_krw_series.index,
        y=jpy_krw_series.values,
        mode='lines',
        name='JPY/KRW (52주)',
        line=dict(color='purple', width=2)
    ))
    
    # 현재 가격 라인
    fig.add_hline(
        y=current_jpy_krw,
        line_dash="dash",
        line_color="red",
        annotation_text=f"현재: {current_jpy_krw:.2f}",
        annotation_position="bottom right"
    )
    
    # 52주 최고가 라인
    fig.add_hline(
        y=jpy_krw_52w_high,
        line_dash="dot",
        line_color="green",
        annotation_text=f"52주 최고: {jpy_krw_52w_high:.2f}",
        annotation_position="top right"
    )
    
    # 52주 최저가 라인
    fig.add_hline(
        y=jpy_krw_52w_low,
        line_dash="dot",
        line_color="orange",
        annotation_text=f"52주 최저: {jpy_krw_52w_low:.2f}",
        annotation_position="bottom right"
    )
    
    # 52주 중간값 라인
    fig.add_hline(
        y=jpy_krw_52w_mid,
        line_dash="dashdot",
        line_color="purple",
        annotation_text=f"52주 중간: {jpy_krw_52w_mid:.2f}",
        annotation_position="top left"
    )
    
    fig.update_layout(
        title=f"엔화 환율 (JPY/KRW) {period_name} 차트",
        xaxis_title="날짜",
        yaxis_title="JPY/KRW",
        hovermode='x unified',
        height=500
    )
    
    return fig

def create_usd_krw_chart(usd_krw_series: pd.Series, current_usd_krw: float, usd_krw_52w_high: float, usd_krw_52w_low: float, usd_krw_52w_mid: float, period_name: str = "1년"):
    """원달러 환율 차트를 생성합니다."""
    fig = go.Figure()
    
    # 52주 USD/KRW 라인
    fig.add_trace(go.Scatter(
        x=usd_krw_series.index,
        y=usd_krw_series.values,
        mode='lines',
        name='USD/KRW (52주)',
        line=dict(color='green', width=2)
    ))
    
    # 현재 가격 라인
    fig.add_hline(
        y=current_usd_krw,
        line_dash="dash",
        line_color="red",
        annotation_text=f"현재: {current_usd_krw:.0f}",
        annotation_position="bottom right"
    )
    
    # 52주 최고가 라인
    fig.add_hline(
        y=usd_krw_52w_high,
        line_dash="dot",
        line_color="green",
        annotation_text=f"52주 최고: {usd_krw_52w_high:.0f}",
        annotation_position="top right"
    )
    
    # 52주 최저가 라인
    fig.add_hline(
        y=usd_krw_52w_low,
        line_dash="dot",
        line_color="orange",
        annotation_text=f"52주 최저: {usd_krw_52w_low:.0f}",
        annotation_position="bottom right"
    )
    
    # 52주 중간값 라인
    fig.add_hline(
        y=usd_krw_52w_mid,
        line_dash="dashdot",
        line_color="purple",
        annotation_text=f"52주 중간: {usd_krw_52w_mid:.0f}",
        annotation_position="top left"
    )
    
    fig.update_layout(
        title=f"원달러 환율 (USD/KRW) {period_name} 차트",
        xaxis_title="날짜",
        yaxis_title="USD/KRW (원)",
        hovermode='x unified',
        height=500
    )
    
    return fig

def create_dxy_usdkrw_combined_chart(dxy_close: pd.Series,
                                     usd_krw_series: pd.Series,
                                     current_dxy: float,
                                     current_usd_krw: float,
                                     period_name: str = "1년"):
    """달러 인덱스(DXY)와 원달러(USD/KRW)를 하나의 이중축 차트로 표시합니다.
    좌측 축: DXY, 우측 축: USD/KRW
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # DXY 라인 (좌측 축)
    fig.add_trace(
        go.Scatter(x=dxy_close.index, y=dxy_close.values, mode='lines', name='DXY', line=dict(color='blue', width=2)),
        secondary_y=False
    )

    # USD/KRW 라인 (우측 축, 실제 값)
    fig.add_trace(
        go.Scatter(x=usd_krw_series.index, y=usd_krw_series.values, mode='lines', name='USD/KRW', line=dict(color='green', width=2)),
        secondary_y=True
    )

    # 현재값 수평선
    fig.add_hline(y=current_dxy, line_dash='dash', line_color='blue', annotation_text=f"DXY 현재: {current_dxy:.2f}", annotation_position='top right', secondary_y=False)
    fig.add_hline(y=current_usd_krw, line_dash='dash', line_color='green', annotation_text=f"USD/KRW 현재: {current_usd_krw:.0f}", annotation_position='bottom right', secondary_y=True)

    # 양 축 모두 데이터 기반 범위(5% 패딩)로 유연 표시
    dxy_min = float(np.nanmin(dxy_close.values))
    dxy_max = float(np.nanmax(dxy_close.values))
    usd_min = float(np.nanmin(usd_krw_series.values))
    usd_max = float(np.nanmax(usd_krw_series.values))
    dxy_pad = (dxy_max - dxy_min) * 0.05 if dxy_max > dxy_min else 0
    usd_pad = (usd_max - usd_min) * 0.05 if usd_max > usd_min else 0
    fig.update_yaxes(title_text="DXY", secondary_y=False, range=[dxy_min - dxy_pad, dxy_max + dxy_pad])
    fig.update_yaxes(title_text="USD/KRW (원)", secondary_y=True, range=[usd_min - usd_pad, usd_max + usd_pad])

    fig.update_layout(
        title=f"달러 인덱스 & 원달러 환율 {period_name} 차트",
        xaxis_title="날짜",
        hovermode='x unified',
        height=550,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )

    return fig

@st.cache_data(ttl=120)
def fetch_usdt_krw_price() -> float | None:
    """Bithumb 공개 API에서 USDT/KRW 현재가(종가)를 가져옵니다.
    실패 시 None을 반환합니다. 2분 캐시.
    """
    url = "https://api.bithumb.com/public/ticker/USDT_KRW"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        payload = resp.json()
        price_str = payload.get("data", {}).get("closing_price")
        return float(price_str) if price_str is not None else None
    except Exception:
        return None

@st.cache_data(ttl=180)
def fetch_hana_usd_krw_rate() -> float | None:
    """네이버 환율 메인 페이지에서 USD/KRW 값을 파싱합니다.
    사용자가 제시한 로직(#exchangeList .head_info .value) 기반. 3분 캐시.
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
    except Exception:
        return None

@st.cache_data(ttl=180)
def fetch_investing_usd_krw_rate() -> float | None:
    """인베스팅닷컴 환율 테이블에서 USD/KRW을 파싱합니다.
    사용자가 제시한 선택자(td.pid-650-last#last_12_28) 기반. 3분 캐시.
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
        # 일부 페이지는 소수점 포함 문자열 제공 가능
        return float(num)
    except Exception:
        return None

@st.cache_data(ttl=180)
def fetch_investing_jpy_krw_rate() -> float | None:
    """인베스팅닷컴 환율 테이블에서 JPY/KRW(원/엔) 값을 파싱합니다.
    사용자 제공 코드 기준: td#last_2_28, class pid-159-last. 3분 캐시.
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
    except Exception:
        return None

@st.cache_data(ttl=60)
def get_investing_usd_krw_for_portfolio() -> float | None:
    """포트폴리오 수익 계산용 인베스팅닷컴 USD/KRW 실시간 환율"""
    return fetch_investing_usd_krw_rate()

@st.cache_data(ttl=60)
def get_investing_jpy_krw_for_portfolio() -> float | None:
    """포트폴리오 수익 계산용 인베스팅닷컴 JPY/KRW 실시간 환율"""
    return fetch_investing_jpy_krw_rate()

def add_jpy_investment(investment_number: int, exchange_rate: float, jpy_amount: float, exchange_name: str, memo: str) -> str:
    """새 엔화 투자 내역을 세션 상태와 Supabase에 추가하고 고유 ID 반환"""
    if 'jpy_investments' not in st.session_state:
        st.session_state.jpy_investments = []
    
    investment_id = str(uuid.uuid4())
    purchase_date = datetime.datetime.now()
    purchase_krw = exchange_rate * jpy_amount
    
    investment = {
        'id': investment_id,
        'investment_number': investment_number,
        'purchase_date': purchase_date.isoformat(),
        'exchange_rate': exchange_rate,
        'jpy_amount': jpy_amount,
        'exchange_name': exchange_name,
        'memo': memo,
        'purchase_krw': purchase_krw
    }
    
    # 세션 상태에 추가
    st.session_state.jpy_investments.append(investment)
    
    # Supabase에 저장
    save_jpy_investment_to_db(investment)
    
    return investment_id

# --- Supabase 데이터베이스 연동 함수들 ---

def save_dollar_investment_to_db(investment_data: Dict) -> bool:
    """달러 투자 데이터를 Supabase에 저장"""
    supabase = init_supabase()
    if not supabase:
        return False
    
    try:
        result = supabase.table("dollar_investments").insert(investment_data).execute()
        return len(result.data) > 0
    except Exception as e:
        st.error(f"달러 투자 저장 실패: {e}")
        return False

def load_dollar_investments_from_db() -> List[Dict]:
    """Supabase에서 달러 투자 데이터 로드"""
    supabase = init_supabase()
    if not supabase:
        return []
    
    try:
        result = supabase.table("dollar_investments").select("*").order("purchase_date", desc=True).execute()
        return result.data
    except Exception as e:
        st.error(f"달러 투자 로드 실패: {e}")
        return []

def delete_dollar_investment_from_db(investment_id: str) -> bool:
    """Supabase에서 달러 투자 삭제"""
    supabase = init_supabase()
    if not supabase:
        return False
    
    try:
        result = supabase.table("dollar_investments").delete().eq("id", investment_id).execute()
        return True
    except Exception as e:
        st.error(f"달러 투자 삭제 실패: {e}")
        return False

def save_dollar_sell_record_to_db(sell_data: Dict) -> bool:
    """달러 매도 기록을 Supabase에 저장"""
    supabase = init_supabase()
    if not supabase:
        return False
    
    try:
        result = supabase.table("dollar_sell_records").insert(sell_data).execute()
        return len(result.data) > 0
    except Exception as e:
        st.error(f"달러 매도 기록 저장 실패: {e}")
        return False

def load_dollar_sell_records_from_db() -> List[Dict]:
    """Supabase에서 달러 매도 기록 로드"""
    supabase = init_supabase()
    if not supabase:
        return []
    
    try:
        result = supabase.table("dollar_sell_records").select("*").order("sell_date", desc=True).execute()
        return result.data
    except Exception as e:
        st.error(f"달러 매도 기록 로드 실패: {e}")
        return []

def delete_dollar_sell_record_from_db(record_id: str) -> bool:
    """Supabase에서 달러 매도 기록 삭제"""
    supabase = init_supabase()
    if not supabase:
        return False
    
    try:
        result = supabase.table("dollar_sell_records").delete().eq("id", record_id).execute()
        return True
    except Exception as e:
        st.error(f"달러 매도 기록 삭제 실패: {e}")
        return False

def save_jpy_investment_to_db(investment_data: Dict) -> bool:
    """엔화 투자 데이터를 Supabase에 저장"""
    supabase = init_supabase()
    if not supabase:
        return False
    
    try:
        result = supabase.table("jpy_investments").insert(investment_data).execute()
        return len(result.data) > 0
    except Exception as e:
        st.error(f"엔화 투자 저장 실패: {e}")
        return False

def load_jpy_investments_from_db() -> List[Dict]:
    """Supabase에서 엔화 투자 데이터 로드"""
    supabase = init_supabase()
    if not supabase:
        return []
    
    try:
        result = supabase.table("jpy_investments").select("*").order("purchase_date", desc=True).execute()
        return result.data
    except Exception as e:
        st.error(f"엔화 투자 로드 실패: {e}")
        return []

def delete_jpy_investment_from_db(investment_id: str) -> bool:
    """Supabase에서 엔화 투자 삭제"""
    supabase = init_supabase()
    if not supabase:
        return False
    
    try:
        result = supabase.table("jpy_investments").delete().eq("id", investment_id).execute()
        return True
    except Exception as e:
        st.error(f"엔화 투자 삭제 실패: {e}")
        return False

def save_jpy_sell_record_to_db(sell_data: Dict) -> bool:
    """엔화 매도 기록을 Supabase에 저장"""
    supabase = init_supabase()
    if not supabase:
        return False
    
    try:
        result = supabase.table("jpy_sell_records").insert(sell_data).execute()
        return len(result.data) > 0
    except Exception as e:
        st.error(f"엔화 매도 기록 저장 실패: {e}")
        return False

def load_jpy_sell_records_from_db() -> List[Dict]:
    """Supabase에서 엔화 매도 기록 로드"""
    supabase = init_supabase()
    if not supabase:
        return []
    
    try:
        result = supabase.table("jpy_sell_records").select("*").order("sell_date", desc=True).execute()
        return result.data
    except Exception as e:
        st.error(f"엔화 매도 기록 로드 실패: {e}")
        return []

def delete_jpy_sell_record_from_db(record_id: str) -> bool:
    """Supabase에서 엔화 매도 기록 삭제"""
    supabase = init_supabase()
    if not supabase:
        return False
    
    try:
        result = supabase.table("jpy_sell_records").delete().eq("id", record_id).execute()
        return True
    except Exception as e:
        st.error(f"엔화 매도 기록 삭제 실패: {e}")
        return False

def add_dollar_investment(investment_number: int, exchange_rate: float, usd_amount: float, exchange_name: str, memo: str) -> str:
    """새 달러 투자 내역을 세션 상태와 Supabase에 추가하고 고유 ID 반환"""
    if 'dollar_investments' not in st.session_state:
        st.session_state.dollar_investments = []
    
    investment_id = str(uuid.uuid4())
    purchase_date = datetime.datetime.now()
    purchase_krw = exchange_rate * usd_amount
    
    investment = {
        'id': investment_id,
        'investment_number': investment_number,
        'purchase_date': purchase_date.isoformat(),
        'exchange_rate': exchange_rate,
        'usd_amount': usd_amount,
        'exchange_name': exchange_name,
        'memo': memo,
        'purchase_krw': purchase_krw
    }
    
    # 세션 상태에 추가
    st.session_state.dollar_investments.append(investment)
    
    # Supabase에 저장
    save_dollar_investment_to_db(investment)
    
    return investment_id

def delete_jpy_investment(investment_id: str) -> bool:
    """엔화 투자 내역 삭제"""
    if 'jpy_investments' not in st.session_state:
        return False
    
    investments = st.session_state.jpy_investments
    for i, inv in enumerate(investments):
        if inv['id'] == investment_id:
            investments.pop(i)
            return True
    return False

def delete_dollar_investment(investment_id: str) -> bool:
    """투자 내역 삭제 (세션 상태와 Supabase에서)"""
    if 'dollar_investments' not in st.session_state:
        return False
    
    investments = st.session_state.dollar_investments
    for i, inv in enumerate(investments):
        if inv['id'] == investment_id:
            investments.pop(i)
            # Supabase에서도 삭제
            delete_dollar_investment_from_db(investment_id)
            return True
    return False

def add_jpy_sell_record(investment_number: int, sell_date: str, sell_rate: float, sell_amount: float, sell_krw: float, profit_krw: float, profit_rate: float) -> str:
    """엔화 매도 기록을 세션 상태에 추가하고 고유 ID 반환"""
    if 'jpy_sell_records' not in st.session_state:
        st.session_state.jpy_sell_records = []
    
    record_id = str(uuid.uuid4())
    
    record = {
        'id': record_id,
        'investment_number': investment_number,
        'sell_date': sell_date,
        'sell_rate': sell_rate,
        'sell_amount': sell_amount,
        'sell_krw': sell_krw,
        'profit_krw': profit_krw,
        'profit_rate': profit_rate
    }
    
    st.session_state.jpy_sell_records.append(record)
    return record_id

def add_sell_record(investment_number: int, sell_date: str, sell_rate: float, sell_amount: float, sell_krw: float, profit_krw: float, profit_rate: float) -> str:
    """매도 기록을 세션 상태와 Supabase에 추가하고 고유 ID 반환"""
    if 'sell_records' not in st.session_state:
        st.session_state.sell_records = []
    
    record_id = str(uuid.uuid4())
    
    record = {
        'id': record_id,
        'investment_number': investment_number,
        'sell_date': sell_date,
        'sell_rate': sell_rate,
        'sell_amount': sell_amount,
        'sell_krw': sell_krw,
        'profit_krw': profit_krw,
        'profit_rate': profit_rate
    }
    
    # 세션 상태에 추가
    st.session_state.sell_records.append(record)
    
    # Supabase에 저장
    save_dollar_sell_record_to_db(record)
    
    return record_id

def sell_jpy_investment(investment_id: str, sell_rate: float, sell_amount: float) -> Dict:
    """엔화 투자 매도 처리"""
    if 'jpy_investments' not in st.session_state:
        return {'success': False, 'message': '엔화 투자 내역이 없습니다.'}
    
    investments = st.session_state.jpy_investments
    for i, inv in enumerate(investments):
        if inv['id'] == investment_id:
            if sell_amount > inv['jpy_amount']:
                return {'success': False, 'message': '매도 금액이 보유 금액을 초과합니다.'}
            
            # 매도 기록 계산
            sell_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            sell_krw = sell_rate * sell_amount
            # 매수 단가 계산 (현재 보유 금액 기준)
            purchase_price_per_jpy = inv['exchange_rate']
            purchase_krw_for_sell = purchase_price_per_jpy * sell_amount
            profit_krw = sell_krw - purchase_krw_for_sell
            profit_rate = (profit_krw / purchase_krw_for_sell * 100) if purchase_krw_for_sell > 0 else 0
            
            # 매도 기록 추가
            add_jpy_sell_record(inv['investment_number'], sell_date, sell_rate, sell_amount, sell_krw, profit_krw, profit_rate)
            
            # 부분 매도인 경우 보유 금액 조정
            if sell_amount < inv['jpy_amount']:
                inv['jpy_amount'] -= sell_amount
                inv['purchase_krw'] = inv['exchange_rate'] * inv['jpy_amount']
                return {'success': True, 'message': f'{sell_amount:,.2f}JPY 매도 완료', 'remaining': inv['jpy_amount']}
            else:
                # 전량 매도인 경우 삭제
                investments.pop(i)
                return {'success': True, 'message': f'{sell_amount:,.2f}JPY 전량 매도 완료', 'remaining': 0}
    
    return {'success': False, 'message': '엔화 투자 내역을 찾을 수 없습니다.'}

def sell_dollar_investment(investment_id: str, sell_rate: float, sell_amount: float) -> Dict:
    """투자 매도 처리"""
    if 'dollar_investments' not in st.session_state:
        return {'success': False, 'message': '투자 내역이 없습니다.'}
    
    investments = st.session_state.dollar_investments
    for i, inv in enumerate(investments):
        if inv['id'] == investment_id:
            if sell_amount > inv['usd_amount']:
                return {'success': False, 'message': '매도 금액이 보유 금액을 초과합니다.'}
            
            # 매도 기록 계산
            sell_date = datetime.datetime.now()
            sell_krw = sell_rate * sell_amount
            # 매수 단가 계산 (현재 보유 금액 기준)
            purchase_price_per_usd = inv['exchange_rate']
            purchase_krw_for_sell = purchase_price_per_usd * sell_amount
            profit_krw = sell_krw - purchase_krw_for_sell
            profit_rate = (profit_krw / purchase_krw_for_sell * 100) if purchase_krw_for_sell > 0 else 0
            
            # 매도 기록 추가
            add_sell_record(inv['investment_number'], sell_date.isoformat(), sell_rate, sell_amount, sell_krw, profit_krw, profit_rate)
            
            # 부분 매도인 경우 보유 금액 조정
            if sell_amount < inv['usd_amount']:
                inv['usd_amount'] -= sell_amount
                inv['purchase_krw'] = inv['exchange_rate'] * inv['usd_amount']
                return {'success': True, 'message': f'{sell_amount:,.2f}USD 매도 완료', 'remaining': inv['usd_amount']}
            else:
                # 전량 매도인 경우 삭제
                investments.pop(i)
                return {'success': True, 'message': f'{sell_amount:,.2f}USD 전량 매도 완료', 'remaining': 0}
    
    return {'success': False, 'message': '투자 내역을 찾을 수 없습니다.'}

def delete_jpy_sell_record(record_id: str) -> bool:
    """엔화 매도 기록 삭제"""
    if 'jpy_sell_records' not in st.session_state:
        return False
    
    records = st.session_state.jpy_sell_records
    for i, record in enumerate(records):
        if record['id'] == record_id:
            records.pop(i)
            return True
    return False

def delete_sell_record(record_id: str) -> bool:
    """매도 기록 삭제 (세션 상태와 Supabase에서)"""
    if 'sell_records' not in st.session_state:
        return False
    
    records = st.session_state.sell_records
    for i, record in enumerate(records):
        if record['id'] == record_id:
            records.pop(i)
            # Supabase에서도 삭제
            delete_dollar_sell_record_from_db(record_id)
            return True
    return False

def calculate_jpy_sell_performance(start_date: str = None, end_date: str = None) -> Dict:
    """기간별 엔화 매도 성과 계산"""
    if 'jpy_sell_records' not in st.session_state:
        return {'total_sell_krw': 0, 'total_profit_krw': 0, 'total_profit_rate': 0.0, 'count': 0}
    
    records = st.session_state.jpy_sell_records
    
    # 날짜 필터링
    if start_date or end_date:
        filtered_records = []
        for record in records:
            record_date = datetime.datetime.strptime(record['sell_date'], "%Y-%m-%d %H:%M").date()
            if start_date:
                start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
                if record_date < start_dt:
                    continue
            if end_date:
                end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
                if record_date > end_dt:
                    continue
            filtered_records.append(record)
        records = filtered_records
    
    if not records:
        return {'total_sell_krw': 0, 'total_profit_krw': 0, 'total_profit_rate': 0.0, 'count': 0}
    
    total_sell_krw = sum(record['sell_krw'] for record in records)
    total_profit_krw = sum(record['profit_krw'] for record in records)
    total_purchase_krw = total_sell_krw - total_profit_krw
    total_profit_rate = (total_profit_krw / total_purchase_krw * 100) if total_purchase_krw > 0 else 0.0
    
    return {
        'total_sell_krw': total_sell_krw,
        'total_profit_krw': total_profit_krw,
        'total_profit_rate': total_profit_rate,
        'count': len(records)
    }

def calculate_sell_performance(start_date: str = None, end_date: str = None) -> Dict:
    """기간별 매도 성과 계산"""
    if 'sell_records' not in st.session_state:
        return {'total_sell_krw': 0, 'total_profit_krw': 0, 'total_profit_rate': 0.0, 'count': 0}
    
    records = st.session_state.sell_records
    
    # 날짜 필터링
    if start_date or end_date:
        filtered_records = []
        for record in records:
            record_date = datetime.datetime.strptime(record['sell_date'], "%Y-%m-%d %H:%M").date()
            if start_date:
                start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
                if record_date < start_dt:
                    continue
            if end_date:
                end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
                if record_date > end_dt:
                    continue
            filtered_records.append(record)
        records = filtered_records
    
    if not records:
        return {'total_sell_krw': 0, 'total_profit_krw': 0, 'total_profit_rate': 0.0, 'count': 0}
    
    total_sell_krw = sum(record['sell_krw'] for record in records)
    total_profit_krw = sum(record['profit_krw'] for record in records)
    total_purchase_krw = total_sell_krw - total_profit_krw
    total_profit_rate = (total_profit_krw / total_purchase_krw * 100) if total_purchase_krw > 0 else 0.0
    
    return {
        'total_sell_krw': total_sell_krw,
        'total_profit_krw': total_profit_krw,
        'total_profit_rate': total_profit_rate,
        'count': len(records)
    }

def calculate_jpy_portfolio_performance(investments: List[Dict]) -> Dict:
    """엔화 포트폴리오 전체 성과 계산"""
    if not investments:
        return {'total_purchase_krw': 0, 'total_current_krw': 0, 'total_profit_krw': 0, 'total_profit_rate': 0.0}
    
    current_rate = get_investing_jpy_krw_for_portfolio()
    if current_rate is None:
        return {'total_purchase_krw': 0, 'total_current_krw': 0, 'total_profit_krw': 0, 'total_profit_rate': 0.0}
    
    total_purchase_krw = sum(inv['purchase_krw'] for inv in investments)
    total_current_krw = sum(inv['jpy_amount'] * current_rate for inv in investments)
    total_profit_krw = total_current_krw - total_purchase_krw
    total_profit_rate = (total_profit_krw / total_purchase_krw * 100) if total_purchase_krw > 0 else 0.0
    
    return {
        'total_purchase_krw': total_purchase_krw,
        'total_current_krw': total_current_krw,
        'total_profit_krw': total_profit_krw,
        'total_profit_rate': total_profit_rate,
        'current_rate': current_rate
    }

def calculate_portfolio_performance(investments: List[Dict]) -> Dict:
    """포트폴리오 전체 성과 계산"""
    if not investments:
        return {'total_purchase_krw': 0, 'total_current_krw': 0, 'total_profit_krw': 0, 'total_profit_rate': 0.0}
    
    current_rate = get_investing_usd_krw_for_portfolio()
    if current_rate is None:
        return {'total_purchase_krw': 0, 'total_current_krw': 0, 'total_profit_krw': 0, 'total_profit_rate': 0.0}
    
    total_purchase_krw = sum(inv['purchase_krw'] for inv in investments)
    total_current_krw = sum(inv['usd_amount'] * current_rate for inv in investments)
    total_profit_krw = total_current_krw - total_purchase_krw
    total_profit_rate = (total_profit_krw / total_purchase_krw * 100) if total_purchase_krw > 0 else 0.0
    
    return {
        'total_purchase_krw': total_purchase_krw,
        'total_current_krw': total_current_krw,
        'total_profit_krw': total_profit_krw,
        'total_profit_rate': total_profit_rate,
        'current_rate': current_rate
    }

def display_jpy_investment_tab():
    """엔화 투자 관리 탭 UI"""
    st.subheader("💴 엔화 투자 관리")
    
    # 포트폴리오 요약
    investments = st.session_state.get('jpy_investments', [])
    if investments:
        perf = calculate_jpy_portfolio_performance(investments)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("총 매수금액", f"{perf['total_purchase_krw']:,.0f}원")
        with col2:
            st.metric("현재 평가금액", f"{perf['total_current_krw']:,.0f}원")
        with col3:
            st.metric("평가 손익", f"{perf['total_profit_krw']:+,.0f}원", delta=f"{perf['total_profit_rate']:+.2f}%")
        with col4:
            st.metric("현재 환율", f"{perf['current_rate']:,.2f}원")
        st.markdown("---")
    
    # 새 투자 추가 폼
    with st.expander("➕ 새 엔화 투자 추가", expanded=False):
        with st.form("add_jpy_investment_form"):
            col1, col2 = st.columns(2)
            with col1:
                investment_number = st.number_input("번호", min_value=1, value=1, step=1, key="jpy_investment_number")
                exchange_rate = st.number_input("매수 환율 (원/JPY)", min_value=0.0, value=9.0, step=0.01, format="%.2f", key="jpy_exchange_rate")
                jpy_amount = st.number_input("매수 엔화 금액 (JPY)", min_value=0.0, value=10000.0, step=0.01, format="%.2f", key="jpy_amount")
            with col2:
                exchange_name = st.text_input("거래소", value="하나은행", placeholder="예: 하나은행, 신한은행, 빗썸 등", key="jpy_exchange_name")
                memo = st.text_area("메모", placeholder="투자 목적, 참고사항 등", key="jpy_memo")
            
            if st.form_submit_button("✅ 투자 추가", type="primary"):
                if exchange_rate > 0 and jpy_amount > 0:
                    investment_id = add_jpy_investment(investment_number, exchange_rate, jpy_amount, exchange_name, memo)
                    st.success(f"투자가 추가되었습니다! (ID: {investment_id[:8]}...)")
                    # 폼 초기화를 위해 세션 상태 업데이트 (rerun 없이)
                    if 'jpy_form_submitted' not in st.session_state:
                        st.session_state.jpy_form_submitted = True
                    else:
                        st.session_state.jpy_form_submitted = not st.session_state.jpy_form_submitted
                else:
                    st.error("매수 환율과 엔화 금액은 0보다 커야 합니다.")
    
    # 투자 내역 테이블
    if investments:
        st.subheader("📊 투자 내역")
        current_rate = get_investing_jpy_krw_for_portfolio()
        
        # 테이블 데이터 준비
        table_data = []
        for inv in investments:
            current_krw = inv['jpy_amount'] * current_rate if current_rate else 0
            profit_krw = current_krw - inv['purchase_krw']
            profit_rate = (profit_krw / inv['purchase_krw'] * 100) if inv['purchase_krw'] > 0 else 0
            
            table_data.append({
                '번호': inv['investment_number'],
                '매수일시': inv['purchase_date'],
                '거래소': inv['exchange_name'],
                '메모': inv['memo'],
                '매수가': f"{inv['exchange_rate']:,.2f}원",
                '매수엔화': f"{inv['jpy_amount']:,.2f}JPY",
                '매수금(KRW)': f"{inv['purchase_krw']:,.0f}원",
                '수익(KRW)': f"{profit_krw:+,.0f}원",
                '수익률': f"{profit_rate:+.2f}%",
                '평가금(KRW)': f"{current_krw:,.0f}원"
            })
        
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # 투자별 액션 버튼들
        st.subheader("📋 투자 관리")
        
        # 투자 선택
        investment_options = [f"{inv['investment_number']}. {inv['purchase_date']} - {inv['exchange_name']} ({inv['jpy_amount']:,.2f}JPY)" for inv in investments]
        selected_investment = st.selectbox("관리할 투자를 선택하세요:", options=investment_options, key="jpy_selected_investment")
        
        if selected_investment:
            # 선택된 투자 찾기
            selected_index = investment_options.index(selected_investment)
            selected_inv = investments[selected_index]
            current_rate = get_investing_jpy_krw_for_portfolio()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write("**🗑️ 삭제**")
                if st.button("삭제", key=f"jpy_delete_btn_{selected_inv['id']}", type="secondary"):
                    if delete_jpy_investment(selected_inv['id']):
                        st.success(f"투자 #{selected_inv['investment_number']}가 삭제되었습니다.")
                        # 삭제 후 선택 초기화
                        if 'jpy_selected_investment' in st.session_state:
                            del st.session_state.jpy_selected_investment
                    else:
                        st.error("삭제에 실패했습니다.")
            
            with col2:
                st.write("**💰 전량 매도**")
                if st.button("전량 매도", key=f"jpy_sell_all_btn_{selected_inv['id']}", type="primary"):
                    if current_rate:
                        result = sell_jpy_investment(selected_inv['id'], current_rate, selected_inv['jpy_amount'])
                        if result['success']:
                            st.success(result['message'])
                            # 전량 매도 후 선택 초기화
                            if 'jpy_selected_investment' in st.session_state:
                                del st.session_state.jpy_selected_investment
                        else:
                            st.error(result['message'])
                    else:
                        st.error("현재 환율을 가져올 수 없습니다.")
            
            with col3:
                st.write("**📊 분할 매도**")
                with st.expander("분할 매도 설정", expanded=False):
                    sell_amount = st.number_input(
                        "매도 금액 (JPY)", 
                        min_value=0.01, 
                        max_value=float(selected_inv['jpy_amount']), 
                        value=float(selected_inv['jpy_amount']/2),
                        step=0.01,
                        key=f"jpy_sell_amount_{selected_inv['id']}"
                    )
                    sell_rate = st.number_input(
                        "매도 환율 (원/JPY)", 
                        min_value=0.0, 
                        value=current_rate if current_rate else 9.0,
                        step=0.01,
                        key=f"jpy_sell_rate_{selected_inv['id']}"
                    )
                    
                    if st.button("분할 매도 실행", key=f"jpy_sell_partial_btn_{selected_inv['id']}", type="primary"):
                        result = sell_jpy_investment(selected_inv['id'], sell_rate, sell_amount)
                        if result['success']:
                            st.success(result['message'])
                            if result['remaining'] > 0:
                                st.info(f"남은 보유 금액: {result['remaining']:,.2f}JPY")
                            else:
                                # 전량 매도된 경우 선택 초기화
                                if 'jpy_selected_investment' in st.session_state:
                                    del st.session_state.jpy_selected_investment
                        else:
                            st.error(result['message'])
            
            # 선택된 투자 상세 정보
            st.markdown("---")
            st.write("**선택된 투자 상세 정보**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("보유 금액", f"{selected_inv['jpy_amount']:,.2f}JPY")
            with col2:
                st.metric("매수가", f"{selected_inv['exchange_rate']:,.2f}원")
            with col3:
                if current_rate:
                    current_value = selected_inv['jpy_amount'] * current_rate
                    profit = current_value - selected_inv['purchase_krw']
                    profit_rate = (profit / selected_inv['purchase_krw'] * 100) if selected_inv['purchase_krw'] > 0 else 0
                    st.metric("현재 평가금액", f"{current_value:,.0f}원", delta=f"{profit:+,.0f}원 ({profit_rate:+.2f}%)")
                else:
                    st.metric("현재 평가금액", "환율 정보 없음")
            with col4:
                st.metric("현재 환율", f"{current_rate:,.2f}원" if current_rate else "정보 없음")
    
    # 매도 기록 섹션
    sell_records = st.session_state.get('jpy_sell_records', [])
    if sell_records:
        st.markdown("---")
        st.subheader("📈 매도 기록")
        
        # 기간별 통계
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("시작 날짜", value=None, key="jpy_sell_start_date")
        with col2:
            end_date = st.date_input("종료 날짜", value=None, key="jpy_sell_end_date")
        
        # 기간별 성과 계산
        start_str = start_date.strftime("%Y-%m-%d") if start_date else None
        end_str = end_date.strftime("%Y-%m-%d") if end_date else None
        sell_perf = calculate_jpy_sell_performance(start_str, end_str)
        
        # 통계 표시
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("총 매도금액", f"{sell_perf['total_sell_krw']:,.0f}원")
        with col2:
            st.metric("총 확정손익", f"{sell_perf['total_profit_krw']:+,.0f}원")
        with col3:
            st.metric("수익률", f"{sell_perf['total_profit_rate']:+.2f}%")
        with col4:
            st.metric("매도 건수", f"{sell_perf['count']}건")
        
        st.markdown("---")
        
        # 개별 매도 기록 테이블
        st.subheader("📊 개별 매도 기록")
        
        # 필터링된 기록으로 테이블 데이터 준비
        filtered_records = sell_records
        if start_str or end_str:
            filtered_records = []
            for record in sell_records:
                record_date = datetime.datetime.strptime(record['sell_date'], "%Y-%m-%d %H:%M").date()
                if start_str:
                    start_dt = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
                    if record_date < start_dt:
                        continue
                if end_str:
                    end_dt = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
                    if record_date > end_dt:
                        continue
                filtered_records.append(record)
        
        table_data = []
        for i, record in enumerate(filtered_records, 1):
            table_data.append({
                '번호': i,
                '투자번호': record['investment_number'],
                '매도일시': record['sell_date'],
                '매도환율': f"{record['sell_rate']:,.2f}원",
                '매도금액': f"{record['sell_amount']:,.2f}JPY",
                '매도금(KRW)': f"{record['sell_krw']:,.0f}원",
                '확정손익': f"{record['profit_krw']:+,.0f}원",
                '수익률': f"{record['profit_rate']:+.2f}%"
            })
        
        if table_data:
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # 매도 기록 삭제 기능
            st.subheader("🗑️ 매도 기록 삭제")
            delete_options = [f"{i}. 투자#{record['investment_number']} - {record['sell_date']} ({record['sell_amount']:,.2f}JPY)" for i, record in enumerate(filtered_records)]
            if delete_options:
                selected_delete = st.selectbox("삭제할 매도 기록을 선택하세요:", options=delete_options, key="delete_jpy_sell_record")
                
                if st.button("🗑️ 선택한 매도 기록 삭제", key="jpy_delete_sell_record_btn", type="secondary"):
                    delete_index = delete_options.index(selected_delete)
                    deleted_record = filtered_records[delete_index]
                    if delete_jpy_sell_record(deleted_record['id']):
                        st.success(f"매도 기록이 삭제되었습니다: 투자#{deleted_record['investment_number']} - {deleted_record['sell_amount']:,.2f}JPY")
                        # 삭제 후 선택 초기화
                        if 'delete_jpy_sell_record' in st.session_state:
                            del st.session_state.delete_jpy_sell_record
                    else:
                        st.error("삭제에 실패했습니다.")
        else:
            st.info("선택한 기간에 매도 기록이 없습니다.")
    else:
        st.info("아직 투자 내역이 없습니다. 위의 '새 엔화 투자 추가' 버튼을 클릭하여 첫 투자를 추가해보세요!")

def display_dollar_investment_tab():
    """달러 투자 관리 탭 UI"""
    st.subheader("💰 달러 투자 관리")
    
    # 포트폴리오 요약
    investments = st.session_state.get('dollar_investments', [])
    if investments:
        perf = calculate_portfolio_performance(investments)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("총 매수금액", f"{perf['total_purchase_krw']:,.0f}원")
        with col2:
            st.metric("현재 평가금액", f"{perf['total_current_krw']:,.0f}원")
        with col3:
            st.metric("평가 손익", f"{perf['total_profit_krw']:+,.0f}원", delta=f"{perf['total_profit_rate']:+.2f}%")
        with col4:
            st.metric("현재 환율", f"{perf['current_rate']:,.2f}원")
        st.markdown("---")
    
    # 새 투자 추가 폼
    with st.expander("➕ 새 달러 투자 추가", expanded=False):
        with st.form("add_investment_form"):
            col1, col2 = st.columns(2)
            with col1:
                investment_number = st.number_input("번호", min_value=1, value=1, step=1)
                exchange_rate = st.number_input("매수 환율 (원/USD)", min_value=0.0, value=1300.0, step=0.01, format="%.2f")
                usd_amount = st.number_input("매수 달러 금액 (USD)", min_value=0.0, value=100.0, step=0.01, format="%.2f")
            with col2:
                exchange_name = st.text_input("거래소", value="하나은행", placeholder="예: 하나은행, 신한은행, 빗썸 등")
                memo = st.text_area("메모", placeholder="투자 목적, 참고사항 등")
            
            if st.form_submit_button("✅ 투자 추가", type="primary"):
                if exchange_rate > 0 and usd_amount > 0:
                    investment_id = add_dollar_investment(investment_number, exchange_rate, usd_amount, exchange_name, memo)
                    st.success(f"투자가 추가되었습니다! (ID: {investment_id[:8]}...)")
                    # 폼 초기화를 위해 세션 상태 업데이트 (rerun 없이)
                    if 'dollar_form_submitted' not in st.session_state:
                        st.session_state.dollar_form_submitted = True
                    else:
                        st.session_state.dollar_form_submitted = not st.session_state.dollar_form_submitted
                else:
                    st.error("매수 환율과 달러 금액은 0보다 커야 합니다.")
    
    # 투자 내역 테이블
    if investments:
        st.subheader("📊 투자 내역")
        current_rate = get_investing_usd_krw_for_portfolio()
        
        # 테이블 데이터 준비
        table_data = []
        for inv in investments:
            current_krw = inv['usd_amount'] * current_rate if current_rate else 0
            profit_krw = current_krw - inv['purchase_krw']
            profit_rate = (profit_krw / inv['purchase_krw'] * 100) if inv['purchase_krw'] > 0 else 0
            
            table_data.append({
                '번호': inv['investment_number'],
                '매수일시': inv['purchase_date'],
                '거래소': inv['exchange_name'],
                '메모': inv['memo'],
                '매수가': f"{inv['exchange_rate']:,.2f}원",
                '매수달러': f"{inv['usd_amount']:,.2f}USD",
                '매수금(KRW)': f"{inv['purchase_krw']:,.0f}원",
                '수익(KRW)': f"{profit_krw:+,.0f}원",
                '수익률': f"{profit_rate:+.2f}%",
                '평가금(KRW)': f"{current_krw:,.0f}원"
            })
        
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # 투자별 액션 버튼들
        st.subheader("📋 투자 관리")
        
        # 투자 선택
        investment_options = [f"{inv['investment_number']}. {inv['purchase_date']} - {inv['exchange_name']} ({inv['usd_amount']:,.2f}USD)" for inv in investments]
        selected_investment = st.selectbox("관리할 투자를 선택하세요:", options=investment_options)
        
        if selected_investment:
            # 선택된 투자 찾기
            selected_index = investment_options.index(selected_investment)
            selected_inv = investments[selected_index]
            current_rate = get_investing_usd_krw_for_portfolio()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write("**🗑️ 삭제**")
                if st.button("삭제", key=f"dollar_delete_btn_{selected_inv['id']}", type="secondary"):
                    if delete_dollar_investment(selected_inv['id']):
                        st.success(f"투자 #{selected_inv['investment_number']}가 삭제되었습니다.")
                        # 삭제 후 선택 초기화
                        if 'selected_investment' in st.session_state:
                            del st.session_state.selected_investment
                    else:
                        st.error("삭제에 실패했습니다.")
            
            with col2:
                st.write("**💰 전량 매도**")
                if st.button("전량 매도", key=f"dollar_sell_all_btn_{selected_inv['id']}", type="primary"):
                    if current_rate:
                        result = sell_dollar_investment(selected_inv['id'], current_rate, selected_inv['usd_amount'])
                        if result['success']:
                            st.success(result['message'])
                            # 전량 매도 후 선택 초기화
                            if 'selected_investment' in st.session_state:
                                del st.session_state.selected_investment
                        else:
                            st.error(result['message'])
                    else:
                        st.error("현재 환율을 가져올 수 없습니다.")
            
            with col3:
                st.write("**📊 분할 매도**")
                with st.expander("분할 매도 설정", expanded=False):
                    sell_amount = st.number_input(
                        "매도 금액 (USD)", 
                        min_value=0.01, 
                        max_value=float(selected_inv['usd_amount']), 
                        value=float(selected_inv['usd_amount']/2),
                        step=0.01,
                        key=f"sell_amount_{selected_inv['id']}"
                    )
                    sell_rate = st.number_input(
                        "매도 환율 (원/USD)", 
                        min_value=0.0, 
                        value=current_rate if current_rate else 1300.0,
                        step=0.01,
                        key=f"sell_rate_{selected_inv['id']}"
                    )
                    
                    if st.button("분할 매도 실행", key=f"dollar_sell_partial_btn_{selected_inv['id']}", type="primary"):
                        result = sell_dollar_investment(selected_inv['id'], sell_rate, sell_amount)
                        if result['success']:
                            st.success(result['message'])
                            if result['remaining'] > 0:
                                st.info(f"남은 보유 금액: {result['remaining']:,.2f}USD")
                            else:
                                # 전량 매도된 경우 선택 초기화
                                if 'selected_investment' in st.session_state:
                                    del st.session_state.selected_investment
                        else:
                            st.error(result['message'])
            
            # 선택된 투자 상세 정보
            st.markdown("---")
            st.write("**선택된 투자 상세 정보**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("보유 금액", f"{selected_inv['usd_amount']:,.2f}USD")
            with col2:
                st.metric("매수가", f"{selected_inv['exchange_rate']:,.2f}원")
            with col3:
                if current_rate:
                    current_value = selected_inv['usd_amount'] * current_rate
                    profit = current_value - selected_inv['purchase_krw']
                    profit_rate = (profit / selected_inv['purchase_krw'] * 100) if selected_inv['purchase_krw'] > 0 else 0
                    st.metric("현재 평가금액", f"{current_value:,.0f}원", delta=f"{profit:+,.0f}원 ({profit_rate:+.2f}%)")
                else:
                    st.metric("현재 평가금액", "환율 정보 없음")
            with col4:
                st.metric("현재 환율", f"{current_rate:,.2f}원" if current_rate else "정보 없음")
    
    # 매도 기록 섹션
    sell_records = st.session_state.get('sell_records', [])
    if sell_records:
        st.markdown("---")
        st.subheader("📈 매도 기록")
        
        # 기간별 통계
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("시작 날짜", value=None, key="sell_start_date")
        with col2:
            end_date = st.date_input("종료 날짜", value=None, key="sell_end_date")
        
        # 기간별 성과 계산
        start_str = start_date.strftime("%Y-%m-%d") if start_date else None
        end_str = end_date.strftime("%Y-%m-%d") if end_date else None
        sell_perf = calculate_sell_performance(start_str, end_str)
        
        # 통계 표시
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("총 매도금액", f"{sell_perf['total_sell_krw']:,.0f}원")
        with col2:
            st.metric("총 확정손익", f"{sell_perf['total_profit_krw']:+,.0f}원")
        with col3:
            st.metric("수익률", f"{sell_perf['total_profit_rate']:+.2f}%")
        with col4:
            st.metric("매도 건수", f"{sell_perf['count']}건")
        
        st.markdown("---")
        
        # 개별 매도 기록 테이블
        st.subheader("📊 개별 매도 기록")
        
        # 필터링된 기록으로 테이블 데이터 준비
        filtered_records = sell_records
        if start_str or end_str:
            filtered_records = []
            for record in sell_records:
                record_date = datetime.datetime.strptime(record['sell_date'], "%Y-%m-%d %H:%M").date()
                if start_str:
                    start_dt = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
                    if record_date < start_dt:
                        continue
                if end_str:
                    end_dt = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
                    if record_date > end_dt:
                        continue
                filtered_records.append(record)
        
        table_data = []
        for i, record in enumerate(filtered_records, 1):
            table_data.append({
                '번호': i,
                '투자번호': record['investment_number'],
                '매도일시': record['sell_date'],
                '매도환율': f"{record['sell_rate']:,.2f}원",
                '매도금액': f"{record['sell_amount']:,.2f}USD",
                '매도금(KRW)': f"{record['sell_krw']:,.0f}원",
                '확정손익': f"{record['profit_krw']:+,.0f}원",
                '수익률': f"{record['profit_rate']:+.2f}%"
            })
        
        if table_data:
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # 매도 기록 삭제 기능
            st.subheader("🗑️ 매도 기록 삭제")
            delete_options = [f"{i}. 투자#{record['investment_number']} - {record['sell_date']} ({record['sell_amount']:,.2f}USD)" for i, record in enumerate(filtered_records)]
            if delete_options:
                selected_delete = st.selectbox("삭제할 매도 기록을 선택하세요:", options=delete_options, key="delete_sell_record")
                
                if st.button("🗑️ 선택한 매도 기록 삭제", key="dollar_delete_sell_record_btn", type="secondary"):
                    delete_index = delete_options.index(selected_delete)
                    deleted_record = filtered_records[delete_index]
                    if delete_sell_record(deleted_record['id']):
                        st.success(f"매도 기록이 삭제되었습니다: 투자#{deleted_record['investment_number']} - {deleted_record['sell_amount']:,.2f}USD")
                        # 삭제 후 선택 초기화
                        if 'delete_sell_record' in st.session_state:
                            del st.session_state.delete_sell_record
                    else:
                        st.error("삭제에 실패했습니다.")
        else:
            st.info("선택한 기간에 매도 기록이 없습니다.")
    else:
        st.info("아직 투자 내역이 없습니다. 위의 '새 달러 투자 추가' 버튼을 클릭하여 첫 투자를 추가해보세요!")

def calculate_indicator_signals(current_dxy: float, dxy_52w_mid: float, 
                                current_usd_krw: float, usd_krw_52w_mid: float,
                                current_jxy: float, jxy_52w_mid: float,
                                current_jpy_krw: float, jpy_krw_52w_mid: float) -> Dict[str, str]:
    """각 지표의 O/X 신호를 계산합니다."""
    
    # 달러 지표
    dxy_signal = "O" if current_dxy < dxy_52w_mid else "X"
    usd_krw_signal = "O" if current_usd_krw < usd_krw_52w_mid else "X"
    
    # 달러 갭 비율
    current_gap_ratio = (current_dxy / current_usd_krw) * 100
    mid_gap_ratio = (dxy_52w_mid / usd_krw_52w_mid) * 100
    gap_ratio_signal = "O" if current_gap_ratio > mid_gap_ratio else "X"
    
    # 적정 환율
    fair_exchange_rate = (current_dxy / mid_gap_ratio) * 100
    fair_rate_signal = "O" if current_usd_krw < fair_exchange_rate else "X"
    
    # 엔화 지표
    jxy_signal = "X" if current_jxy > jxy_52w_mid else "O"
    jpy_krw_signal = "O" if current_jpy_krw < jpy_krw_52w_mid else "X"
    
    # 엔화 갭 비율
    current_jpy_gap_ratio = (current_jxy * 100) / (current_jpy_krw * 100)
    mid_jpy_gap_ratio = (jxy_52w_mid * 100) / (jpy_krw_52w_mid * 100)
    jpy_gap_ratio_signal = "O" if current_jpy_gap_ratio > mid_jpy_gap_ratio else "X"
    
    # 엔화 적정 환율
    jpy_fair_exchange_rate = (current_jxy) / (jxy_52w_mid / jpy_krw_52w_mid)
    jpy_fair_rate_signal = "O" if current_jpy_krw < jpy_fair_exchange_rate else "X"
    
    return {
        'dxy': dxy_signal,
        'usd_krw': usd_krw_signal,
        'gap_ratio': gap_ratio_signal,
        'fair_rate': fair_rate_signal,
        'jxy': jxy_signal,
        'jpy_krw': jpy_krw_signal,
        'jpy_gap_ratio': jpy_gap_ratio_signal,
        'jpy_fair_rate': jpy_fair_rate_signal
    }

def create_summary_indicators_tab():
    """모든 기간별 지표를 한눈에 보여주는 종합 탭"""
    st.markdown("## 📊 투자 지표 종합")
    st.markdown("모든 기간의 지표를 한눈에 확인하세요. **O**는 매수 신호, **X**는 매도 신호입니다.")
    
    # 모든 기간 데이터 계산
    periods = [1, 3, 6, 12]
    period_names = {1: "1개월", 3: "3개월", 6: "6개월", 12: "1년"}
    
    all_signals = {}
    
    with st.spinner("모든 기간 데이터를 분석하는 중..."):
        for period in periods:
            try:
                df_close, df_high, df_low, current_rates = fetch_period_data_and_current_rates(period)
                dxy_close = calculate_dollar_index_series(df_close)
                current_dxy = calculate_current_dxy(current_rates)
                
                # 달러 지표 계산
                dxy_52w_high = dxy_close.max()
                dxy_52w_low = dxy_close.min()
                dxy_52w_mid = (dxy_52w_high + dxy_52w_low) / 2
                
                usd_krw_close = df_close['USD_KRW']
                usd_krw_high = df_high['USD_KRW']
                usd_krw_low = df_low['USD_KRW']
                current_usd_krw = current_rates['USD_KRW']
                
                # 인베스팅닷컴 현재가 우선 적용
                try:
                    investing_usd = fetch_investing_usd_krw_rate()
                    if investing_usd:
                        current_usd_krw = investing_usd
                except:
                    pass
                
                usd_krw_52w_high = usd_krw_high.max()
                usd_krw_52w_low = usd_krw_low.min()
                usd_krw_52w_mid = (usd_krw_52w_high + usd_krw_52w_low) / 2
                
                # 엔화 지표 계산
                usd_jpy_close = df_close['USD_JPY']
                usd_jpy_high = df_high['USD_JPY']
                usd_jpy_low = df_low['USD_JPY']
                
                jxy_close = 100 / usd_jpy_close
                jxy_high = 100 / usd_jpy_low
                jxy_low = 100 / usd_jpy_high
                current_jxy = current_rates['JXY']
                
                jxy_52w_high = jxy_high.max()
                jxy_52w_low = jxy_low.min()
                jxy_52w_mid = (jxy_52w_high + jxy_52w_low) / 2
                
                jpy_krw_close = usd_krw_close / usd_jpy_close
                jpy_krw_high = df_high['USD_KRW'] / usd_jpy_low
                jpy_krw_low = df_low['USD_KRW'] / usd_jpy_high
                current_jpy_krw = current_rates['JPY_KRW']
                
                # 인베스팅닷컴 JPY/KRW 현재가 우선 적용
                try:
                    investing_jpy = fetch_investing_jpy_krw_rate()
                    if investing_jpy:
                        current_jpy_krw = investing_jpy
                except:
                    pass
                
                jpy_krw_52w_high = jpy_krw_high.max()
                jpy_krw_52w_low = jpy_krw_low.min()
                jpy_krw_52w_mid = (jpy_krw_52w_high + jpy_krw_52w_low) / 2
                
                # 신호 계산
                signals = calculate_indicator_signals(
                    current_dxy, dxy_52w_mid,
                    current_usd_krw, usd_krw_52w_mid,
                    current_jxy, jxy_52w_mid,
                    current_jpy_krw, jpy_krw_52w_mid
                )
                
                all_signals[period] = signals
                
            except Exception as e:
                st.error(f"{period_names[period]} 데이터 처리 중 오류: {str(e)}")
                all_signals[period] = {k: "-" for k in ['dxy', 'usd_krw', 'gap_ratio', 'fair_rate', 
                                                         'jxy', 'jpy_krw', 'jpy_gap_ratio', 'jpy_fair_rate']}
    
    # 달러 투자 지표 테이블
    st.markdown("### 💵 달러 투자 지표")
    
    dollar_data = []
    for period in periods:
        signals = all_signals.get(period, {})
        dollar_data.append({
            '기간': period_names[period],
            '달러지수': signals.get('dxy', '-'),
            '원달러환율': signals.get('usd_krw', '-'),
            '갭 비율': signals.get('gap_ratio', '-'),
            '적정환율': signals.get('fair_rate', '-')
        })
    
    dollar_df = pd.DataFrame(dollar_data)
    
    # 스타일링된 테이블 표시
    st.markdown("""
    <style>
    .signal-table {
        font-size: 24px;
        text-align: center;
    }
    .signal-o {
        color: #28a745;
        font-weight: bold;
        font-size: 32px;
    }
    .signal-x {
        color: #dc3545;
        font-weight: bold;
        font-size: 32px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # HTML 테이블로 변환하여 O/X에 색상 적용
    html_table = "<table style='width:100%; border-collapse: collapse; margin: 20px 0;'>"
    html_table += "<thead><tr style='background-color: #f0f2f6; border-bottom: 2px solid #ddd;'>"
    for col in dollar_df.columns:
        html_table += f"<th style='padding: 15px; text-align: center; font-size: 18px;'>{col}</th>"
    html_table += "</tr></thead><tbody>"
    
    for _, row in dollar_df.iterrows():
        html_table += "<tr style='border-bottom: 1px solid #ddd;'>"
        for idx, (col, val) in enumerate(row.items()):
            if idx == 0:  # 기간 열
                html_table += f"<td style='padding: 15px; text-align: center; font-weight: bold; font-size: 16px;'>{val}</td>"
            else:  # O/X 열
                color_class = "signal-o" if val == "O" else "signal-x" if val == "X" else ""
                html_table += f"<td style='padding: 15px; text-align: center;'><span class='{color_class}'>{val}</span></td>"
        html_table += "</tr>"
    
    html_table += "</tbody></table>"
    st.markdown(html_table, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 엔화 투자 지표 테이블
    st.markdown("### 💴 엔화 투자 지표")
    
    jpy_data = []
    for period in periods:
        signals = all_signals.get(period, {})
        jpy_data.append({
            '기간': period_names[period],
            '엔화지수': signals.get('jxy', '-'),
            '엔화환율': signals.get('jpy_krw', '-'),
            '갭 비율': signals.get('jpy_gap_ratio', '-'),
            '적정환율': signals.get('jpy_fair_rate', '-')
        })
    
    jpy_df = pd.DataFrame(jpy_data)
    
    # HTML 테이블로 변환
    html_table = "<table style='width:100%; border-collapse: collapse; margin: 20px 0;'>"
    html_table += "<thead><tr style='background-color: #f0f2f6; border-bottom: 2px solid #ddd;'>"
    for col in jpy_df.columns:
        html_table += f"<th style='padding: 15px; text-align: center; font-size: 18px;'>{col}</th>"
    html_table += "</tr></thead><tbody>"
    
    for _, row in jpy_df.iterrows():
        html_table += "<tr style='border-bottom: 1px solid #ddd;'>"
        for idx, (col, val) in enumerate(row.items()):
            if idx == 0:  # 기간 열
                html_table += f"<td style='padding: 15px; text-align: center; font-weight: bold; font-size: 16px;'>{val}</td>"
            else:  # O/X 열
                color_class = "signal-o" if val == "O" else "signal-x" if val == "X" else ""
                html_table += f"<td style='padding: 15px; text-align: center;'><span class='{color_class}'>{val}</span></td>"
        html_table += "</tr>"
    
    html_table += "</tbody></table>"
    st.markdown(html_table, unsafe_allow_html=True)
    
    # 설명
    st.markdown("""
    ---
    #### 📖 지표 설명
    
    **달러 투자 지표:**
    - **달러지수**: 현재 DXY가 기간 중간값보다 낮으면 O (매수 신호)
    - **원달러환율**: 현재 USD/KRW가 기간 중간값보다 낮으면 O (매수 신호)
    - **갭 비율**: 현재 갭 비율이 기간 중간 갭 비율보다 높으면 O (매수 신호)
    - **적정환율**: 현재 환율이 적정 환율보다 낮으면 O (매수 신호)
    
    **엔화 투자 지표:**
    - **엔화지수**: 현재 JXY가 기간 중간값보다 낮으면 O (매수 신호)
    - **엔화환율**: 현재 JPY/KRW가 기간 중간값보다 낮으면 O (매수 신호)
    - **갭 비율**: 현재 갭 비율이 기간 중간 갭 비율보다 높으면 O (매수 신호)
    - **적정환율**: 현재 환율이 적정 환율보다 낮으면 O (매수 신호)
    
    💡 **팁**: 여러 기간에서 O가 많을수록 매수 타이밍으로 적합합니다.
    """)

def display_analysis_results(dxy_close: pd.Series, current_dxy: float, df_close: pd.DataFrame, df_high: pd.DataFrame, df_low: pd.DataFrame, current_rates: Dict[str, float], period_months: int = 12):
    """
    종가 DXY 시리즈를 기반으로 지정된 기간의 최고가/최저가를 분석하고 스트림릿 UI에 표시합니다.
    """
    
    # 기간별 최고 DXY: 종가 시리즈의 최대값 (DXY는 종가 기준으로 계산됨)
    dxy_52w_high = dxy_close.max()
    
    # 기간별 최저 DXY: 종가 시리즈의 최소값 (DXY는 종가 기준으로 계산됨)
    dxy_52w_low = dxy_close.min()
    
    # 기간별 중간값: 최고가와 최저가의 중간값
    dxy_52w_mid = (dxy_52w_high + dxy_52w_low) / 2
    
    # USD/KRW 데이터 처리 - 이제 High/Low 데이터 사용
    usd_krw_close = df_close['USD_KRW']
    usd_krw_high = df_high['USD_KRW']
    usd_krw_low = df_low['USD_KRW']
    current_usd_krw = current_rates['USD_KRW']
    # 인베스팅닷컴 현재가 우선 적용 (표시/지표용)
    investing_usd_for_tab = None
    try:
        investing_usd_for_tab = fetch_investing_usd_krw_rate()
    except Exception:
        investing_usd_for_tab = None
    current_usd_krw_display = investing_usd_for_tab if (investing_usd_for_tab is not None) else current_usd_krw
    
    # 기간별 최고가/최저가는 일봉의 High/Low에서 추출
    usd_krw_52w_high = usd_krw_high.max()  # 일봉 고가 중 최고값
    usd_krw_52w_low = usd_krw_low.min()    # 일봉 저가 중 최저값
    usd_krw_52w_mid = (usd_krw_52w_high + usd_krw_52w_low) / 2
    
    # USD/JPY 데이터 처리 - High/Low 데이터 사용
    usd_jpy_close = df_close['USD_JPY']
    usd_jpy_high = df_high['USD_JPY']
    usd_jpy_low = df_low['USD_JPY']
    current_usd_jpy = current_rates['USD_JPY']
    
    # 52주 최고가/최저가는 일봉의 High/Low에서 추출
    usd_jpy_52w_high = usd_jpy_high.max()  # 일봉 고가 중 최고값
    usd_jpy_52w_low = usd_jpy_low.min()    # 일봉 저가 중 최저값
    usd_jpy_52w_mid = (usd_jpy_52w_high + usd_jpy_52w_low) / 2
    
    # JXY 데이터 처리 - USD/JPY 역수로 계산
    # JXY = 100 / USD/JPY이므로, USD/JPY가 높을 때 JXY는 낮아지고, USD/JPY가 낮을 때 JXY는 높아진다
    jxy_close = 100 / usd_jpy_close  # USD/JPY 종가의 역수
    jxy_high = 100 / usd_jpy_low     # USD/JPY 저가의 역수가 JXY 고가
    jxy_low = 100 / usd_jpy_high     # USD/JPY 고가의 역수가 JXY 저가
    current_jxy = current_rates['JXY']
    
    # 52주 최고가/최저가 계산
    jxy_52w_high = jxy_high.max()  # JXY 최고값
    jxy_52w_low = jxy_low.min()    # JXY 최저값
    jxy_52w_mid = (jxy_52w_high + jxy_52w_low) / 2
    
    # JPY/KRW 데이터 처리 - USD/KRW / USD/JPY로 계산
    # JPY/KRW = USD/KRW / USD/JPY이므로, USD/KRW가 높고 USD/JPY가 낮을 때 JPY/KRW는 높아진다
    jpy_krw_close = usd_krw_close / usd_jpy_close  # USD/KRW 종가 / USD/JPY 종가
    jpy_krw_high = usd_krw_high / usd_jpy_low      # USD/KRW 고가 / USD/JPY 저가 = JPY/KRW 고가
    jpy_krw_low = usd_krw_low / usd_jpy_high       # USD/KRW 저가 / USD/JPY 고가 = JPY/KRW 저가
    current_jpy_krw = current_rates['JPY_KRW']
    # 인베스팅닷컴 JPY/KRW 현재가 우선 적용 (표시/지표용)
    investing_jpy_for_tab = None
    try:
        investing_jpy_for_tab = fetch_investing_jpy_krw_rate()
    except Exception:
        investing_jpy_for_tab = None
    current_jpy_krw_display = investing_jpy_for_tab if (investing_jpy_for_tab is not None) else current_jpy_krw
    
    # 52주 최고가/최저가 계산
    jpy_krw_52w_high = jpy_krw_high.max()  # JPY/KRW 최고값
    jpy_krw_52w_low = jpy_krw_low.min()    # JPY/KRW 최저값
    jpy_krw_52w_mid = (jpy_krw_52w_high + jpy_krw_52w_low) / 2
    
    # 탭 생성
    # 기간별 탭 제목 설정
    period_names = {1: "1개월", 3: "3개월", 6: "6개월", 12: "1년"}
    period_name = period_names.get(period_months, "1년")
    
    tab0, tab1, tab2, tab3, tab4 = st.tabs(["📊 지표 종합", f"🎯 달러투자 ({period_name})", f"💴 엔화투자 ({period_name})", "💰 달러투자 관리", "💴 엔화투자 관리"])
    
    with tab0:
        # 지표 종합 탭
        create_summary_indicators_tab()
    
    with tab1:
        # DXY 위치 분석 (시각화만)
        create_position_indicator(current_dxy, dxy_52w_high, dxy_52w_low, dxy_52w_mid)
        
        st.markdown("---")
        
        # 원달러 환율 위치 분석 (시각화만)
        create_usd_krw_position_indicator(current_usd_krw_display, usd_krw_52w_high, usd_krw_52w_low, usd_krw_52w_mid)
        
        st.markdown("---")
        
        # 달러 갭 비율 분석
        create_dollar_gap_indicator(current_dxy, current_usd_krw_display, dxy_52w_mid, usd_krw_52w_mid)
        
        st.markdown("---")
        
        # 적정 환율 분석
        create_fair_exchange_rate_indicator(current_dxy, current_usd_krw_display, dxy_52w_mid, usd_krw_52w_mid)
        
        st.markdown("---")
        
        # DXY & 원달러 결합 차트
        st.subheader(f"📈 달러 인덱스 & 원달러 환율 {period_name} 차트")
        combined_fig = create_dxy_usdkrw_combined_chart(dxy_close, usd_krw_close, current_dxy, current_usd_krw_display, period_name)
        st.plotly_chart(combined_fig, use_container_width=True)
        
        # 상세 데이터 표시
        with st.expander("📋 상세 데이터 보기"):
            st.subheader("최근 5일 DXY 데이터")
            recent_data = dxy_close.tail().to_frame()
            recent_data.index.name = "날짜"
            recent_data.columns = ["DXY"]
            st.dataframe(recent_data)
            
            # 통계 요약
            st.subheader("통계 요약")
            col1, col2 = st.columns(2)
            
            # 범위 계산
            range_diff = dxy_52w_high - dxy_52w_low
            position = (current_dxy - dxy_52w_low) / range_diff * 100 if range_diff > 0 else 0
            
            with col1:
                st.write("**기본 통계**")
                stats = {
                    "평균": f"{dxy_close.mean():.2f}",
                    "중앙값": f"{dxy_close.median():.2f}",
                    "표준편차": f"{dxy_close.std():.2f}"
                }
                for key, value in stats.items():
                    st.write(f"- {key}: {value}")
            
            with col2:
                st.write("**범위 정보**")
                range_info = {
                    "전체 범위": f"{range_diff:.2f}",
                    "현재 위치": f"{position:.1f}%",
                    "데이터 포인트": f"{len(dxy_close)}개",
                    f"{period_name} 중간값": f"{dxy_52w_mid:.2f}"
                }
                for key, value in range_info.items():
                    st.write(f"- {key}: {value}")
    
    with tab2:
        # JXY 위치 분석 (시각화만)
        create_jxy_position_indicator(current_jxy, jxy_52w_high, jxy_52w_low, jxy_52w_mid)
        
        st.markdown("---")
        
        # 엔화 환율 위치 분석 (시각화만)
        create_jpy_position_indicator(current_jpy_krw_display, jpy_krw_52w_high, jpy_krw_52w_low, jpy_krw_52w_mid)
        
        st.markdown("---")
        
        # 엔화 갭 비율 분석
        create_jpy_gap_indicator(current_jxy, current_jpy_krw_display, jxy_52w_mid, jpy_krw_52w_mid)
        
        st.markdown("---")
        
        # 엔화 적정 환율 분석
        create_jpy_fair_exchange_rate_indicator(current_jxy, current_jpy_krw_display, jxy_52w_mid, jpy_krw_52w_mid)
        
        st.markdown("---")
        
        # 엔화 환율 차트
        st.subheader(f"💴 엔화 환율 (JPY/KRW) {period_name} 차트")
        jpy_krw_fig = create_jpy_krw_chart(jpy_krw_close, current_jpy_krw_display, jpy_krw_52w_high, jpy_krw_52w_low, jpy_krw_52w_mid, period_name)
        st.plotly_chart(jpy_krw_fig, use_container_width=True)
    
    with tab3:
        display_dollar_investment_tab()
    
    with tab4:
        display_jpy_investment_tab()


# --- 스트림릿 메인 앱 ---
def load_data_from_supabase():
    """Supabase에서 데이터 로드"""
    # 달러 투자 데이터 로드
    dollar_investments = load_dollar_investments_from_db()
    if dollar_investments:
        st.session_state.dollar_investments = dollar_investments
    
    # 달러 매도 기록 로드
    dollar_sell_records = load_dollar_sell_records_from_db()
    if dollar_sell_records:
        st.session_state.sell_records = dollar_sell_records
    
    # 엔화 투자 데이터 로드
    jpy_investments = load_jpy_investments_from_db()
    if jpy_investments:
        st.session_state.jpy_investments = jpy_investments
    
    # 엔화 매도 기록 로드
    jpy_sell_records = load_jpy_sell_records_from_db()
    if jpy_sell_records:
        st.session_state.jpy_sell_records = jpy_sell_records

def main():
    """스트림릿 메인 애플리케이션"""
    
    # Supabase에서 데이터 로드 (앱 시작 시 한 번만)
    if 'data_loaded' not in st.session_state:
        load_data_from_supabase()
        st.session_state.data_loaded = True
    
    # 사이드바 설정
    st.sidebar.title("⚙️ 설정")
    
    # 새로고침 버튼
    if st.sidebar.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        # 새로고침을 위해 세션 상태 업데이트
        if 'refresh_trigger' not in st.session_state:
            st.session_state.refresh_trigger = True
        else:
            st.session_state.refresh_trigger = not st.session_state.refresh_trigger
    
    # 기간 선택 드롭다운
    st.sidebar.subheader("📅 분석 기간 선택")
    period_options = {
        "1개월": 1,
        "3개월": 3, 
        "6개월": 6,
        "1년": 12
    }
    selected_period = st.sidebar.selectbox(
        "분석 기간을 선택하세요:",
        options=list(period_options.keys()),
        index=3,  # 기본값: 1년
        key="period_selector"
    )
    selected_months = period_options[selected_period]
    
    # 캐시된 데이터 가져오기 함수 (기간별로 캐시)
    @st.cache_data(ttl=300)  # 5분 캐시
    def get_cached_data(period_months):
        """데이터를 캐시하여 성능 향상"""
        historical_df_close, historical_df_high, historical_df_low, current_rates = fetch_period_data_and_current_rates(period_months)
        dxy_close = calculate_dollar_index_series(historical_df_close)
        current_dxy = calculate_current_dxy(current_rates)
        return dxy_close, current_dxy, historical_df_close, historical_df_high, historical_df_low, current_rates
    
    try:
        # 캐시된 데이터 가져오기 (선택된 기간으로)
        dxy_close, current_dxy, df_close, df_high, df_low, current_rates = get_cached_data(selected_months)
        
        # 분석 결과 표시
        display_analysis_results(dxy_close, current_dxy, df_close, df_high, df_low, current_rates, selected_months)
        
        # 사이드바에 현재 환율 정보 표시
        st.sidebar.subheader("💱 현재 환율")
        
        # 1) 원달러 환율 - 인베스팅닷컴
        investing_usd = fetch_investing_usd_krw_rate()
        if investing_usd is not None:
            st.sidebar.metric(
                label="원달러 (USD/KRW, 인베스팅닷컴)",
                value=f"{investing_usd:,.2f}원"
            )

        # 2) 하나은행 달러 환율 (USD/KRW) - 네이버
        hana_rate = fetch_hana_usd_krw_rate()
        if hana_rate is not None:
            st.sidebar.metric(
                label="하나은행 달러 (USD/KRW, 네이버)",
                value=f"{hana_rate:,.2f}원"
            )
        else:
            st.sidebar.caption("하나은행 달러 환율을 불러올 수 없습니다.")

        # 3) 테더 환율 (USDT/KRW) - 빗썸(Bithumb)
        usdt_krw = fetch_usdt_krw_price()
        if usdt_krw is not None:
            st.sidebar.metric(
                label="테더 (USDT/KRW, 빗썸)",
                value=f"{usdt_krw:,.0f}원"
            )
        else:
            st.sidebar.caption("USDT 가격을 불러올 수 없습니다.")

        # 4) 김치프리미엄: 테더-인베스팅닷컴 달러 수식 기반 (USDT/Investing - 1)
        if (usdt_krw is not None) and (investing_usd is not None) and investing_usd > 0:
            kimchi_ratio = usdt_krw / investing_usd
            kimchi_pct = (kimchi_ratio - 1.0) * 100.0
            diff_krw = usdt_krw - investing_usd
            st.sidebar.metric(
                label="김치프리미엄",
                value=f"{kimchi_pct:+.2f}%",
                delta=f"{diff_krw:,.0f}원",
                delta_color="inverse"  # +일 때 빨강, -일 때 초록
            )
            st.sidebar.caption(f"USDT/Investing 비율: {kimchi_ratio:.4f}x")

        # 인베스팅닷컴 원엔 환율 (JPY/KRW)
        investing_jpy = fetch_investing_jpy_krw_rate()
        if investing_jpy is not None:
            st.sidebar.metric(
                label="원엔 (JPY/KRW, 인베스팅닷컴)",
                value=f"{investing_jpy:,.2f}원"
            )
        
        # 푸터
        st.markdown("---")
        st.markdown(
            """
            <div style='text-align: center; color: gray;'>
                <small>
                    데이터 출처: Yahoo Finance | 
                    업데이트: 5분마다 자동 갱신 | 
                    마지막 업데이트: {}
                </small>
            </div>
            """.format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            unsafe_allow_html=True
        )
        
    except Exception as e:
        st.error(f"❌ 오류가 발생했습니다: {str(e)}")
        st.info("새로고침 버튼을 클릭하여 다시 시도해 주세요.")

if __name__ == "__main__":
    main()