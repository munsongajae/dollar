# 📊 환율 데이터 캐싱 시스템

## 🎯 개선 사항

기존에는 앱을 실행할 때마다 1년치 환율 데이터를 yfinance에서 다시 가져왔습니다. 
이제 **Supabase 데이터베이스를 활용한 캐싱 시스템**으로 변경되었습니다!

### ✨ 장점

1. **⚡ 빠른 로딩 속도**
   - 최초 1회만 전체 데이터 다운로드
   - 이후에는 DB에서 즉시 로드 (초단위 → 밀리초 단위)

2. **🔄 증분 업데이트**
   - 마지막 저장 날짜 이후 데이터만 추가로 fetch
   - API 호출 최소화

3. **🛡️ 크롤링 제한 회피**
   - yfinance API 호출 횟수 대폭 감소
   - 안정적인 서비스 운영

4. **💾 데이터 보존**
   - 과거 데이터가 DB에 영구 저장
   - 야후 파이낸스 장애 시에도 이전 데이터 사용 가능

## 🗂️ 새로운 파일 구조

```
dollar/
├── database/
│   └── exchange_history_db.py       # 환율 히스토리 DB 관리
├── services/
│   ├── exchange_rate.py             # 기존 환율 조회 (실시간 데이터)
│   └── exchange_rate_cached.py      # 캐시 활용 환율 조회 (신규)
└── supabase_schema.sql              # exchange_rate_history 테이블 추가
```

## 🗄️ 데이터베이스 스키마

### `exchange_rate_history` 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID | Primary Key |
| date | DATE | 날짜 |
| currency_pair | VARCHAR(20) | 통화쌍 (예: EUR_USD, USD_KRW) |
| open | DECIMAL(15,6) | 시가 |
| high | DECIMAL(15,6) | 고가 |
| low | DECIMAL(15,6) | 저가 |
| close | DECIMAL(15,6) | 종가 |
| created_at | TIMESTAMP | 생성 시간 |

**저장되는 통화쌍:**
- EUR_USD, USD_JPY, GBP_USD, USD_CAD, USD_SEK, USD_CHF
- USD_KRW, JPY_KRW, JXY

## 🔄 작동 방식

### 1. 최초 실행
```
사용자 → fetch_period_data_with_cache()
         ↓
    DB 조회 (비어있음)
         ↓
    yfinance에서 1년치 데이터 다운로드
         ↓
    DB에 저장
         ↓
    데이터 반환
```

### 2. 이후 실행 (당일)
```
사용자 → fetch_period_data_with_cache()
         ↓
    DB 조회 (데이터 있음, 최신)
         ↓
    ✅ DB 데이터 즉시 반환 (API 호출 없음!)
```

### 3. 이후 실행 (다음날)
```
사용자 → fetch_period_data_with_cache()
         ↓
    DB 조회 (마지막 날짜: 어제)
         ↓
    yfinance에서 오늘 데이터만 다운로드
         ↓
    DB에 추가 (증분 업데이트)
         ↓
    병합된 데이터 반환
```

## 📝 사용 방법

### Supabase 테이블 생성

1. Supabase 콘솔 접속
2. SQL Editor에서 `supabase_schema.sql` 실행
3. `exchange_rate_history` 테이블 생성 확인

### 코드에서 사용

```python
from services.exchange_rate_cached import fetch_period_data_with_cache

# 기존 코드
# df_close, df_high, df_low, current_rates = fetch_period_data_and_current_rates(12)

# 신규 코드 (자동으로 DB 캐시 활용)
df_close, df_high, df_low, current_rates = fetch_period_data_with_cache(12)
```

## 🎛️ 설정

### TTL (Time To Live) 조정

Streamlit 캐시는 유지하되 TTL을 더 늘릴 수 있습니다:

```python
# app_new.py
@st.cache_data(ttl=3600)  # 기존 300초 → 1시간으로 변경 가능
def get_market_data(period: int):
    df_close, df_high, df_low, current_rates = fetch_period_data_with_cache(period)
    ...
```

## 🧪 테스트

### 1. 최초 실행 테스트
```bash
# DB 테이블 초기화 (선택사항)
# DELETE FROM exchange_rate_history;

streamlit run app_new.py
```
→ "yfinance에서 전체 데이터 가져오는 중..." 메시지 확인
→ "데이터가 데이터베이스에 저장되었습니다!" 메시지 확인

### 2. 재실행 테스트
```bash
streamlit run app_new.py
```
→ "캐시된 데이터를 사용합니다." 메시지 확인
→ 로딩 시간이 대폭 단축됨을 확인

### 3. DB 데이터 확인
```sql
-- Supabase SQL Editor
SELECT 
    currency_pair, 
    COUNT(*) as record_count,
    MIN(date) as first_date,
    MAX(date) as last_date
FROM exchange_rate_history
GROUP BY currency_pair
ORDER BY currency_pair;
```

## 🔧 문제 해결

### DB 연결 오류
```
⚠️ Supabase 설정이 필요합니다
```
→ `.env` 파일에 `SUPABASE_URL`과 `SUPABASE_ANON_KEY` 확인

### 테이블 없음 오류
```
relation "exchange_rate_history" does not exist
```
→ `supabase_schema.sql` 실행 확인

### 데이터가 업데이트되지 않음
```python
# DB 강제 업데이트가 필요한 경우
from database.exchange_history_db import exchange_history_db

# 특정 통화쌍의 최근 날짜 확인
latest = exchange_history_db.get_latest_date('USD_KRW')
print(f"최근 업데이트: {latest}")
```

## 📊 성능 비교

| 항목 | 기존 방식 | 신규 방식 (DB 캐시) |
|------|----------|-------------------|
| 최초 로딩 | ~15초 | ~15초 (동일) |
| 재실행 로딩 | ~15초 | **~1초** ⚡ |
| API 호출 | 매번 전체 | 증분만 |
| 크롤링 제한 위험 | 높음 | 낮음 |
| 오프라인 대응 | 불가능 | 가능 (과거 데이터) |

## 🚀 향후 개선 사항

- [ ] 데이터 품질 체크 (결측치, 이상값 감지)
- [ ] 배치 작업으로 자동 업데이트 (매일 자정)
- [ ] 다른 데이터 소스 추가 (백업용)
- [ ] 데이터 압축 (파티셔닝, 아카이빙)

## 💡 참고

- 현재 가격은 여전히 실시간으로 yfinance에서 가져옵니다
- DB에는 과거 OHLC 데이터만 저장됩니다
- Streamlit 캐시와 DB 캐시가 이중으로 작동하여 최적의 성능을 제공합니다

