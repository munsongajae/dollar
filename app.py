"""
달러/엔화 투자 관리 앱 (개선 버전)
토스 스타일의 모던한 UI/UX 적용
"""
import streamlit as st
import datetime
from typing import Dict

# 페이지 설정 (반드시 첫 번째로!)
st.set_page_config(
    page_title="환율 투자 관리",
    page_icon="💵",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 모듈 임포트
from components.custom_styles import inject_custom_styles, create_metric_card, create_gradient_card
from components.charts import create_dxy_chart, create_jpy_krw_chart, create_usd_krw_chart
from components.indicators import (
    create_dxy_position_indicator,
    create_jxy_position_indicator,
    create_usd_krw_position_indicator,
    create_jpy_krw_position_indicator,
    create_gap_indicator,
    create_fair_rate_indicator
)
from components.investment_ui import display_investment_tab
from components.sell_records_ui import display_sell_records_tab
from services.exchange_rate import (
    fetch_usdt_krw_price,
    fetch_hana_usd_krw_rate,
    fetch_investing_usd_krw_rate,
    fetch_investing_jpy_krw_rate
)
from services.exchange_rate_cached import fetch_period_data_with_cache
from services.index_calculator import calculate_dollar_index_series, calculate_current_dxy
from database.dollar_db import load_dollar_investments, load_dollar_sell_records
from database.jpy_db import load_jpy_investments, load_jpy_sell_records
from utils.formatters import format_currency, format_percentage
import pandas as pd


def calculate_indicator_signals(current_dxy: float, dxy_52w_mid: float, 
                                current_usd_krw: float, usd_krw_52w_mid: float,
                                current_jxy: float, jxy_52w_mid: float,
                                current_jpy_krw: float, jpy_krw_52w_mid: float):
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
    jxy_signal = "O" if current_jxy < jxy_52w_mid else "X"  # JXY는 낮을수록 좋음 (저평가)
    jpy_krw_signal = "O" if current_jpy_krw < jpy_krw_52w_mid else "X"
    
    # 엔화 갭 비율 (100엔당 기준)
    current_jpy_gap_ratio = (current_jxy * 100) / (current_jpy_krw * 100)
    mid_jpy_gap_ratio = (jxy_52w_mid * 100) / (jpy_krw_52w_mid * 100)
    jpy_gap_ratio_signal = "O" if current_jpy_gap_ratio > mid_jpy_gap_ratio else "X"
    
    # 엔화 적정 환율 (100엔당 기준)
    mid_jpy_gap_ratio_raw = jxy_52w_mid / jpy_krw_52w_mid
    jpy_fair_exchange_rate = (current_jxy / mid_jpy_gap_ratio_raw) * 100  # 100엔당
    current_jpy_krw_100 = current_jpy_krw * 100  # 100엔당
    jpy_fair_rate_signal = "O" if current_jpy_krw_100 < jpy_fair_exchange_rate else "X"
    
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
    st.markdown("모든 기간의 지표를 한눈에 확인하세요. **O**는 매수 신호, **X**는 매도 신호입니다.")
    
    # 실시간 환율 정보 (HTML 테이블로 2열 고정)
    st.markdown("### 💱 실시간 환율")
    
    # 데이터 가져오기 (기본값 설정)
    investing_usd = fetch_investing_usd_krw_rate() or 0
    hana_rate = fetch_hana_usd_krw_rate() or 0
    usdt_krw = fetch_usdt_krw_price() or 0
    investing_jpy = fetch_investing_jpy_krw_rate() or 0
    
    # 김치프리미엄 계산
    kimchi_pct = 0
    diff_krw = 0
    if usdt_krw and investing_usd and investing_usd > 0:
        kimchi_ratio = usdt_krw / investing_usd
        kimchi_pct = (kimchi_ratio - 1.0) * 100.0
        diff_krw = usdt_krw - investing_usd
    
    # HTML 테이블로 2열 레이아웃 생성
    from config.settings import COLORS
    
    html_table = f"""
    <style>
    .exchange-rate-table {{
        width: 100%;
        display: table;
        border-collapse: collapse;
        margin-bottom: 1.5rem;
    }}
    .exchange-rate-row {{
        display: table-row;
    }}
    .exchange-rate-cell {{
        display: table-cell;
        width: 50%;
        padding: 0.5rem;
        vertical-align: top;
    }}
    .metric-box {{
        background: {COLORS['background_primary']};
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        border: 1px solid {COLORS['gray_200']};
    }}
    .metric-label {{
        font-size: 0.875rem;
        color: {COLORS['text_secondary']};
        font-weight: 500;
        margin-bottom: 0.5rem;
    }}
    .metric-value {{
        font-size: 1.5rem;
        color: {COLORS['text_primary']};
        font-weight: 700;
        letter-spacing: -0.02em;
    }}
    .metric-delta {{
        font-size: 0.875rem;
        color: {COLORS['text_secondary']};
        margin-top: 0.25rem;
    }}
    
    @media (max-width: 640px) {{
        .metric-label {{
            font-size: 0.7rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .metric-value {{
            font-size: 1.1rem;
        }}
        .metric-delta {{
            font-size: 0.7rem;
        }}
        .metric-box {{
            padding: 0.75rem;
            margin-bottom: 0.4rem;
        }}
        .exchange-rate-cell {{
            padding: 0.25rem;
        }}
    }}
    </style>
    
    <div class="exchange-rate-table">
        <div class="exchange-rate-row">
            <div class="exchange-rate-cell">
                <!-- 왼쪽 컬럼 -->
                <div class="metric-box">
                    <div class="metric-label">USD/KRW (인베스팅)</div>
                    <div class="metric-value">{investing_usd:,.2f}원</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">USDT/KRW (빗썸)</div>
                    <div class="metric-value">{usdt_krw:,.0f}원</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">JPY/KRW (인베스팅)</div>
                    <div class="metric-value">{investing_jpy:,.4f}원</div>
                </div>
            </div>
            <div class="exchange-rate-cell">
                <!-- 오른쪽 컬럼 -->
                <div class="metric-box">
                    <div class="metric-label">USD/KRW (하나은행)</div>
                    <div class="metric-value">{hana_rate:,.2f}원</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">김치프리미엄</div>
                    <div class="metric-value">{kimchi_pct:+.2f}%</div>
                    <div class="metric-delta">{diff_krw:+,.0f}원</div>
                </div>
            </div>
        </div>
    </div>
    """
    
    st.markdown(html_table, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 모든 기간 데이터 계산
    periods = [1, 3, 6, 12]
    period_names = {1: "1개월", 3: "3개월", 6: "6개월", 12: "1년"}
    
    all_signals = {}
    
    with st.spinner("모든 기간 데이터를 분석하는 중..."):
        for period in periods:
            try:
                df_close, df_high, df_low, current_rates = fetch_period_data_with_cache(period)
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
                
                # JPY/KRW 계산 (1엔당)
                jpy_krw_close = df_close['JPY_KRW']
                jpy_krw_high = df_high['JPY_KRW']
                jpy_krw_low = df_low['JPY_KRW']
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


def load_data_from_db():
    """데이터베이스에서 모든 데이터 로드"""
    if 'data_loaded' not in st.session_state:
        # 달러 투자 데이터
        dollar_investments = load_dollar_investments()
        if dollar_investments:
            st.session_state.dollar_investments = dollar_investments
        else:
            st.session_state.dollar_investments = []
        
        # 달러 매도 기록
        dollar_sell_records = load_dollar_sell_records()
        if dollar_sell_records:
            st.session_state.sell_records = dollar_sell_records
        else:
            st.session_state.sell_records = []
        
        # 엔화 투자 데이터
        jpy_investments = load_jpy_investments()
        if jpy_investments:
            st.session_state.jpy_investments = jpy_investments
        else:
            st.session_state.jpy_investments = []
        
        # 엔화 매도 기록
        jpy_sell_records = load_jpy_sell_records()
        if jpy_sell_records:
            st.session_state.jpy_sell_records = jpy_sell_records
        else:
            st.session_state.jpy_sell_records = []
        
        st.session_state.data_loaded = True


def render_main_dashboard():
    """메인 대시보드 렌더링"""
    
    # 헤더 (업데이트 시간 + 새로고침 버튼)
    col1, col2 = st.columns([5, 1])
    with col1:
        st.caption(f"마지막 업데이트: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    with col2:
        if st.button("🔄 새로고침", type="secondary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # 탭 메뉴
    tab0, tab1, tab2, tab3 = st.tabs([
        "📊 종합",
        "📈 분석",
        "💰 투자",
        "📋 매도"
    ])
    
    with tab0:
        # 종합 지표 탭 (모든 기간)
        create_summary_indicators_tab()
        
    with tab1:
        # 통합 환율 분석 탭
        # 통화 선택
        col_currency, col_period, col_spacer = st.columns([1, 1, 3])
        
        with col_currency:
            currency = st.radio(
                "💱 통화 선택",
                options=["💵 달러", "💴 엔화"],
                horizontal=True,
                key="analysis_currency"
            )
        
        with col_period:
            period_options = {"1개월": 1, "3개월": 3, "6개월": 6, "1년": 12}
            selected_period = st.selectbox(
                "📅 분석 기간",
                options=list(period_options.keys()),
                index=3,  # 1년
                key="analysis_period"
            )
            period_months = period_options[selected_period]
        
        # 선택된 통화에 따라 분석 표시
        if currency == "💵 달러":
            # 달러 분석
            try:
                df_close, df_high, df_low, current_rates = fetch_period_data_with_cache(period_months)
                dxy_series = calculate_dollar_index_series(df_close)
                current_dxy = calculate_current_dxy(current_rates)
                
                # USD/KRW 데이터 추출
                usd_krw_series = df_close['USD_KRW']
                usd_krw_52w_high = df_high['USD_KRW'].max()
                usd_krw_52w_low = df_low['USD_KRW'].min()
                usd_krw_52w_mid = (usd_krw_52w_high + usd_krw_52w_low) / 2
                current_usd_krw = current_rates['USD_KRW']
                
                # DXY 데이터
                dxy_52w_high = dxy_series.max()
                dxy_52w_low = dxy_series.min()
                dxy_52w_mid = (dxy_52w_high + dxy_52w_low) / 2
                
                # 지표 표시 (4개 통일성 있게)
                # 1. 달러지수 (DXY)
                create_dxy_position_indicator(current_dxy, dxy_52w_high, dxy_52w_low, dxy_52w_mid)
                st.markdown("---")
                
                # 2. 달러환율 (USD/KRW)
                create_usd_krw_position_indicator(current_usd_krw, usd_krw_52w_high, usd_krw_52w_low, usd_krw_52w_mid)
                st.markdown("---")
                
                # 3. 갭 비율
                dollar_gap_current = (current_dxy / current_usd_krw) * 100
                dollar_gap_mid = (dxy_52w_mid / usd_krw_52w_mid) * 100
                create_gap_indicator("📊 달러 갭 비율", dollar_gap_current, dollar_gap_mid)
                st.markdown("---")
                
                # 4. 적정환율
                mid_gap_ratio = (dxy_52w_mid / usd_krw_52w_mid) * 100
                fair_exchange_rate = (current_dxy / mid_gap_ratio) * 100
                create_fair_rate_indicator("💰 적정 환율", current_usd_krw, fair_exchange_rate)
                
                # 차트 표시
                st.markdown("---")
                st.subheader("📊 차트")
                
                # DXY 차트
                period_name = f"{period_months}개월" if period_months < 12 else "1년"
                fig_dxy = create_dxy_chart(dxy_series, current_dxy, dxy_52w_high, dxy_52w_low, dxy_52w_mid, period_name)
                st.plotly_chart(fig_dxy, use_container_width=True)
                
                # USD/KRW 차트
                fig_usd_krw = create_usd_krw_chart(usd_krw_series, current_usd_krw, usd_krw_52w_high, usd_krw_52w_low, usd_krw_52w_mid, period_name)
                st.plotly_chart(fig_usd_krw, use_container_width=True)
            except Exception as e:
                st.error(f"❌ 오류가 발생했습니다: {str(e)}")
        else:
            # 엔화 분석
            try:
                df_close, df_high, df_low, current_rates = fetch_period_data_with_cache(period_months)
                
                # JPY/KRW 데이터 추출 (1엔당, 표시는 100엔당)
                jpy_krw_series = df_close['JPY_KRW']
                jpy_krw_52w_high = df_high['JPY_KRW'].max()
                jpy_krw_52w_low = df_low['JPY_KRW'].min()
                jpy_krw_52w_mid = (jpy_krw_52w_high + jpy_krw_52w_low) / 2
                current_jpy_krw = current_rates['JPY_KRW']
                
                # JXY 데이터 계산
                current_jxy = current_rates.get('JXY', 0)
                # 간단한 JXY 계산: USD/JPY를 역수로 변환하여 정규화
                usd_jpy_series = df_close['USD_JPY']
                jxy_series = 100 / usd_jpy_series
                jxy_52w_high = jxy_series.max()
                jxy_52w_low = jxy_series.min()
                jxy_52w_mid = (jxy_52w_high + jxy_52w_low) / 2
                
                # 지표 표시 (4개 통일성 있게)
                # 1. 엔화지수 (JXY)
                create_jxy_position_indicator(current_jxy, jxy_52w_high, jxy_52w_low, jxy_52w_mid)
                st.markdown("---")
                
                # 2. 엔화환율 (JPY/KRW, 100엔당)
                create_jpy_krw_position_indicator(current_jpy_krw, jpy_krw_52w_high, jpy_krw_52w_low, jpy_krw_52w_mid)
                st.markdown("---")
                
                # 3. 갭 비율 (기존 로직: 양쪽 다 *100 하여 100엔당 기준)
                jpy_gap_current = (current_jxy * 100) / (current_jpy_krw * 100)
                jpy_gap_mid = (jxy_52w_mid * 100) / (jpy_krw_52w_mid * 100)
                create_gap_indicator("📊 엔화 갭 비율", jpy_gap_current, jpy_gap_mid)
                st.markdown("---")
                
                # 4. 적정환율 (기존 로직: 1엔당 계산, 표시는 100엔당)
                mid_jpy_gap_ratio = jxy_52w_mid / jpy_krw_52w_mid
                jpy_fair_exchange_rate = current_jxy / mid_jpy_gap_ratio
                create_fair_rate_indicator("💰 적정 환율", current_jpy_krw * 100, jpy_fair_exchange_rate * 100)
                
                # 차트 표시
                st.subheader("📊 차트")
                period_name = f"{period_months}개월" if period_months < 12 else "1년"
                
                # JPY/KRW 차트 (100엔 기준으로 변환)
                jpy_krw_series_100 = jpy_krw_series * 100
                fig_jpy_krw = create_jpy_krw_chart(jpy_krw_series_100, current_jpy_krw * 100, 
                                                   jpy_krw_52w_high * 100, jpy_krw_52w_low * 100, 
                                                   jpy_krw_52w_mid * 100, period_name)
                st.plotly_chart(fig_jpy_krw, use_container_width=True)
            except Exception as e:
                st.error(f"❌ 오류가 발생했습니다: {str(e)}")
    
    with tab2:
        # 통합 투자 관리 탭
        display_investment_tab()
    
    with tab3:
        # 통합 매도 기록 탭
        display_sell_records_tab()


def main():
    """메인 애플리케이션"""
    # 커스텀 스타일 적용
    inject_custom_styles()
    
    # 데이터베이스에서 데이터 로드
    load_data_from_db()
    
    # 메인 대시보드 렌더링
    render_main_dashboard()
    
    # 푸터
    st.markdown("---")
    st.markdown(
        f"""
        <div style='text-align: center; color: #8B95A1; padding: 20px 0;'>
            <small>
                📊 데이터 출처: Yahoo Finance, 인베스팅닷컴, 빗썸<br>
                🔄 업데이트: 5분마다 자동 갱신<br>
                ⏰ {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            </small>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()

