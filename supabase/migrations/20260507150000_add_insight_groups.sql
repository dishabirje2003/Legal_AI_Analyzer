-- Add insight_groups column to document_clauses table
-- Stores grouped/merged clause insights for the enterprise UI
ALTER TABLE document_clauses 
ADD COLUMN IF NOT EXISTS insight_groups JSONB DEFAULT '[]'::jsonb;

-- Add comment for documentation
COMMENT ON COLUMN document_clauses.insight_groups IS 'Grouped clause insights for enterprise UI - merged by category (risks, payments, deadlines, etc.)';
