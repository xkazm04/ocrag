-- ============================================
-- Migration 005: Recursive Research Tables
-- ============================================
-- Adds tables for N-level recursive chain-of-investigation
-- with automatic follow-up generation and saturation tracking.
--
-- Run this migration after 004_add_profile_research.sql
-- ============================================

-- ============================================
-- RESEARCH TREES
-- Tracks recursive research sessions
-- ============================================
CREATE TABLE IF NOT EXISTS research_trees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    root_query TEXT NOT NULL,
    workspace_id TEXT NOT NULL DEFAULT 'default',

    -- Configuration (stored as JSON for flexibility)
    config JSONB NOT NULL DEFAULT '{
        "depth_limit": 5,
        "saturation_threshold": 0.8,
        "max_nodes": 50,
        "max_follow_ups_per_node": 5,
        "follow_up_types": ["predecessor", "consequence"],
        "min_priority_score": 0.3,
        "parallel_nodes": 3
    }',

    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),

    -- Progress metrics
    total_nodes INTEGER DEFAULT 0,
    completed_nodes INTEGER DEFAULT 0,
    max_depth_reached INTEGER DEFAULT 0,

    -- Cost tracking
    total_tokens_used INTEGER DEFAULT 0,
    estimated_cost_usd DECIMAL(10, 4) DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Additional metadata
    metadata JSONB DEFAULT '{}'
);

-- Indexes for research_trees
CREATE INDEX IF NOT EXISTS idx_research_trees_workspace ON research_trees(workspace_id);
CREATE INDEX IF NOT EXISTS idx_research_trees_status ON research_trees(status);
CREATE INDEX IF NOT EXISTS idx_research_trees_created ON research_trees(created_at DESC);


-- ============================================
-- RESEARCH NODES
-- Individual nodes in the research tree
-- ============================================
CREATE TABLE IF NOT EXISTS research_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tree_id UUID NOT NULL REFERENCES research_trees(id) ON DELETE CASCADE,
    parent_node_id UUID REFERENCES research_nodes(id) ON DELETE SET NULL,

    -- Query information
    query TEXT NOT NULL,
    query_type TEXT NOT NULL DEFAULT 'initial'
        CHECK (query_type IN ('initial', 'predecessor', 'consequence', 'detail',
                              'verification', 'financial', 'temporal')),

    -- Tree position
    depth INTEGER NOT NULL DEFAULT 0,

    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'skipped')),

    -- Research results
    saturation_score FLOAT DEFAULT 0.0
        CHECK (saturation_score >= 0.0 AND saturation_score <= 1.0),
    findings_count INTEGER DEFAULT 0,
    new_entities_count INTEGER DEFAULT 0,

    -- Skip reason if applicable
    skip_reason TEXT
        CHECK (skip_reason IS NULL OR skip_reason IN ('duplicate', 'saturated', 'depth_limit', 'irrelevant', 'max_nodes')),

    -- Link to actual research execution
    session_id UUID,  -- References research_sessions if available

    -- Timing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    execution_time_ms INTEGER,

    -- Prevent duplicate queries within same tree
    UNIQUE(tree_id, query)
);

-- Indexes for research_nodes
CREATE INDEX IF NOT EXISTS idx_research_nodes_tree ON research_nodes(tree_id);
CREATE INDEX IF NOT EXISTS idx_research_nodes_tree_depth ON research_nodes(tree_id, depth);
CREATE INDEX IF NOT EXISTS idx_research_nodes_parent ON research_nodes(parent_node_id);
CREATE INDEX IF NOT EXISTS idx_research_nodes_status ON research_nodes(status);
CREATE INDEX IF NOT EXISTS idx_research_nodes_type ON research_nodes(query_type);


-- ============================================
-- NODE FOLLOW-UPS
-- Generated follow-up questions from each node
-- ============================================
CREATE TABLE IF NOT EXISTS node_follow_ups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_node_id UUID NOT NULL REFERENCES research_nodes(id) ON DELETE CASCADE,

    -- Follow-up details
    follow_up_query TEXT NOT NULL,
    follow_up_type TEXT NOT NULL
        CHECK (follow_up_type IN ('predecessor', 'consequence', 'detail',
                                   'verification', 'financial', 'temporal')),

    -- Prioritization
    priority_score FLOAT DEFAULT 0.5
        CHECK (priority_score >= 0.0 AND priority_score <= 1.0),
    reasoning TEXT,

    -- Link to created node (if executed)
    target_node_id UUID REFERENCES research_nodes(id) ON DELETE SET NULL,

    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'queued', 'executed', 'skipped')),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for node_follow_ups
CREATE INDEX IF NOT EXISTS idx_node_follow_ups_source ON node_follow_ups(source_node_id);
CREATE INDEX IF NOT EXISTS idx_node_follow_ups_target ON node_follow_ups(target_node_id);
CREATE INDEX IF NOT EXISTS idx_node_follow_ups_status ON node_follow_ups(status);
CREATE INDEX IF NOT EXISTS idx_node_follow_ups_priority ON node_follow_ups(priority_score DESC);


-- ============================================
-- NODE FINDINGS
-- Findings extracted from each research node
-- ============================================
CREATE TABLE IF NOT EXISTS node_findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_id UUID NOT NULL REFERENCES research_nodes(id) ON DELETE CASCADE,

    -- Finding content
    content TEXT NOT NULL,
    finding_type TEXT DEFAULT 'fact'
        CHECK (finding_type IN ('fact', 'claim', 'event', 'relationship', 'quote')),

    -- Confidence and evidence
    confidence FLOAT DEFAULT 0.5
        CHECK (confidence >= 0.0 AND confidence <= 1.0),
    evidence_strength TEXT DEFAULT 'medium'
        CHECK (evidence_strength IN ('high', 'medium', 'low', 'alleged')),

    -- Source tracking
    sources JSONB DEFAULT '[]',

    -- Entity mentions
    entities_mentioned JSONB DEFAULT '[]',

    -- Temporal context
    temporal_context JSONB DEFAULT '{}',

    -- Deduplication
    content_hash TEXT,
    is_duplicate BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for node_findings
CREATE INDEX IF NOT EXISTS idx_node_findings_node ON node_findings(node_id);
CREATE INDEX IF NOT EXISTS idx_node_findings_type ON node_findings(finding_type);
CREATE INDEX IF NOT EXISTS idx_node_findings_hash ON node_findings(content_hash);


-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Get the reasoning chain from root to a node
CREATE OR REPLACE FUNCTION get_reasoning_chain(target_node_id UUID)
RETURNS TABLE(depth INT, query TEXT, query_type TEXT) AS $$
WITH RECURSIVE chain AS (
    -- Start from target node
    SELECT id, parent_node_id, query, query_type, depth
    FROM research_nodes
    WHERE id = target_node_id

    UNION ALL

    -- Walk up to parent
    SELECT n.id, n.parent_node_id, n.query, n.query_type, n.depth
    FROM research_nodes n
    JOIN chain c ON n.id = c.parent_node_id
)
SELECT depth, query, query_type
FROM chain
ORDER BY depth ASC;
$$ LANGUAGE SQL;


-- Calculate tree progress percentage
CREATE OR REPLACE FUNCTION get_tree_progress(tree_id UUID)
RETURNS FLOAT AS $$
DECLARE
    total INT;
    completed INT;
BEGIN
    SELECT total_nodes, completed_nodes
    INTO total, completed
    FROM research_trees
    WHERE id = tree_id;

    IF total IS NULL OR total = 0 THEN
        RETURN 0.0;
    END IF;

    RETURN (completed::FLOAT / total::FLOAT) * 100;
END;
$$ LANGUAGE plpgsql;


-- Get pending nodes at a specific depth
CREATE OR REPLACE FUNCTION get_pending_nodes_at_depth(p_tree_id UUID, p_depth INT)
RETURNS SETOF research_nodes AS $$
    SELECT * FROM research_nodes
    WHERE tree_id = p_tree_id
      AND depth = p_depth
      AND status = 'pending'
    ORDER BY created_at ASC;
$$ LANGUAGE SQL;


-- ============================================
-- TRIGGERS
-- ============================================

-- Update tree metrics when nodes change
CREATE OR REPLACE FUNCTION update_tree_metrics()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE research_trees
    SET
        total_nodes = (SELECT COUNT(*) FROM research_nodes WHERE tree_id = NEW.tree_id),
        completed_nodes = (SELECT COUNT(*) FROM research_nodes WHERE tree_id = NEW.tree_id AND status = 'completed'),
        max_depth_reached = (SELECT COALESCE(MAX(depth), 0) FROM research_nodes WHERE tree_id = NEW.tree_id AND status = 'completed')
    WHERE id = NEW.tree_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_tree_metrics
    AFTER INSERT OR UPDATE ON research_nodes
    FOR EACH ROW EXECUTE FUNCTION update_tree_metrics();


-- ============================================
-- COMMENTS
-- ============================================
COMMENT ON TABLE research_trees IS
    'Tracks recursive research sessions with N-level depth exploration.';

COMMENT ON TABLE research_nodes IS
    'Individual research units in a tree, each representing a query and its findings.';

COMMENT ON TABLE node_follow_ups IS
    'Generated follow-up questions from research findings, prioritized for execution.';

COMMENT ON TABLE node_findings IS
    'Facts, claims, and events extracted from research node execution.';

COMMENT ON FUNCTION get_reasoning_chain IS
    'Returns the question chain from root to a specific node for provenance tracking.';
