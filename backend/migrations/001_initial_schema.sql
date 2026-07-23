-- DART0s Initial Schema
-- Run this in Supabase SQL Editor to set up the database.

-- 1. Users table (extends Supabase Auth users if needed, but stand-alone here)
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  plan TEXT NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'developer')),
  api_key TEXT UNIQUE,
  created_at TIMESTAMPTZ DEFAULT now(),
  plan_updated_by TEXT,
  plan_updated_at TIMESTAMPTZ
);

-- 2. Disclosures table
CREATE TABLE IF NOT EXISTS disclosures (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dart_rcept_no TEXT UNIQUE NOT NULL,
  ticker TEXT NOT NULL,
  company_name TEXT NOT NULL,
  title TEXT NOT NULL,
  raw_text TEXT NOT NULL,
  published_at TIMESTAMPTZ NOT NULL,
  category TEXT,
  sub_rule_id TEXT,
  dvi_score NUMERIC,
  impact_level TEXT CHECK (impact_level IN ('HIGH_IMPACT', 'NORMAL', 'LOW_IMPACT')),
  risk_flag TEXT CHECK (risk_flag IN ('CLEAN', 'CAUTION', 'HIGH_RISK_TRAP')),
  deceptive_pattern_detected BOOLEAN,
  momentum_authenticity TEXT CHECK (momentum_authenticity IN ('HIGH', 'MEDIUM', 'LOW')),
  llm_summary TEXT,
  key_metrics JSONB,
  llm_raw_response JSONB,
  llm_status TEXT DEFAULT 'PENDING' CHECK (llm_status IN ('PENDING', 'DONE')),
  is_feed_visible BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_disclosures_published_at ON disclosures(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_disclosures_ticker ON disclosures(ticker);
CREATE INDEX IF NOT EXISTS idx_disclosures_dvi_score ON disclosures(dvi_score DESC);
CREATE INDEX IF NOT EXISTS idx_disclosures_feed_visible
  ON disclosures(is_feed_visible)
  WHERE is_feed_visible = true;

-- 3. Row Level Security (RLS) — basic protection; refine per endpoint
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE disclosures ENABLE ROW LEVEL SECURITY;

-- Users can read their own row
CREATE POLICY users_select_own ON users
  FOR SELECT USING (auth.uid() = id);

-- Disclosures: public read for visible rows (authenticated or anon)
CREATE POLICY disclosures_select_visible ON disclosures
  FOR SELECT USING (is_feed_visible = true);

-- Service role full access (for backend)
CREATE POLICY disclosures_service_all ON disclosures
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY users_service_all ON users
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
