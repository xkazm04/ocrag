-- Migration: Add 'financial' and 'evidence' to claim_type constraint
-- Date: 2025-12-25
-- Purpose: Allow financial transaction claims for investigative research

-- Step 1: Drop the existing constraint
ALTER TABLE knowledge_claims
DROP CONSTRAINT IF EXISTS knowledge_claims_claim_type_check;

-- Step 2: Add new constraint with expanded claim types
ALTER TABLE knowledge_claims
ADD CONSTRAINT knowledge_claims_claim_type_check
CHECK (claim_type IN ('fact', 'event', 'relationship', 'pattern', 'prediction', 'financial', 'evidence'));

-- Verify the constraint
-- SELECT conname, pg_get_constraintdef(oid)
-- FROM pg_constraint
-- WHERE conrelid = 'knowledge_claims'::regclass AND conname = 'knowledge_claims_claim_type_check';
