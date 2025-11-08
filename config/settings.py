"""
애플리케이션 설정 및 상수
"""
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Supabase 설정
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# 환율 데이터 설정
EXCHANGE_RATE_CACHE_TTL = 300  # 5분

# 달러 인덱스 계산 상수
DXY_INITIAL_CONSTANT = 50.143432
DXY_WEIGHTS = {
    'EUR_USD': -0.576,
    'USD_JPY': 0.136,
    'GBP_USD': -0.119,
    'USD_CAD': 0.091,
    'USD_SEK': 0.042,
    'USD_CHF': 0.036
}

# Yahoo Finance 티커
DXY_TICKERS = {
    'EUR_USD': 'EURUSD=X',
    'USD_JPY': 'JPY=X',
    'GBP_USD': 'GBPUSD=X',
    'USD_CAD': 'CAD=X',
    'USD_SEK': 'SEK=X',
    'USD_CHF': 'CHF=X'
}

USD_KRW_TICKER = 'USDKRW=X'

# 기간 설정
PERIOD_MAP = {
    1: '1mo',
    3: '3mo',
    6: '6mo',
    12: '1y'
}

# 색상 테마 (토스 스타일)
COLORS = {
    'primary': '#3182F6',
    'success': '#00C471',
    'warning': '#FFA500',
    'error': '#F04452',
    'text_primary': '#191F28',
    'text_secondary': '#4E5968',
    'text_tertiary': '#8B95A1',
    'background_primary': '#FFFFFF',
    'background_secondary': '#F9FAFB',
    'gray_50': '#F9FAFB',
    'gray_100': '#F2F4F6',
    'gray_200': '#E5E8EB',
    'gray_300': '#D1D6DB',
    'gray_400': '#B0B8C1',
    'gray_500': '#8B95A1',
    'gray_600': '#6B7684',
    'gray_700': '#4E5968',
    'gray_800': '#333D4B',
    'gray_900': '#191F28',
}

# 외부 API URL
INVESTING_USD_KRW_URL = "https://kr.investing.com/currencies/usd-krw"
INVESTING_JPY_KRW_URL = "https://kr.investing.com/currencies/jpy-krw"
HANA_BANK_URL = "https://finance.naver.com/marketindex/exchangeDetail.nhn?marketindexCd=FX_USDKRW"
BITHUMB_USDT_URL = "https://api.bithumb.com/public/ticker/USDT_KRW"

