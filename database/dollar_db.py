"""
달러 투자 관련 데이터베이스 작업
"""
from typing import Dict, List, Optional
from .supabase_client import get_supabase_client


def save_dollar_investment(investment_data: Dict) -> bool:
    """
    달러 투자 데이터를 DB에 저장
    
    Args:
        investment_data: 투자 정보 딕셔너리
        
    Returns:
        bool: 저장 성공 여부
    """
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        supabase.table('dollar_investments').insert(investment_data).execute()
        return True
    except Exception as e:
        print(f"데이터 저장 실패: {e}")
        return False


def load_dollar_investments() -> List[Dict]:
    """
    모든 달러 투자 데이터를 DB에서 로드
    
    Returns:
        List[Dict]: 투자 데이터 리스트
    """
    supabase = get_supabase_client()
    if not supabase:
        return []
    
    try:
        response = supabase.table('dollar_investments').select('*').order('purchase_date', desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"데이터 로드 실패: {e}")
        return []


def delete_dollar_investment(investment_id: str) -> bool:
    """
    특정 달러 투자 데이터를 DB에서 삭제
    
    Args:
        investment_id: 투자 ID
        
    Returns:
        bool: 삭제 성공 여부
    """
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        supabase.table('dollar_investments').delete().eq('id', investment_id).execute()
        return True
    except Exception as e:
        print(f"데이터 삭제 실패: {e}")
        return False


def save_dollar_sell_record(sell_data: Dict) -> bool:
    """
    달러 매도 기록을 DB에 저장
    
    Args:
        sell_data: 매도 정보 딕셔너리
        
    Returns:
        bool: 저장 성공 여부
    """
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        supabase.table('dollar_sell_records').insert(sell_data).execute()
        return True
    except Exception as e:
        print(f"매도 기록 저장 실패: {e}")
        return False


def load_dollar_sell_records() -> List[Dict]:
    """
    모든 달러 매도 기록을 DB에서 로드
    
    Returns:
        List[Dict]: 매도 기록 리스트
    """
    supabase = get_supabase_client()
    if not supabase:
        return []
    
    try:
        response = supabase.table('dollar_sell_records').select('*').order('sell_date', desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"매도 기록 로드 실패: {e}")
        return []


def delete_dollar_sell_record(record_id: str) -> bool:
    """
    특정 달러 매도 기록을 DB에서 삭제
    
    Args:
        record_id: 매도 기록 ID
        
    Returns:
        bool: 삭제 성공 여부
    """
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        supabase.table('dollar_sell_records').delete().eq('id', record_id).execute()
        return True
    except Exception as e:
        print(f"매도 기록 삭제 실패: {e}")
        return False


def sell_dollar_investment(investment_id: str, sell_rate: float, sell_amount: float) -> Dict:
    """
    달러 투자를 매도 처리
    
    Args:
        investment_id: 투자 ID
        sell_rate: 매도 환율
        sell_amount: 매도 금액 (USD)
        
    Returns:
        Dict: {'success': bool, 'message': str, 'remaining': float}
    """
    supabase = get_supabase_client()
    if not supabase:
        return {'success': False, 'message': 'DB 연결 실패', 'remaining': 0}
    
    try:
        # 투자 정보 조회
        response = supabase.table('dollar_investments').select('*').eq('id', investment_id).execute()
        if not response.data:
            return {'success': False, 'message': '투자 정보를 찾을 수 없습니다', 'remaining': 0}
        
        investment = response.data[0]
        current_amount = investment['usd_amount']
        
        # 매도 금액 검증
        if sell_amount > current_amount:
            return {'success': False, 'message': f'보유 금액({current_amount:.2f}USD)보다 많이 매도할 수 없습니다', 'remaining': current_amount}
        
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
        
        save_success = save_dollar_sell_record(sell_data)
        if not save_success:
            return {'success': False, 'message': '매도 기록 저장 실패', 'remaining': current_amount}
        
        # 전량 매도: 투자 삭제
        remaining = current_amount - sell_amount
        if remaining <= 0.01:  # 거의 0에 가까우면 전량 매도로 처리
            supabase.table('dollar_investments').delete().eq('id', investment_id).execute()
            return {'success': True, 'message': f'{sell_amount:.2f}USD 전량 매도 완료', 'remaining': 0}
        
        # 분할 매도: 투자 금액 업데이트
        new_purchase_krw = (current_amount - sell_amount) * investment['exchange_rate']
        supabase.table('dollar_investments').update({
            'usd_amount': remaining,
            'purchase_krw': new_purchase_krw
        }).eq('id', investment_id).execute()
        
        return {'success': True, 'message': f'{sell_amount:.2f}USD 매도 완료', 'remaining': remaining}
        
    except Exception as e:
        print(f"매도 처리 실패: {e}")
        return {'success': False, 'message': f'매도 처리 중 오류: {str(e)}', 'remaining': 0}

