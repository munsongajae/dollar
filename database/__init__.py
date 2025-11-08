"""
데이터베이스 모듈
"""
from .supabase_client import get_supabase_client
from .dollar_db import (
    save_dollar_investment,
    load_dollar_investments,
    delete_dollar_investment,
    save_dollar_sell_record,
    load_dollar_sell_records,
    delete_dollar_sell_record
)
from .jpy_db import (
    save_jpy_investment,
    load_jpy_investments,
    delete_jpy_investment,
    save_jpy_sell_record,
    load_jpy_sell_records,
    delete_jpy_sell_record
)
from .exchange_history_db import exchange_history_db

__all__ = [
    'get_supabase_client',
    'save_dollar_investment',
    'load_dollar_investments',
    'delete_dollar_investment',
    'save_dollar_sell_record',
    'load_dollar_sell_records',
    'delete_dollar_sell_record',
    'save_jpy_investment',
    'load_jpy_investments',
    'delete_jpy_investment',
    'save_jpy_sell_record',
    'load_jpy_sell_records',
    'delete_jpy_sell_record',
    'exchange_history_db',
]

