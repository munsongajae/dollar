"""
토스 스타일의 커스텀 UI 컴포넌트
"""
import streamlit as st
from config.settings import COLORS


def inject_custom_styles():
    """
    토스 스타일의 커스텀 CSS를 앱에 주입합니다.
    """
    st.markdown(f"""
    <style>
    /* 전역 폰트 및 배경 */
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    html, body, [class*="css"] {{
        font-family: "Pretendard", -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
        background-color: {COLORS['background_secondary']};
        font-size: 16px; /* 기본 폰트 크기 설정 */
    }}
    
    /* 기본 텍스트 크기 */
    p, span, div, label {{
        font-size: 1rem; /* 16px */
        line-height: 1.6;
    }}
    
    /* 메인 컨테이너 */
    .main .block-container {{
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }}
    
    /* 제목 스타일 */
    h1 {{
        color: {COLORS['text_primary']};
        font-weight: 700;
        letter-spacing: -0.02em;
        margin-bottom: 0.5rem;
    }}
    
    h2 {{
        color: {COLORS['text_primary']};
        font-weight: 600;
        letter-spacing: -0.01em;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }}
    
    h3 {{
        color: {COLORS['text_secondary']};
        font-weight: 600;
        letter-spacing: -0.01em;
    }}
    
    /* 카드 스타일 (토스 스타일) */
    .stCard {{
        background: {COLORS['background_primary']};
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        border: 1px solid {COLORS['gray_200']};
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    
    .stCard:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
    }}
    
    /* 메트릭 카드 개선 */
    [data-testid="stMetricValue"] {{
        font-size: 2.5rem;
        font-weight: 700;
        color: {COLORS['text_primary']};
        letter-spacing: -0.02em;
    }}
    
    [data-testid="stMetricLabel"] {{
        font-size: 0.875rem;
        color: {COLORS['text_secondary']};
        font-weight: 500;
    }}
    
    [data-testid="stMetricDelta"] {{
        font-size: 1rem;
        font-weight: 600;
    }}
    
    /* 버튼 스타일 (토스 스타일) */
    .stButton > button {{
        background: {COLORS['primary']};
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.2s ease;
        box-shadow: 0 2px 8px rgba(49, 130, 246, 0.2);
    }}
    
    .stButton > button:hover {{
        background: #1B64DA;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(49, 130, 246, 0.3);
    }}
    
    .stButton > button:active {{
        transform: translateY(0);
    }}
    
    /* 입력 필드 스타일 */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div {{
        border-radius: 8px;
        border: 1px solid {COLORS['gray_300']};
        padding: 10px 14px;
        font-size: 1rem;
        transition: border-color 0.2s ease;
    }}
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {{
        border-color: {COLORS['primary']};
        box-shadow: 0 0 0 3px rgba(49, 130, 246, 0.1);
    }}
    
    /* 탭 스타일 개선 */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: {COLORS['gray_100']};
        border-radius: 12px;
        padding: 4px;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 600;
        color: {COLORS['text_secondary']};
        border: none;
        background-color: transparent;
        transition: all 0.2s ease;
    }}
    
    .stTabs [aria-selected="true"] {{
        background-color: {COLORS['background_primary']};
        color: {COLORS['primary']};
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }}
    
    /* 사이드바 스타일 */
    [data-testid="stSidebar"] {{
        background-color: {COLORS['background_primary']};
        padding: 2rem 1rem;
    }}
    
    [data-testid="stSidebar"] .stMetric {{
        background: {COLORS['gray_100']};
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }}
    
    /* 데이터프레임 스타일 */
    .stDataFrame {{
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }}
    
    /* 프로그레스 바 */
    .stProgress > div > div > div {{
        background-color: {COLORS['primary']};
        border-radius: 4px;
    }}
    
    /* 성공 메시지 */
    .stSuccess {{
        background-color: rgba(0, 196, 113, 0.1);
        color: {COLORS['success']};
        border-left: 4px solid {COLORS['success']};
        border-radius: 8px;
        padding: 16px;
    }}
    
    /* 에러 메시지 */
    .stError {{
        background-color: rgba(240, 68, 82, 0.1);
        color: {COLORS['error']};
        border-left: 4px solid {COLORS['error']};
        border-radius: 8px;
        padding: 16px;
    }}
    
    /* 경고 메시지 */
    .stWarning {{
        background-color: rgba(255, 165, 0, 0.1);
        color: {COLORS['warning']};
        border-left: 4px solid {COLORS['warning']};
        border-radius: 8px;
        padding: 16px;
    }}
    
    /* 정보 메시지 */
    .stInfo {{
        background-color: rgba(49, 130, 246, 0.1);
        color: {COLORS['primary']};
        border-left: 4px solid {COLORS['primary']};
        border-radius: 8px;
        padding: 16px;
    }}
    
    /* 차트 컨테이너 */
    .js-plotly-plot {{
        border-radius: 16px;
        overflow: hidden;
    }}
    
    /* 스크롤바 스타일 */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}
    
    ::-webkit-scrollbar-track {{
        background: {COLORS['gray_100']};
        border-radius: 4px;
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: {COLORS['gray_300']};
        border-radius: 4px;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: {COLORS['gray_400']};
    }}
    
    /* 애니메이션 */
    @keyframes slideIn {{
        from {{
            opacity: 0;
            transform: translateY(20px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}
    
    .animate-in {{
        animation: slideIn 0.4s ease-out;
    }}
    
    /* ========================================
       모바일 반응형 스타일 (Phase 1)
       ======================================== */
    
    /* 모바일 (최대 768px) */
    @media (max-width: 768px) {{
        /* 기본 폰트 크기 증가 */
        html, body, [class*="css"] {{
            font-size: 18px; /* 모바일에서 기본 폰트 크기 증가 */
        }}
        
        /* 기본 텍스트 크기 */
        p, span, div, label {{
            font-size: 1.125rem; /* 18px */
        }}
        
        /* 메인 컨테이너 패딩 축소 */
        .main .block-container {{
            padding-top: 1rem;
            padding-bottom: 2rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }}
        
        /* 제목 크기 유지/증가 */
        h1 {{
            font-size: 2rem; /* 모바일에서도 크게 유지 */
            margin-bottom: 0.5rem;
        }}
        
        h2 {{
            font-size: 1.75rem; /* 크게 유지 */
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
        }}
        
        h3 {{
            font-size: 1.5rem; /* 크게 유지 */
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }}
        
        /* 메트릭 값 크기 증가 */
        [data-testid="stMetricValue"] {{
            font-size: 2.25rem !important; /* 모바일에서 더 크게 */
        }}
        
        [data-testid="stMetricLabel"] {{
            font-size: 0.9375rem !important; /* 15px - 더 크게 */
        }}
        
        [data-testid="stMetricDelta"] {{
            font-size: 1rem !important; /* 더 크게 */
        }}
        
        /* 카드 패딩 축소 */
        .stCard {{
            padding: 16px;
            border-radius: 12px;
        }}
        
        /* 버튼 터치 영역 확보 (최소 44px) */
        .stButton > button {{
            min-height: 44px;
            padding: 12px 20px;
            font-size: 1rem !important; /* 16px - 더 크게 */
            border-radius: 10px;
        }}
        
        /* 입력 필드 터치 친화적 */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div {{
            min-height: 44px;
            font-size: 18px !important; /* 모바일에서 더 크게 */
            padding: 12px;
        }}
        
        /* 탭 스타일 모바일 최적화 */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 4px;
            padding: 3px;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            padding: 8px 10px;
            font-size: 0.9375rem !important; /* 15px - 더 크게 */
            white-space: nowrap;
            min-width: auto;
            flex: 1;
        }}
        
        /* 이모지와 텍스트 사이 간격 축소 */
        .stTabs [data-baseweb="tab"] > div {{
            line-height: 1.2;
        }}
        
        /* 데이터프레임 가로 스크롤 */
        .stDataFrame {{
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }}
        
        /* 차트 컨테이너 - 모바일 최적화 */
        .js-plotly-plot {{
            max-width: 100%;
            height: 350px !important;
        }}
        
        .js-plotly-plot .plotly {{
            height: 350px !important;
        }}
        
        /* 차트 내부 텍스트 크기 유지 */
        .js-plotly-plot text {{
            font-size: 12px !important; /* 차트 텍스트도 조금 더 크게 */
        }}
        
        /* 차트 annotation 크기 유지 */
        .js-plotly-plot .annotation-text {{
            font-size: 11px !important; /* 차트 텍스트도 조금 더 크게 */
        }}
        
        /* 테이블 텍스트 크기 증가 */
        table, th, td {{
            font-size: 0.9375rem !important; /* 15px */
        }}
        
        /* Streamlit 기본 요소 텍스트 크기 */
        .stMarkdown {{
            font-size: 1.125rem !important; /* 18px */
        }}
        
        .element-container {{
            font-size: 1.125rem !important;
        }}
        
        /* 카드 내부 텍스트 크기 */
        .stCard p, .stCard span, .stCard div {{
            font-size: 1.0625rem !important; /* 17px */
        }}
    }}
    
    /* 태블릿 (768px ~ 1024px) */
    @media (min-width: 768px) and (max-width: 1024px) {{
        .main .block-container {{
            padding-top: 1.5rem;
            max-width: 900px;
        }}
        
        h1 {{
            font-size: 2rem;
        }}
        
        h2 {{
            font-size: 1.75rem;
        }}
        
        [data-testid="stMetricValue"] {{
            font-size: 2rem;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)


def create_metric_card(label: str, value: str, delta: str = None, delta_color: str = "normal") -> None:
    """
    토스 스타일의 메트릭 카드를 생성합니다.
    
    Args:
        label: 라벨 텍스트
        value: 메인 값
        delta: 변화량 (선택사항)
        delta_color: 변화량 색상 ("normal", "inverse", "off")
    """
    delta_html = ""
    if delta:
        delta_color_map = {
            "normal": COLORS['success'] if "+" in delta else COLORS['error'],
            "inverse": COLORS['error'] if "+" in delta else COLORS['success'],
            "off": COLORS['text_tertiary']
        }
        color = delta_color_map.get(delta_color, COLORS['text_tertiary'])
        delta_html = f'<div style="color: {color}; font-size: 1rem; font-weight: 600; margin-top: 8px;">{delta}</div>'
    
    st.markdown(f"""
    <div class="stCard animate-in" style="margin-bottom: 16px;">
        <div style="color: {COLORS['text_secondary']}; font-size: 0.875rem; font-weight: 500; margin-bottom: 8px;">
            {label}
        </div>
        <div style="color: {COLORS['text_primary']}; font-size: 2.5rem; font-weight: 700; letter-spacing: -0.02em;">
            {value}
        </div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def create_gradient_card(title: str, value: str, subtitle: str = None, gradient: str = "blue") -> None:
    """
    그라데이션 배경의 카드를 생성합니다 (토스 스타일).
    
    Args:
        title: 제목
        value: 메인 값
        subtitle: 부제목 (선택사항)
        gradient: 그라데이션 타입 ("blue", "green", "red")
    """
    gradient_map = {
        "blue": f"linear-gradient(135deg, {COLORS['primary']} 0%, #1B64DA 100%)",
        "green": f"linear-gradient(135deg, {COLORS['success']} 0%, #00A35E 100%)",
        "red": f"linear-gradient(135deg, {COLORS['error']} 0%, #D43644 100%)"
    }
    bg_gradient = gradient_map.get(gradient, gradient_map["blue"])
    
    subtitle_html = ""
    if subtitle:
        subtitle_html = f'<div style="color: rgba(255, 255, 255, 0.8); font-size: 0.875rem; margin-top: 8px;">{subtitle}</div>'
    
    st.markdown(f"""
    <div class="animate-in" style="
        background: {bg_gradient};
        border-radius: 16px;
        padding: 24px;
        color: white;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        margin-bottom: 16px;
    ">
        <div style="font-size: 0.875rem; font-weight: 500; margin-bottom: 8px; opacity: 0.9;">
            {title}
        </div>
        <div style="font-size: 2.5rem; font-weight: 700; letter-spacing: -0.02em;">
            {value}
        </div>
        {subtitle_html}
    </div>
    """, unsafe_allow_html=True)

