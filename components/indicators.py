"""
위치 및 갭 지표 컴포넌트
"""
import streamlit as st
from config.settings import COLORS


def create_position_indicator(title: str, current_value: float, high_value: float, 
                              low_value: float, mid_value: float, 
                              reverse_logic: bool = False, multiplier: float = 1.0):
    """
    범용 위치 지표를 생성합니다.
    
    Args:
        title: 지표 제목
        current_value: 현재 값
        high_value: 최고 값
        low_value: 최저 값
        mid_value: 중간 값
        reverse_logic: True면 낮을수록 O (역방향 로직)
        multiplier: 표시 값 배율 (예: 100을 곱하려면 100)
    """
    st.markdown(f"### {title}")
    
    # O/X 표시 로직
    if reverse_logic:
        is_good = current_value < mid_value
    else:
        is_good = current_value > mid_value
    
    ox_symbol = "O" if is_good else "X"
    ox_color = COLORS['success'] if is_good else COLORS['error']
    
    # 위치 계산 (0-100%)
    if high_value != low_value:
        position_percent = ((current_value - low_value) / (high_value - low_value)) * 100
        position_percent = max(0, min(100, position_percent))
    else:
        position_percent = 50
    
    # 값 포맷팅
    current_display = current_value * multiplier
    low_display = low_value * multiplier
    mid_display = mid_value * multiplier
    high_display = high_value * multiplier
    
    st.markdown(f"""
    <style>
    .indicator-container {{
        display: flex;
        align-items: center;
        gap: 15px;
        margin: 12px 0;
        background: {COLORS['background_primary']};
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }}
    .indicator-ox {{
        font-size: 36px;
        color: {ox_color};
        flex-shrink: 0;
        font-weight: 700;
    }}
    .indicator-bar {{
        background: linear-gradient(to right, {COLORS['success']} 0%, {COLORS['warning']} 50%, {COLORS['error']} 100%);
        height: 24px;
        border-radius: 12px;
        position: relative;
        border: 2px solid {COLORS['gray_300']};
    }}
    .indicator-label {{
        font-size: 11px;
        color: {COLORS['text_secondary']};
    }}
    .indicator-value {{
        font-size: 14px;
        font-weight: 700;
        color: {COLORS['text_primary']};
    }}
    
    @media (max-width: 768px) {{
        .indicator-container {{
            gap: 10px;
            padding: 12px;
            margin: 8px 0;
        }}
        .indicator-ox {{
            font-size: 24px;
        }}
        .indicator-bar {{
            height: 20px;
        }}
        .indicator-label {{
            font-size: 9px;
        }}
        .indicator-value {{
            font-size: 12px;
        }}
    }}
    </style>
    <div class="indicator-container">
        <div class="indicator-ox">
            {ox_symbol}
        </div>
        <div style="flex-grow: 1;">
            <div class="indicator-bar">
                <!-- 중간값 마커 -->
                <div style="
                    position: absolute;
                    left: 50%;
                    top: -4px;
                    width: 0;
                    height: 0;
                    border-left: 6px solid transparent;
                    border-right: 6px solid transparent;
                    border-top: 12px solid {COLORS['error']};
                    transform: translateX(-50%);
                "></div>
                <!-- 현재값 마커 -->
                <div style="
                    position: absolute;
                    left: {position_percent}%;
                    top: -4px;
                    width: 0;
                    height: 0;
                    border-left: 6px solid transparent;
                    border-right: 6px solid transparent;
                    border-top: 12px solid {COLORS['text_primary']};
                    transform: translateX(-50%);
                "></div>
                <!-- 라벨들 -->
                <div class="indicator-label" style="
                    position: absolute;
                    left: 0%;
                    top: 30px;
                ">최저<br>{low_display:.2f}</div>
                <div class="indicator-label" style="
                    position: absolute;
                    left: 50%;
                    top: 30px;
                    transform: translateX(-50%);
                ">중간<br><br>{mid_display:.2f}</div>
                <div class="indicator-label" style="
                    position: absolute;
                    right: 0%;
                    top: 30px;
                ">최고<br>{high_display:.2f}</div>
                <!-- 현재값 라벨 -->
                <div class="indicator-label" style="
                    position: absolute;
                    left: {position_percent}%;
                    top: -20px;
                    font-weight: 600;
                    transform: translateX(-50%);
                ">현재</div>
                <!-- 현재값 수치 -->
                <div class="indicator-value" style="
                    position: absolute;
                    left: {position_percent}%;
                    top: 50%;
                    transform: translate(-50%, -50%);
                ">{current_display:.2f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def create_dxy_position_indicator(current_dxy: float, dxy_52w_high: float, 
                                  dxy_52w_low: float, dxy_52w_mid: float):
    """달러 인덱스 위치 지표"""
    create_position_indicator(
        title="💵 달러지수 (DXY)",
        current_value=current_dxy,
        high_value=dxy_52w_high,
        low_value=dxy_52w_low,
        mid_value=dxy_52w_mid,
        reverse_logic=True,  # DXY는 낮을수록 좋음
        multiplier=1.0
    )


def create_jxy_position_indicator(current_jxy: float, jxy_52w_high: float, 
                                  jxy_52w_low: float, jxy_52w_mid: float):
    """엔화 인덱스 위치 지표"""
    create_position_indicator(
        title="💴 엔화지수 (JXY)",
        current_value=current_jxy,
        high_value=jxy_52w_high,
        low_value=jxy_52w_low,
        mid_value=jxy_52w_mid,
        reverse_logic=True,  # JXY는 낮을수록 좋음 (저평가 시 매수)
        multiplier=100.0
    )


def create_usd_krw_position_indicator(current_usd_krw: float, usd_krw_52w_high: float,
                                      usd_krw_52w_low: float, usd_krw_52w_mid: float):
    """달러 환율 위치 지표"""
    create_position_indicator(
        title="💵 달러환율 (USD/KRW)",
        current_value=current_usd_krw,
        high_value=usd_krw_52w_high,
        low_value=usd_krw_52w_low,
        mid_value=usd_krw_52w_mid,
        reverse_logic=True,  # 환율은 낮을수록 좋음
        multiplier=1.0
    )


def create_jpy_krw_position_indicator(current_jpy_krw: float, jpy_krw_52w_high: float,
                                      jpy_krw_52w_low: float, jpy_krw_52w_mid: float):
    """엔화 환율 위치 지표"""
    create_position_indicator(
        title="💴 엔화환율",
        current_value=current_jpy_krw,
        high_value=jpy_krw_52w_high,
        low_value=jpy_krw_52w_low,
        mid_value=jpy_krw_52w_mid,
        reverse_logic=True,  # 환율은 낮을수록 좋음
        multiplier=100.0
    )


def create_gap_indicator(title: str, current_gap: float, mid_gap: float):
    """
    갭 비율 지표를 생성합니다 (position indicator 스타일).
    
    Args:
        title: 지표 제목
        current_gap: 현재 갭 비율
        mid_gap: 중간 갭 비율 (52주)
    """
    st.markdown(f"### {title}")
    
    # O/X 표시 로직 (현재 갭이 중간 갭보다 크면 O)
    is_good = current_gap > mid_gap
    ox_symbol = "O" if is_good else "X"
    ox_color = COLORS['success'] if is_good else COLORS['error']
    
    # 범위 계산 (중간값 기준 ±20%)
    gap_range = mid_gap * 0.2
    low_display = mid_gap - gap_range
    high_display = mid_gap + gap_range
    
    # 위치 계산
    if high_display != low_display:
        position_percent = ((current_gap - low_display) / (high_display - low_display)) * 100
        position_percent = max(0, min(100, position_percent))
    else:
        position_percent = 50
    
    st.markdown(f"""
    <style>
    .gap-indicator-container {{
        display: flex;
        align-items: center;
        gap: 15px;
        margin: 12px 0;
        background: {COLORS['background_primary']};
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }}
    .gap-indicator-ox {{
        font-size: 36px;
        color: {ox_color};
        flex-shrink: 0;
        font-weight: 700;
    }}
    .gap-indicator-bar {{
        background: linear-gradient(to right, {COLORS['success']} 0%, {COLORS['warning']} 50%, {COLORS['error']} 100%);
        height: 24px;
        border-radius: 12px;
        position: relative;
        border: 2px solid {COLORS['gray_300']};
    }}
    .gap-indicator-value {{
        font-size: 14px;
        font-weight: 600;
        color: {COLORS['text_primary']};
        white-space: nowrap;
    }}
    
    @media (max-width: 768px) {{
        .gap-indicator-container {{
            gap: 10px;
            padding: 12px;
            margin: 8px 0;
        }}
        .gap-indicator-ox {{
            font-size: 24px;
        }}
        .gap-indicator-bar {{
            height: 20px;
        }}
        .gap-indicator-value {{
            font-size: 11px;
        }}
    }}
    </style>
    <div class="gap-indicator-container">
        <div class="gap-indicator-ox">
            {ox_symbol}
        </div>
        <div style="flex-grow: 1;">
            <div class="gap-indicator-bar">
                <!-- 중간값 마커 -->
                <div style="
                    position: absolute;
                    left: 50%;
                    top: -4px;
                    width: 0;
                    height: 0;
                    border-left: 6px solid transparent;
                    border-right: 6px solid transparent;
                    border-top: 12px solid {COLORS['error']};
                    transform: translateX(-50%);
                "></div>
                <!-- 현재값 마커 -->
                <div style="
                    position: absolute;
                    left: {position_percent}%;
                    top: -4px;
                    width: 0;
                    height: 0;
                    border-left: 6px solid transparent;
                    border-right: 6px solid transparent;
                    border-top: 12px solid {COLORS['text_primary']};
                    transform: translateX(-50%);
                "></div>
                <!-- 라벨들 -->
                <div class="gap-indicator-value" style="
                    position: absolute;
                    left: {position_percent}%;
                    top: -24px;
                    transform: translateX(-50%);
                ">현재 갭 비율: {current_gap:.4f}</div>
                <div class="gap-indicator-value" style="
                    position: absolute;
                    left: 50%;
                    top: 30px;
                    transform: translateX(-50%);
                ">달러 갭 비율: {mid_gap:.4f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def create_fair_rate_indicator(title: str, current_rate: float, fair_rate: float):
    """
    적정환율 지표를 생성합니다 (position indicator 스타일).
    
    Args:
        title: 지표 제목
        current_rate: 현재 환율
        fair_rate: 적정 환율
    """
    st.markdown(f"### {title}")
    
    # O/X 표시 로직 (현재 환율이 적정 환율보다 낮으면 O)
    is_good = current_rate < fair_rate
    ox_symbol = "O" if is_good else "X"
    ox_color = COLORS['success'] if is_good else COLORS['error']
    
    # 범위 계산 (적정환율 기준 ±10%)
    rate_range = fair_rate * 0.1
    low_display = fair_rate - rate_range
    high_display = fair_rate + rate_range
    
    # 위치 계산
    if high_display != low_display:
        position_percent = ((current_rate - low_display) / (high_display - low_display)) * 100
        position_percent = max(0, min(100, position_percent))
    else:
        position_percent = 50
    
    st.markdown(f"""
    <style>
    .fair-rate-container {{
        display: flex;
        align-items: center;
        gap: 15px;
        margin: 12px 0;
        background: {COLORS['background_primary']};
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }}
    .fair-rate-ox {{
        font-size: 36px;
        color: {ox_color};
        flex-shrink: 0;
        font-weight: 700;
    }}
    .fair-rate-bar {{
        background: linear-gradient(to right, {COLORS['success']} 0%, {COLORS['warning']} 50%, {COLORS['error']} 100%);
        height: 24px;
        border-radius: 12px;
        position: relative;
        border: 2px solid {COLORS['gray_300']};
    }}
    .fair-rate-value {{
        font-size: 14px;
        font-weight: 600;
        color: {COLORS['text_primary']};
        white-space: nowrap;
    }}
    
    @media (max-width: 768px) {{
        .fair-rate-container {{
            gap: 10px;
            padding: 12px;
            margin: 8px 0;
        }}
        .fair-rate-ox {{
            font-size: 24px;
        }}
        .fair-rate-bar {{
            height: 20px;
        }}
        .fair-rate-value {{
            font-size: 11px;
        }}
    }}
    </style>
    <div class="fair-rate-container">
        <div class="fair-rate-ox">
            {ox_symbol}
        </div>
        <div style="flex-grow: 1;">
            <div class="fair-rate-bar">
                <!-- 적정환율 마커 (중간) -->
                <div style="
                    position: absolute;
                    left: 50%;
                    top: -4px;
                    width: 0;
                    height: 0;
                    border-left: 6px solid transparent;
                    border-right: 6px solid transparent;
                    border-top: 12px solid {COLORS['error']};
                    transform: translateX(-50%);
                "></div>
                <!-- 현재환율 마커 -->
                <div style="
                    position: absolute;
                    left: {position_percent}%;
                    top: -4px;
                    width: 0;
                    height: 0;
                    border-left: 6px solid transparent;
                    border-right: 6px solid transparent;
                    border-top: 12px solid {COLORS['text_primary']};
                    transform: translateX(-50%);
                "></div>
                <!-- 라벨들 -->
                <div class="fair-rate-value" style="
                    position: absolute;
                    left: {position_percent}%;
                    top: -24px;
                    transform: translateX(-50%);
                ">현재 환율: {current_rate:.2f}</div>
                <div class="fair-rate-value" style="
                    position: absolute;
                    left: 50%;
                    top: 30px;
                    transform: translateX(-50%);
                ">적정 환율: {fair_rate:.2f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

