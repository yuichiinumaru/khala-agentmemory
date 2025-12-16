-- Khala Admin Queries
-- Import this file into Surrealist "Query" view or use as a snippet library.

-- 1. 🔍 Inspect Recent Memories
-- View the last 20 memories created.
SELECT * FROM memory ORDER BY created_at DESC LIMIT 20;

-- 2. 🕸️ Graph Health: Find Orphans (Strategy 171)
-- Nodes with no outgoing or incoming links.
SELECT id, content FROM memory
WHERE array::len(->links) = 0
AND array::len(<-links) = 0;

-- 3. 🛡️ Security: Verification Failures
-- Memories flagged by VerificationGate or VisualSanitizer.
SELECT * FROM memory
WHERE metadata.verification_status = 'failed'
OR metadata.sanitization_record.was_sanitized = true;

-- 4. ⚙️ System: Job Queue Status
-- Monitor distributed consolidation.
SELECT status, count() FROM jobs GROUP BY status;

-- 5. 🧠 Intelligence: High Surprise Memories
-- Inspect memories that triggered high surprise scores (if implemented).
SELECT * FROM memory ORDER BY surprise_score DESC LIMIT 10;

-- 6. 🧹 Maintenance: Trash Can
-- Memories marked for deletion/archival.
SELECT * FROM memory WHERE is_archived = true;
