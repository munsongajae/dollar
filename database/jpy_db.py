"""
엔화 투자 관련 데이터베이스 작업
"""
from typing import Dict, List
from .supabase_client import get_supabase_client


def save_jpy_investment(investment_data: Dict) -> bool:
    """엔화 투자 데이터를 DB에 저장"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        supabase.table('jpy_investments').insert(investment_data).execute()
        return True
    except Exception as e:
        print(f"데이터 저장 실패: {e}")
        return False


def load_jpy_investments() -> List[Dict]:
    """모든 엔화 투자 데이터를 DB에서 로드"""
    supabase = get_supabase_client()
    if not supabase:
        return []
    
    try:
        response = supabase.table('jpy_investments').select('*').order('purchase_date', desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"데이터 로드 실패: {e}")
        return []


def delete_jpy_investment(investment_id: str) -> bool:
    """특정 엔화 투자 데이터를 DB에서 삭제"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        supabase.table('jpy_investments').delete().eq('id', investment_id).execute()
        return True
    except Exception as e:
        print(f"데이터 삭제 실패: {e}")
        return False


def save_jpy_sell_record(sell_data: Dict) -> bool:
    """엔화 매도 기록을 DB에 저장"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        supabase.table('jpy_sell_records').insert(sell_data).execute()
        return True
    except Exception as e:
        print(f"매도 기록 저장 실패: {e}")
        return False


def load_jpy_sell_records() -> List[Dict]:
    """모든 엔화 매도 기록을 DB에서 로드"""
    supabase = get_supabase_client()
    if not supabase:
        return []
    
    try:
        response = supabase.table('jpy_sell_records').select('*').order('sell_date', desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"매도 기록 로드 실패: {e}")
        return []


def delete_jpy_sell_record(record_id: str) -> bool:
    """특정 엔화 매도 기록을 DB에서 삭제"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        supabase.table('jpy_sell_records').delete().eq('id', record_id).execute()
        return True
    except Exception as e:
        print(f"매도 기록 삭제 실패: {e}")
        return False


def sell_jpy_investment(investment_id: str, sell_rate: float, sell_amount: float) -> Dict:
    """
    엔화 투자를 매도 처리
    
    Args:
        investment_id: 투자 ID
        sell_rate: 매도 환율
        sell_amount: 매도 금액 (JPY)
        
    Returns:
        Dict: {'success': bool, 'message': str, 'remaining': float}
    """
    supabase = get_supabase_client()
    if not supabase:
        return {'success': False, 'message': 'DB 연결 실패', 'remaining': 0}
    
    try:
        # 투자 정보 조회
        response = supabase.table('jpy_investments').select('*').eq('id', investment_id).execute()
        if not response.data:
            return {'success': False, 'message': '투자 정보를 찾을 수 없습니다', 'remaining': 0}
        
        investment = response.data[0]
        current_amount = investment['jpy_amount']
        
        # 매도 금액 검증
        if sell_amount > current_amount:
            return {'success': False, 'message': f'보유 금액({current_amount:.2f}JPY)보다 많이 매도할 수 없습니다', 'remaining': current_amount}
        
        # 매도 기록 저장
        import datetime
        sell_data = {
            'investment_id': investment_id,
            'investment_number': investment['investment_number'],
            'sell_date': datetime.datetime.now().isoformat(),
            'purchase_rate': investment['exchange_rate'],
            'sell_rate': sell_rate,
            'sell_amount': sell_amount,
            'sell_krw': sell_amount * sell_rate,
            'profit_krw': (sell_rate - investment['exchange_rate']) * sell_amount,
            'exchange_name': investment['exchange_name']
        }
        
        save_success = save_jpy_sell_record(sell_data)
        if not save_success:
            return {'success': False, 'message': '매도 기록 저장 실패', 'remaining': current_amount}
        
        # 전량 매도: 투자 삭제
        remaining = current_amount - sell_amount
        if remaining <= 1:  # 거의 0에 가까우면 전량 매도로 처리
            supabase.table('jpy_investments').delete().eq('id', investment_id).execute()
            return {'success': True, 'message': f'{sell_amount:.2f}JPY 전량 매도 완료', 'remaining': 0}
        
        # 분할 매도: 투자 금액 업데이트
        new_purchase_krw = (current_amount - sell_amount) * investment['exchange_rate']
        supabase.table('jpy_investments').update({
            'jpy_amount': remaining,
            'purchase_krw': new_purchase_krw
        }).eq('id', investment_id).execute()
        
        return {'success': True, 'message': f'{sell_amount:.2f}JPY 매도 완료', 'remaining': remaining}
        
    except Exception as e:
        print(f"매도 처리 실패: {e}")
        return {'success': False, 'message': f'매도 처리 중 오류: {str(e)}', 'remaining': 0}

