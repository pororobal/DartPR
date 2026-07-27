-- scoring_audit: DVI score 로깅 + LLM enrichment 추적
-- Supabase SQL Editor에서 실행 후 dart_poller가 자동 INSERT
CREATE TABLE IF NOT EXISTS scoring_audit (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    disclosure_id TEXT NOT NULL,
    title TEXT NOT NULL,
    rule_score INT NOT NULL,
    rule_category TEXT NOT NULL,
    rule_sub_rule_id TEXT,
    feed_visible BOOLEAN DEFAULT FALSE,
    llm_triggered BOOLEAN DEFAULT FALSE,
    llm_summary_snippet TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_score ON scoring_audit(rule_score);
CREATE INDEX IF NOT EXISTS idx_audit_created ON scoring_audit(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_category ON scoring_audit(rule_category);
