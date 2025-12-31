-- ============================================
-- Migration 006: Financial Entities Tables
-- ============================================
-- Adds tables for financial forensics research including
-- financial entities, transactions, corporate structures,
-- and property records.
--
-- Run this migration after 005_add_recursive_research.sql
-- ============================================

-- ============================================
-- FINANCIAL ENTITIES
-- Companies, trusts, accounts, etc.
-- ============================================
CREATE TABLE IF NOT EXISTS financial_entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Link to main knowledge entity if exists
    entity_id UUID,  -- References knowledge_entities(id)

    -- Entity information
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL
        CHECK (entity_type IN ('corporation', 'llc', 'trust', 'foundation',
                               'partnership', 'bank_account', 'brokerage',
                               'shell_company', 'unknown')),

    -- Registration details
    jurisdiction TEXT,  -- State/country of incorporation
    registration_number TEXT,  -- Corp ID, EIN, etc.
    status TEXT CHECK (status IN ('active', 'dissolved', 'merged', 'unknown')),

    -- Dates
    incorporation_date DATE,
    dissolution_date DATE,

    -- Address information
    registered_agent TEXT,
    registered_address TEXT,

    -- Additional data (SEC CIK, OpenCorporates URL, etc.)
    metadata JSONB DEFAULT '{}',

    -- Workspace and timestamps
    workspace_id TEXT DEFAULT 'default',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for financial_entities
CREATE INDEX IF NOT EXISTS idx_fin_entities_entity ON financial_entities(entity_id);
CREATE INDEX IF NOT EXISTS idx_fin_entities_name ON financial_entities(name);
CREATE INDEX IF NOT EXISTS idx_fin_entities_type ON financial_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_fin_entities_jurisdiction ON financial_entities(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_fin_entities_workspace ON financial_entities(workspace_id);

-- Trigger for updated_at
CREATE TRIGGER update_fin_entities_updated_at
    BEFORE UPDATE ON financial_entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================
-- FINANCIAL TRANSACTIONS
-- Money flows between entities
-- ============================================
CREATE TABLE IF NOT EXISTS financial_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Transaction parties
    source_entity_id UUID REFERENCES financial_entities(id) ON DELETE SET NULL,
    target_entity_id UUID REFERENCES financial_entities(id) ON DELETE SET NULL,

    -- Transaction details
    transaction_type TEXT NOT NULL
        CHECK (transaction_type IN ('transfer', 'sale', 'purchase', 'loan',
                                     'investment', 'donation', 'fee',
                                     'settlement', 'salary', 'gift')),

    -- Amount information
    amount DECIMAL(20, 2),
    currency TEXT DEFAULT 'USD',

    -- Timing
    transaction_date DATE,
    transaction_date_precision TEXT DEFAULT 'day'
        CHECK (transaction_date_precision IN ('day', 'month', 'year', 'approximate')),

    -- Description and purpose
    description TEXT,
    purpose TEXT,

    -- Evidence tracking
    evidence_strength TEXT DEFAULT 'medium'
        CHECK (evidence_strength IN ('high', 'medium', 'low', 'alleged')),
    source_document TEXT,  -- Reference to source
    source_url TEXT,

    -- Additional data
    metadata JSONB DEFAULT '{}',

    -- Workspace and timestamps
    workspace_id TEXT DEFAULT 'default',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for financial_transactions
CREATE INDEX IF NOT EXISTS idx_fin_tx_source ON financial_transactions(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_fin_tx_target ON financial_transactions(target_entity_id);
CREATE INDEX IF NOT EXISTS idx_fin_tx_date ON financial_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_fin_tx_type ON financial_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_fin_tx_amount ON financial_transactions(amount);
CREATE INDEX IF NOT EXISTS idx_fin_tx_workspace ON financial_transactions(workspace_id);


-- ============================================
-- CORPORATE RELATIONSHIPS
-- Ownership, control, and organizational links
-- ============================================
CREATE TABLE IF NOT EXISTS corporate_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Related entities
    parent_entity_id UUID REFERENCES financial_entities(id) ON DELETE CASCADE,
    child_entity_id UUID REFERENCES financial_entities(id) ON DELETE CASCADE,

    -- Relationship details
    relationship_type TEXT NOT NULL
        CHECK (relationship_type IN ('owns', 'controls', 'subsidiary', 'affiliate',
                                      'director', 'officer', 'registered_agent',
                                      'beneficial_owner', 'nominee')),

    -- Ownership percentage (NULL if not ownership relationship)
    ownership_percentage DECIMAL(5, 2)
        CHECK (ownership_percentage IS NULL OR
               (ownership_percentage >= 0 AND ownership_percentage <= 100)),

    -- Time period
    start_date DATE,
    end_date DATE,

    -- Evidence tracking
    evidence_strength TEXT DEFAULT 'medium'
        CHECK (evidence_strength IN ('high', 'medium', 'low', 'alleged')),
    source_document TEXT,
    source_url TEXT,

    -- Workspace and timestamps
    workspace_id TEXT DEFAULT 'default',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for corporate_relationships
CREATE INDEX IF NOT EXISTS idx_corp_rel_parent ON corporate_relationships(parent_entity_id);
CREATE INDEX IF NOT EXISTS idx_corp_rel_child ON corporate_relationships(child_entity_id);
CREATE INDEX IF NOT EXISTS idx_corp_rel_type ON corporate_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_corp_rel_workspace ON corporate_relationships(workspace_id);


-- ============================================
-- BENEFICIAL OWNERS
-- Ultimate ownership tracking
-- ============================================
CREATE TABLE IF NOT EXISTS beneficial_owners (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Company being owned
    company_entity_id UUID NOT NULL REFERENCES financial_entities(id) ON DELETE CASCADE,

    -- Owner (person or ultimate parent company)
    owner_entity_id UUID,  -- References knowledge_entities(id)
    owner_name TEXT,  -- Fallback if no entity exists

    -- Ownership details
    ownership_type TEXT NOT NULL
        CHECK (ownership_type IN ('direct', 'indirect', 'beneficial', 'nominee')),
    ownership_percentage DECIMAL(5, 2),
    control_type TEXT CHECK (control_type IN ('voting', 'economic', 'both')),

    -- Evidence tracking
    evidence_strength TEXT DEFAULT 'medium'
        CHECK (evidence_strength IN ('high', 'medium', 'low', 'alleged')),
    source_document TEXT,

    -- Workspace and timestamps
    workspace_id TEXT DEFAULT 'default',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for beneficial_owners
CREATE INDEX IF NOT EXISTS idx_beneficial_company ON beneficial_owners(company_entity_id);
CREATE INDEX IF NOT EXISTS idx_beneficial_owner ON beneficial_owners(owner_entity_id);
CREATE INDEX IF NOT EXISTS idx_beneficial_workspace ON beneficial_owners(workspace_id);


-- ============================================
-- PROPERTY RECORDS
-- Real estate holdings and transfers
-- ============================================
CREATE TABLE IF NOT EXISTS property_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Property details
    property_address TEXT NOT NULL,
    property_type TEXT CHECK (property_type IN ('residential', 'commercial', 'land', 'mixed')),
    jurisdiction TEXT,  -- County, State
    parcel_id TEXT,

    -- Ownership
    owner_entity_id UUID REFERENCES financial_entities(id) ON DELETE SET NULL,
    owner_name TEXT,  -- Fallback name

    -- Purchase information
    purchase_date DATE,
    purchase_price DECIMAL(20, 2),

    -- Sale information (if sold)
    sale_date DATE,
    sale_price DECIMAL(20, 2),

    -- Current valuation
    current_assessed_value DECIMAL(20, 2),

    -- Source
    source_url TEXT,

    -- Additional data
    metadata JSONB DEFAULT '{}',

    -- Workspace and timestamps
    workspace_id TEXT DEFAULT 'default',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for property_records
CREATE INDEX IF NOT EXISTS idx_property_owner ON property_records(owner_entity_id);
CREATE INDEX IF NOT EXISTS idx_property_address ON property_records(property_address);
CREATE INDEX IF NOT EXISTS idx_property_jurisdiction ON property_records(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_property_workspace ON property_records(workspace_id);


-- ============================================
-- SHELL COMPANY INDICATORS
-- Tracking suspicious patterns
-- ============================================
CREATE TABLE IF NOT EXISTS shell_company_indicators (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Entity being analyzed
    entity_id UUID NOT NULL REFERENCES financial_entities(id) ON DELETE CASCADE,

    -- Indicator details
    indicator_type TEXT NOT NULL
        CHECK (indicator_type IN ('secrecy_jurisdiction', 'no_physical_address',
                                   'registered_agent_only', 'no_employees',
                                   'circular_ownership', 'rapid_ownership_changes',
                                   'no_public_filings', 'nominee_directors')),

    -- Confidence
    confidence FLOAT DEFAULT 0.5
        CHECK (confidence >= 0.0 AND confidence <= 1.0),

    -- Details
    details TEXT,
    source_document TEXT,

    -- Timestamps
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for shell_company_indicators
CREATE INDEX IF NOT EXISTS idx_shell_entity ON shell_company_indicators(entity_id);
CREATE INDEX IF NOT EXISTS idx_shell_type ON shell_company_indicators(indicator_type);


-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Get total inflow for an entity
CREATE OR REPLACE FUNCTION get_entity_inflow(p_entity_id UUID, p_start_date DATE DEFAULT NULL, p_end_date DATE DEFAULT NULL)
RETURNS DECIMAL AS $$
    SELECT COALESCE(SUM(amount), 0)
    FROM financial_transactions
    WHERE target_entity_id = p_entity_id
      AND (p_start_date IS NULL OR transaction_date >= p_start_date)
      AND (p_end_date IS NULL OR transaction_date <= p_end_date);
$$ LANGUAGE SQL;


-- Get total outflow for an entity
CREATE OR REPLACE FUNCTION get_entity_outflow(p_entity_id UUID, p_start_date DATE DEFAULT NULL, p_end_date DATE DEFAULT NULL)
RETURNS DECIMAL AS $$
    SELECT COALESCE(SUM(amount), 0)
    FROM financial_transactions
    WHERE source_entity_id = p_entity_id
      AND (p_start_date IS NULL OR transaction_date >= p_start_date)
      AND (p_end_date IS NULL OR transaction_date <= p_end_date);
$$ LANGUAGE SQL;


-- Count shell company indicators for an entity
CREATE OR REPLACE FUNCTION count_shell_indicators(p_entity_id UUID)
RETURNS INT AS $$
    SELECT COUNT(*)::INT
    FROM shell_company_indicators
    WHERE entity_id = p_entity_id
      AND confidence >= 0.5;
$$ LANGUAGE SQL;


-- Check if entity is likely a shell company (2+ indicators)
CREATE OR REPLACE FUNCTION is_likely_shell_company(p_entity_id UUID)
RETURNS BOOLEAN AS $$
    SELECT count_shell_indicators(p_entity_id) >= 2;
$$ LANGUAGE SQL;


-- ============================================
-- VIEWS
-- ============================================

-- Entity financial summary
CREATE OR REPLACE VIEW entity_financial_summary AS
SELECT
    fe.id,
    fe.name,
    fe.entity_type,
    fe.jurisdiction,
    fe.status,
    get_entity_inflow(fe.id) as total_inflow,
    get_entity_outflow(fe.id) as total_outflow,
    get_entity_inflow(fe.id) - get_entity_outflow(fe.id) as net_flow,
    (SELECT COUNT(*) FROM financial_transactions WHERE source_entity_id = fe.id OR target_entity_id = fe.id) as transaction_count,
    count_shell_indicators(fe.id) as shell_indicators,
    is_likely_shell_company(fe.id) as likely_shell
FROM financial_entities fe;


-- ============================================
-- COMMENTS
-- ============================================
COMMENT ON TABLE financial_entities IS
    'Companies, trusts, accounts, and other financial vehicles.';

COMMENT ON TABLE financial_transactions IS
    'Money flows between financial entities with amounts, dates, and purposes.';

COMMENT ON TABLE corporate_relationships IS
    'Ownership, control, and organizational relationships between entities.';

COMMENT ON TABLE beneficial_owners IS
    'Ultimate beneficial owners of companies, tracing through shell structures.';

COMMENT ON TABLE property_records IS
    'Real estate holdings and historical transfers.';

COMMENT ON TABLE shell_company_indicators IS
    'Suspicious patterns that may indicate shell company activity.';
