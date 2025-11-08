"""
Supabase 클라이언트 연결 관리
"""
import streamlit as st
from supabase import create_client, Client
from typing import Optional
from config.settings import SUPABASE_URL, SUPABASE_ANON_KEY


@st.cache_resource
def get_supabase_client() -> Optional[Client]:
    """
    Supabase 클라이언트를 초기화하고 반환합니다.
    
    Returns:
        Client: Supabase 클라이언트 인스턴스, 실패 시 None
    """
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        st.warning("⚠️ Supabase 설정이 필요합니다. .env 파일에 SUPABASE_URL과 SUPABASE_ANON_KEY를 설정해주세요.")
        return None
    
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        return supabase
    except Exception as e:
        st.error(f"❌ Supabase 연결 실패: {e}")
        return None

