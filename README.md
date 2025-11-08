# 달러/엔화 투자 관리 앱

Streamlit과 Supabase를 사용한 환율 투자 관리 웹 애플리케이션입니다.

## 주요 기능

- 실시간 환율 정보 (인베스팅닷컴, 야후파이낸스, 하나은행)
- 달러/엔화 투자 포트폴리오 관리
- 투자 기록 및 매도 기록 관리
- 기간별 성과 분석
- 김치프리미엄 계산

## 설치 및 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. Supabase 설정

1. [Supabase](https://supabase.com)에서 새 프로젝트 생성
2. SQL Editor에서 `supabase_schema.sql` 파일의 내용 실행
3. 프로젝트 설정에서 URL과 Anon Key 복사

### 3. 환경변수 설정

`env_example.txt` 파일을 참고하여 `.env` 파일 생성:

```bash
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
```

### 4. 애플리케이션 실행

```bash
streamlit run app.py
```

## 데이터베이스 스키마

### 달러 투자 테이블 (dollar_investments)
- id: UUID (Primary Key)
- investment_number: 투자 번호
- purchase_date: 매수일시
- exchange_rate: 매수 환율
- usd_amount: 매수 달러 금액
- exchange_name: 거래소명
- memo: 메모
- purchase_krw: 매수금액 (KRW)

### 달러 매도 기록 테이블 (dollar_sell_records)
- id: UUID (Primary Key)
- investment_number: 투자 번호
- sell_date: 매도일시
- sell_rate: 매도 환율
- sell_amount: 매도 금액
- sell_krw: 매도금액 (KRW)
- profit_krw: 확정손익
- profit_rate: 수익률

### 엔화 투자 테이블 (jpy_investments)
- 달러 투자 테이블과 동일한 구조 (usd_amount → jpy_amount)

### 엔화 매도 기록 테이블 (jpy_sell_records)
- 달러 매도 기록 테이블과 동일한 구조

## 주요 기능 설명

### 1. 실시간 환율
- 인베스팅닷컴 USD/KRW, JPY/KRW
- 하나은행 USD/KRW
- 테더 USDT/KRW (Bithumb)
- 김치프리미엄 계산

### 2. 투자 관리
- 투자 추가/삭제
- 전량 매도/분할 매도
- 실시간 손익 계산
- 기간별 성과 분석

### 3. 데이터 저장
- Supabase PostgreSQL 데이터베이스
- 세션 상태와 데이터베이스 동기화
- 자동 백업 및 복원

## 문제 해결

### Supabase 연결 오류
- 환경변수 설정 확인
- Supabase 프로젝트 상태 확인
- 네트워크 연결 확인

### 데이터 로드 실패
- 데이터베이스 테이블 존재 확인
- RLS 정책 설정 확인
- API 키 권한 확인

## 라이선스

MIT License

