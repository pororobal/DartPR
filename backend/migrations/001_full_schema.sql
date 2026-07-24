-- ============================================================================
-- DART0s Full Schema Migration
-- Run this in Supabase SQL Editor (service_role needed for some operations)
-- ============================================================================

-- 1. New columns on disclosures
ALTER TABLE disclosures ADD COLUMN IF NOT EXISTS sub_type TEXT;
ALTER TABLE disclosures ADD COLUMN IF NOT EXISTS is_feed_visible BOOLEAN DEFAULT false;
ALTER TABLE disclosures ADD COLUMN IF NOT EXISTS skip_llm BOOLEAN DEFAULT false;

-- 1b. New columns on users
ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_expires_at TIMESTAMPTZ;

-- 2. Index for history lookups
CREATE INDEX IF NOT EXISTS idx_disclosures_ticker_cat_date
  ON disclosures(ticker, category, published_at DESC);

-- 3. Administrative report patterns table
CREATE TABLE IF NOT EXISTS administrative_report_patterns (
  id SERIAL PRIMARY KEY,
  pattern TEXT NOT NULL,
  active BOOLEAN DEFAULT true
);

INSERT INTO administrative_report_patterns (pattern) VALUES
  ('효력발생안내'),
  ('증권발행실적보고서'),
  ('동일인등출자계열회사와의상품'),
  ('기업설명회'),
  ('IR개최'),
  ('특수관계인과의거래'),
  ('주식매수선택권부여'),
  ('합병등종료보고서'),
  ('자기주식취득결과보고서'),
  ('매매거래정지'),
  ('매매거래정지해제'),
  ('주주명부폐쇄기간'),
  ('기준일설정'),
  ('정정신고'),
  ('임원'),
  ('주요주주특정증권등소유상황보고서'),
  ('사외이사의선임'),
  ('사외이사의해임'),
  ('사외이사의중도퇴임'),
  ('영업보고서');

-- 4. Conglomerate groups table
CREATE TABLE IF NOT EXISTS conglomerate_groups (
  id SERIAL PRIMARY KEY,
  group_name TEXT NOT NULL,
  affiliate_name TEXT NOT NULL,
  designated_year INTEGER NOT NULL
);

-- Insert top 30+ conglomerates (2026 기준 공정위 지정)
INSERT INTO conglomerate_groups (group_name, affiliate_name, designated_year) VALUES
  ('삼성', '삼성전자', 2026),
  ('삼성', '삼성물산', 2026),
  ('삼성', '삼성생명', 2026),
  ('삼성', '삼성전기', 2026),
  ('삼성', '삼성SDI', 2026),
  ('삼성', '삼성화재', 2026),
  ('삼성', '삼성중공업', 2026),
  ('SK', 'SK하이닉스', 2026),
  ('SK', 'SK텔레콤', 2026),
  ('SK', 'SK이노베이션', 2026),
  ('SK', 'SK네트웍스', 2026),
  ('SK', 'SK스퀘어', 2026),
  ('SK', 'SK바이오팜', 2026),
  ('SK', 'SK가스', 2026),
  ('SK', 'SK리츠', 2026),
  ('현대자동차', '현대자동차', 2026),
  ('현대자동차', '기아', 2026),
  ('현대자동차', '현대모비스', 2026),
  ('현대자동차', '현대제철', 2026),
  ('현대자동차', '현대건설', 2026),
  ('현대자동차', '현대위아', 2026),
  ('현대자동차', '현대오토에버', 2026),
  ('LG', 'LG전자', 2026),
  ('LG', 'LG화학', 2026),
  ('LG', 'LG에너지솔루션', 2026),
  ('LG', 'LG유플러스', 2026),
  ('LG', 'LG생활건강', 2026),
  ('LG', 'LG디스플레이', 2026),
  ('롯데', '롯데지주', 2026),
  ('롯데', '롯데쇼핑', 2026),
  ('롯데', '롯데케미칼', 2026),
  ('롯데', '롯데칠성', 2026),
  ('롯데', '롯데웰푸드', 2026),
  ('포스코', '포스코홀딩스', 2026),
  ('포스코', '포스코인터내셔널', 2026),
  ('포스코', '포스코퓨처엠', 2026),
  ('한화', '한화에어로스페이스', 2026),
  ('한화', '한화솔루션', 2026),
  ('한화', '한화생명', 2026),
  ('한화', '한화시스템', 2026),
  ('GS', 'GS칼텍스', 2026),
  ('GS', 'GS리테일', 2026),
  ('GS', 'GS건설', 2026),
  ('HD현대', 'HD현대중공업', 2026),
  ('HD현대', 'HD한국조선해양', 2026),
  ('HD현대', 'HD현대일렉트릭', 2026),
  ('HD현대', 'HD현대건설기계', 2026),
  ('신세계', '신세계', 2026),
  ('신세계', '이마트', 2026),
  ('CJ', 'CJ제일제당', 2026),
  ('CJ', 'CJ대한통운', 2026),
  ('CJ', 'CJENM', 2026),
  ('CJ', 'CJCGV', 2026),
  ('네이버', '네이버', 2026),
  ('네이버', '네이버웹툰', 2026),
  ('카카오', '카카오', 2026),
  ('카카오', '카카오뱅크', 2026),
  ('카카오', '카카오게임즈', 2026),
  ('카카오', '카카오페이', 2026),
  ('넷마블', '넷마블', 2026),
  ('넷마블', '넷마블에프앤씨', 2026),
  ('두산', '두산에너빌리티', 2026),
  ('두산', '두산밥캣', 2026),
  ('두산', '두산로보틱스', 2026),
  ('DL', 'DL이앤씨', 2026),
  ('DL', 'DL케미칼', 2026),
  ('DL', '대림비앤코', 2026),
  ('HYL', 'HL만도', 2026),
  ('HYL', 'HL홀딩스', 2026),
  ('KCC', 'KCC', 2026),
  ('KCC', 'KCC글라스', 2026),
  ('호반건설', '호반건설', 2026),
  ('호반건설', '호반호텔앤리조트', 2026),
  ('태광', '태광산업', 2026),
  ('태광', '티브로드', 2026),
  ('하림', '하림', 2026),
  ('하림', '팜스코', 2026),
  ('SM', 'SM', 2026),
  ('셀트리온', '셀트리온', 2026),
  ('셀트리온', '셀트리온헬스케어', 2026),
  ('한국타이어', '한국타이어앤테크놀로지', 2026),
  ('한국타이어', '한국프리시전웍스', 2026),
  ('에쓰오일', '에쓰오일', 2026),
  ('금호석유화학', '금호석유화학', 2026),
  ('금호석유화학', '금호피앤비', 2026),
  ('DB', 'DB손해보험', 2026),
  ('DB', 'DB하이텍', 2026),
  ('삼천리', '삼천리', 2026),
  ('장금상선', '장금상선', 2026),
  ('코오롱', '코오롱인더스트리', 2026),
  ('코오롱', '코오롱생명과학', 2026),
  ('S&L', 'S&L', 2026),
  ('OCI', 'OCI', 2026),
  ('OCI', 'OCI홀딩스', 2026),
  ('대우건설', '대우건설', 2026),
  ('HMM', 'HMM', 2026),
  ('아모레퍼시픽', '아모레퍼시픽', 2026),
  ('아모레퍼시픽', '아모레G', 2026),
  ('LX', 'LX인터내셔널', 2026),
  ('LX', 'LX하우시스', 2026),
  ('LX', 'LX세미콘', 2026),
  ('미래에셋', '미래에셋증권', 2026),
  ('미래에셋', '미래에셋자산운용', 2026),
  ('NH농협', 'NH농협은행', 2026),
  ('NH농협', 'NH투자증권', 2026),
  ('KDB산업은행', 'KDB산업은행', 2026),
  ('KB금융', 'KB국민은행', 2026),
  ('KB금융', 'KB증권', 2026),
  ('신한금융', '신한은행', 2026),
  ('신한금융', '신한투자증권', 2026),
  ('하나금융', '하나은행', 2026),
  ('하나금융', '하나증권', 2026),
  ('우리금융', '우리은행', 2026),
  ('우리금융', '우리금융지주', 2026);

-- 5. Seed administrative patterns into disclosures (mark existing ones)
-- This is optional; the code will check patterns at runtime
