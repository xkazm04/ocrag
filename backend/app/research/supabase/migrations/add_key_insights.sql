-- Migration: Add Key Insights Schema Extension
-- Date: 2025-12-25
-- Purpose: Enable tagging of "hidden gems" - insights not visible at first sight
--          that emerged from deep research analysis

-- ============================================
-- TABLE 1: key_insights
-- ============================================
-- Stores tagged insights from perspectives and findings
-- that represent non-obvious discoveries

CREATE TABLE IF NOT EXISTS key_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Source reference (one of these should be set)
    perspective_id UUID REFERENCES research_perspectives(id) ON DELETE CASCADE,
    finding_id UUID REFERENCES research_findings(id) ON DELETE CASCADE,
    claim_id UUID REFERENCES knowledge_claims(id) ON DELETE CASCADE,

    -- The insight content
    insight_text TEXT NOT NULL,
    insight_summary VARCHAR(200),  -- Short summary for display

    -- Categorization
    insight_category VARCHAR(50) NOT NULL CHECK (insight_category IN (
        'financial_connection',     -- Hidden money trails, transactions
        'temporal_pattern',         -- Timeline correlations, date patterns
        'network_link',             -- Non-obvious relationship between entities
        'behavioral_pattern',       -- Repeated behaviors, patterns of action
        'document_correlation',     -- Cross-document evidence links
        'contradiction',            -- Conflicting information revealing truth
        'gap_indicator',            -- What's missing that should be there
        'power_structure',          -- Hidden hierarchy or control mechanisms
        'cover_up_evidence',        -- Evidence of concealment
        'other'                     -- For edge cases
    )),

    -- Importance rating
    importance_level VARCHAR(20) NOT NULL DEFAULT 'notable' CHECK (importance_level IN (
        'critical',     -- Major discovery, case-changing
        'significant',  -- Important connection, needs follow-up
        'notable',      -- Interesting, worth remembering
        'minor'         -- Small detail, context only
    )),

    -- Discoverability rating (how hard was this to find?)
    discoverability VARCHAR(20) NOT NULL DEFAULT 'moderate' CHECK (discoverability IN (
        'surface',      -- Obvious from documents
        'moderate',     -- Required some analysis
        'deep',         -- Required cross-referencing multiple sources
        'hidden_gem'    -- Only found through deep analysis, easy to miss
    )),

    -- Manual notes and context
    analyst_notes TEXT,
    follow_up_needed BOOLEAN DEFAULT false,
    follow_up_notes TEXT,

    -- Verification status
    verification_status VARCHAR(20) DEFAULT 'unverified' CHECK (verification_status IN (
        'unverified',   -- Not yet checked
        'verified',     -- Confirmed by additional sources
        'disputed',     -- Contradicting evidence exists
        'false'         -- Determined to be incorrect
    )),

    -- Related entities (for quick filtering)
    related_entities TEXT[],  -- Array of entity names mentioned

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'system',

    -- Ensure at least one source reference
    CONSTRAINT insight_has_source CHECK (
        perspective_id IS NOT NULL OR
        finding_id IS NOT NULL OR
        claim_id IS NOT NULL
    )
);

-- Index for efficient querying
CREATE INDEX IF NOT EXISTS idx_insights_category ON key_insights(insight_category);
CREATE INDEX IF NOT EXISTS idx_insights_importance ON key_insights(importance_level);
CREATE INDEX IF NOT EXISTS idx_insights_discoverability ON key_insights(discoverability);
CREATE INDEX IF NOT EXISTS idx_insights_perspective ON key_insights(perspective_id);
CREATE INDEX IF NOT EXISTS idx_insights_finding ON key_insights(finding_id);
CREATE INDEX IF NOT EXISTS idx_insights_verification ON key_insights(verification_status);

-- Full-text search on insight content
CREATE INDEX IF NOT EXISTS idx_insights_text_search
ON key_insights USING gin(to_tsvector('english', insight_text));

-- ============================================
-- TABLE 2: insight_connections
-- ============================================
-- Links related insights together (insight chains)

CREATE TABLE IF NOT EXISTS insight_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    insight_from_id UUID NOT NULL REFERENCES key_insights(id) ON DELETE CASCADE,
    insight_to_id UUID NOT NULL REFERENCES key_insights(id) ON DELETE CASCADE,
    connection_type VARCHAR(50) NOT NULL CHECK (connection_type IN (
        'supports',         -- This insight supports the other
        'contradicts',      -- This insight contradicts the other
        'extends',          -- This insight adds detail to the other
        'precedes',         -- This insight happened before (temporal)
        'follows',          -- This insight follows from the other
        'same_pattern',     -- Both insights show same pattern
        'related'           -- General relation
    )),
    connection_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT no_self_connection CHECK (insight_from_id != insight_to_id),
    CONSTRAINT unique_connection UNIQUE (insight_from_id, insight_to_id, connection_type)
);

-- ============================================
-- TABLE 3: insight_tags
-- ============================================
-- Flexible tagging system for insights

CREATE TABLE IF NOT EXISTS insight_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tag_name VARCHAR(50) NOT NULL UNIQUE,
    tag_description TEXT,
    tag_color VARCHAR(7) DEFAULT '#6B7280',  -- Hex color for UI
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Junction table for many-to-many
CREATE TABLE IF NOT EXISTS insight_tag_links (
    insight_id UUID NOT NULL REFERENCES key_insights(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES insight_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (insight_id, tag_id)
);

-- ============================================
-- SEED DATA: Default tags
-- ============================================

INSERT INTO insight_tags (tag_name, tag_description, tag_color) VALUES
    ('money-trail', 'Financial connections and transactions', '#10B981'),
    ('power-dynamics', 'Control, influence, hierarchy', '#8B5CF6'),
    ('timeline-key', 'Critical date or sequence', '#F59E0B'),
    ('witness-link', 'Connected to witness testimony', '#EF4444'),
    ('document-proof', 'Backed by document evidence', '#3B82F6'),
    ('follow-up-priority', 'Needs immediate follow-up', '#EC4899'),
    ('cross-reference', 'Links multiple sources', '#14B8A6'),
    ('legal-relevance', 'Relevant to legal proceedings', '#6366F1')
ON CONFLICT (tag_name) DO NOTHING;

-- ============================================
-- VIEW: insight_summary
-- ============================================
-- Aggregated view for quick insight overview

CREATE OR REPLACE VIEW insight_summary AS
SELECT
    ki.id,
    ki.insight_summary,
    ki.insight_category,
    ki.importance_level,
    ki.discoverability,
    ki.verification_status,
    ki.follow_up_needed,
    ki.related_entities,
    ki.created_at,
    CASE
        WHEN ki.perspective_id IS NOT NULL THEN 'perspective'
        WHEN ki.finding_id IS NOT NULL THEN 'finding'
        WHEN ki.claim_id IS NOT NULL THEN 'claim'
    END as source_type,
    COALESCE(ki.perspective_id, ki.finding_id, ki.claim_id) as source_id,
    array_agg(DISTINCT it.tag_name) FILTER (WHERE it.tag_name IS NOT NULL) as tags
FROM key_insights ki
LEFT JOIN insight_tag_links itl ON ki.id = itl.insight_id
LEFT JOIN insight_tags it ON itl.tag_id = it.id
GROUP BY ki.id;

-- ============================================
-- FUNCTION: Update timestamp trigger
-- ============================================

CREATE OR REPLACE FUNCTION update_insight_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_insight_updated ON key_insights;
CREATE TRIGGER trg_insight_updated
    BEFORE UPDATE ON key_insights
    FOR EACH ROW
    EXECUTE FUNCTION update_insight_timestamp();

-- ============================================
-- SAMPLE QUERIES (for reference)
-- ============================================

-- Find all critical hidden gems:
-- SELECT * FROM key_insights
-- WHERE importance_level = 'critical' AND discoverability = 'hidden_gem';

-- Find insights by category with tags:
-- SELECT * FROM insight_summary
-- WHERE insight_category = 'financial_connection';

-- Find insights needing follow-up:
-- SELECT * FROM key_insights
-- WHERE follow_up_needed = true
-- ORDER BY importance_level DESC;

-- Find connected insights:
-- SELECT ki1.insight_summary as from_insight,
--        ic.connection_type,
--        ki2.insight_summary as to_insight
-- FROM insight_connections ic
-- JOIN key_insights ki1 ON ic.insight_from_id = ki1.id
-- JOIN key_insights ki2 ON ic.insight_to_id = ki2.id;
