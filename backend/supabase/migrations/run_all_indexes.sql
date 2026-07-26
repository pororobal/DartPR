-- Run this in Supabase Dashboard → SQL Editor (한 번만 실행)
-- 모든 성능 인덱스를 일괄 생성합니다.

-- 1. pg_trgm 확장 (부분일치 검색용)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 2. 실시간/Live feed: WHERE is_feed_visible = TRUE ORDER BY published_at DESC
--    이 인덱스가 없으면 10초+ 소요
CREATE INDEX IF NOT EXISTS idx_disclosures_feed
    ON public.disclosures (is_feed_visible, published_at DESC);

-- 3. 히스토리: ticker 부분일치 검색
CREATE INDEX IF NOT EXISTS idx_disclosures_ticker
    ON public.disclosures USING gin (ticker gin_trgm_ops);

-- 4. 히스토리: company_name 부분일치 검색
CREATE INDEX IF NOT EXISTS idx_disclosures_company_name
    ON public.disclosures USING gin (company_name gin_trgm_ops);

-- 5. 로그인: users.email 조회
CREATE INDEX IF NOT EXISTS idx_users_email
    ON public.users (email);

-- 6. 히스토리: category 필터
CREATE INDEX IF NOT EXISTS idx_disclosures_category
    ON public.disclosures (category);

-- 7. 히스토리: dvi_score 범위 필터
CREATE INDEX IF NOT EXISTS idx_disclosures_score
    ON public.disclosures (dvi_score);

-- 8. llm_status 필터 (PENDING/DONE 조회)
CREATE INDEX IF NOT EXISTS idx_disclosures_llm_status
    ON public.disclosures (llm_status);
