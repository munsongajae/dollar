"""
환율 히스토리 데이터베이스 관리
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
from database.supabase_client import get_supabase_client


class ExchangeHistoryDB:
    """환율 히스토리 데이터베이스 관리 클래스"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    def get_latest_date(self, currency_pair: str) -> Optional[datetime]:
        """특정 통화쌍의 가장 최근 날짜를 조회합니다."""
        if not self.supabase:
            return None
        
        try:
            response = self.supabase.table('exchange_rate_history') \
                .select('date') \
                .eq('currency_pair', currency_pair) \
                .order('date', desc=True) \
                .limit(1) \
                .execute()
            
            if response.data and len(response.data) > 0:
                return pd.to_datetime(response.data[0]['date'])
            return None
        except Exception as e:
            st.warning(f"최근 날짜 조회 실패 ({currency_pair}): {e}")
            return None
    
    def get_all_latest_dates(self, currency_pairs: list) -> Dict[str, Optional[datetime]]:
        """모든 통화쌍의 가장 최근 날짜를 한번에 조회합니다."""
        if not self.supabase:
            return {pair: None for pair in currency_pairs}
        
        try:
            response = self.supabase.table('exchange_rate_history') \
                .select('currency_pair, date') \
                .in_('currency_pair', currency_pairs) \
                .order('date', desc=True) \
                .execute()
            
            # 각 통화쌍별로 가장 최근 날짜 추출
            latest_dates = {}
            for pair in currency_pairs:
                pair_dates = [pd.to_datetime(item['date']) 
                             for item in response.data 
                             if item['currency_pair'] == pair]
                latest_dates[pair] = max(pair_dates) if pair_dates else None
            
            return latest_dates
        except Exception as e:
            st.warning(f"최근 날짜 일괄 조회 실패: {e}")
            return {pair: None for pair in currency_pairs}
    
    def save_history_data(self, df_close: pd.DataFrame, df_high: pd.DataFrame, 
                          df_low: pd.DataFrame, df_open: Optional[pd.DataFrame] = None) -> bool:
        """OHLC 데이터를 데이터베이스에 저장합니다."""
        if not self.supabase:
            return False
        
        try:
            # Open 데이터가 없으면 Close로 대체
            if df_open is None:
                df_open = df_close.copy()
            
            records = []
            for date_idx in df_close.index:
                date_str = pd.to_datetime(date_idx).strftime('%Y-%m-%d')
                
                for currency_pair in df_close.columns:
                    record = {
                        'date': date_str,
                        'currency_pair': currency_pair,
                        'open': float(df_open.loc[date_idx, currency_pair]),
                        'high': float(df_high.loc[date_idx, currency_pair]),
                        'low': float(df_low.loc[date_idx, currency_pair]),
                        'close': float(df_close.loc[date_idx, currency_pair])
                    }
                    records.append(record)
            
            # 배치 업서트 (중복 시 업데이트)
            if records:
                # onConflict 파라미터로 UNIQUE 제약조건 컬럼 지정
                self.supabase.table('exchange_rate_history').upsert(
                    records, 
                    on_conflict='date,currency_pair'
                ).execute()
                return True
            
            return False
        except Exception as e:
            st.error(f"데이터 저장 실패: {e}")
            return False
    
    def load_history_data(self, currency_pairs: list, start_date: datetime, 
                          end_date: datetime) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """데이터베이스에서 OHLC 데이터를 조회합니다."""
        if not self.supabase:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        try:
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            response = self.supabase.table('exchange_rate_history') \
                .select('*') \
                .in_('currency_pair', currency_pairs) \
                .gte('date', start_str) \
                .lte('date', end_str) \
                .order('date') \
                .execute()
            
            if not response.data:
                return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
            
            # 데이터프레임 생성
            df = pd.DataFrame(response.data)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # OHLC 별로 pivot
            df_close = df.pivot_table(values='close', index='date', columns='currency_pair')
            df_high = df.pivot_table(values='high', index='date', columns='currency_pair')
            df_low = df.pivot_table(values='low', index='date', columns='currency_pair')
            
            return df_close, df_high, df_low
        except Exception as e:
            st.warning(f"데이터 조회 실패: {e}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    def get_data_coverage(self, currency_pairs: list, 
                          required_months: int) -> Dict[str, bool]:
        """각 통화쌍의 데이터 커버리지를 확인합니다."""
        if not self.supabase:
            return {pair: False for pair in currency_pairs}
        
        required_date = datetime.now() - timedelta(days=required_months * 30)
        latest_dates = self.get_all_latest_dates(currency_pairs)
        
        coverage = {}
        for pair in currency_pairs:
            latest = latest_dates.get(pair)
            if latest is None:
                coverage[pair] = False
            else:
                # 최근 데이터가 오늘이거나 어제인 경우 충분한 커버리지로 판단
                days_ago = (datetime.now() - latest).days
                coverage[pair] = days_ago <= 1
        
        return coverage


# 전역 인스턴스
exchange_history_db = ExchangeHistoryDB()

