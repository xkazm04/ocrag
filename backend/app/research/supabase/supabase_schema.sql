-- ============================================
-- Deep Research Knowledge Base - Supabase Schema
-- ============================================
-- Run this in your Supabase SQL Editor
-- Requires pgvector extension for embeddings

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";  -- For semantic embeddings

-- ============================================
-- KNOWLEDGE TOPICS
-- Hierarchical topic tree for categorizing research
-- ============================================
CREATE TABLE IF NOT EXISTS knowledge_topics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_id UUID REFERENCES knowledge_topics(id) ON DELETE SET NULL,

    -- Identity
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,

    -- Topic metadata
    topic_type TEXT CHECK (topic_type IN ('domain', 'event', 'entity', 'concept', 'region', 'timeperiod')),
    icon TEXT,
    color TEXT,

    -- Aggregated stats (denormalized for performance)
    finding_count INT DEFAULT 0,
    entity_count INT DEFAULT 0,
    session_count INT DEFAULT 0,
    last_activity_at TIMESTAMPTZ,

    -- Hierarchy path for efficient queries
    path TEXT[] DEFAULT '{}',
    depth INT DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- KNOWLEDGE ENTITIES
-- Deduplicated actors, organizations, locations
-- ============================================
CREATE TABLE IF NOT EXISTS knowledge_entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Identity
    canonical_name TEXT NOT NULL,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('person', 'organization', 'location', 'product', 'concept', 'event')),
    aliases TEXT[] DEFAULT '{}',

    -- Deduplication
    name_hash TEXT NOT NULL,
    embedding VECTOR(768),

    -- Profile data
    description TEXT,
    profile_data JSONB DEFAULT '{}',
    image_url TEXT,

    -- External links
    external_ids JSONB DEFAULT '{}',

    -- Aggregated stats
    mention_count INT DEFAULT 0,
    claim_count INT DEFAULT 0,

    -- Verification
    is_verified BOOLEAN DEFAULT FALSE,
    verified_by_user_id TEXT,
    verified_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(name_hash, entity_type)
);

-- ============================================
-- KNOWLEDGE CLAIMS
-- Core knowledge units - deduplicated findings
-- ============================================
CREATE TABLE IF NOT EXISTS knowledge_claims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Content
    claim_type TEXT NOT NULL CHECK (claim_type IN ('fact', 'event', 'relationship', 'pattern', 'prediction', 'actor', 'evidence', 'gap')),
    content TEXT NOT NULL,
    summary TEXT,

    -- Deduplication
    content_hash TEXT NOT NULL,
    embedding VECTOR(768),

    -- Classification
    topic_id UUID REFERENCES knowledge_topics(id) ON DELETE SET NULL,
    tags TEXT[] DEFAULT '{}',

    -- Confidence & verification
    confidence_score FLOAT DEFAULT 0.5 CHECK (confidence_score >= 0 AND confidence_score <= 1),
    verification_status TEXT DEFAULT 'unverified' CHECK (verification_status IN ('unverified', 'corroborated', 'disputed', 'verified', 'retracted')),
    corroboration_count INT DEFAULT 0,

    -- Temporal context
    temporal_context TEXT CHECK (temporal_context IN ('historical', 'current', 'ongoing', 'predicted')),
    event_date DATE,
    date_range_start DATE,
    date_range_end DATE,

    -- Visibility & ownership
    visibility TEXT DEFAULT 'public' CHECK (visibility IN ('public', 'workspace', 'private')),
    created_by_user_id TEXT,
    workspace_id TEXT DEFAULT 'default',

    -- Versioning
    version INT DEFAULT 1,
    superseded_by UUID REFERENCES knowledge_claims(id) ON DELETE SET NULL,
    is_current BOOLEAN DEFAULT TRUE,

    -- Original source session
    origin_session_id UUID,  -- Will reference research_sessions after it's created

    -- Metadata
    extracted_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- CLAIM RELATIONSHIPS
-- Knowledge graph edges - causality, support, contradiction
-- ============================================
CREATE TABLE IF NOT EXISTS claim_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    source_claim_id UUID REFERENCES knowledge_claims(id) ON DELETE CASCADE NOT NULL,
    target_claim_id UUID REFERENCES knowledge_claims(id) ON DELETE CASCADE NOT NULL,

    -- Relationship type
    relationship_type TEXT NOT NULL CHECK (relationship_type IN (
        'causes',       -- Source caused/led to target (causality)
        'supports',     -- Source provides evidence for target
        'contradicts',  -- Source conflicts with target
        'expands',      -- Source adds detail to target
        'supersedes',   -- Source replaces target (newer info)
        'related_to',   -- General relationship
        'part_of',      -- Source is component of target
        'precedes',     -- Temporal: source happened before target
        'follows',      -- Temporal: source happened after target
        'enables',      -- Source makes target possible
        'prevents'      -- Source blocks target
    )),

    -- Relationship metadata
    strength FLOAT DEFAULT 0.5 CHECK (strength >= 0 AND strength <= 1),
    description TEXT,
    bidirectional BOOLEAN DEFAULT FALSE,

    -- Provenance
    created_by_session_id UUID,
    created_by_user_id TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(source_claim_id, target_claim_id, relationship_type)
);

-- ============================================
-- CLAIM ENTITIES
-- Links claims to entities (who/what is involved)
-- ============================================
CREATE TABLE IF NOT EXISTS claim_entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    claim_id UUID REFERENCES knowledge_claims(id) ON DELETE CASCADE NOT NULL,
    entity_id UUID REFERENCES knowledge_entities(id) ON DELETE CASCADE NOT NULL,

    -- Role in the claim
    role TEXT CHECK (role IN ('subject', 'object', 'actor', 'target', 'location', 'mentioned', 'source', 'beneficiary')),

    -- Extracted context
    context_snippet TEXT,
    sentiment FLOAT,  -- -1.0 to 1.0

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(claim_id, entity_id, role)
);

-- ============================================
-- RESEARCH SESSIONS
-- Container for research investigations
-- ============================================
CREATE TABLE IF NOT EXISTS research_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT,
    workspace_id TEXT DEFAULT 'default',

    -- Session metadata
    title TEXT NOT NULL,
    query TEXT NOT NULL,
    template_type TEXT NOT NULL DEFAULT 'investigative',
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'searching', 'analyzing', 'completed', 'paused', 'failed')),

    -- Topic association
    primary_topic_id UUID REFERENCES knowledge_topics(id) ON DELETE SET NULL,
    topic_ids UUID[] DEFAULT '{}',

    -- Parameters
    parameters JSONB DEFAULT '{}',

    -- Stats
    claim_count INT DEFAULT 0,
    source_count INT DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Add foreign key from knowledge_claims to research_sessions
ALTER TABLE knowledge_claims
    ADD CONSTRAINT fk_claims_origin_session
    FOREIGN KEY (origin_session_id)
    REFERENCES research_sessions(id) ON DELETE SET NULL;

-- Add foreign key from claim_relationships to research_sessions
ALTER TABLE claim_relationships
    ADD CONSTRAINT fk_relationships_session
    FOREIGN KEY (created_by_session_id)
    REFERENCES research_sessions(id) ON DELETE SET NULL;

-- ============================================
-- RESEARCH QUERIES
-- Individual search queries executed
-- ============================================
CREATE TABLE IF NOT EXISTS research_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE NOT NULL,

    query_text TEXT NOT NULL,
    query_purpose TEXT,
    query_round INT DEFAULT 1,

    -- Execution metadata
    executed_at TIMESTAMPTZ DEFAULT NOW(),
    execution_time_ms INT,
    result_count INT DEFAULT 0,

    -- Gemini grounding metadata
    model_used TEXT DEFAULT 'gemini-2.0-flash',
    grounding_metadata JSONB
);

-- ============================================
-- RESEARCH SOURCES
-- Web sources discovered during research (globally deduplicated)
-- ============================================
CREATE TABLE IF NOT EXISTS research_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_id UUID REFERENCES research_queries(id) ON DELETE SET NULL,

    -- Can be session-specific or global
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE,
    is_global BOOLEAN DEFAULT FALSE,

    -- Source information
    url TEXT NOT NULL,
    url_hash TEXT NOT NULL,  -- For deduplication
    title TEXT,
    domain TEXT,
    snippet TEXT,
    full_content TEXT,  -- Cached content if fetched

    -- Credibility assessment
    credibility_score FLOAT CHECK (credibility_score >= 0 AND credibility_score <= 1),
    credibility_factors JSONB,
    source_type TEXT CHECK (source_type IN ('news', 'academic', 'government', 'corporate', 'blog', 'social', 'wiki', 'unknown')),

    -- Metadata
    discovered_at TIMESTAMPTZ DEFAULT NOW(),
    content_date DATE,
    last_verified_at TIMESTAMPTZ,

    -- Citation count
    citation_count INT DEFAULT 0
);

-- Global sources must have unique URLs
CREATE UNIQUE INDEX IF NOT EXISTS idx_sources_global_url ON research_sources(url_hash) WHERE is_global = TRUE;

-- ============================================
-- CLAIM SOURCES
-- Links claims to their evidence (web, document, or other claims)
-- ============================================
CREATE TABLE IF NOT EXISTS claim_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    claim_id UUID REFERENCES knowledge_claims(id) ON DELETE CASCADE NOT NULL,

    -- Source type
    source_type TEXT NOT NULL CHECK (source_type IN ('web', 'document', 'claim', 'user_input', 'inference')),

    -- For web sources
    web_source_id UUID REFERENCES research_sources(id) ON DELETE SET NULL,

    -- For claim-as-source (cross-reference)
    source_claim_id UUID REFERENCES knowledge_claims(id) ON DELETE SET NULL,

    -- For documents (future)
    document_id UUID,
    document_path TEXT,

    -- Provenance
    excerpt TEXT,
    page_number INT,
    timestamp_in_source TEXT,

    -- Confidence
    support_strength FLOAT DEFAULT 0.5 CHECK (support_strength >= 0 AND support_strength <= 1),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- RESEARCH FINDINGS
-- Session-specific findings (before promotion to knowledge base)
-- ============================================
CREATE TABLE IF NOT EXISTS research_findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE NOT NULL,

    -- Finding content
    finding_type TEXT NOT NULL CHECK (finding_type IN ('fact', 'claim', 'event', 'actor', 'relationship', 'pattern', 'gap', 'evidence')),
    content TEXT NOT NULL,
    summary TEXT,

    -- Analysis metadata
    perspective TEXT,
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    supporting_sources UUID[],

    -- Temporal context
    temporal_context TEXT CHECK (temporal_context IN ('past', 'present', 'ongoing', 'prediction')),
    event_date DATE,
    date_range_start DATE,
    date_range_end DATE,

    -- Relationships (within session)
    related_findings UUID[],
    contradicts UUID[],

    -- Knowledge base link
    knowledge_claim_id UUID REFERENCES knowledge_claims(id) ON DELETE SET NULL,
    is_promoted BOOLEAN DEFAULT FALSE,
    promotion_type TEXT,  -- 'created', 'matched', 'expanded', 'merged'

    -- Metadata
    extracted_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- FINDING CLAIMS
-- Links session findings to knowledge claims (many-to-many)
-- ============================================
CREATE TABLE IF NOT EXISTS finding_claims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    finding_id UUID REFERENCES research_findings(id) ON DELETE CASCADE NOT NULL,
    claim_id UUID REFERENCES knowledge_claims(id) ON DELETE CASCADE NOT NULL,

    -- How was this link created?
    link_type TEXT CHECK (link_type IN ('created', 'matched', 'expanded', 'merged', 'manual')),
    match_score FLOAT,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(finding_id, claim_id)
);

-- ============================================
-- RESEARCH PERSPECTIVES
-- Expert persona analyses
-- ============================================
CREATE TABLE IF NOT EXISTS research_perspectives (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE NOT NULL,

    perspective_type TEXT NOT NULL CHECK (perspective_type IN ('historical', 'political', 'economic', 'psychological', 'military', 'social', 'technological')),

    analysis_text TEXT NOT NULL,
    key_insights TEXT[],
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),

    findings_analyzed UUID[],
    sources_cited UUID[],

    recommendations TEXT[],
    warnings TEXT[],

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- SIMILARITY CANDIDATES
-- Queue for deduplication review
-- ============================================
CREATE TABLE IF NOT EXISTS similarity_candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    claim_id UUID REFERENCES knowledge_claims(id) ON DELETE CASCADE NOT NULL,
    similar_claim_id UUID REFERENCES knowledge_claims(id) ON DELETE CASCADE NOT NULL,

    similarity_score FLOAT NOT NULL CHECK (similarity_score >= 0 AND similarity_score <= 1),
    similarity_type TEXT CHECK (similarity_type IN ('semantic', 'entity_overlap', 'content_hash', 'both')),

    -- Shared entities
    shared_entities UUID[],

    -- Review status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'merged', 'distinct', 'ignored')),
    reviewed_by_user_id TEXT,
    reviewed_at TIMESTAMPTZ,
    merge_decision TEXT,  -- 'keep_source', 'keep_target', 'merge_both', 'create_new'

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(claim_id, similar_claim_id)
);

-- ============================================
-- RESEARCH CACHE
-- For reusing previous research
-- ============================================
CREATE TABLE IF NOT EXISTS research_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    query_hash TEXT NOT NULL,
    template_type TEXT NOT NULL,
    workspace_id TEXT DEFAULT 'default',

    cached_session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE,
    cache_expires_at TIMESTAMPTZ,

    hit_count INT DEFAULT 0,
    last_hit_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(query_hash, template_type, workspace_id)
);

-- ============================================
-- RESEARCH DOCUMENTS
-- Links research to uploaded documents
-- ============================================
CREATE TABLE IF NOT EXISTS research_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE NOT NULL,

    external_document_id TEXT NOT NULL,
    document_path TEXT,

    extracted_content TEXT,
    extraction_purpose TEXT,
    relevance_score FLOAT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================

-- Topics
CREATE INDEX IF NOT EXISTS idx_topics_parent ON knowledge_topics(parent_id);
CREATE INDEX IF NOT EXISTS idx_topics_path ON knowledge_topics USING GIN(path);
CREATE INDEX IF NOT EXISTS idx_topics_slug ON knowledge_topics(slug);
CREATE INDEX IF NOT EXISTS idx_topics_type ON knowledge_topics(topic_type);

-- Entities
CREATE INDEX IF NOT EXISTS idx_entities_type ON knowledge_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_name_hash ON knowledge_entities(name_hash);
CREATE INDEX IF NOT EXISTS idx_entities_canonical ON knowledge_entities(canonical_name);
-- Vector index for similarity search (create after data exists)
-- CREATE INDEX idx_entities_embedding ON knowledge_entities USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);

-- Claims
CREATE INDEX IF NOT EXISTS idx_claims_topic ON knowledge_claims(topic_id);
CREATE INDEX IF NOT EXISTS idx_claims_type ON knowledge_claims(claim_type);
CREATE INDEX IF NOT EXISTS idx_claims_content_hash ON knowledge_claims(content_hash);
CREATE INDEX IF NOT EXISTS idx_claims_visibility ON knowledge_claims(visibility);
CREATE INDEX IF NOT EXISTS idx_claims_verification ON knowledge_claims(verification_status);
CREATE INDEX IF NOT EXISTS idx_claims_current ON knowledge_claims(is_current) WHERE is_current = TRUE;
CREATE INDEX IF NOT EXISTS idx_claims_workspace ON knowledge_claims(workspace_id);
CREATE INDEX IF NOT EXISTS idx_claims_origin_session ON knowledge_claims(origin_session_id);
CREATE INDEX IF NOT EXISTS idx_claims_tags ON knowledge_claims USING GIN(tags);
-- Vector index for similarity search (create after data exists)
-- CREATE INDEX idx_claims_embedding ON knowledge_claims USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);

-- Relationships
CREATE INDEX IF NOT EXISTS idx_relationships_source ON claim_relationships(source_claim_id);
CREATE INDEX IF NOT EXISTS idx_relationships_target ON claim_relationships(target_claim_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON claim_relationships(relationship_type);

-- Claim-Entity links
CREATE INDEX IF NOT EXISTS idx_claim_entities_claim ON claim_entities(claim_id);
CREATE INDEX IF NOT EXISTS idx_claim_entities_entity ON claim_entities(entity_id);
CREATE INDEX IF NOT EXISTS idx_claim_entities_role ON claim_entities(role);

-- Claim sources
CREATE INDEX IF NOT EXISTS idx_claim_sources_claim ON claim_sources(claim_id);
CREATE INDEX IF NOT EXISTS idx_claim_sources_web ON claim_sources(web_source_id);
CREATE INDEX IF NOT EXISTS idx_claim_sources_source_claim ON claim_sources(source_claim_id);

-- Sessions
CREATE INDEX IF NOT EXISTS idx_sessions_workspace ON research_sessions(workspace_id);
CREATE INDEX IF NOT EXISTS idx_sessions_template ON research_sessions(template_type);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON research_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON research_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON research_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_primary_topic ON research_sessions(primary_topic_id);

-- Queries
CREATE INDEX IF NOT EXISTS idx_queries_session ON research_queries(session_id);

-- Sources
CREATE INDEX IF NOT EXISTS idx_sources_session ON research_sources(session_id);
CREATE INDEX IF NOT EXISTS idx_sources_credibility ON research_sources(credibility_score DESC);
CREATE INDEX IF NOT EXISTS idx_sources_domain ON research_sources(domain);
CREATE INDEX IF NOT EXISTS idx_sources_url_hash ON research_sources(url_hash);

-- Findings
CREATE INDEX IF NOT EXISTS idx_findings_session ON research_findings(session_id);
CREATE INDEX IF NOT EXISTS idx_findings_type ON research_findings(finding_type);
CREATE INDEX IF NOT EXISTS idx_findings_promoted ON research_findings(is_promoted);
CREATE INDEX IF NOT EXISTS idx_findings_claim ON research_findings(knowledge_claim_id);

-- Finding-Claims links
CREATE INDEX IF NOT EXISTS idx_finding_claims_finding ON finding_claims(finding_id);
CREATE INDEX IF NOT EXISTS idx_finding_claims_claim ON finding_claims(claim_id);

-- Perspectives
CREATE INDEX IF NOT EXISTS idx_perspectives_session ON research_perspectives(session_id);
CREATE INDEX IF NOT EXISTS idx_perspectives_type ON research_perspectives(perspective_type);

-- Similarity candidates
CREATE INDEX IF NOT EXISTS idx_similarity_pending ON similarity_candidates(status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_similarity_claim ON similarity_candidates(claim_id);

-- Cache
CREATE INDEX IF NOT EXISTS idx_cache_lookup ON research_cache(query_hash, template_type, workspace_id);

-- ============================================
-- FUNCTIONS
-- ============================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to tables with updated_at
CREATE TRIGGER update_topics_updated_at BEFORE UPDATE ON knowledge_topics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_entities_updated_at BEFORE UPDATE ON knowledge_entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_claims_updated_at BEFORE UPDATE ON knowledge_claims
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON research_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Update topic path when parent changes
CREATE OR REPLACE FUNCTION update_topic_path()
RETURNS TRIGGER AS $$
DECLARE
    parent_path TEXT[];
    parent_depth INT;
BEGIN
    IF NEW.parent_id IS NULL THEN
        NEW.path = ARRAY[NEW.id::TEXT];
        NEW.depth = 0;
    ELSE
        SELECT path, depth INTO parent_path, parent_depth
        FROM knowledge_topics WHERE id = NEW.parent_id;

        NEW.path = array_append(parent_path, NEW.id::TEXT);
        NEW.depth = parent_depth + 1;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_topic_path BEFORE INSERT OR UPDATE OF parent_id ON knowledge_topics
    FOR EACH ROW EXECUTE FUNCTION update_topic_path();

-- Update topic stats when claims change
CREATE OR REPLACE FUNCTION update_topic_claim_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.topic_id IS NOT NULL THEN
        UPDATE knowledge_topics
        SET finding_count = finding_count + 1,
            last_activity_at = NOW()
        WHERE id = NEW.topic_id;
    ELSIF TG_OP = 'DELETE' AND OLD.topic_id IS NOT NULL THEN
        UPDATE knowledge_topics
        SET finding_count = GREATEST(0, finding_count - 1)
        WHERE id = OLD.topic_id;
    ELSIF TG_OP = 'UPDATE' AND OLD.topic_id IS DISTINCT FROM NEW.topic_id THEN
        IF OLD.topic_id IS NOT NULL THEN
            UPDATE knowledge_topics
            SET finding_count = GREATEST(0, finding_count - 1)
            WHERE id = OLD.topic_id;
        END IF;
        IF NEW.topic_id IS NOT NULL THEN
            UPDATE knowledge_topics
            SET finding_count = finding_count + 1,
                last_activity_at = NOW()
            WHERE id = NEW.topic_id;
        END IF;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_claim_topic_stats AFTER INSERT OR UPDATE OR DELETE ON knowledge_claims
    FOR EACH ROW EXECUTE FUNCTION update_topic_claim_stats();

-- Update entity stats when claim_entities change
CREATE OR REPLACE FUNCTION update_entity_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE knowledge_entities
        SET claim_count = claim_count + 1,
            mention_count = mention_count + 1
        WHERE id = NEW.entity_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE knowledge_entities
        SET claim_count = GREATEST(0, claim_count - 1),
            mention_count = GREATEST(0, mention_count - 1)
        WHERE id = OLD.entity_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_entity_stats AFTER INSERT OR DELETE ON claim_entities
    FOR EACH ROW EXECUTE FUNCTION update_entity_stats();

-- Update source citation count
CREATE OR REPLACE FUNCTION update_source_citations()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.web_source_id IS NOT NULL THEN
        UPDATE research_sources
        SET citation_count = citation_count + 1
        WHERE id = NEW.web_source_id;
    ELSIF TG_OP = 'DELETE' AND OLD.web_source_id IS NOT NULL THEN
        UPDATE research_sources
        SET citation_count = GREATEST(0, citation_count - 1)
        WHERE id = OLD.web_source_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_source_citations AFTER INSERT OR DELETE ON claim_sources
    FOR EACH ROW EXECUTE FUNCTION update_source_citations();

-- Get topic path (ancestors)
CREATE OR REPLACE FUNCTION get_topic_path(topic_uuid UUID)
RETURNS TABLE(id UUID, name TEXT, slug TEXT, depth INT) AS $$
WITH RECURSIVE topic_tree AS (
    SELECT t.id, t.name, t.slug, t.parent_id, 0 as depth
    FROM knowledge_topics t WHERE t.id = topic_uuid
    UNION ALL
    SELECT t.id, t.name, t.slug, t.parent_id, tt.depth + 1
    FROM knowledge_topics t
    JOIN topic_tree tt ON t.id = tt.parent_id
)
SELECT id, name, slug, depth FROM topic_tree ORDER BY depth DESC;
$$ LANGUAGE SQL STABLE;

-- Get topic children (descendants)
CREATE OR REPLACE FUNCTION get_topic_descendants(topic_uuid UUID)
RETURNS TABLE(id UUID, name TEXT, slug TEXT, depth INT) AS $$
WITH RECURSIVE topic_tree AS (
    SELECT t.id, t.name, t.slug, 0 as depth
    FROM knowledge_topics t WHERE t.id = topic_uuid
    UNION ALL
    SELECT t.id, t.name, t.slug, tt.depth + 1
    FROM knowledge_topics t
    JOIN topic_tree tt ON t.parent_id = tt.id
)
SELECT id, name, slug, depth FROM topic_tree WHERE depth > 0 ORDER BY depth;
$$ LANGUAGE SQL STABLE;

-- Get claim causality chain (what caused this)
CREATE OR REPLACE FUNCTION get_causal_chain(claim_uuid UUID, max_depth INT DEFAULT 5)
RETURNS TABLE(claim_id UUID, content TEXT, summary TEXT, depth INT, relationship TEXT, strength FLOAT) AS $$
WITH RECURSIVE causal_tree AS (
    SELECT c.id as claim_id, c.content, c.summary, 0 as depth, NULL::TEXT as relationship, NULL::FLOAT as strength
    FROM knowledge_claims c WHERE c.id = claim_uuid
    UNION ALL
    SELECT kc.id, kc.content, kc.summary, ct.depth + 1, cr.relationship_type, cr.strength
    FROM knowledge_claims kc
    JOIN claim_relationships cr ON kc.id = cr.source_claim_id
    JOIN causal_tree ct ON cr.target_claim_id = ct.claim_id
    WHERE ct.depth < max_depth
    AND kc.is_current = TRUE
    AND cr.relationship_type IN ('causes', 'precedes', 'enables', 'part_of')
)
SELECT claim_id, content, summary, depth, relationship, strength FROM causal_tree ORDER BY depth;
$$ LANGUAGE SQL STABLE;

-- Get claim consequences (what this caused)
CREATE OR REPLACE FUNCTION get_consequences(claim_uuid UUID, max_depth INT DEFAULT 5)
RETURNS TABLE(claim_id UUID, content TEXT, summary TEXT, depth INT, relationship TEXT, strength FLOAT) AS $$
WITH RECURSIVE consequence_tree AS (
    SELECT c.id as claim_id, c.content, c.summary, 0 as depth, NULL::TEXT as relationship, NULL::FLOAT as strength
    FROM knowledge_claims c WHERE c.id = claim_uuid
    UNION ALL
    SELECT kc.id, kc.content, kc.summary, ct.depth + 1, cr.relationship_type, cr.strength
    FROM knowledge_claims kc
    JOIN claim_relationships cr ON kc.id = cr.target_claim_id
    JOIN consequence_tree ct ON cr.source_claim_id = ct.claim_id
    WHERE ct.depth < max_depth
    AND kc.is_current = TRUE
    AND cr.relationship_type IN ('causes', 'precedes', 'enables')
)
SELECT claim_id, content, summary, depth, relationship, strength FROM consequence_tree ORDER BY depth;
$$ LANGUAGE SQL STABLE;

-- Find claims by entity
CREATE OR REPLACE FUNCTION get_claims_by_entity(entity_uuid UUID, limit_count INT DEFAULT 50)
RETURNS TABLE(claim_id UUID, claim_type TEXT, content TEXT, summary TEXT, role TEXT, confidence FLOAT) AS $$
SELECT kc.id, kc.claim_type, kc.content, kc.summary, ce.role, kc.confidence_score
FROM knowledge_claims kc
JOIN claim_entities ce ON kc.id = ce.claim_id
WHERE ce.entity_id = entity_uuid
AND kc.is_current = TRUE
ORDER BY kc.confidence_score DESC, kc.created_at DESC
LIMIT limit_count;
$$ LANGUAGE SQL STABLE;

-- Find similar claims (requires embedding)
-- Note: Create IVFFlat index first: CREATE INDEX idx_claims_embedding ON knowledge_claims USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);
CREATE OR REPLACE FUNCTION find_similar_claims(
    claim_embedding VECTOR(768),
    similarity_threshold FLOAT DEFAULT 0.85,
    limit_count INT DEFAULT 10,
    exclude_claim_id UUID DEFAULT NULL
)
RETURNS TABLE(claim_id UUID, claim_type TEXT, content TEXT, summary TEXT, similarity FLOAT) AS $$
SELECT
    id,
    claim_type,
    content,
    summary,
    1 - (embedding <=> claim_embedding) as similarity
FROM knowledge_claims
WHERE is_current = TRUE
AND embedding IS NOT NULL
AND (exclude_claim_id IS NULL OR id != exclude_claim_id)
AND 1 - (embedding <=> claim_embedding) > similarity_threshold
ORDER BY embedding <=> claim_embedding
LIMIT limit_count;
$$ LANGUAGE SQL STABLE;

-- Get related claims (all relationship types)
CREATE OR REPLACE FUNCTION get_related_claims(claim_uuid UUID)
RETURNS TABLE(
    claim_id UUID,
    content TEXT,
    summary TEXT,
    relationship_type TEXT,
    direction TEXT,
    strength FLOAT
) AS $$
SELECT
    kc.id,
    kc.content,
    kc.summary,
    cr.relationship_type,
    'outgoing' as direction,
    cr.strength
FROM knowledge_claims kc
JOIN claim_relationships cr ON kc.id = cr.target_claim_id
WHERE cr.source_claim_id = claim_uuid
AND kc.is_current = TRUE

UNION ALL

SELECT
    kc.id,
    kc.content,
    kc.summary,
    cr.relationship_type,
    'incoming' as direction,
    cr.strength
FROM knowledge_claims kc
JOIN claim_relationships cr ON kc.id = cr.source_claim_id
WHERE cr.target_claim_id = claim_uuid
AND kc.is_current = TRUE

ORDER BY strength DESC;
$$ LANGUAGE SQL STABLE;

-- ============================================
-- ROW LEVEL SECURITY (Enable when ready)
-- ============================================

-- Uncomment when auth is implemented:
-- ALTER TABLE knowledge_claims ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE research_sessions ENABLE ROW LEVEL SECURITY;

-- Public claims are visible to all
-- CREATE POLICY claims_public_read ON knowledge_claims
--     FOR SELECT USING (visibility = 'public');

-- Users can see their own private claims
-- CREATE POLICY claims_own_private ON knowledge_claims
--     FOR ALL USING (created_by_user_id = current_setting('app.user_id', true));

-- Workspace members can see workspace claims
-- CREATE POLICY claims_workspace ON knowledge_claims
--     FOR SELECT USING (
--         visibility = 'workspace'
--         AND workspace_id = current_setting('app.workspace_id', true)
--     );

-- ============================================
-- ADDITIONAL TABLES
-- See migration files for:
-- - 004_add_profile_research.sql: entity_research_pairs, entity_profile_research
-- ============================================
