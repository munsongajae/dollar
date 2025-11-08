-- 달러 매도 기록 테이블에 컬럼 추가
ALTER TABLE dollar_sell_records 
ADD COLUMN IF NOT EXISTS investment_id UUID,
ADD COLUMN IF NOT EXISTS purchase_rate DECIMAL(10,4),
ADD COLUMN IF NOT EXISTS exchange_name VARCHAR(100);

-- 엔화 매도 기록 테이블에 컬럼 추가
ALTER TABLE jpy_sell_records 
ADD COLUMN IF NOT EXISTS investment_id UUID,
ADD COLUMN IF NOT EXISTS purchase_rate DECIMAL(10,4),
ADD COLUMN IF NOT EXISTS exchange_name VARCHAR(100);

-- profit_rate 컬럼 제거 (사용하지 않음)
ALTER TABLE dollar_sell_records DROP COLUMN IF EXISTS profit_rate;
ALTER TABLE jpy_sell_records DROP COLUMN IF EXISTS profit_rate;

