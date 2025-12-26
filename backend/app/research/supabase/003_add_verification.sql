-- Migration 003: Add verification and document extraction tables
-- For fact-checking statements and extracting evidence from documents

-- =============================================================================
-- VERIFICATION RESULTS TABLE
-- Stores fact-check results with caching support
-- =============================================================================

CREATE TABLE IF NOT EXISTS verification_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Input
    statement TEXT NOT NULL,
    statement_hash TEXT NOT NULL,  -- SHA256 for caching

    -- Verdict
    verdict TEXT NOT NULL CHECK (verdict IN ('supported', 'contradicted', 'inconclusive')),
    confidence_score REAL DEFAULT 0.5 CHECK (confidence_score >= 0 AND confidence_score <= 1),

    -- Evidence
    supporting_evidence JSONB DEFAULT '[]',
    contradicting_evidence JSONB DEFAULT '[]',

    -- Related claims (read-only lookup, stored as reference)
    related_claim_ids UUID[] DEFAULT '{}',
    related_claims_summary TEXT,

    -- Web sources
    web_sources JSONB DEFAULT '[]',
    grounding_metadata JSONB,

    -- Cache control
    expires_at TIMESTAMPTZ,
    hit_count INT DEFAULT 0,

    -- Audit
    workspace_id TEXT DEFAULT 'default',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for verification_results
CREATE INDEX IF NOT EXISTS idx_verification_hash ON verification_results(statement_hash);
CREATE INDEX IF NOT EXISTS idx_verification_workspace ON verification_results(workspace_id);
CREATE INDEX IF NOT EXISTS idx_verification_expires ON verification_results(expires_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_verification_cache ON verification_results(statement_hash, workspace_id);


-- =============================================================================
-- DOCUMENT EXTRACTIONS TABLE
-- Tracks document processing for evidence extraction
-- =============================================================================

CREATE TABLE IF NOT EXISTS document_extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Input
    topic_id UUID REFERENCES knowledge_topics(id) ON DELETE SET NULL,
    document_type TEXT CHECK (document_type IN ('text', 'pdf')),
    document_hash TEXT NOT NULL,
    document_preview TEXT,  -- First 500 chars for reference

    -- Results summary
    status TEXT DEFAULT 'completed' CHECK (status IN ('processing', 'completed', 'failed')),
    findings_count INT DEFAULT 0,
    quality_filtered_count INT DEFAULT 0,

    -- Stats
    new_findings INT DEFAULT 0,
    updated_findings INT DEFAULT 0,
    skipped_findings INT DEFAULT 0,

    -- Metadata
    processing_time_ms INT,
    error_message TEXT,
    workspace_id TEXT DEFAULT 'default',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for document_extractions
CREATE INDEX IF NOT EXISTS idx_extraction_topic ON document_extractions(topic_id);
CREATE INDEX IF NOT EXISTS idx_extraction_workspace ON document_extractions(workspace_id);
CREATE INDEX IF NOT EXISTS idx_extraction_hash ON document_extractions(document_hash);


-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Function to increment verification hit count
CREATE OR REPLACE FUNCTION increment_verification_hit(v_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE verification_results
    SET hit_count = hit_count + 1,
        updated_at = NOW()
    WHERE id = v_id;
END;
$$ LANGUAGE plpgsql;

-- Function to clean expired verifications
CREATE OR REPLACE FUNCTION cleanup_expired_verifications()
RETURNS INT AS $$
DECLARE
    deleted_count INT;
BEGIN
    DELETE FROM verification_results
    WHERE expires_at < NOW();

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
