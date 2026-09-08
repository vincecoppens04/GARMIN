-- =====================================================================
-- AUGUR Version 2: Advanced Sports Science & Autonomic Matrix Migration
-- =====================================================================
-- Run this SQL in your Supabase project's SQL Editor (https://supabase.com/dashboard)
-- All statements use IF NOT EXISTS to guarantee idempotent and safe execution.

-- 1. Extend daily_summaries table with Version 2 physiological metrics
ALTER TABLE daily_summaries
ADD COLUMN IF NOT EXISTS immune_strain_index NUMERIC,
ADD COLUMN IF NOT EXISTS immune_tier TEXT,
ADD COLUMN IF NOT EXISTS nocturnal_dip_pct NUMERIC,
ADD COLUMN IF NOT EXISTS sleep_curve_type TEXT,
ADD COLUMN IF NOT EXISTS hrv_trend_slope NUMERIC,
ADD COLUMN IF NOT EXISTS restoration_pct NUMERIC,
ADD COLUMN IF NOT EXISTS restlessness_index NUMERIC,
ADD COLUMN IF NOT EXISTS social_jetlag_min NUMERIC,
ADD COLUMN IF NOT EXISTS chronic_strain_debt NUMERIC,
ADD COLUMN IF NOT EXISTS alcohol_latency_hr NUMERIC,
ADD COLUMN IF NOT EXISTS stress_balance_ratio NUMERIC,
ADD COLUMN IF NOT EXISTS recommended_bedtime TEXT,
ADD COLUMN IF NOT EXISTS sleep_equation_str TEXT,
ADD COLUMN IF NOT EXISTS metrics_v2 JSONB DEFAULT '{}'::jsonb;

-- 2. Extend activities table with HRR and Metabolic metrics
ALTER TABLE activities
ADD COLUMN IF NOT EXISTS hrr_60s INTEGER,
ADD COLUMN IF NOT EXISTS hrr_120s INTEGER,
ADD COLUMN IF NOT EXISTS hrr_benchmark TEXT,
ADD COLUMN IF NOT EXISTS glycogen_depleted_kcal NUMERIC,
ADD COLUMN IF NOT EXISTS carb_refuel_target_g NUMERIC,
ADD COLUMN IF NOT EXISTS stress_recovery_min NUMERIC,
ADD COLUMN IF NOT EXISTS metrics_v2 JSONB DEFAULT '{}'::jsonb;

-- 3. Create index on JSONB fields for rapid querying
CREATE INDEX IF NOT EXISTS idx_daily_summaries_metrics_v2 ON daily_summaries USING gin (metrics_v2);
CREATE INDEX IF NOT EXISTS idx_activities_metrics_v2 ON activities USING gin (metrics_v2);

-- Verification Query
COMMENT ON COLUMN daily_summaries.metrics_v2 IS 'AUGUR V2 full computational telemetry payload';
COMMENT ON COLUMN activities.metrics_v2 IS 'AUGUR V2 metabolic and autonomic recovery payload';
