-- ============================================
-- Migration 004: Profile Research Tables
-- ============================================
-- Adds tables for LLM-powered entity profile research
-- and connection tracking between entities.
--
-- Run this migration after 003_add_verification.sql
-- ============================================

-- ============================================
-- ENTITY RESEARCH PAIRS
-- Tracks which entity pairs have been researched for connections
-- Prevents duplicate research and stores connection strength
-- ============================================
CREATE TABLE IF NOT EXISTS entity_research_pairs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Entity pair (stored in sorted order for consistent lookups)
    -- Always store with entity_a_id < entity_b_id (lexicographically)
    entity_a_id TEXT NOT NULL,
    entity_b_id TEXT NOT NULL,

    -- Research results
    research_date TIMESTAMPTZ DEFAULT NOW(),
    connection_strength TEXT CHECK (connection_strength IN ('strong', 'moderate', 'weak', 'none', 'unknown')),
    connections_count INT DEFAULT 0,
    summary TEXT,

    -- Full connection details as JSON
    connection_details JSONB DEFAULT '[]',

    -- Metadata
    workspace_id TEXT DEFAULT 'default',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure unique pairs (order-independent due to sorted storage)
    UNIQUE(entity_a_id, entity_b_id)
);

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_research_pairs_entity_a ON entity_research_pairs(entity_a_id);
CREATE INDEX IF NOT EXISTS idx_research_pairs_entity_b ON entity_research_pairs(entity_b_id);
CREATE INDEX IF NOT EXISTS idx_research_pairs_strength ON entity_research_pairs(connection_strength);
CREATE INDEX IF NOT EXISTS idx_research_pairs_date ON entity_research_pairs(research_date DESC);
CREATE INDEX IF NOT EXISTS idx_research_pairs_workspace ON entity_research_pairs(workspace_id);

-- Trigger for updated_at
CREATE TRIGGER update_research_pairs_updated_at
    BEFORE UPDATE ON entity_research_pairs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================
-- ENTITY PROFILE RESEARCH
-- Stores LLM-researched profile information for entities
-- Includes positions, companies, affiliations, events
-- ============================================
CREATE TABLE IF NOT EXISTS entity_profile_research (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Link to entity
    entity_id UUID NOT NULL,

    -- Research timestamp
    research_date TIMESTAMPTZ DEFAULT NOW(),

    -- Structured research results
    positions JSONB DEFAULT '[]',
    -- Format: [{"title": "CEO", "organization": "Acme Corp", "start_date": "2000", "end_date": "2010", "notes": "..."}]

    companies JSONB DEFAULT '[]',
    -- Format: [{"name": "Acme Corp", "role": "owner/founder/board", "dates": "2000-2010", "notes": "..."}]

    affiliations JSONB DEFAULT '[]',
    -- Format: [{"organization": "...", "type": "membership/partnership", "dates": "..."}]

    events JSONB DEFAULT '[]',
    -- Format: [{"date": "2005-03-15", "description": "...", "significance": "high/medium/low"}]

    associates JSONB DEFAULT '[]',
    -- Format: [{"name": "John Doe", "relationship": "business partner", "context": "..."}]

    -- Summary and sources
    summary TEXT,
    sources JSONB DEFAULT '[]',
    -- Format: [{"url": "...", "title": "...", "domain": "..."}]

    -- Raw LLM response for reference
    raw_text TEXT,

    -- Date context used for research (e.g., "1990-2010")
    date_context TEXT,

    -- Metadata
    workspace_id TEXT DEFAULT 'default',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_profile_research_entity ON entity_profile_research(entity_id);
CREATE INDEX IF NOT EXISTS idx_profile_research_date ON entity_profile_research(research_date DESC);
CREATE INDEX IF NOT EXISTS idx_profile_research_workspace ON entity_profile_research(workspace_id);

-- GIN indexes for JSON queries
CREATE INDEX IF NOT EXISTS idx_profile_research_positions ON entity_profile_research USING GIN(positions);
CREATE INDEX IF NOT EXISTS idx_profile_research_companies ON entity_profile_research USING GIN(companies);


-- ============================================
-- HELPER VIEW: Entity Research Status
-- Shows which entities have been researched
-- ============================================
CREATE OR REPLACE VIEW entity_research_status AS
SELECT
    e.id as entity_id,
    e.canonical_name,
    e.entity_type,
    COUNT(DISTINCT CASE
        WHEN rp.entity_a_id = e.id::text THEN rp.entity_b_id
        WHEN rp.entity_b_id = e.id::text THEN rp.entity_a_id
    END) as pairs_researched,
    MAX(pr.research_date) as last_profile_research,
    MAX(rp.research_date) as last_connection_research
FROM knowledge_entities e
LEFT JOIN entity_research_pairs rp
    ON e.id::text = rp.entity_a_id OR e.id::text = rp.entity_b_id
LEFT JOIN entity_profile_research pr
    ON e.id = pr.entity_id
GROUP BY e.id, e.canonical_name, e.entity_type;


-- ============================================
-- HELPER FUNCTION: Check if pair is researched
-- ============================================
CREATE OR REPLACE FUNCTION is_pair_researched(entity_1 UUID, entity_2 UUID)
RETURNS BOOLEAN AS $$
DECLARE
    id_a TEXT;
    id_b TEXT;
    result BOOLEAN;
BEGIN
    -- Sort IDs for consistent lookup
    IF entity_1::text < entity_2::text THEN
        id_a := entity_1::text;
        id_b := entity_2::text;
    ELSE
        id_a := entity_2::text;
        id_b := entity_1::text;
    END IF;

    SELECT EXISTS(
        SELECT 1 FROM entity_research_pairs
        WHERE entity_a_id = id_a AND entity_b_id = id_b
    ) INTO result;

    RETURN result;
END;
$$ LANGUAGE plpgsql;


-- ============================================
-- HELPER FUNCTION: Get unresearched pairs
-- Returns entity IDs that haven't been researched with the given entity
-- ============================================
CREATE OR REPLACE FUNCTION get_unresearched_pairs(
    source_entity UUID,
    target_entities UUID[]
)
RETURNS UUID[] AS $$
DECLARE
    unresearched UUID[];
    target UUID;
BEGIN
    unresearched := ARRAY[]::UUID[];

    FOREACH target IN ARRAY target_entities
    LOOP
        IF NOT is_pair_researched(source_entity, target) THEN
            unresearched := array_append(unresearched, target);
        END IF;
    END LOOP;

    RETURN unresearched;
END;
$$ LANGUAGE plpgsql;


-- ============================================
-- COMMENTS
-- ============================================
COMMENT ON TABLE entity_research_pairs IS
    'Tracks which entity pairs have been researched for connections. Entity IDs stored in sorted order for consistent lookups.';

COMMENT ON TABLE entity_profile_research IS
    'Stores LLM-researched profile information including positions, companies, affiliations, and events.';

COMMENT ON FUNCTION is_pair_researched IS
    'Check if two entities have been researched for connections. Order-independent.';

COMMENT ON FUNCTION get_unresearched_pairs IS
    'Returns array of target entity IDs that have not been researched against the source entity.';
