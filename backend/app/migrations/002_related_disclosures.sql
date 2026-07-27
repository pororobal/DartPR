-- 관련공시 컨텍스트 연결을 위한 컬럼 추가
-- Supabase SQL Editor에서 service_role로 실행 필요
ALTER TABLE disclosures
  ADD COLUMN IF NOT EXISTS related_status TEXT DEFAULT 'NONE',
  ADD COLUMN IF NOT EXISTS merged_summary TEXT,
  ADD COLUMN IF NOT EXISTS merged_sentiment TEXT,
  ADD COLUMN IF NOT EXISTS merged_horizon TEXT,
  ADD COLUMN IF NOT EXISTS merged_confidence TEXT,
  ADD COLUMN IF NOT EXISTS related_disclosures JSONB DEFAULT '[]'::jsonb;
