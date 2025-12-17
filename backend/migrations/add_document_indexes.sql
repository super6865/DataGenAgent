-- Add indexes to documents table for better query performance
-- This fixes the "Out of sort memory" error when sorting by upload_time
-- Note: MySQL doesn't support IF NOT EXISTS for CREATE INDEX, so check if index exists first

-- Check if index exists before creating (run this query first):
-- SELECT COUNT(*) FROM information_schema.statistics 
-- WHERE table_schema = DATABASE() AND table_name = 'documents' AND index_name = 'idx_documents_upload_time';

-- Add index on upload_time for sorting
CREATE INDEX idx_documents_upload_time ON documents(upload_time);

-- Add index on parse_status for filtering
CREATE INDEX idx_documents_parse_status ON documents(parse_status);

-- Optional: Add composite index for common query patterns
-- CREATE INDEX idx_documents_status_time ON documents(parse_status, upload_time);
