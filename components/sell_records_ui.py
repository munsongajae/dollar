"""
매도 기록 관리 UI 컴포넌트
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import datetime
from database import dollar_db, jpy_db
from utils.formatters import format_currency, format_percentage
from config.settings import COLORS


def display_sell_records_tab():
    """통합 매도 기록 탭 UI"""
    # 통화 선택
    col_currency, col_period, col_spacer = st.columns([1, 1, 3])
    
    with col_currency:
        currency = st.radio(
            "💱 통화 선택",
            options=["💵 달러", "💴 엔화"],
            horizontal=True,
            key="sell_records_currency"
        )
    
    # 선택된 통화에 따라 해당 탭 표시
    if currency == "💵 달러":
        _display_dollar_sell_records(col_period)
    else:
        _display_jpy_sell_records(col_period)


def _display_dollar_sell_records(col_period):
    """달러 매도 기록 표시 (내부 함수)"""
    st.subheader("💰 달러 매도 기록")
    
    # 모바일 반응형 스타일 추가
    st.markdown("""
    <style>
    .sell-record-card {
        background: white;
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    
    @media (max-width: 768px) {
        .sell-record-card {
            padding: 0.75rem;
        }
        
        /* 현황판 컬럼을 모바일에서 2열로 */
        [data-testid="column"] {
            min-width: 50% !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 기간 선택
    with col_period:
        period_options = {"1개월": 30, "3개월": 90, "6개월": 180, "1년": 365, "전체": None, "사용자 지정": "custom"}
        selected_period = st.selectbox(
            "📅 조회 기간",
            options=list(period_options.keys()),
            index=3,  # 1년
            key="dollar_sell_period"
        )
        period_days = period_options[selected_period]
    
    # 사용자 지정 기간 입력
    start_date = None
    end_date = None
    if period_days == "custom":
        # 날짜 입력 반응형 스타일
        st.markdown("""
        <style>
        /* 날짜 입력 레이블 간결하게 */
        label[data-testid="stWidgetLabel"] {
            font-size: 0.875rem;
        }
        
        @media (max-width: 640px) {
            /* 모바일에서 날짜 입력 세로 배치 */
            div[data-testid="column"] {
                width: 100% !important;
                flex: none !important;
            }
        }
        </style>
        """, unsafe_allow_html=True)
        
        col_start, col_end = st.columns(2)
        with col_start:
            start_date = st.date_input(
                "시작일",
                value=datetime.datetime.now() - datetime.timedelta(days=365),
                key="dollar_sell_start_date"
            )
        with col_end:
            end_date = st.date_input(
                "종료일",
                value=datetime.datetime.now(),
                key="dollar_sell_end_date"
            )
    
    # 매도 기록 로드
    sell_records = st.session_state.get('sell_records', [])
    
    # 기간 필터링
    if sell_records:
        if period_days == "custom" and start_date and end_date:
            # 사용자 지정 기간 필터링
            start_dt = datetime.datetime.combine(start_date, datetime.time.min)
            end_dt = datetime.datetime.combine(end_date, datetime.time.max)
            filtered_records = []
            for record in sell_records:
                try:
                    sell_dt = datetime.datetime.fromisoformat(record['sell_date'])
                    if sell_dt.tzinfo is not None:
                        sell_dt = sell_dt.replace(tzinfo=None)
                    if start_dt <= sell_dt <= end_dt:
                        filtered_records.append(record)
                except:
                    filtered_records.append(record)
            sell_records = filtered_records
        elif period_days and period_days != "custom":
            # 기존 방식: N일 이전부터
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=period_days)
            filtered_records = []
            for record in sell_records:
                try:
                    sell_dt = datetime.datetime.fromisoformat(record['sell_date'])
                    if sell_dt.tzinfo is not None:
                        sell_dt = sell_dt.replace(tzinfo=None)
                    if sell_dt >= cutoff_date:
                        filtered_records.append(record)
                except:
                    filtered_records.append(record)
            sell_records = filtered_records
    
    if not sell_records:
        st.info("매도 기록이 없습니다.")
        return
    
    # 종합 통계 계산
    total_sell_krw = sum(record['sell_krw'] for record in sell_records)
    total_sell_usd = sum(record['sell_amount'] for record in sell_records)
    total_profit_krw = sum(record['profit_krw'] for record in sell_records)
    
    # 평균 매수/매도 환율 계산
    total_purchase_krw = sum(record['sell_amount'] * record['purchase_rate'] for record in sell_records)
    avg_purchase_rate = total_purchase_krw / total_sell_usd if total_sell_usd > 0 else 0
    avg_sell_rate = total_sell_krw / total_sell_usd if total_sell_usd > 0 else 0
    profit_rate = (total_profit_krw / total_purchase_krw * 100) if total_purchase_krw > 0 else 0
    
    # 현황판 HTML 테이블 생성
    profit_sign = "+" if total_profit_krw >= 0 else ""
    profit_color = COLORS['success'] if total_profit_krw >= 0 else COLORS['error']
    
    summary_html = f"""
    <style>
    .sell-summary-table {{
        width: 100%;
        margin-bottom: 1.5rem;
    }}
    .sell-summary-row {{
        display: flex;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
    }}
    .sell-summary-metric {{
        background: {COLORS['background_primary']};
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        border: 1px solid {COLORS['gray_200']};
        flex: 1;
    }}
    .sell-summary-label {{
        font-size: 0.875rem;
        color: {COLORS['text_secondary']};
        font-weight: 500;
        margin-bottom: 0.5rem;
    }}
    .sell-summary-value {{
        font-size: 1.5rem;
        color: {COLORS['text_primary']};
        font-weight: 700;
        letter-spacing: -0.02em;
    }}
    .sell-summary-delta {{
        font-size: 0.875rem;
        color: {profit_color};
        margin-top: 0.25rem;
    }}
    
    @media (max-width: 768px) {{
        .sell-summary-row {{
            flex-wrap: wrap;
        }}
        .sell-summary-metric {{
            padding: 0.75rem;
        }}
        .sell-summary-label {{
            font-size: 0.7rem;
            white-space: nowrap;
        }}
        .sell-summary-value {{
            font-size: 1rem;
        }}
        .sell-summary-delta {{
            font-size: 0.7rem;
        }}
        /* 첫 행 3개 */
        .sell-summary-row:first-child .sell-summary-metric {{
            flex: 0 0 calc(33.33% - 0.35rem);
        }}
        /* 두 번째 행 2개 */
        .sell-summary-row:last-child .sell-summary-metric {{
            flex: 0 0 calc(50% - 0.25rem);
        }}
    }}
    </style>
    
    <div class="sell-summary-table">
        <!-- 첫 행: 3개 항목 -->
        <div class="sell-summary-row">
            <div class="sell-summary-metric">
                <div class="sell-summary-label">총 매도금액</div>
                <div class="sell-summary-value">{int(total_sell_krw):,}원</div>
            </div>
            <div class="sell-summary-metric">
                <div class="sell-summary-label">총 매도 달러</div>
                <div class="sell-summary-value">{int(total_sell_usd):,} USD</div>
            </div>
            <div class="sell-summary-metric">
                <div class="sell-summary-label">확정 손익</div>
                <div class="sell-summary-value">{profit_sign}{int(total_profit_krw):,}원</div>
                <div class="sell-summary-delta">{profit_sign}{profit_rate:.2f}%</div>
            </div>
        </div>
        <!-- 두 번째 행: 2개 항목 -->
        <div class="sell-summary-row">
            <div class="sell-summary-metric">
                <div class="sell-summary-label">평균 매수가</div>
                <div class="sell-summary-value">{avg_purchase_rate:,.2f}원</div>
            </div>
            <div class="sell-summary-metric">
                <div class="sell-summary-label">평균 매도가</div>
                <div class="sell-summary-value">{avg_sell_rate:,.2f}원</div>
            </div>
        </div>
    </div>
    """
    
    st.markdown(summary_html, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 개별 매도 기록 리스트
    st.markdown("### 📋 개별 매도 내역")
    
    for record in sell_records:
        # 날짜 포맷
        try:
            sell_dt = datetime.datetime.fromisoformat(record['sell_date'])
            formatted_date = sell_dt.strftime('%Y-%m-%d %H:%M')
        except:
            formatted_date = record['sell_date'][:16]
        
        profit_rate_individual = ((record['sell_rate'] - record['purchase_rate']) / record['purchase_rate'] * 100) if record['purchase_rate'] > 0 else 0
        profit_sign = "+" if record['profit_krw'] >= 0 else ""
        profit_color_hex = COLORS['success'] if record['profit_krw'] >= 0 else COLORS['error']
        
        # HTML 테이블로 2열 매도 기록 카드 생성
        sell_card_html = f"""
        <div style="background: {COLORS['background_primary']}; border-radius: 12px; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); border: 1px solid {COLORS['gray_200']};">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="width: 50%; padding: 0.5rem; vertical-align: top;">
                        <div style="font-size: 1rem; font-weight: 700; color: {COLORS['text_primary']}; margin-bottom: 0.5rem;">#{record['investment_number']} {record.get('exchange_name', '-')}</div>
                        <div style="font-size: 0.875rem; color: {COLORS['text_secondary']}; margin: 0.25rem 0;">📅 {formatted_date}</div>
                        <div style="font-size: 0.875rem; color: {COLORS['text_secondary']}; margin: 0.25rem 0;">💵 {record['sell_amount']:.2f} USD</div>
                    </td>
                    <td style="width: 50%; padding: 0.5rem; vertical-align: top;">
                        <div style="margin: 0.5rem 0;">
                            <div style="font-size: 0.75rem; color: {COLORS['text_secondary']}; margin-bottom: 0.25rem;">매수가 → 매도가</div>
                            <div style="font-size: 0.875rem; color: {COLORS['text_primary']}; margin-bottom: 0.5rem;">{record['purchase_rate']:,.2f}원 → <strong>{record['sell_rate']:,.2f}원</strong></div>
                            <div style="font-size: 0.75rem; color: {COLORS['text_secondary']}; margin-bottom: 0.25rem;">매도금액</div>
                            <div style="font-size: 1.2rem; font-weight: 700; color: {COLORS['text_primary']};">{int(record['sell_krw']):,}원</div>
                            <div style="font-size: 0.875rem; color: {profit_color_hex}; font-weight: 600; margin-top: 0.25rem;">
                                {profit_sign}{profit_rate_individual:.2f}% ({profit_sign}{int(record['profit_krw']):,}원)
                            </div>
                        </div>
                    </td>
                </tr>
            </table>
        </div>
        """
        
        components.html(sell_card_html, height=180)
        
        # 삭제 버튼
        if st.button("🗑️ 삭제", key=f"dollar_sell_delete_{record['id']}", use_container_width=True):
            if dollar_db.delete_dollar_sell_record(record['id']):
                # 세션 스테이트 갱신
                from database.dollar_db import load_dollar_sell_records
                st.session_state.sell_records = load_dollar_sell_records() or []
                st.success(f"매도 기록 #{record['investment_number']}가 삭제되었습니다.")
                st.rerun()
            else:
                st.error("삭제 실패")
        
        st.markdown("---")


def _display_jpy_sell_records(col_period):
    """엔화 매도 기록 표시 (내부 함수)"""
    st.subheader("💴 엔화 매도 기록")
    
    # 모바일 반응형 스타일 추가
    st.markdown("""
    <style>
    .sell-record-card {
        background: white;
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    
    @media (max-width: 768px) {
        .sell-record-card {
            padding: 0.75rem;
        }
        
        /* 현황판 컬럼을 모바일에서 2열로 */
        [data-testid="column"] {
            min-width: 50% !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 기간 선택
    with col_period:
        period_options = {"1개월": 30, "3개월": 90, "6개월": 180, "1년": 365, "전체": None, "사용자 지정": "custom"}
        selected_period = st.selectbox(
            "📅 조회 기간",
            options=list(period_options.keys()),
            index=3,  # 1년
            key="jpy_sell_period"
        )
        period_days = period_options[selected_period]
    
    # 사용자 지정 기간 입력
    start_date = None
    end_date = None
    if period_days == "custom":
        # 날짜 입력 반응형 스타일
        st.markdown("""
        <style>
        /* 날짜 입력 레이블 간결하게 */
        label[data-testid="stWidgetLabel"] {
            font-size: 0.875rem;
        }
        
        @media (max-width: 640px) {
            /* 모바일에서 날짜 입력 세로 배치 */
            div[data-testid="column"] {
                width: 100% !important;
                flex: none !important;
            }
        }
        </style>
        """, unsafe_allow_html=True)
        
        col_start, col_end = st.columns(2)
        with col_start:
            start_date = st.date_input(
                "시작일",
                value=datetime.datetime.now() - datetime.timedelta(days=365),
                key="jpy_sell_start_date"
            )
        with col_end:
            end_date = st.date_input(
                "종료일",
                value=datetime.datetime.now(),
                key="jpy_sell_end_date"
            )
    
    # 매도 기록 로드
    sell_records = st.session_state.get('jpy_sell_records', [])
    
    # 기간 필터링
    if sell_records:
        if period_days == "custom" and start_date and end_date:
            # 사용자 지정 기간 필터링
            start_dt = datetime.datetime.combine(start_date, datetime.time.min)
            end_dt = datetime.datetime.combine(end_date, datetime.time.max)
            filtered_records = []
            for record in sell_records:
                try:
                    sell_dt = datetime.datetime.fromisoformat(record['sell_date'])
                    if sell_dt.tzinfo is not None:
                        sell_dt = sell_dt.replace(tzinfo=None)
                    if start_dt <= sell_dt <= end_dt:
                        filtered_records.append(record)
                except:
                    filtered_records.append(record)
            sell_records = filtered_records
        elif period_days and period_days != "custom":
            # 기존 방식: N일 이전부터
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=period_days)
            filtered_records = []
            for record in sell_records:
                try:
                    sell_dt = datetime.datetime.fromisoformat(record['sell_date'])
                    if sell_dt.tzinfo is not None:
                        sell_dt = sell_dt.replace(tzinfo=None)
                    if sell_dt >= cutoff_date:
                        filtered_records.append(record)
                except:
                    filtered_records.append(record)
            sell_records = filtered_records
    
    if not sell_records:
        st.info("매도 기록이 없습니다.")
        return
    
    # 종합 통계 계산
    total_sell_krw = sum(record['sell_krw'] for record in sell_records)
    total_sell_jpy = sum(record['sell_amount'] for record in sell_records)
    total_profit_krw = sum(record['profit_krw'] for record in sell_records)
    
    # 평균 매수/매도 환율 계산
    total_purchase_krw = sum(record['sell_amount'] * record['purchase_rate'] for record in sell_records)
    avg_purchase_rate = total_purchase_krw / total_sell_jpy if total_sell_jpy > 0 else 0
    avg_sell_rate = total_sell_krw / total_sell_jpy if total_sell_jpy > 0 else 0
    profit_rate = (total_profit_krw / total_purchase_krw * 100) if total_purchase_krw > 0 else 0
    
    # 현황판 HTML 테이블 생성
    profit_sign = "+" if total_profit_krw >= 0 else ""
    profit_color = COLORS['success'] if total_profit_krw >= 0 else COLORS['error']
    
    summary_html = f"""
    <style>
    .sell-summary-table-jpy {{
        width: 100%;
        margin-bottom: 1.5rem;
    }}
    .sell-summary-row-jpy {{
        display: flex;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
    }}
    .sell-summary-metric-jpy {{
        background: {COLORS['background_primary']};
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        border: 1px solid {COLORS['gray_200']};
        flex: 1;
    }}
    .sell-summary-label-jpy {{
        font-size: 0.875rem;
        color: {COLORS['text_secondary']};
        font-weight: 500;
        margin-bottom: 0.5rem;
    }}
    .sell-summary-value-jpy {{
        font-size: 1.5rem;
        color: {COLORS['text_primary']};
        font-weight: 700;
        letter-spacing: -0.02em;
    }}
    .sell-summary-delta-jpy {{
        font-size: 0.875rem;
        color: {profit_color};
        margin-top: 0.25rem;
    }}
    
    @media (max-width: 768px) {{
        .sell-summary-row-jpy {{
            flex-wrap: wrap;
        }}
        .sell-summary-metric-jpy {{
            padding: 0.75rem;
        }}
        .sell-summary-label-jpy {{
            font-size: 0.7rem;
            white-space: nowrap;
        }}
        .sell-summary-value-jpy {{
            font-size: 1rem;
        }}
        .sell-summary-delta-jpy {{
            font-size: 0.7rem;
        }}
        /* 첫 행 3개 */
        .sell-summary-row-jpy:first-child .sell-summary-metric-jpy {{
            flex: 0 0 calc(33.33% - 0.35rem);
        }}
        /* 두 번째 행 2개 */
        .sell-summary-row-jpy:last-child .sell-summary-metric-jpy {{
            flex: 0 0 calc(50% - 0.25rem);
        }}
    }}
    </style>
    
    <div class="sell-summary-table-jpy">
        <!-- 첫 행: 3개 항목 -->
        <div class="sell-summary-row-jpy">
            <div class="sell-summary-metric-jpy">
                <div class="sell-summary-label-jpy">총 매도금액</div>
                <div class="sell-summary-value-jpy">{int(total_sell_krw):,}원</div>
            </div>
            <div class="sell-summary-metric-jpy">
                <div class="sell-summary-label-jpy">총 매도 엔화</div>
                <div class="sell-summary-value-jpy">{int(total_sell_jpy):,} JPY</div>
            </div>
            <div class="sell-summary-metric-jpy">
                <div class="sell-summary-label-jpy">확정 손익</div>
                <div class="sell-summary-value-jpy">{profit_sign}{int(total_profit_krw):,}원</div>
                <div class="sell-summary-delta-jpy">{profit_sign}{profit_rate:.2f}%</div>
            </div>
        </div>
        <!-- 두 번째 행: 2개 항목 -->
        <div class="sell-summary-row-jpy">
            <div class="sell-summary-metric-jpy">
                <div class="sell-summary-label-jpy">평균 매수가</div>
                <div class="sell-summary-value-jpy">{avg_purchase_rate:.4f}원</div>
            </div>
            <div class="sell-summary-metric-jpy">
                <div class="sell-summary-label-jpy">평균 매도가</div>
                <div class="sell-summary-value-jpy">{avg_sell_rate:.4f}원</div>
            </div>
        </div>
    </div>
    """
    
    st.markdown(summary_html, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 개별 매도 기록 리스트
    st.markdown("### 📋 개별 매도 내역")
    
    for record in sell_records:
        # 날짜 포맷
        try:
            sell_dt = datetime.datetime.fromisoformat(record['sell_date'])
            formatted_date = sell_dt.strftime('%Y-%m-%d %H:%M')
        except:
            formatted_date = record['sell_date'][:16]
        
        profit_rate_individual = ((record['sell_rate'] - record['purchase_rate']) / record['purchase_rate'] * 100) if record['purchase_rate'] > 0 else 0
        profit_sign = "+" if record['profit_krw'] >= 0 else ""
        profit_color_hex = COLORS['success'] if record['profit_krw'] >= 0 else COLORS['error']
        
        # HTML 테이블로 2열 매도 기록 카드 생성 (엔화)
        sell_card_html = f"""
        <div style="background: {COLORS['background_primary']}; border-radius: 12px; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); border: 1px solid {COLORS['gray_200']};">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="width: 50%; padding: 0.5rem; vertical-align: top;">
                        <div style="font-size: 1rem; font-weight: 700; color: {COLORS['text_primary']}; margin-bottom: 0.5rem;">#{record['investment_number']} {record.get('exchange_name', '-')}</div>
                        <div style="font-size: 0.875rem; color: {COLORS['text_secondary']}; margin: 0.25rem 0;">📅 {formatted_date}</div>
                        <div style="font-size: 0.875rem; color: {COLORS['text_secondary']}; margin: 0.25rem 0;">💴 {record['sell_amount']:.2f} JPY</div>
                    </td>
                    <td style="width: 50%; padding: 0.5rem; vertical-align: top;">
                        <div style="margin: 0.5rem 0;">
                            <div style="font-size: 0.75rem; color: {COLORS['text_secondary']}; margin-bottom: 0.25rem;">매수가 → 매도가</div>
                            <div style="font-size: 0.875rem; color: {COLORS['text_primary']}; margin-bottom: 0.5rem;">{record['purchase_rate']:.4f}원 → <strong>{record['sell_rate']:.4f}원</strong></div>
                            <div style="font-size: 0.75rem; color: {COLORS['text_secondary']}; margin-bottom: 0.25rem;">매도금액</div>
                            <div style="font-size: 1.2rem; font-weight: 700; color: {COLORS['text_primary']};">{int(record['sell_krw']):,}원</div>
                            <div style="font-size: 0.875rem; color: {profit_color_hex}; font-weight: 600; margin-top: 0.25rem;">
                                {profit_sign}{profit_rate_individual:.2f}% ({profit_sign}{int(record['profit_krw']):,}원)
                            </div>
                        </div>
                    </td>
                </tr>
            </table>
        </div>
        """
        
        components.html(sell_card_html, height=180)
        
        # 삭제 버튼
        if st.button("🗑️ 삭제", key=f"jpy_sell_delete_{record['id']}", use_container_width=True):
            if jpy_db.delete_jpy_sell_record(record['id']):
                # 세션 스테이트 갱신
                from database.jpy_db import load_jpy_sell_records
                st.session_state.jpy_sell_records = load_jpy_sell_records() or []
                st.success(f"매도 기록 #{record['investment_number']}가 삭제되었습니다.")
                st.rerun()
            else:
                st.error("삭제 실패")
        
        st.markdown("---")

