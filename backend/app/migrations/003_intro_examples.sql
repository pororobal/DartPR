-- 매일 20:00 KST에 갱신되는 소개페이지 예시 공시
-- Supabase SQL Editor에서 service_role로 실행 필요
CREATE TABLE IF NOT EXISTS intro_examples (
  id BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  target_date DATE NOT NULL DEFAULT CURRENT_DATE,
  examples JSONB NOT NULL DEFAULT '[]'::jsonb,
  CONSTRAINT unique_target_date UNIQUE (target_date)
);

ALTER TABLE intro_examples ENABLE ROW LEVEL SECURITY;

-- anon/pro service_role 모두 읽기 가능
CREATE POLICY "Anyone can read intro_examples"
  ON intro_examples FOR SELECT
  USING (true);
