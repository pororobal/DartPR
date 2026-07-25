-- Performance indexes for DART0s
-- Run this in Supabase Dashboard → SQL Editor

-- 1. Live feed query: WHERE is_feed_visible = TRUE ORDER BY published_at DESC LIMIT 20
CREATE INDEX IF NOT EXISTS idx_disclosures_feed
    ON public.disclosures (is_feed_visible, published_at DESC);

-- 2. History search: filter by ticker (partial match)
CREATE INDEX IF NOT EXISTS idx_disclosures_ticker
    ON public.disclosures USING gin (ticker gin_trgm_ops);

-- 3. History search: filter by company_name (partial match)
CREATE INDEX IF NOT EXISTS idx_disclosures_company_name
    ON public.disclosures USING gin (company_name gin_trgm_ops);

-- 4. Auth lookup: users by email
CREATE INDEX IF NOT EXISTS idx_users_email
    ON public.users (email);

-- 5. History: filter by category
CREATE INDEX IF NOT EXISTS idx_disclosures_category
    ON public.disclosures (category);

-- 6. History: filter by dvi_score range
CREATE INDEX IF NOT EXISTS idx_disclosures_score
    ON public.disclosures (dvi_score);

-- Note: gin_trgm_ops requires pg_trgm extension.
-- Run this first if not already enabled:
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;
