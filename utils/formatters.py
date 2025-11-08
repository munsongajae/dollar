"""
숫자 포맷팅 유틸리티
"""


def format_currency(amount: float, currency: str = "원", with_sign: bool = False, as_integer: bool = False, decimals: int = 2) -> str:
    """
    금액을 포맷팅합니다.
    
    Args:
        amount: 금액
        currency: 통화 단위 (기본값: "원")
        with_sign: +/- 부호 포함 여부 (기본값: False)
        as_integer: 정수로 표시할지 여부 (기본값: False)
        decimals: 소수점 자릿수 (기본값: 2, as_integer=True일 때는 무시됨)
        
    Returns:
        str: 포맷팅된 금액 문자열
    
    Examples:
        >>> format_currency(1234567.89)
        '1,234,567.89원'
        >>> format_currency(1234567.89, as_integer=True)
        '1,234,568원'
        >>> format_currency(9.1234, decimals=4)
        '9.1234원'
        >>> format_currency(1234567.89, with_sign=True)
        '+1,234,567.89원'
        >>> format_currency(-1234567.89, with_sign=True)
        '-1,234,567.89원'
    """
    sign = "+" if amount > 0 and with_sign else ""
    if as_integer:
        formatted = f"{int(round(amount)):,}"
    else:
        formatted = f"{amount:,.{decimals}f}"
    return f"{sign}{formatted}{currency}"


def format_percentage(value: float, decimals: int = 2, with_sign: bool = True) -> str:
    """
    퍼센트 값을 포맷팅합니다.
    
    Args:
        value: 퍼센트 값
        decimals: 소수점 자릿수 (기본값: 2)
        with_sign: +/- 부호 포함 여부 (기본값: True)
        
    Returns:
        str: 포맷팅된 퍼센트 문자열
        
    Examples:
        >>> format_percentage(12.3456)
        '+12.35%'
        >>> format_percentage(-5.6789, decimals=1)
        '-5.7%'
    """
    sign = "+" if value > 0 and with_sign else ""
    return f"{sign}{value:.{decimals}f}%"


def format_number(value: float, decimals: int = 2) -> str:
    """
    숫자를 천 단위 구분자와 함께 포맷팅합니다.
    
    Args:
        value: 숫자
        decimals: 소수점 자릿수 (기본값: 2)
        
    Returns:
        str: 포맷팅된 숫자 문자열
        
    Examples:
        >>> format_number(1234567.89)
        '1,234,567.89'
    """
    return f"{value:,.{decimals}f}"

