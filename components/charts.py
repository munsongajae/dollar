"""
차트 생성 컴포넌트
"""
import plotly.graph_objects as go
import pandas as pd


def create_dxy_chart(dxy_close: pd.Series, current_dxy: float, dxy_52w_high: float, 
                     dxy_52w_low: float, dxy_52w_mid: float, period_name: str = "1년"):
    """달러 인덱스 차트를 생성합니다."""
    fig = go.Figure()
    
    # 인덱스를 날짜 형식으로 변환
    dates = pd.to_datetime(dxy_close.index).tz_localize(None)
    
    # 52주 달러 인덱스 라인
    fig.add_trace(go.Scatter(
        x=dates,
        y=dxy_close.values,
        mode='lines',
        name='DXY',
        line=dict(color='#3182F6', width=2)
    ))
    
    # 현재 가격 라인
    fig.add_hline(
        y=current_dxy,
        line_dash="dash",
        line_color="#F04452",
        annotation_text=f"현재: {current_dxy:.2f}",
        annotation_position="bottom right"
    )
    
    # 52주 최고가 라인
    fig.add_hline(
        y=dxy_52w_high,
        line_dash="dot",
        line_color="#00C471",
        annotation_text=f"최고: {dxy_52w_high:.2f}",
        annotation_position="top right"
    )
    
    # 52주 최저가 라인
    fig.add_hline(
        y=dxy_52w_low,
        line_dash="dot",
        line_color="#FFA500",
        annotation_text=f"최저: {dxy_52w_low:.2f}",
        annotation_position="bottom right"
    )
    
    # 52주 중간값 라인
    fig.add_hline(
        y=dxy_52w_mid,
        line_dash="dashdot",
        line_color="#8B95A1",
        annotation_text=f"중간: {dxy_52w_mid:.2f}",
        annotation_position="top left"
    )
    
    fig.update_layout(
        title=dict(
            text=f"💵 달러 인덱스 (DXY) {period_name} 차트",
            font=dict(size=16)
        ),
        xaxis_title="날짜",
        yaxis_title="DXY",
        hovermode='x unified',
        height=450,
        margin=dict(l=60, r=40, t=60, b=50),
        plot_bgcolor='#F9FAFB',
        paper_bgcolor='#FFFFFF',
        font=dict(family="Pretendard, sans-serif", color="#191F28", size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig


def create_jpy_krw_chart(jpy_krw_series: pd.Series, current_jpy_krw: float, 
                         jpy_krw_52w_high: float, jpy_krw_52w_low: float, 
                         jpy_krw_52w_mid: float, period_name: str = "1년"):
    """엔화 환율 차트를 생성합니다."""
    fig = go.Figure()
    
    # 인덱스를 날짜 형식으로 변환
    dates = pd.to_datetime(jpy_krw_series.index).tz_localize(None)
    
    # JPY/KRW 라인
    fig.add_trace(go.Scatter(
        x=dates,
        y=jpy_krw_series.values,
        mode='lines',
        name='JPY/KRW',
        line=dict(color='#3182F6', width=2)
    ))
    
    # 현재 가격 라인
    fig.add_hline(
        y=current_jpy_krw,
        line_dash="dash",
        line_color="#F04452",
        annotation_text=f"현재: {current_jpy_krw:.2f}",
        annotation_position="bottom right"
    )
    
    # 52주 최고가 라인
    fig.add_hline(
        y=jpy_krw_52w_high,
        line_dash="dot",
        line_color="#00C471",
        annotation_text=f"최고: {jpy_krw_52w_high:.2f}",
        annotation_position="top right"
    )
    
    # 52주 최저가 라인
    fig.add_hline(
        y=jpy_krw_52w_low,
        line_dash="dot",
        line_color="#FFA500",
        annotation_text=f"최저: {jpy_krw_52w_low:.2f}",
        annotation_position="bottom right"
    )
    
    # 52주 중간값 라인
    fig.add_hline(
        y=jpy_krw_52w_mid,
        line_dash="dashdot",
        line_color="#8B95A1",
        annotation_text=f"중간: {jpy_krw_52w_mid:.2f}",
        annotation_position="top left"
    )
    
    fig.update_layout(
        title=dict(
            text=f"💴 엔화 환율 (JPY/KRW) {period_name} 차트",
            font=dict(size=16)
        ),
        xaxis_title="날짜",
        yaxis_title="JPY/KRW (원)",
        hovermode='x unified',
        height=450,
        margin=dict(l=60, r=40, t=60, b=50),
        plot_bgcolor='#F9FAFB',
        paper_bgcolor='#FFFFFF',
        font=dict(family="Pretendard, sans-serif", color="#191F28", size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig


def create_usd_krw_chart(usd_krw_series: pd.Series, current_usd_krw: float, 
                         usd_krw_52w_high: float, usd_krw_52w_low: float, 
                         usd_krw_52w_mid: float, period_name: str = "1년"):
    """원화 환율 차트를 생성합니다."""
    fig = go.Figure()
    
    # 인덱스를 날짜 형식으로 변환
    dates = pd.to_datetime(usd_krw_series.index).tz_localize(None)
    
    # USD/KRW 라인
    fig.add_trace(go.Scatter(
        x=dates,
        y=usd_krw_series.values,
        mode='lines',
        name='USD/KRW',
        line=dict(color='#3182F6', width=2)
    ))
    
    # 현재 가격 라인
    fig.add_hline(
        y=current_usd_krw,
        line_dash="dash",
        line_color="#F04452",
        annotation_text=f"현재: {current_usd_krw:.2f}",
        annotation_position="bottom right"
    )
    
    # 52주 최고가 라인
    fig.add_hline(
        y=usd_krw_52w_high,
        line_dash="dot",
        line_color="#00C471",
        annotation_text=f"최고: {usd_krw_52w_high:.2f}",
        annotation_position="top right"
    )
    
    # 52주 최저가 라인
    fig.add_hline(
        y=usd_krw_52w_low,
        line_dash="dot",
        line_color="#FFA500",
        annotation_text=f"최저: {usd_krw_52w_low:.2f}",
        annotation_position="bottom right"
    )
    
    # 52주 중간값 라인
    fig.add_hline(
        y=usd_krw_52w_mid,
        line_dash="dashdot",
        line_color="#8B95A1",
        annotation_text=f"중간: {usd_krw_52w_mid:.2f}",
        annotation_position="top left"
    )
    
    fig.update_layout(
        title=dict(
            text=f"💵 달러 환율 (USD/KRW) {period_name} 차트",
            font=dict(size=16)
        ),
        xaxis_title="날짜",
        yaxis_title="USD/KRW (원)",
        hovermode='x unified',
        height=450,
        margin=dict(l=60, r=40, t=60, b=50),
        plot_bgcolor='#F9FAFB',
        paper_bgcolor='#FFFFFF',
        font=dict(family="Pretendard, sans-serif", color="#191F28", size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

