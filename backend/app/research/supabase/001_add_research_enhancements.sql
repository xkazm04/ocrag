-- ============================================
-- Migration 001: Research Enhancements
-- ============================================
-- Adds tables for:
-- - Query decomposition tracking
-- - Sub-query execution
-- - Finding-level relationships
-- - Contradictions and research gaps
-- - Causal chains
-- - Finding-level perspectives
-- ============================================

-- ============================================
-- QUERY DECOMPOSITIONS
-- Track how complex queries are decomposed
-- ============================================
CREATE TABLE IF NOT EXISTS query_decompositions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE,

    -- Original query
    original_query TEXT NOT NULL,

    -- Decomposition strategy
    decomposition_strategy TEXT NOT NULL CHECK (decomposition_strategy IN (
        'temporal',   -- Split by time periods
        'thematic',   -- Split by themes/aspects
        'actor',      -- Split by key actors
        'hybrid',     -- Combination of strategies
        'none'        -- No decomposition needed
    )),
    needs_decomposition BOOLEAN DEFAULT FALSE,

    -- Detected elements
    detected_themes TEXT[],
    detected_actors TEXT[],
    date_range_years INT,
    decomposition_reasoning TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- SUB-QUERIES
-- Individual queries from decomposition
-- ============================================
CREATE TABLE IF NOT EXISTS sub_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decomposition_id UUID REFERENCES query_decompositions(id) ON DELETE CASCADE,

    -- Sub-query identification
    sub_query_id TEXT NOT NULL,  -- sq_1, sq_2, etc.
    query_text TEXT NOT NULL,

    -- Execution ordering
    batch_order INT NOT NULL,
    depends_on TEXT[],  -- IDs of dependent sub-queries

    -- Focus
    focus_theme TEXT,
    focus_actors TEXT[],
    composition_role TEXT CHECK (composition_role IN (
        'background',   -- Provides context
        'primary',      -- Main focus
        'synthesis',    -- Combines results
        'equal'         -- Equal importance
    )),

    -- Temporal bounds
    date_start DATE,
    date_end DATE,

    -- Execution results
    executed_at TIMESTAMPTZ,
    result_finding_count INT,
    result_source_count INT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- FINDING RELATIONSHIPS
-- Session-scoped relationships between findings
-- ============================================
CREATE TABLE IF NOT EXISTS finding_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE,

    source_finding_id UUID REFERENCES research_findings(id) ON DELETE CASCADE,
    target_finding_id UUID REFERENCES research_findings(id) ON DELETE CASCADE,

    -- Relationship type
    relationship_type TEXT NOT NULL CHECK (relationship_type IN (
        'causes',       -- Source caused/led to target
        'supports',     -- Source provides evidence for target
        'contradicts',  -- Source conflicts with target
        'expands',      -- Source adds detail to target
        'precedes',     -- Source happened before target
        'involves'      -- Findings share common actors/entities
    )),

    -- Relationship metadata
    strength FLOAT DEFAULT 0.5 CHECK (strength >= 0 AND strength <= 1),
    description TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(source_finding_id, target_finding_id, relationship_type)
);

-- ============================================
-- RESEARCH CONTRADICTIONS
-- Conflicting claims detected during research
-- ============================================
CREATE TABLE IF NOT EXISTS research_contradictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE,

    finding_id_1 UUID REFERENCES research_findings(id) ON DELETE CASCADE,
    finding_id_2 UUID REFERENCES research_findings(id) ON DELETE CASCADE,

    -- The conflicting claims
    claim_1 TEXT NOT NULL,
    claim_2 TEXT NOT NULL,

    -- Sources for each claim
    source_1 TEXT,
    source_2 TEXT,

    -- Analysis
    significance TEXT,
    resolution_hint TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- RESEARCH GAPS
-- Identified gaps in research coverage
-- ============================================
CREATE TABLE IF NOT EXISTS research_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE,

    -- Gap type
    gap_type TEXT NOT NULL CHECK (gap_type IN (
        'temporal',     -- Missing time period coverage
        'actor',        -- Missing actor information
        'topic',        -- Missing topic/theme coverage
        'evidence',     -- Claims lacking evidence
        'geographic'    -- Missing geographic coverage
    )),

    -- Gap details
    description TEXT NOT NULL,
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low')),

    -- Suggestions
    suggested_queries TEXT[],
    related_finding_ids UUID[],

    -- Temporal gaps
    gap_start DATE,
    gap_end DATE,

    -- Actor gaps
    missing_actor TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- CAUSAL CHAINS
-- Sequences of cause-effect relationships
-- ============================================
CREATE TABLE IF NOT EXISTS causal_chains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE,

    -- Chain of finding IDs in causal order
    finding_ids UUID[] NOT NULL,

    -- Description of each step in the chain
    descriptions TEXT[],

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- FINDING PERSPECTIVES
-- Perspective analysis at the individual finding level
-- ============================================
CREATE TABLE IF NOT EXISTS finding_perspectives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE,
    finding_id UUID REFERENCES research_findings(id) ON DELETE CASCADE,

    -- Perspective type
    perspective_type TEXT NOT NULL CHECK (perspective_type IN (
        'historical',
        'financial',
        'journalist',
        'conspirator',
        'network'
    )),

    -- Analysis data (type-specific JSONB)
    -- Historical: {historical_context, precedents, patterns, key_insight}
    -- Financial: {economic_context, beneficiaries, follow_the_money}
    -- Journalist: {source_assessment, red_flags, questions}
    -- Conspirator: {alternative_explanation, probability, supporting_evidence}
    -- Network: {actor_role, connections, power_dynamics}
    analysis_data JSONB NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(finding_id, perspective_type)
);

-- ============================================
-- INDEXES - BASIC
-- ============================================

-- Query decompositions
CREATE INDEX IF NOT EXISTS idx_decomp_session ON query_decompositions(session_id);

-- Sub-queries
CREATE INDEX IF NOT EXISTS idx_subq_decomp ON sub_queries(decomposition_id);
CREATE INDEX IF NOT EXISTS idx_subq_batch ON sub_queries(batch_order);

-- Finding relationships
CREATE INDEX IF NOT EXISTS idx_findrel_session ON finding_relationships(session_id);
CREATE INDEX IF NOT EXISTS idx_findrel_source ON finding_relationships(source_finding_id);
CREATE INDEX IF NOT EXISTS idx_findrel_target ON finding_relationships(target_finding_id);
CREATE INDEX IF NOT EXISTS idx_findrel_type ON finding_relationships(relationship_type);

-- Contradictions
CREATE INDEX IF NOT EXISTS idx_contra_session ON research_contradictions(session_id);
CREATE INDEX IF NOT EXISTS idx_contra_finding1 ON research_contradictions(finding_id_1);
CREATE INDEX IF NOT EXISTS idx_contra_finding2 ON research_contradictions(finding_id_2);

-- Research gaps
CREATE INDEX IF NOT EXISTS idx_gaps_session ON research_gaps(session_id);
CREATE INDEX IF NOT EXISTS idx_gaps_type ON research_gaps(gap_type);
CREATE INDEX IF NOT EXISTS idx_gaps_priority ON research_gaps(priority);

-- Causal chains
CREATE INDEX IF NOT EXISTS idx_chains_session ON causal_chains(session_id);

-- Finding perspectives
CREATE INDEX IF NOT EXISTS idx_findpersp_session ON finding_perspectives(session_id);
CREATE INDEX IF NOT EXISTS idx_findpersp_finding ON finding_perspectives(finding_id);
CREATE INDEX IF NOT EXISTS idx_findpersp_type ON finding_perspectives(perspective_type);

-- ============================================
-- ADVANCED INDEXES - PERFORMANCE OPTIMIZATION
-- For tables expected to grow to tens of thousands of rows
-- ============================================

-- ----------------------------------------
-- COMPOSITE INDEXES for common query patterns
-- ----------------------------------------

-- Finding perspectives: Most common query is "get all perspectives for a finding"
-- Covering index includes analysis_data to avoid table lookup
CREATE INDEX IF NOT EXISTS idx_findpersp_finding_type_cover
    ON finding_perspectives(finding_id, perspective_type)
    INCLUDE (analysis_data, created_at);

-- Finding perspectives: Query by session + type (e.g., "all historical perspectives in session")
CREATE INDEX IF NOT EXISTS idx_findpersp_session_type
    ON finding_perspectives(session_id, perspective_type);

-- Finding relationships: Graph traversal queries need fast source/target + type lookups
CREATE INDEX IF NOT EXISTS idx_findrel_source_type
    ON finding_relationships(source_finding_id, relationship_type)
    INCLUDE (target_finding_id, strength);

CREATE INDEX IF NOT EXISTS idx_findrel_target_type
    ON finding_relationships(target_finding_id, relationship_type)
    INCLUDE (source_finding_id, strength);

-- Finding relationships: Session-scoped graph queries
CREATE INDEX IF NOT EXISTS idx_findrel_session_type_strength
    ON finding_relationships(session_id, relationship_type, strength DESC);

-- Sub-queries: Common pattern is getting all sub-queries for a decomposition in order
CREATE INDEX IF NOT EXISTS idx_subq_decomp_order
    ON sub_queries(decomposition_id, batch_order)
    INCLUDE (sub_query_id, query_text, composition_role);

-- Research gaps: Priority-based queries within sessions
CREATE INDEX IF NOT EXISTS idx_gaps_session_priority
    ON research_gaps(session_id, priority, gap_type);

-- ----------------------------------------
-- PARTIAL INDEXES for filtered queries
-- ----------------------------------------

-- High-priority gaps only (frequently queried subset)
CREATE INDEX IF NOT EXISTS idx_gaps_high_priority
    ON research_gaps(session_id, created_at DESC)
    WHERE priority = 'high';

-- Active/executed sub-queries only
CREATE INDEX IF NOT EXISTS idx_subq_executed
    ON sub_queries(decomposition_id, executed_at)
    WHERE executed_at IS NOT NULL;

-- Pending sub-queries (not yet executed)
CREATE INDEX IF NOT EXISTS idx_subq_pending
    ON sub_queries(decomposition_id, batch_order)
    WHERE executed_at IS NULL;

-- Causal relationships only (for chain building)
CREATE INDEX IF NOT EXISTS idx_findrel_causal
    ON finding_relationships(source_finding_id, target_finding_id)
    WHERE relationship_type IN ('causes', 'precedes');

-- Contradiction relationships only
CREATE INDEX IF NOT EXISTS idx_findrel_contradicts
    ON finding_relationships(session_id, source_finding_id, target_finding_id)
    WHERE relationship_type = 'contradicts';

-- Strong relationships only (strength > 0.7)
CREATE INDEX IF NOT EXISTS idx_findrel_strong
    ON finding_relationships(session_id, relationship_type)
    WHERE strength > 0.7;

-- Decompositions that needed splitting
CREATE INDEX IF NOT EXISTS idx_decomp_needed
    ON query_decompositions(session_id, decomposition_strategy)
    WHERE needs_decomposition = TRUE;

-- ----------------------------------------
-- GIN INDEXES for array columns
-- Enables fast array containment queries (@>, <@, &&)
-- ----------------------------------------

-- Query decompositions: Search by detected themes/actors
CREATE INDEX IF NOT EXISTS idx_decomp_themes_gin
    ON query_decompositions USING GIN(detected_themes);

CREATE INDEX IF NOT EXISTS idx_decomp_actors_gin
    ON query_decompositions USING GIN(detected_actors);

-- Sub-queries: Search by focus actors and dependencies
CREATE INDEX IF NOT EXISTS idx_subq_actors_gin
    ON sub_queries USING GIN(focus_actors);

CREATE INDEX IF NOT EXISTS idx_subq_depends_gin
    ON sub_queries USING GIN(depends_on);

-- Research gaps: Search by suggested queries and related findings
CREATE INDEX IF NOT EXISTS idx_gaps_queries_gin
    ON research_gaps USING GIN(suggested_queries);

CREATE INDEX IF NOT EXISTS idx_gaps_findings_gin
    ON research_gaps USING GIN(related_finding_ids);

-- Causal chains: Search for chains containing specific findings
CREATE INDEX IF NOT EXISTS idx_chains_findings_gin
    ON causal_chains USING GIN(finding_ids);

-- ----------------------------------------
-- JSONB INDEXES for analysis_data queries
-- ----------------------------------------

-- GIN index for full JSONB search (key existence, containment)
CREATE INDEX IF NOT EXISTS idx_findpersp_data_gin
    ON finding_perspectives USING GIN(analysis_data);

-- Path-specific indexes for common JSONB queries
-- These use jsonb_path_ops for smaller, faster indexes

-- Historical: Search by precedents
CREATE INDEX IF NOT EXISTS idx_findpersp_historical_precedents
    ON finding_perspectives USING GIN((analysis_data->'precedents') jsonb_path_ops)
    WHERE perspective_type = 'historical';

-- Financial: Search by beneficiaries
CREATE INDEX IF NOT EXISTS idx_findpersp_financial_beneficiaries
    ON finding_perspectives USING GIN((analysis_data->'beneficiaries') jsonb_path_ops)
    WHERE perspective_type = 'financial';

-- Journalist: Search by red_flags
CREATE INDEX IF NOT EXISTS idx_findpersp_journalist_redflags
    ON finding_perspectives USING GIN((analysis_data->'red_flags') jsonb_path_ops)
    WHERE perspective_type = 'journalist';

-- Network: Search by connections
CREATE INDEX IF NOT EXISTS idx_findpersp_network_connections
    ON finding_perspectives USING GIN((analysis_data->'connections') jsonb_path_ops)
    WHERE perspective_type = 'network';

-- Expression index for key_insight text search
CREATE INDEX IF NOT EXISTS idx_findpersp_key_insight
    ON finding_perspectives((analysis_data->>'key_insight'))
    WHERE analysis_data->>'key_insight' IS NOT NULL;

-- ----------------------------------------
-- BRIN INDEXES for time-series data
-- Excellent for append-only tables with correlated created_at
-- Much smaller than B-tree, fast for range queries
-- ----------------------------------------

CREATE INDEX IF NOT EXISTS idx_findpersp_created_brin
    ON finding_perspectives USING BRIN(created_at)
    WITH (pages_per_range = 32);

CREATE INDEX IF NOT EXISTS idx_findrel_created_brin
    ON finding_relationships USING BRIN(created_at)
    WITH (pages_per_range = 32);

CREATE INDEX IF NOT EXISTS idx_contra_created_brin
    ON research_contradictions USING BRIN(created_at)
    WITH (pages_per_range = 32);

CREATE INDEX IF NOT EXISTS idx_gaps_created_brin
    ON research_gaps USING BRIN(created_at)
    WITH (pages_per_range = 32);

CREATE INDEX IF NOT EXISTS idx_chains_created_brin
    ON causal_chains USING BRIN(created_at)
    WITH (pages_per_range = 32);

CREATE INDEX IF NOT EXISTS idx_subq_created_brin
    ON sub_queries USING BRIN(created_at)
    WITH (pages_per_range = 32);

-- ----------------------------------------
-- EXPRESSION INDEXES for computed values
-- ----------------------------------------

-- Finding relationships: Index on relationship strength bucket for histograms
CREATE INDEX IF NOT EXISTS idx_findrel_strength_bucket
    ON finding_relationships((
        CASE
            WHEN strength >= 0.8 THEN 'very_strong'
            WHEN strength >= 0.6 THEN 'strong'
            WHEN strength >= 0.4 THEN 'moderate'
            ELSE 'weak'
        END
    ));

-- Research gaps: Index on temporal gap duration (for sorting/filtering)
CREATE INDEX IF NOT EXISTS idx_gaps_duration
    ON research_gaps((gap_end - gap_start))
    WHERE gap_start IS NOT NULL AND gap_end IS NOT NULL;

-- Sub-queries: Index on result size for analytics
CREATE INDEX IF NOT EXISTS idx_subq_result_size
    ON sub_queries((result_finding_count + COALESCE(result_source_count, 0)))
    WHERE result_finding_count IS NOT NULL;

-- ----------------------------------------
-- HASH INDEXES for exact equality lookups
-- Faster than B-tree for pure equality, no range support
-- ----------------------------------------

-- Finding perspectives: Fast exact finding_id lookup
CREATE INDEX IF NOT EXISTS idx_findpersp_finding_hash
    ON finding_perspectives USING HASH(finding_id);

-- Finding relationships: Fast source/target lookups
CREATE INDEX IF NOT EXISTS idx_findrel_source_hash
    ON finding_relationships USING HASH(source_finding_id);

CREATE INDEX IF NOT EXISTS idx_findrel_target_hash
    ON finding_relationships USING HASH(target_finding_id);

-- ----------------------------------------
-- STATISTICS for query planner optimization
-- ----------------------------------------

-- Increase statistics targets for high-cardinality columns
ALTER TABLE finding_perspectives ALTER COLUMN finding_id SET STATISTICS 1000;
ALTER TABLE finding_perspectives ALTER COLUMN session_id SET STATISTICS 500;
ALTER TABLE finding_relationships ALTER COLUMN source_finding_id SET STATISTICS 1000;
ALTER TABLE finding_relationships ALTER COLUMN target_finding_id SET STATISTICS 1000;
ALTER TABLE finding_relationships ALTER COLUMN session_id SET STATISTICS 500;

-- ----------------------------------------
-- TABLE STORAGE OPTIMIZATION
-- ----------------------------------------

-- Set fill factor for tables with frequent updates
-- Lower fill factor leaves room for HOT updates
ALTER TABLE finding_relationships SET (fillfactor = 90);
ALTER TABLE research_gaps SET (fillfactor = 90);

-- Set autovacuum thresholds for high-volume tables
ALTER TABLE finding_perspectives SET (
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02
);

ALTER TABLE finding_relationships SET (
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02
);

-- ============================================
-- FUNCTIONS
-- ============================================

-- Get all relationships for a finding
CREATE OR REPLACE FUNCTION get_finding_relationships(finding_uuid UUID)
RETURNS TABLE(
    related_finding_id UUID,
    finding_content TEXT,
    finding_summary TEXT,
    relationship_type TEXT,
    direction TEXT,
    strength FLOAT
) AS $$
SELECT
    rf.id,
    rf.content,
    rf.summary,
    fr.relationship_type,
    'outgoing' as direction,
    fr.strength
FROM research_findings rf
JOIN finding_relationships fr ON rf.id = fr.target_finding_id
WHERE fr.source_finding_id = finding_uuid

UNION ALL

SELECT
    rf.id,
    rf.content,
    rf.summary,
    fr.relationship_type,
    'incoming' as direction,
    fr.strength
FROM research_findings rf
JOIN finding_relationships fr ON rf.id = fr.source_finding_id
WHERE fr.target_finding_id = finding_uuid

ORDER BY strength DESC;
$$ LANGUAGE SQL STABLE;

-- Get causal chain for a finding
CREATE OR REPLACE FUNCTION get_finding_causal_chain(finding_uuid UUID, max_depth INT DEFAULT 5)
RETURNS TABLE(finding_id UUID, content TEXT, summary TEXT, depth INT, relationship TEXT) AS $$
WITH RECURSIVE causal_tree AS (
    SELECT rf.id, rf.content, rf.summary, 0 as depth, NULL::TEXT as relationship
    FROM research_findings rf WHERE rf.id = finding_uuid
    UNION ALL
    SELECT rf.id, rf.content, rf.summary, ct.depth + 1, fr.relationship_type
    FROM research_findings rf
    JOIN finding_relationships fr ON rf.id = fr.source_finding_id
    JOIN causal_tree ct ON fr.target_finding_id = ct.id
    WHERE ct.depth < max_depth
    AND fr.relationship_type IN ('causes', 'precedes')
)
SELECT id, content, summary, depth, relationship FROM causal_tree ORDER BY depth;
$$ LANGUAGE SQL STABLE;

-- Get all perspectives for a finding
CREATE OR REPLACE FUNCTION get_finding_all_perspectives(finding_uuid UUID)
RETURNS TABLE(perspective_type TEXT, analysis_data JSONB) AS $$
SELECT perspective_type, analysis_data
FROM finding_perspectives
WHERE finding_id = finding_uuid
ORDER BY perspective_type;
$$ LANGUAGE SQL STABLE;

-- Get high-priority research gaps
CREATE OR REPLACE FUNCTION get_priority_gaps(session_uuid UUID)
RETURNS TABLE(gap_type TEXT, description TEXT, priority TEXT, suggested_queries TEXT[]) AS $$
SELECT gap_type, description, priority, suggested_queries
FROM research_gaps
WHERE session_id = session_uuid
ORDER BY
    CASE priority
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'low' THEN 3
    END,
    created_at DESC;
$$ LANGUAGE SQL STABLE;
