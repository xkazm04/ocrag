-- Migration: Fix research_sources and research_perspectives constraints
-- Date: 2025-12-25
-- Purpose: Fix database constraint issues causing save failures

-- ============================================
-- FIX 1: research_sources table
-- ============================================

-- 1a. Add unique constraint for upsert on (session_id, url)
-- First, remove any duplicate entries that would violate the constraint
DELETE FROM research_sources a
USING research_sources b
WHERE a.id < b.id
  AND a.session_id = b.session_id
  AND a.url = b.url;

-- Create the unique constraint for upsert
CREATE UNIQUE INDEX IF NOT EXISTS idx_sources_session_url
ON research_sources(session_id, url);

-- 1b. Make url_hash nullable (it's generated, not always provided)
ALTER TABLE research_sources
ALTER COLUMN url_hash DROP NOT NULL;

-- 1c. Add 'web' to source_type constraint
ALTER TABLE research_sources
DROP CONSTRAINT IF EXISTS research_sources_source_type_check;

ALTER TABLE research_sources
ADD CONSTRAINT research_sources_source_type_check
CHECK (source_type IN (
    'news', 'academic', 'government', 'corporate', 'blog',
    'social', 'wiki', 'unknown', 'web', 'database', 'api'
));

-- 1d. Create trigger to auto-generate url_hash if not provided
CREATE OR REPLACE FUNCTION generate_url_hash()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.url_hash IS NULL AND NEW.url IS NOT NULL THEN
        NEW.url_hash := md5(NEW.url);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_generate_url_hash ON research_sources;
CREATE TRIGGER trg_generate_url_hash
    BEFORE INSERT OR UPDATE ON research_sources
    FOR EACH ROW
    EXECUTE FUNCTION generate_url_hash();

-- ============================================
-- FIX 2: research_perspectives table
-- ============================================

-- 2a. Expand perspective_type constraint to include all used types
ALTER TABLE research_perspectives
DROP CONSTRAINT IF EXISTS research_perspectives_perspective_type_check;

ALTER TABLE research_perspectives
ADD CONSTRAINT research_perspectives_perspective_type_check
CHECK (perspective_type IN (
    -- Original types
    'historical', 'political', 'economic', 'psychological',
    'military', 'social', 'technological',
    -- Investigative types
    'financial', 'journalist', 'conspirator', 'network',
    -- Business/competitive types
    'competitive_advantage', 'pricing_strategy', 'market_position', 'swot',
    -- Financial analysis types
    'valuation', 'risk', 'investment',
    -- Legal/compliance types
    'compliance', 'regulatory_risk', 'legal',
    -- Technical types
    'technical', 'ethical',
    -- Generic fallback
    'unknown', 'general'
));

-- ============================================
-- FIX 3: research_findings table
-- ============================================

-- 3a. Add 'financial' to finding_type if not already present
ALTER TABLE research_findings
DROP CONSTRAINT IF EXISTS research_findings_finding_type_check;

ALTER TABLE research_findings
ADD CONSTRAINT research_findings_finding_type_check
CHECK (finding_type IN (
    'fact', 'claim', 'event', 'actor', 'relationship',
    'pattern', 'gap', 'evidence', 'financial', 'prediction'
));

-- ============================================
-- VERIFICATION QUERIES (run after migration)
-- ============================================

-- Check constraints are updated
-- SELECT conname, pg_get_constraintdef(oid)
-- FROM pg_constraint
-- WHERE conrelid = 'research_sources'::regclass;

-- SELECT conname, pg_get_constraintdef(oid)
-- FROM pg_constraint
-- WHERE conrelid = 'research_perspectives'::regclass;

-- SELECT conname, pg_get_constraintdef(oid)
-- FROM pg_constraint
-- WHERE conrelid = 'research_findings'::regclass;
