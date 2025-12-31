-- ============================================
-- Migration 007: Causality Extensions
-- ============================================
-- Extends the existing claim_relationships with causality metadata
-- and adds tables for pre-computed causal chains and patterns.
--
-- Run this migration after 006_add_financial_entities.sql
-- ============================================

-- ============================================
-- EXTEND CLAIM RELATIONSHIPS
-- Add causality-specific columns
-- ============================================

-- Causality confidence (how certain is the causal link?)
ALTER TABLE claim_relationships
ADD COLUMN IF NOT EXISTS causality_confidence FLOAT DEFAULT 0.5
    CHECK (causality_confidence >= 0.0 AND causality_confidence <= 1.0);

-- Causality mechanism (how does A cause B?)
ALTER TABLE claim_relationships
ADD COLUMN IF NOT EXISTS causality_mechanism TEXT
    CHECK (causality_mechanism IS NULL OR causality_mechanism IN (
        'financial', 'legal', 'organizational', 'informational',
        'social', 'physical', 'political'
    ));

-- Temporal gap between events
ALTER TABLE claim_relationships
ADD COLUMN IF NOT EXISTS temporal_gap_days INTEGER;

-- Counterfactual reasoning
ALTER TABLE claim_relationships
ADD COLUMN IF NOT EXISTS counterfactual_reasoning TEXT;


-- ============================================
-- CAUSAL CHAINS
-- Pre-computed chains for fast queries
-- ============================================
CREATE TABLE IF NOT EXISTS causal_chains (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Chain classification
    chain_type TEXT NOT NULL
        CHECK (chain_type IN ('cause_chain', 'consequence_chain', 'enabling_chain')),

    -- Chain endpoints
    start_claim_id UUID NOT NULL,  -- References knowledge_claims(id)
    end_claim_id UUID NOT NULL,    -- References knowledge_claims(id)

    -- Chain structure
    chain_length INTEGER NOT NULL CHECK (chain_length > 0),
    claim_ids UUID[] NOT NULL,  -- Ordered array of claim IDs
    relationship_types TEXT[] NOT NULL,  -- Ordered array of relationship types

    -- Confidence (product of individual link confidences)
    total_confidence FLOAT NOT NULL
        CHECK (total_confidence >= 0.0 AND total_confidence <= 1.0),

    -- Human-readable narrative
    narrative TEXT,

    -- Workspace and timestamps
    workspace_id TEXT NOT NULL DEFAULT 'default',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint on chain endpoints and type
    UNIQUE(start_claim_id, end_claim_id, chain_type)
);

-- Indexes for causal_chains
CREATE INDEX IF NOT EXISTS idx_causal_chains_start ON causal_chains(start_claim_id);
CREATE INDEX IF NOT EXISTS idx_causal_chains_end ON causal_chains(end_claim_id);
CREATE INDEX IF NOT EXISTS idx_causal_chains_type ON causal_chains(chain_type);
CREATE INDEX IF NOT EXISTS idx_causal_chains_confidence ON causal_chains(total_confidence DESC);
CREATE INDEX IF NOT EXISTS idx_causal_chains_workspace ON causal_chains(workspace_id);
CREATE INDEX IF NOT EXISTS idx_causal_chains_claims ON causal_chains USING GIN(claim_ids);


-- ============================================
-- CAUSAL PATTERNS
-- Detected recurring patterns
-- ============================================
CREATE TABLE IF NOT EXISTS causal_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Pattern identification
    pattern_name TEXT NOT NULL,
    pattern_type TEXT NOT NULL
        CHECK (pattern_type IN ('enabling_network', 'cover_up', 'escalation',
                                 'retaliation', 'protection', 'obstruction',
                                 'money_laundering', 'recruitment')),

    -- Pattern description
    description TEXT,

    -- Involved elements
    involved_entities UUID[] NOT NULL,  -- Array of entity IDs
    claim_ids UUID[] NOT NULL,  -- Claims that form this pattern

    -- Confidence
    confidence FLOAT NOT NULL
        CHECK (confidence >= 0.0 AND confidence <= 1.0),

    -- Detection tracking
    first_detected_at TIMESTAMPTZ DEFAULT NOW(),
    occurrence_count INTEGER DEFAULT 1,

    -- Workspace
    workspace_id TEXT DEFAULT 'default'
);

-- Indexes for causal_patterns
CREATE INDEX IF NOT EXISTS idx_causal_patterns_type ON causal_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_causal_patterns_confidence ON causal_patterns(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_causal_patterns_entities ON causal_patterns USING GIN(involved_entities);
CREATE INDEX IF NOT EXISTS idx_causal_patterns_claims ON causal_patterns USING GIN(claim_ids);
CREATE INDEX IF NOT EXISTS idx_causal_patterns_workspace ON causal_patterns(workspace_id);


-- ============================================
-- CAUSAL LINKS
-- Individual causal relationships extracted by LLM
-- ============================================
CREATE TABLE IF NOT EXISTS causal_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Events/claims being linked
    source_event TEXT NOT NULL,
    source_claim_id UUID,  -- References knowledge_claims(id) if available
    target_event TEXT NOT NULL,
    target_claim_id UUID,  -- References knowledge_claims(id) if available

    -- Causality classification
    causality_type TEXT NOT NULL
        CHECK (causality_type IN ('caused_by', 'enabled_by', 'prevented_by',
                                   'triggered_by', 'preceded', 'resulted_in',
                                   'contributed_to')),

    -- Confidence and evidence
    confidence FLOAT NOT NULL
        CHECK (confidence >= 0.0 AND confidence <= 1.0),
    mechanism TEXT
        CHECK (mechanism IS NULL OR mechanism IN (
            'financial', 'legal', 'organizational', 'informational',
            'social', 'physical', 'political'
        )),

    -- Temporal information
    temporal_gap_days INTEGER,

    -- Reasoning
    reasoning TEXT NOT NULL,
    counterfactual TEXT,  -- "If A hadn't happened, B would not have occurred"
    evidence JSONB DEFAULT '[]',  -- Supporting evidence

    -- Workspace and timestamps
    workspace_id TEXT DEFAULT 'default',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Source tracking (which research created this)
    research_node_id UUID,  -- References research_nodes(id) if from recursive research
    source_session_id UUID  -- References research_sessions(id)
);

-- Indexes for causal_links
CREATE INDEX IF NOT EXISTS idx_causal_links_source_claim ON causal_links(source_claim_id);
CREATE INDEX IF NOT EXISTS idx_causal_links_target_claim ON causal_links(target_claim_id);
CREATE INDEX IF NOT EXISTS idx_causal_links_type ON causal_links(causality_type);
CREATE INDEX IF NOT EXISTS idx_causal_links_confidence ON causal_links(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_causal_links_workspace ON causal_links(workspace_id);


-- ============================================
-- INDEX ON EXISTING TABLE
-- Optimize causality queries on claim_relationships
-- ============================================
CREATE INDEX IF NOT EXISTS idx_claim_rel_causality
    ON claim_relationships(relationship_type)
    WHERE relationship_type IN ('causes', 'enables', 'prevents', 'triggers', 'precedes', 'results_in');


-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Find direct causes of a claim
CREATE OR REPLACE FUNCTION find_direct_causes(p_claim_id UUID, p_min_confidence FLOAT DEFAULT 0.3)
RETURNS TABLE(
    source_claim_id UUID,
    causality_type TEXT,
    confidence FLOAT,
    mechanism TEXT,
    reasoning TEXT
) AS $$
    SELECT
        source_claim_id,
        causality_type,
        confidence,
        mechanism,
        reasoning
    FROM causal_links
    WHERE target_claim_id = p_claim_id
      AND confidence >= p_min_confidence
    ORDER BY confidence DESC;
$$ LANGUAGE SQL;


-- Find direct consequences of a claim
CREATE OR REPLACE FUNCTION find_direct_consequences(p_claim_id UUID, p_min_confidence FLOAT DEFAULT 0.3)
RETURNS TABLE(
    target_claim_id UUID,
    causality_type TEXT,
    confidence FLOAT,
    mechanism TEXT,
    reasoning TEXT
) AS $$
    SELECT
        target_claim_id,
        causality_type,
        confidence,
        mechanism,
        reasoning
    FROM causal_links
    WHERE source_claim_id = p_claim_id
      AND confidence >= p_min_confidence
    ORDER BY confidence DESC;
$$ LANGUAGE SQL;


-- Get all causal chains involving a claim
CREATE OR REPLACE FUNCTION get_claim_causal_chains(p_claim_id UUID)
RETURNS TABLE(
    chain_id UUID,
    chain_type TEXT,
    chain_length INT,
    total_confidence FLOAT,
    narrative TEXT,
    is_start BOOLEAN,
    is_end BOOLEAN
) AS $$
    SELECT
        id as chain_id,
        chain_type,
        chain_length,
        total_confidence,
        narrative,
        (start_claim_id = p_claim_id) as is_start,
        (end_claim_id = p_claim_id) as is_end
    FROM causal_chains
    WHERE start_claim_id = p_claim_id
       OR end_claim_id = p_claim_id
       OR p_claim_id = ANY(claim_ids)
    ORDER BY total_confidence DESC;
$$ LANGUAGE SQL;


-- Calculate chain confidence (product of link confidences)
CREATE OR REPLACE FUNCTION calculate_chain_confidence(p_claim_ids UUID[])
RETURNS FLOAT AS $$
DECLARE
    total_conf FLOAT := 1.0;
    i INT;
    link_conf FLOAT;
BEGIN
    FOR i IN 1..array_length(p_claim_ids, 1) - 1 LOOP
        SELECT confidence INTO link_conf
        FROM causal_links
        WHERE source_claim_id = p_claim_ids[i]
          AND target_claim_id = p_claim_ids[i + 1]
        LIMIT 1;

        IF link_conf IS NULL THEN
            RETURN 0.0;  -- Chain broken
        END IF;

        total_conf := total_conf * link_conf;
    END LOOP;

    RETURN total_conf;
END;
$$ LANGUAGE plpgsql;


-- ============================================
-- VIEWS
-- ============================================

-- High-confidence causal links view
CREATE OR REPLACE VIEW high_confidence_causal_links AS
SELECT
    cl.*,
    sc.content as source_content,
    tc.content as target_content
FROM causal_links cl
LEFT JOIN knowledge_claims sc ON cl.source_claim_id = sc.id
LEFT JOIN knowledge_claims tc ON cl.target_claim_id = tc.id
WHERE cl.confidence >= 0.7
ORDER BY cl.confidence DESC;


-- Pattern summary view
CREATE OR REPLACE VIEW causal_pattern_summary AS
SELECT
    pattern_type,
    COUNT(*) as pattern_count,
    AVG(confidence) as avg_confidence,
    SUM(occurrence_count) as total_occurrences,
    array_agg(DISTINCT pattern_name) as pattern_names
FROM causal_patterns
GROUP BY pattern_type
ORDER BY pattern_count DESC;


-- ============================================
-- COMMENTS
-- ============================================
COMMENT ON TABLE causal_chains IS
    'Pre-computed causal chains for efficient causality queries.';

COMMENT ON TABLE causal_patterns IS
    'Detected recurring causal patterns like cover-ups, enabling networks, etc.';

COMMENT ON TABLE causal_links IS
    'Individual causal relationships extracted by LLM analysis.';

COMMENT ON FUNCTION find_direct_causes IS
    'Find all claims that directly caused a given claim.';

COMMENT ON FUNCTION find_direct_consequences IS
    'Find all claims that were directly caused by a given claim.';

COMMENT ON FUNCTION calculate_chain_confidence IS
    'Calculate the total confidence of a causal chain as the product of link confidences.';
