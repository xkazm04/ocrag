-- Migration: Add research_jobs table for async job tracking
-- Version: 002
-- Description: Supports async research API with job submission and status polling

-- ============================================================================
-- RESEARCH JOBS TABLE
-- ============================================================================
-- Tracks async research jobs with status, progress, and completion stats

CREATE TABLE IF NOT EXISTS research_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to research session (created during processing)
    session_id UUID REFERENCES research_sessions(id) ON DELETE SET NULL,

    -- Job metadata
    query TEXT NOT NULL,
    workspace_id TEXT NOT NULL DEFAULT 'default',
    template_type TEXT NOT NULL DEFAULT 'investigative',
    parameters JSONB DEFAULT '{}',

    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    current_stage TEXT DEFAULT NULL,
    progress_pct REAL DEFAULT 0.0 CHECK (progress_pct >= 0 AND progress_pct <= 100),

    -- Timestamps
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Error handling
    error_message TEXT,
    error_details JSONB,

    -- Completion stats (populated when completed)
    -- Example structure:
    -- {
    --   "findings_count": 15,
    --   "perspectives_count": 5,
    --   "sources_count": 42,
    --   "key_summary": "Brief summary of research findings...",
    --   "token_usage": {"input": 5000, "output": 2000, "total": 7000},
    --   "cost_usd": 0.05,
    --   "duration_seconds": 45.2,
    --   "topic_id": "uuid-if-matched",
    --   "topic_name": "Topic Name",
    --   "dedup_stats": {"new": 10, "updated": 3, "discarded": 2}
    -- }
    stats JSONB DEFAULT NULL,

    -- Topic matching result
    matched_topic_id UUID REFERENCES knowledge_topics(id) ON DELETE SET NULL,
    topic_match_confidence REAL,
    topic_match_reasoning TEXT
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Primary query patterns
CREATE INDEX IF NOT EXISTS idx_jobs_status ON research_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_workspace ON research_jobs(workspace_id);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON research_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_session ON research_jobs(session_id);

-- Composite index for workspace + status queries
CREATE INDEX IF NOT EXISTS idx_jobs_workspace_status
    ON research_jobs(workspace_id, status);

-- Partial index for active jobs (pending/running)
CREATE INDEX IF NOT EXISTS idx_jobs_active
    ON research_jobs(workspace_id, created_at DESC)
    WHERE status IN ('pending', 'running');

-- Topic matching lookups
CREATE INDEX IF NOT EXISTS idx_jobs_matched_topic ON research_jobs(matched_topic_id);

-- ============================================================================
-- TRIGGER: Auto-update updated_at timestamp
-- ============================================================================

CREATE OR REPLACE FUNCTION update_research_jobs_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS research_jobs_updated_at ON research_jobs;

CREATE TRIGGER research_jobs_updated_at
    BEFORE UPDATE ON research_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_research_jobs_timestamp();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE research_jobs IS 'Async research job tracking for submit/poll pattern';
COMMENT ON COLUMN research_jobs.status IS 'Job status: pending, running, completed, failed, cancelled';
COMMENT ON COLUMN research_jobs.current_stage IS 'Current processing stage: health_check, topic_matching, decomposition, searching, extraction, perspectives, relationships, deduplication, completed';
COMMENT ON COLUMN research_jobs.progress_pct IS 'Progress percentage 0-100';
COMMENT ON COLUMN research_jobs.stats IS 'Completion stats JSON with findings_count, key_summary, token_usage, etc.';
COMMENT ON COLUMN research_jobs.matched_topic_id IS 'Topic matched via LLM analysis before processing';
