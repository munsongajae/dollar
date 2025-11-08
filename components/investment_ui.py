"""
투자 관리 UI 컴포넌트
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import datetime
from database import dollar_db, jpy_db
from services.exchange_rate import get_investing_usd_krw_for_portfolio, get_investing_jpy_krw_for_portfolio
from utils.formatters import format_currency, format_percentage
from config.settings import COLORS


def display_investment_tab():
    """통합 투자 관리 탭 UI"""
    # 통화 선택
    currency = st.radio(
        "💱 통화 선택",
        options=["💵 달러", "💴 엔화"],
        horizontal=True,
        key="investment_currency"
    )
    
    # 선택된 통화에 따라 해당 투자 관리 표시
    if currency == "💵 달러":
        display_dollar_investment_tab()
    else:
        display_jpy_investment_tab()


def calculate_dollar_portfolio_performance(investments):
    """달러 투자 포트폴리오 성과를 계산합니다."""
    if not investments:
        return {
            'total_purchase_krw': 0,
            'total_current_krw': 0,
            'total_profit_krw': 0,
            'total_profit_rate': 0,
            'current_rate': 0
        }
    
    current_rate = get_investing_usd_krw_for_portfolio()
    total_purchase_krw = sum(inv['purchase_krw'] for inv in investments)
    total_usd = sum(inv['usd_amount'] for inv in investments)
    total_current_krw = total_usd * current_rate if current_rate else 0
    total_profit_krw = total_current_krw - total_purchase_krw
    total_profit_rate = (total_profit_krw / total_purchase_krw * 100) if total_purchase_krw > 0 else 0
    
    return {
        'total_purchase_krw': total_purchase_krw,
        'total_current_krw': total_current_krw,
        'total_profit_krw': total_profit_krw,
        'total_profit_rate': total_profit_rate,
        'current_rate': current_rate
    }


def calculate_jpy_portfolio_performance(investments):
    """엔화 투자 포트폴리오 성과를 계산합니다."""
    if not investments:
        return {
            'total_purchase_krw': 0,
            'total_current_krw': 0,
            'total_profit_krw': 0,
            'total_profit_rate': 0,
            'current_rate': 0
        }
    
    current_rate = get_investing_jpy_krw_for_portfolio()
    total_purchase_krw = sum(inv['purchase_krw'] for inv in investments)
    total_jpy = sum(inv['jpy_amount'] for inv in investments)
    total_current_krw = total_jpy * current_rate if current_rate else 0
    total_profit_krw = total_current_krw - total_purchase_krw
    total_profit_rate = (total_profit_krw / total_purchase_krw * 100) if total_purchase_krw > 0 else 0
    
    return {
        'total_purchase_krw': total_purchase_krw,
        'total_current_krw': total_current_krw,
        'total_profit_krw': total_profit_krw,
        'total_profit_rate': total_profit_rate,
        'current_rate': current_rate
    }


def display_dollar_investment_tab():
    """달러 투자 관리 탭 UI"""
    # 포트폴리오 요약
    investments = st.session_state.get('dollar_investments', [])
    if investments:
        perf = calculate_dollar_portfolio_performance(investments)
        
        # HTML 테이블로 2x2 그리드 생성
        profit_sign = "+" if perf['total_profit_krw'] >= 0 else ""
        profit_color = COLORS['success'] if perf['total_profit_krw'] >= 0 else COLORS['error']
        
        portfolio_html = f"""
        <style>
        .portfolio-table {{
            width: 100%;
            display: table;
            border-collapse: collapse;
            margin-bottom: 1.5rem;
        }}
        .portfolio-row {{
            display: table-row;
        }}
        .portfolio-cell {{
            display: table-cell;
            width: 50%;
            padding: 0.5rem;
            vertical-align: top;
        }}
        .portfolio-metric {{
            background: {COLORS['background_primary']};
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 0.5rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
            border: 1px solid {COLORS['gray_200']};
        }}
        .portfolio-label {{
            font-size: 0.875rem;
            color: {COLORS['text_secondary']};
            font-weight: 500;
            margin-bottom: 0.5rem;
        }}
        .portfolio-value {{
            font-size: 1.5rem;
            color: {COLORS['text_primary']};
            font-weight: 700;
            letter-spacing: -0.02em;
        }}
        .portfolio-delta {{
            font-size: 0.875rem;
            color: {profit_color};
            margin-top: 0.25rem;
        }}
        
        @media (max-width: 768px) {{
            .portfolio-label {{
                font-size: 0.75rem;
            }}
            .portfolio-value {{
                font-size: 1.1rem;
            }}
            .portfolio-delta {{
                font-size: 0.75rem;
            }}
            .portfolio-metric {{
                padding: 0.75rem;
                margin-bottom: 0.4rem;
            }}
            .portfolio-cell {{
                padding: 0.25rem;
            }}
        }}
        </style>
        
        <div class="portfolio-table">
            <div class="portfolio-row">
                <div class="portfolio-cell">
                    <!-- 총 매수금액 -->
                    <div class="portfolio-metric">
                        <div class="portfolio-label">총 매수금액</div>
                        <div class="portfolio-value">{int(perf['total_purchase_krw']):,}원</div>
                    </div>
                </div>
                <div class="portfolio-cell">
                    <!-- 현재 평가금액 -->
                    <div class="portfolio-metric">
                        <div class="portfolio-label">현재 평가금액</div>
                        <div class="portfolio-value">{int(perf['total_current_krw']):,}원</div>
                    </div>
                </div>
            </div>
            <div class="portfolio-row">
                <div class="portfolio-cell">
                    <!-- 평가 손익 -->
                    <div class="portfolio-metric">
                        <div class="portfolio-label">평가 손익</div>
                        <div class="portfolio-value">{profit_sign}{int(perf['total_profit_krw']):,}원</div>
                        <div class="portfolio-delta">{profit_sign}{perf['total_profit_rate']:.2f}%</div>
                    </div>
                </div>
                <div class="portfolio-cell">
                    <!-- 현재 환율 -->
                    <div class="portfolio-metric">
                        <div class="portfolio-label">현재 환율</div>
                        <div class="portfolio-value">{perf['current_rate']:,.2f}원</div>
                    </div>
                </div>
            </div>
        </div>
        """
        
        st.markdown(portfolio_html, unsafe_allow_html=True)
        st.markdown("---")
    
    # 새 투자 추가 폼
    with st.expander("➕ 달러 투자 추가", expanded=False):
        # 반응형 폼 스타일
        st.markdown("""
        <style>
        /* 데스크톱: 2열 레이아웃 */
        @media (min-width: 769px) {
            div[data-testid="stForm"] > div > div {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 1rem;
            }
        }
        
        /* 모바일: 1열 레이아웃 */
        @media (max-width: 768px) {
            div[data-testid="stForm"] > div > div {
                display: block;
            }
            
            /* 제출 버튼 전체 너비 */
            div[data-testid="stForm"] button {
                width: 100% !important;
            }
        }
        </style>
        """, unsafe_allow_html=True)
        
        with st.form("add_dollar_investment_form"):
            # 반응형 컬럼 (CSS로 제어)
            col1, col2 = st.columns(2)
            with col1:
                investment_number = st.number_input("번호", min_value=1, value=1, step=1, key="dollar_investment_number")
                exchange_rate = st.number_input("매수 환율 (원/USD)", min_value=0.0, value=1300.0, step=0.1, format="%.2f", key="dollar_exchange_rate")
                usd_amount = st.number_input("매수 달러 (USD)", min_value=0.0, value=100.0, step=0.01, format="%.2f", key="dollar_usd_amount")
            with col2:
                exchange_name = st.text_input("거래소", value="빗썸", placeholder="빗썸, 업비트 등", key="dollar_exchange_name")
                memo = st.text_area("메모", placeholder="투자 목적 등", key="dollar_memo", height=100)
            
            submitted = st.form_submit_button("✅ 추가", type="primary", use_container_width=True)
            
            if submitted:
                if exchange_rate > 0 and usd_amount > 0:
                    investment_data = {
                        'investment_number': investment_number,
                        'purchase_date': datetime.datetime.now().isoformat(),
                        'exchange_rate': exchange_rate,
                        'usd_amount': usd_amount,
                        'exchange_name': exchange_name,
                        'memo': memo,
                        'purchase_krw': exchange_rate * usd_amount
                    }
                    success = dollar_db.save_dollar_investment(investment_data)
                    if success:
                        # 세션 스테이트 갱신
                        from database.dollar_db import load_dollar_investments
                        st.session_state.dollar_investments = load_dollar_investments() or []
                        st.success("✅ 투자가 추가되었습니다!")
                        st.rerun()
                    else:
                        st.error("❌ 투자 추가 실패")
                else:
                    st.error("❌ 환율과 금액을 확인하세요")
    
    # 투자 내역 카드
    if investments:
        st.subheader("📊 투자 내역")
        
        current_rate = get_investing_usd_krw_for_portfolio()
        
        for inv in investments:
            current_krw = inv['usd_amount'] * current_rate if current_rate else 0
            profit_krw = current_krw - inv['purchase_krw']
            profit_rate = (profit_krw / inv['purchase_krw'] * 100) if inv['purchase_krw'] > 0 else 0
            
            # 매수일시를 간단한 형식으로 변환
            purchase_date_str = inv['purchase_date']
            try:
                purchase_dt = datetime.datetime.fromisoformat(purchase_date_str)
                formatted_date = purchase_dt.strftime('%Y-%m-%d %H:%M')
            except:
                formatted_date = purchase_date_str[:16]
            
            # 수익률에 따른 색상
            profit_emoji = "🟢" if profit_krw >= 0 else "🔴"
            profit_color_hex = COLORS['success'] if profit_krw >= 0 else COLORS['error']
            profit_sign = "+" if profit_krw >= 0 else ""
            
            # HTML 테이블로 2열 투자 카드 생성
            memo_html = f"<div style='font-size: 0.875rem; color: {COLORS['text_secondary']}; margin: 0.25rem 0;'>📝 {inv.get('memo', '')}</div>" if inv.get('memo') else ""
            
            invest_card_html = f"""
            <div style="background: {COLORS['background_primary']}; border-radius: 12px; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); border: 1px solid {COLORS['gray_200']};">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="width: 50%; padding: 0.5rem; vertical-align: top;">
                            <div style="font-size: 1.1rem; font-weight: 700; color: {COLORS['text_primary']}; margin-bottom: 0.5rem;">#{inv['investment_number']} {inv['exchange_name']}</div>
                            <div style="font-size: 0.875rem; color: {COLORS['text_secondary']}; margin: 0.25rem 0;">📅 {formatted_date}</div>
                            {memo_html}
                            <div style="margin: 0.5rem 0;">
                                <div style="font-size: 0.75rem; color: {COLORS['text_secondary']}; margin-bottom: 0.25rem;">매수가</div>
                                <div style="font-size: 1.2rem; font-weight: 700; color: {COLORS['text_primary']};">{int(inv['exchange_rate']):,}원</div>
                                <div style="font-size: 0.875rem; color: {COLORS['text_secondary']}; margin-top: 0.25rem;">💵 {inv['usd_amount']:.2f} USD</div>
                            </div>
                        </td>
                        <td style="width: 50%; padding: 0.5rem; vertical-align: top;">
                            <div style="margin: 0.5rem 0;">
                                <div style="font-size: 0.75rem; color: {COLORS['text_secondary']}; margin-bottom: 0.25rem;">평가금액</div>
                                <div style="font-size: 1.2rem; font-weight: 700; color: {COLORS['text_primary']};">{int(current_krw):,}원</div>
                                <div style="font-size: 0.875rem; color: {profit_color_hex}; font-weight: 600; margin-top: 0.25rem;">
                                    {profit_emoji} {profit_sign}{profit_rate:.2f}% ({profit_sign}{int(profit_krw):,}원)
                                </div>
                            </div>
                        </td>
                    </tr>
                </table>
            </div>
            """
            
            components.html(invest_card_html, height=200)
            
            with st.container():
                # 액션 버튼 (2x2 그리드로 배치)
                st.markdown(f"""
                <style>
                .button-grid-{inv['id']} {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 0.5rem;
                    margin-bottom: 1rem;
                }}
                
                @media (max-width: 768px) {{
                    .button-grid-{inv['id']} {{
                        gap: 0.25rem;
                    }}
                }}
                </style>
                """, unsafe_allow_html=True)
                
                # 액션 버튼 (2열 배치)
                col_b1, col_b2 = st.columns(2)
                
                with col_b1:
                    # 삭제 버튼
                    if st.button("🗑️ 삭제", key=f"dollar_delete_{inv['id']}", use_container_width=True):
                        if dollar_db.delete_dollar_investment(inv['id']):
                            # 세션 스테이트 갱신
                            from database.dollar_db import load_dollar_investments
                            st.session_state.dollar_investments = load_dollar_investments() or []
                            st.success(f"투자 #{inv['investment_number']}가 삭제되었습니다.")
                            st.rerun()
                        else:
                            st.error("삭제 실패")
                    
                    # 전량매도 popover
                    with st.popover("💰 전량매도", use_container_width=True):
                        sell_rate_all = st.number_input(
                            "매도 환율 (원/USD)", 
                            min_value=0.0, 
                            value=current_rate if current_rate else 1300.0,
                            step=0.1,
                            key=f"dollar_sell_rate_all_{inv['id']}"
                        )
                        st.caption(f"전량: {inv['usd_amount']:.2f} USD")
                        
                        if st.button("전량 매도 실행", key=f"dollar_sell_all_exec_{inv['id']}", type="primary", use_container_width=True):
                            result = dollar_db.sell_dollar_investment(inv['id'], sell_rate_all, inv['usd_amount'])
                            if result['success']:
                                # 세션 스테이트 갱신 (투자 내역 + 매도 기록)
                                from database.dollar_db import load_dollar_investments, load_dollar_sell_records
                                st.session_state.dollar_investments = load_dollar_investments() or []
                                st.session_state.sell_records = load_dollar_sell_records() or []
                                st.success(result['message'])
                                st.rerun()
                            else:
                                st.error(result['message'])
                
                with col_b2:
                    # 분할매도 popover
                    with st.popover("📊 분할매도", use_container_width=True):
                        sell_amount = st.number_input(
                            "매도 금액 (USD)", 
                            min_value=0.01, 
                            max_value=float(inv['usd_amount']), 
                            value=float(inv['usd_amount']/2),
                            step=0.01,
                            key=f"dollar_sell_amt_{inv['id']}"
                        )
                        sell_rate = st.number_input(
                            "매도 환율 (원/USD)", 
                            min_value=0.0, 
                            value=current_rate if current_rate else 1300.0,
                            step=0.1,
                            key=f"dollar_sell_rate_{inv['id']}"
                        )
                        
                        if st.button("매도 실행", key=f"dollar_sell_exec_{inv['id']}", type="primary", use_container_width=True):
                            result = dollar_db.sell_dollar_investment(inv['id'], sell_rate, sell_amount)
                            if result['success']:
                                # 세션 스테이트 갱신 (투자 내역 + 매도 기록)
                                from database.dollar_db import load_dollar_investments, load_dollar_sell_records
                                st.session_state.dollar_investments = load_dollar_investments() or []
                                st.session_state.sell_records = load_dollar_sell_records() or []
                                st.success(result['message'])
                                st.rerun()
                            else:
                                st.error(result['message'])
                
                st.markdown("---")


def display_jpy_investment_tab():
    """엔화 투자 관리 탭 UI"""
    # 포트폴리오 요약
    investments = st.session_state.get('jpy_investments', [])
    if investments:
        perf = calculate_jpy_portfolio_performance(investments)
        
        # HTML 테이블로 2x2 그리드 생성
        profit_sign = "+" if perf['total_profit_krw'] >= 0 else ""
        profit_color = COLORS['success'] if perf['total_profit_krw'] >= 0 else COLORS['error']
        
        portfolio_html = f"""
        <style>
        .portfolio-table-jpy {{
            width: 100%;
            display: table;
            border-collapse: collapse;
            margin-bottom: 1.5rem;
        }}
        .portfolio-row-jpy {{
            display: table-row;
        }}
        .portfolio-cell-jpy {{
            display: table-cell;
            width: 50%;
            padding: 0.5rem;
            vertical-align: top;
        }}
        .portfolio-metric-jpy {{
            background: {COLORS['background_primary']};
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 0.5rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
            border: 1px solid {COLORS['gray_200']};
        }}
        .portfolio-label-jpy {{
            font-size: 0.875rem;
            color: {COLORS['text_secondary']};
            font-weight: 500;
            margin-bottom: 0.5rem;
        }}
        .portfolio-value-jpy {{
            font-size: 1.5rem;
            color: {COLORS['text_primary']};
            font-weight: 700;
            letter-spacing: -0.02em;
        }}
        .portfolio-delta-jpy {{
            font-size: 0.875rem;
            color: {profit_color};
            margin-top: 0.25rem;
        }}
        
        @media (max-width: 768px) {{
            .portfolio-label-jpy {{
                font-size: 0.75rem;
            }}
            .portfolio-value-jpy {{
                font-size: 1.1rem;
            }}
            .portfolio-delta-jpy {{
                font-size: 0.75rem;
            }}
            .portfolio-metric-jpy {{
                padding: 0.75rem;
                margin-bottom: 0.4rem;
            }}
            .portfolio-cell-jpy {{
                padding: 0.25rem;
            }}
        }}
        </style>
        
        <div class="portfolio-table-jpy">
            <div class="portfolio-row-jpy">
                <div class="portfolio-cell-jpy">
                    <!-- 총 매수금액 -->
                    <div class="portfolio-metric-jpy">
                        <div class="portfolio-label-jpy">총 매수금액</div>
                        <div class="portfolio-value-jpy">{int(perf['total_purchase_krw']):,}원</div>
                    </div>
                </div>
                <div class="portfolio-cell-jpy">
                    <!-- 현재 평가금액 -->
                    <div class="portfolio-metric-jpy">
                        <div class="portfolio-label-jpy">현재 평가금액</div>
                        <div class="portfolio-value-jpy">{int(perf['total_current_krw']):,}원</div>
                    </div>
                </div>
            </div>
            <div class="portfolio-row-jpy">
                <div class="portfolio-cell-jpy">
                    <!-- 평가 손익 -->
                    <div class="portfolio-metric-jpy">
                        <div class="portfolio-label-jpy">평가 손익</div>
                        <div class="portfolio-value-jpy">{profit_sign}{int(perf['total_profit_krw']):,}원</div>
                        <div class="portfolio-delta-jpy">{profit_sign}{perf['total_profit_rate']:.2f}%</div>
                    </div>
                </div>
                <div class="portfolio-cell-jpy">
                    <!-- 현재 환율 -->
                    <div class="portfolio-metric-jpy">
                        <div class="portfolio-label-jpy">현재 환율</div>
                        <div class="portfolio-value-jpy">{perf['current_rate']:.4f}원</div>
                    </div>
                </div>
            </div>
        </div>
        """
        
        st.markdown(portfolio_html, unsafe_allow_html=True)
        st.markdown("---")
    
    # 새 투자 추가 폼
    with st.expander("➕ 엔화 투자 추가", expanded=False):
        # 반응형 폼 스타일
        st.markdown("""
        <style>
        /* 데스크톱: 2열 레이아웃 */
        @media (min-width: 769px) {
            div[data-testid="stForm"] > div > div {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 1rem;
            }
        }
        
        /* 모바일: 1열 레이아웃 */
        @media (max-width: 768px) {
            div[data-testid="stForm"] > div > div {
                display: block;
            }
            
            /* 제출 버튼 전체 너비 */
            div[data-testid="stForm"] button {
                width: 100% !important;
            }
        }
        </style>
        """, unsafe_allow_html=True)
        
        with st.form("add_jpy_investment_form"):
            # 반응형 컬럼 (CSS로 제어)
            col1, col2 = st.columns(2)
            with col1:
                investment_number = st.number_input("번호", min_value=1, value=1, step=1, key="jpy_investment_number")
                exchange_rate = st.number_input("매수 환율 (원/JPY)", min_value=0.0, value=9.0, step=0.01, format="%.4f", key="jpy_exchange_rate")
                jpy_amount = st.number_input("매수 엔화 (JPY)", min_value=0.0, value=10000.0, step=0.01, format="%.2f", key="jpy_amount")
            with col2:
                exchange_name = st.text_input("거래소", value="하나은행", placeholder="하나은행, 신한은행 등", key="jpy_exchange_name")
                memo = st.text_area("메모", placeholder="투자 목적 등", key="jpy_memo", height=100)
            
            submitted = st.form_submit_button("✅ 추가", type="primary", use_container_width=True)
            
            if submitted:
                if exchange_rate > 0 and jpy_amount > 0:
                    investment_data = {
                        'investment_number': investment_number,
                        'purchase_date': datetime.datetime.now().isoformat(),
                        'exchange_rate': exchange_rate,
                        'jpy_amount': jpy_amount,
                        'exchange_name': exchange_name,
                        'memo': memo,
                        'purchase_krw': exchange_rate * jpy_amount
                    }
                    success = jpy_db.save_jpy_investment(investment_data)
                    if success:
                        # 세션 스테이트 갱신
                        from database.jpy_db import load_jpy_investments
                        st.session_state.jpy_investments = load_jpy_investments() or []
                        st.success("✅ 투자가 추가되었습니다!")
                        st.rerun()
                    else:
                        st.error("❌ 투자 추가 실패")
                else:
                    st.error("❌ 환율과 금액을 확인하세요")
    
    # 투자 내역 카드
    if investments:
        st.subheader("📊 투자 내역")
        
        current_rate = get_investing_jpy_krw_for_portfolio()
        
        for inv in investments:
            current_krw = inv['jpy_amount'] * current_rate if current_rate else 0
            profit_krw = current_krw - inv['purchase_krw']
            profit_rate = (profit_krw / inv['purchase_krw'] * 100) if inv['purchase_krw'] > 0 else 0
            
            # 매수일시를 간단한 형식으로 변환
            purchase_date_str = inv['purchase_date']
            try:
                purchase_dt = datetime.datetime.fromisoformat(purchase_date_str)
                formatted_date = purchase_dt.strftime('%Y-%m-%d %H:%M')
            except:
                formatted_date = purchase_date_str[:16]
            
            # 수익률에 따른 색상
            profit_emoji = "🟢" if profit_krw >= 0 else "🔴"
            profit_color_hex = COLORS['success'] if profit_krw >= 0 else COLORS['error']
            profit_sign = "+" if profit_krw >= 0 else ""
            
            # HTML 테이블로 2열 투자 카드 생성 (엔화)
            memo_html = f"<div style='font-size: 0.875rem; color: {COLORS['text_secondary']}; margin: 0.25rem 0;'>📝 {inv.get('memo', '')}</div>" if inv.get('memo') else ""
            
            invest_card_html = f"""
            <div style="background: {COLORS['background_primary']}; border-radius: 12px; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); border: 1px solid {COLORS['gray_200']};">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="width: 50%; padding: 0.5rem; vertical-align: top;">
                            <div style="font-size: 1.1rem; font-weight: 700; color: {COLORS['text_primary']}; margin-bottom: 0.5rem;">#{inv['investment_number']} {inv['exchange_name']}</div>
                            <div style="font-size: 0.875rem; color: {COLORS['text_secondary']}; margin: 0.25rem 0;">📅 {formatted_date}</div>
                            {memo_html}
                            <div style="margin: 0.5rem 0;">
                                <div style="font-size: 0.75rem; color: {COLORS['text_secondary']}; margin-bottom: 0.25rem;">매수가</div>
                                <div style="font-size: 1.2rem; font-weight: 700; color: {COLORS['text_primary']};">{inv['exchange_rate']:.4f}원</div>
                                <div style="font-size: 0.875rem; color: {COLORS['text_secondary']}; margin-top: 0.25rem;">💴 {inv['jpy_amount']:.2f} JPY</div>
                            </div>
                        </td>
                        <td style="width: 50%; padding: 0.5rem; vertical-align: top;">
                            <div style="margin: 0.5rem 0;">
                                <div style="font-size: 0.75rem; color: {COLORS['text_secondary']}; margin-bottom: 0.25rem;">평가금액</div>
                                <div style="font-size: 1.2rem; font-weight: 700; color: {COLORS['text_primary']};">{int(current_krw):,}원</div>
                                <div style="font-size: 0.875rem; color: {profit_color_hex}; font-weight: 600; margin-top: 0.25rem;">
                                    {profit_emoji} {profit_sign}{profit_rate:.2f}% ({profit_sign}{int(profit_krw):,}원)
                                </div>
                            </div>
                        </td>
                    </tr>
                </table>
            </div>
            """
            
            components.html(invest_card_html, height=200)
            
            with st.container():
                # 액션 버튼 (2열 배치)
                col_b1, col_b2 = st.columns(2)
                
                with col_b1:
                    # 삭제 버튼
                    if st.button("🗑️ 삭제", key=f"jpy_delete_{inv['id']}", use_container_width=True):
                        if jpy_db.delete_jpy_investment(inv['id']):
                            # 세션 스테이트 갱신
                            from database.jpy_db import load_jpy_investments
                            st.session_state.jpy_investments = load_jpy_investments() or []
                            st.success(f"투자 #{inv['investment_number']}가 삭제되었습니다.")
                            st.rerun()
                        else:
                            st.error("삭제 실패")
                    
                    # 전량매도 popover
                    with st.popover("💰 전량매도", use_container_width=True):
                        sell_rate_all = st.number_input(
                            "매도 환율 (원/JPY)", 
                            min_value=0.0, 
                            value=current_rate if current_rate else 9.0,
                            step=0.0001,
                            format="%.4f",
                            key=f"jpy_sell_rate_all_{inv['id']}"
                        )
                        st.caption(f"전량: {inv['jpy_amount']:.2f} JPY")
                        
                        if st.button("전량 매도 실행", key=f"jpy_sell_all_exec_{inv['id']}", type="primary", use_container_width=True):
                            result = jpy_db.sell_jpy_investment(inv['id'], sell_rate_all, inv['jpy_amount'])
                            if result['success']:
                                # 세션 스테이트 갱신 (투자 내역 + 매도 기록)
                                from database.jpy_db import load_jpy_investments, load_jpy_sell_records
                                st.session_state.jpy_investments = load_jpy_investments() or []
                                st.session_state.jpy_sell_records = load_jpy_sell_records() or []
                                st.success(result['message'])
                                st.rerun()
                            else:
                                st.error(result['message'])
                
                with col_b2:
                    # 분할매도 popover
                    with st.popover("📊 분할매도", use_container_width=True):
                        sell_amount = st.number_input(
                            "매도 금액 (JPY)", 
                            min_value=0.01, 
                            max_value=float(inv['jpy_amount']), 
                            value=float(inv['jpy_amount']/2),
                            step=0.01,
                            key=f"jpy_sell_amt_{inv['id']}"
                        )
                        sell_rate = st.number_input(
                            "매도 환율 (원/JPY)", 
                            min_value=0.0, 
                            value=current_rate if current_rate else 9.0,
                            step=0.0001,
                            format="%.4f",
                            key=f"jpy_sell_rate_{inv['id']}"
                        )
                        
                        if st.button("매도 실행", key=f"jpy_sell_exec_{inv['id']}", type="primary", use_container_width=True):
                            result = jpy_db.sell_jpy_investment(inv['id'], sell_rate, sell_amount)
                            if result['success']:
                                # 세션 스테이트 갱신 (투자 내역 + 매도 기록)
                                from database.jpy_db import load_jpy_investments, load_jpy_sell_records
                                st.session_state.jpy_investments = load_jpy_investments() or []
                                st.session_state.jpy_sell_records = load_jpy_sell_records() or []
                                st.success(result['message'])
                                st.rerun()
                            else:
                                st.error(result['message'])
                
                st.markdown("---")

