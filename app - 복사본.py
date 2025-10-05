import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Tuple
import datetime

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
    
    # 52주 최고가/최저가 계산
    jpy_krw_52w_high = jpy_krw_high.max()  # JPY/KRW 최고값
    jpy_krw_52w_low = jpy_krw_low.min()    # JPY/KRW 최저값
    jpy_krw_52w_mid = (jpy_krw_52w_high + jpy_krw_52w_low) / 2
    
    # 탭 생성
    # 기간별 탭 제목 설정
    period_names = {1: "1개월", 3: "3개월", 6: "6개월", 12: "1년"}
    period_name = period_names.get(period_months, "1년")
    
    tab1, tab2 = st.tabs([f"🎯 달러투자 ({period_name})", f"💴 엔화투자 ({period_name})"])
    
    with tab1:
        # DXY 위치 분석 (시각화만)
        create_position_indicator(current_dxy, dxy_52w_high, dxy_52w_low, dxy_52w_mid)
        
        st.markdown("---")
        
        # 원달러 환율 위치 분석 (시각화만)
        create_usd_krw_position_indicator(current_usd_krw, usd_krw_52w_high, usd_krw_52w_low, usd_krw_52w_mid)
        
        st.markdown("---")
        
        # 달러 갭 비율 분석
        create_dollar_gap_indicator(current_dxy, current_usd_krw, dxy_52w_mid, usd_krw_52w_mid)
        
        st.markdown("---")
        
        # 적정 환율 분석
        create_fair_exchange_rate_indicator(current_dxy, current_usd_krw, dxy_52w_mid, usd_krw_52w_mid)
        
        st.markdown("---")
        
        # DXY 차트
        st.subheader(f"📈 달러 인덱스 (DXY) {period_name} 차트")
        dxy_fig = create_dxy_chart(dxy_close, current_dxy, dxy_52w_high, dxy_52w_low, dxy_52w_mid, period_name)
        st.plotly_chart(dxy_fig, use_container_width=True)
        
        st.markdown("---")
        
        # 원달러 환율 차트
        st.subheader(f"💴 원달러 환율 (USD/KRW) {period_name} 차트")
        usd_krw_fig = create_usd_krw_chart(usd_krw_close, current_usd_krw, usd_krw_52w_high, usd_krw_52w_low, usd_krw_52w_mid, period_name)
        st.plotly_chart(usd_krw_fig, use_container_width=True)
        
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
        create_jpy_position_indicator(current_jpy_krw, jpy_krw_52w_high, jpy_krw_52w_low, jpy_krw_52w_mid)
        
        st.markdown("---")
        
        # 엔화 갭 비율 분석
        create_jpy_gap_indicator(current_jxy, current_jpy_krw, jxy_52w_mid, jpy_krw_52w_mid)
        
        st.markdown("---")
        
        # 엔화 적정 환율 분석
        create_jpy_fair_exchange_rate_indicator(current_jxy, current_jpy_krw, jxy_52w_mid, jpy_krw_52w_mid)
        
        st.markdown("---")
        
        # 엔화 환율 차트
        st.subheader(f"💴 엔화 환율 (JPY/KRW) {period_name} 차트")
        jpy_krw_fig = create_jpy_krw_chart(jpy_krw_close, current_jpy_krw, jpy_krw_52w_high, jpy_krw_52w_low, jpy_krw_52w_mid, period_name)
        st.plotly_chart(jpy_krw_fig, use_container_width=True)


# --- 스트림릿 메인 앱 ---
def main():
    """스트림릿 메인 애플리케이션"""
    
    # 사이드바 설정
    st.sidebar.title("⚙️ 설정")
    
    # 새로고침 버튼
    if st.sidebar.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()
    
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
        
        # 원달러 환율
        if 'USD_KRW' in current_rates:
            st.sidebar.metric(
                label="원달러 (USD/KRW)",
                value=f"{current_rates['USD_KRW']:.0f}원"
            )
        
        # 원엔 환율 (JPY/KRW)
        if 'JPY_KRW' in current_rates:
            st.sidebar.metric(
                label="원엔 (JPY/KRW)",
                value=f"{current_rates['JPY_KRW']:.2f}원"
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