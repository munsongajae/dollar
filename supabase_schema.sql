-- 달러 투자 테이블
CREATE TABLE IF NOT EXISTS dollar_investments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investment_number INTEGER NOT NULL,
    purchase_date TIMESTAMP WITH TIME ZONE NOT NULL,
    exchange_rate DECIMAL(10,4) NOT NULL,
    usd_amount DECIMAL(15,2) NOT NULL,
    exchange_name VARCHAR(100) NOT NULL,
    memo TEXT,
    purchase_krw DECIMAL(15,2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 달러 매도 기록 테이블
CREATE TABLE IF NOT EXISTS dollar_sell_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investment_number INTEGER NOT NULL,
    sell_date TIMESTAMP WITH TIME ZONE NOT NULL,
    sell_rate DECIMAL(10,4) NOT NULL,
    sell_amount DECIMAL(15,2) NOT NULL,
    sell_krw DECIMAL(15,2) NOT NULL,
    profit_krw DECIMAL(15,2) NOT NULL,
    profit_rate DECIMAL(8,4) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 엔화 투자 테이블
CREATE TABLE IF NOT EXISTS jpy_investments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investment_number INTEGER NOT NULL,
    purchase_date TIMESTAMP WITH TIME ZONE NOT NULL,
    exchange_rate DECIMAL(10,4) NOT NULL,
    jpy_amount DECIMAL(15,2) NOT NULL,
    exchange_name VARCHAR(100) NOT NULL,
    memo TEXT,
    purchase_krw DECIMAL(15,2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 엔화 매도 기록 테이블
CREATE TABLE IF NOT EXISTS jpy_sell_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investment_number INTEGER NOT NULL,
    sell_date TIMESTAMP WITH TIME ZONE NOT NULL,
    sell_rate DECIMAL(10,4) NOT NULL,
    sell_amount DECIMAL(15,2) NOT NULL,
    sell_krw DECIMAL(15,2) NOT NULL,
    profit_krw DECIMAL(15,2) NOT NULL,
    profit_rate DECIMAL(8,4) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_dollar_investments_number ON dollar_investments(investment_number);
CREATE INDEX IF NOT EXISTS idx_dollar_investments_date ON dollar_investments(purchase_date);
CREATE INDEX IF NOT EXISTS idx_dollar_sell_records_number ON dollar_sell_records(investment_number);
CREATE INDEX IF NOT EXISTS idx_dollar_sell_records_date ON dollar_sell_records(sell_date);

CREATE INDEX IF NOT EXISTS idx_jpy_investments_number ON jpy_investments(investment_number);
CREATE INDEX IF NOT EXISTS idx_jpy_investments_date ON jpy_investments(purchase_date);
CREATE INDEX IF NOT EXISTS idx_jpy_sell_records_number ON jpy_sell_records(investment_number);
CREATE INDEX IF NOT EXISTS idx_jpy_sell_records_date ON jpy_sell_records(sell_date);

-- RLS (Row Level Security) 정책 설정
ALTER TABLE dollar_investments ENABLE ROW LEVEL SECURITY;
ALTER TABLE dollar_sell_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE jpy_investments ENABLE ROW LEVEL SECURITY;
ALTER TABLE jpy_sell_records ENABLE ROW LEVEL SECURITY;

-- 모든 사용자가 읽기/쓰기 가능하도록 설정 (개발용)
CREATE POLICY "Allow all operations for all users" ON dollar_investments FOR ALL USING (true);
CREATE POLICY "Allow all operations for all users" ON dollar_sell_records FOR ALL USING (true);
CREATE POLICY "Allow all operations for all users" ON jpy_investments FOR ALL USING (true);
CREATE POLICY "Allow all operations for all users" ON jpy_sell_records FOR ALL USING (true);
