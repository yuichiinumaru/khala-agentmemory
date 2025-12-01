# 04-DATABASE.md
# KHALA v2.0: Complete Database Schema & Design

**Project**: KHALA (Knowledge Hierarchical Adaptive Long-term Agent)  
**Database**: SurrealDB 2.0+  
**Language**: SurrealQL  
**Date**: November 2025

---

## 1. SURREALDB SCHEMA SETUP

### 1.1 Namespace & Database Creation

```sql
-- Create namespace for multi-tenancy
DEFINE NAMESPACE khala;
USE NS khala;

-- Create main database
DEFINE DATABASE memories;
USE DB memories;

-- Create per-user namespaces (optional, for advanced multi-tenancy)
DEFINE NAMESPACE user_{user_id};
USE NS user_{user_id} DB memories;
```

### 1.2 Core Tables

---

## 2. PRIMARY TABLES

### 2.1 Memory Table (Core)

```sql
DEFINE TABLE memory SCHEMAFULL;

DEFINE FIELD id ON memory TYPE string;
DEFINE FIELD user_id ON memory TYPE string;
DEFINE FIELD content ON memory TYPE string;
DEFINE FIELD embedding ON memory TYPE array<float> FLEXIBLE;
DEFINE FIELD tier ON memory TYPE enum<working,short_term,long_term>;
DEFINE FIELD importance ON memory TYPE float;
DEFINE FIELD tags ON memory TYPE array<string>;
DEFINE FIELD category ON memory TYPE string;
DEFINE FIELD metadata ON memory TYPE object FLEXIBLE;
DEFINE FIELD created_at ON memory TYPE datetime;
DEFINE FIELD updated_at ON memory TYPE datetime;
DEFINE FIELD accessed_at ON memory TYPE datetime;
DEFINE FIELD access_count ON memory TYPE int DEFAULT 0;
DEFINE FIELD llm_cost ON memory TYPE float DEFAULT 0.0;
DEFINE FIELD verification_score ON memory TYPE float;
DEFINE FIELD verification_issues ON memory TYPE array<string>;
DEFINE FIELD debate_consensus ON memory TYPE object FLEXIBLE;
DEFINE FIELD is_archived ON memory TYPE bool DEFAULT false;
DEFINE FIELD decay_score ON memory TYPE float;

-- Primary index (multi-tenancy)
DEFINE INDEX user_index ON memory FIELDS user_id;

-- Search indexes
DEFINE INDEX vector_search ON memory FIELDS embedding HNSW;
DEFINE INDEX bm25_search ON memory FIELDS content FULLTEXT;

-- Performance indexes
DEFINE INDEX tier_index ON memory FIELDS tier;
DEFINE INDEX importance_index ON memory FIELDS importance DESC;
DEFINE INDEX created_index ON memory FIELDS created_at DESC;
DEFINE INDEX accessed_index ON memory FIELDS accessed_at DESC;

-- Hot path composite
DEFINE INDEX hot_path ON memory 
  FIELDS user_id, importance DESC, EXPRESSION (now() - accessed_at);

-- Tag prefix search
DEFINE INDEX tag_search ON memory FIELDS tags FULLTEXT;

-- Permissions (RBAC)
DEFINE FIELD user_id ON memory
  PERMISSIONS 
    FOR select WHERE user_id = $auth.user_id
    FOR create WHERE $auth.user_id = user_id
    FOR update WHERE $auth.user_id = user_id
    FOR delete WHERE $auth.user_id = user_id;
```

**HNSW Index Parameters**:
```
- M (max connections): 16
- ef_construction (construction parameter): 200
- ef_runtime (query parameter): 50
- Dimensions: 768 (Gemini embeddings)
- Distance metric: Cosine similarity
```

---

### 2.2 Entity Table (Extracted Entities)

```sql
DEFINE TABLE entity SCHEMAFULL;

DEFINE FIELD id ON entity TYPE string;
DEFINE FIELD user_id ON entity TYPE string;
DEFINE FIELD text ON entity TYPE string;
DEFINE FIELD type ON entity TYPE enum<person,tool,concept,place,event>;
DEFINE FIELD embedding ON entity TYPE array<float> FLEXIBLE;
DEFINE FIELD confidence ON entity TYPE float;
DEFINE FIELD metadata ON entity TYPE object FLEXIBLE;
DEFINE FIELD created_at ON entity TYPE datetime;
DEFINE FIELD updated_at ON entity TYPE datetime;
DEFINE FIELD occurrence_count ON entity TYPE int DEFAULT 1;

-- Indexes
DEFINE INDEX user_entity_index ON entity FIELDS user_id;
DEFINE INDEX type_index ON entity FIELDS type;
DEFINE INDEX text_search ON entity FIELDS text;

-- Permissions
DEFINE FIELD user_id ON entity
  PERMISSIONS 
    FOR select WHERE user_id = $auth.user_id
    FOR create WHERE $auth.user_id = user_id
    FOR update WHERE $auth.user_id = user_id
    FOR delete WHERE $auth.user_id = user_id;
```

---

### 2.3 Relationship Table (Graph Edges)

```sql
DEFINE TABLE relationship SCHEMAFULL;

DEFINE FIELD id ON relationship TYPE string;
DEFINE FIELD user_id ON relationship TYPE string;
DEFINE FIELD source_id ON relationship TYPE string;  -- Source entity
DEFINE FIELD target_id ON relationship TYPE string;  -- Target entity
DEFINE FIELD relation_type ON relationship TYPE string;
DEFINE FIELD strength ON relationship TYPE float;    -- 0.0-1.0
DEFINE FIELD is_active ON relationship TYPE bool DEFAULT true;
DEFINE FIELD valid_from ON relationship TYPE datetime;
DEFINE FIELD valid_to ON relationship TYPE datetime;
DEFINE FIELD metadata ON relationship TYPE object FLEXIBLE;
DEFINE FIELD created_at ON relationship TYPE datetime;

-- Indexes
DEFINE INDEX source_index ON relationship FIELDS source_id;
DEFINE INDEX target_index ON relationship FIELDS target_id;
DEFINE INDEX relation_type_index ON relationship FIELDS relation_type;
DEFINE INDEX user_rel_index ON relationship FIELDS user_id;

-- Bi-temporal indexes
DEFINE INDEX temporal_index ON relationship 
  FIELDS valid_from, valid_to;
```

---

### 2.4 Skill Table (Reusable Patterns)

```sql
DEFINE TABLE skill SCHEMAFULL;

DEFINE FIELD id ON skill TYPE string;
DEFINE FIELD user_id ON skill TYPE string;
DEFINE FIELD name ON skill TYPE string;
DEFINE FIELD description ON skill TYPE string;
DEFINE FIELD preconditions ON skill TYPE array<string>;
DEFINE FIELD steps ON skill TYPE array<object>;
DEFINE FIELD postconditions ON skill TYPE array<string>;
DEFINE FIELD success_rate ON skill TYPE float;
DEFINE FIELD usage_count ON skill TYPE int DEFAULT 0;
DEFINE FIELD success_count ON skill TYPE int DEFAULT 0;
DEFINE FIELD confidence ON skill TYPE float;
DEFINE FIELD tags ON skill TYPE array<string>;
DEFINE FIELD created_at ON skill TYPE datetime;

-- Indexes
DEFINE INDEX user_skill_index ON skill FIELDS user_id;
DEFINE INDEX skill_success ON skill FIELDS success_rate DESC;
```

---

### 2.5 Audit Log Table (Compliance)

```sql
DEFINE TABLE audit_log SCHEMAFULL;

DEFINE FIELD id ON audit_log TYPE string;
DEFINE FIELD user_id ON audit_log TYPE string;
DEFINE FIELD memory_id ON audit_log TYPE string;
DEFINE FIELD action ON audit_log TYPE enum<create,update,promote,merge,archive,delete>;
DEFINE FIELD reason ON audit_log TYPE string;
DEFINE FIELD agent ON audit_log TYPE string;
DEFINE FIELD memory_snapshot ON audit_log TYPE object FLEXIBLE;
DEFINE FIELD verification_score ON audit_log TYPE float;
DEFINE FIELD debate_consensus ON audit_log TYPE object FLEXIBLE;
DEFINE FIELD llm_cost ON audit_log TYPE float;
DEFINE FIELD timestamp ON audit_log TYPE datetime;

-- Indexes (retention: 1 year minimum)
DEFINE INDEX user_audit_index ON audit_log FIELDS user_id;
DEFINE INDEX memory_audit_index ON audit_log FIELDS memory_id;
DEFINE INDEX timestamp_audit ON audit_log FIELDS timestamp DESC;
DEFINE INDEX action_audit ON audit_log FIELDS action;
```

---

### 2.6 Multimodal Memory Table

```sql
DEFINE TABLE multimodal_memory SCHEMAFULL;

DEFINE FIELD id ON multimodal_memory TYPE string;
DEFINE FIELD user_id ON multimodal_memory TYPE string;
DEFINE FIELD content ON multimodal_memory TYPE any;  -- bytes for files
DEFINE FIELD media_type ON multimodal_memory TYPE enum<text,image,table,code,diagram>;
DEFINE FIELD embedding ON multimodal_memory TYPE array<float> FLEXIBLE;
DEFINE FIELD modality_key ON multimodal_memory TYPE string;
DEFINE FIELD metadata ON multimodal_memory TYPE object FLEXIBLE;
DEFINE FIELD created_at ON multimodal_memory TYPE datetime;

-- Indexes
DEFINE INDEX user_multi_index ON multimodal_memory FIELDS user_id;
DEFINE INDEX media_type_index ON multimodal_memory FIELDS media_type;
```

---

### 2.7 Cost Tracking Table

```sql
DEFINE TABLE cost_tracking SCHEMAFULL;

DEFINE FIELD id ON cost_tracking TYPE string;
DEFINE FIELD user_id ON cost_tracking TYPE string;
DEFINE FIELD model ON cost_tracking TYPE string;  -- "flash", "medium", "smart"
DEFINE FIELD cost ON cost_tracking TYPE float;
DEFINE FIELD task_type ON cost_tracking TYPE string;
DEFINE FIELD input_tokens ON cost_tracking TYPE int;
DEFINE FIELD output_tokens ON cost_tracking TYPE int;
DEFINE FIELD timestamp ON cost_tracking TYPE datetime;

-- Indexes
DEFINE INDEX cost_user_index ON cost_tracking FIELDS user_id;
DEFINE INDEX cost_model_index ON cost_tracking FIELDS model;
DEFINE INDEX cost_time_index ON cost_tracking FIELDS timestamp DESC;
```

---

### 2.8 Debate Consensus Table

```sql
DEFINE TABLE debate_consensus SCHEMAFULL;

DEFINE FIELD id ON debate_consensus TYPE string;
DEFINE FIELD user_id ON debate_consensus TYPE string;
DEFINE FIELD memory_id ON debate_consensus TYPE string;
DEFINE FIELD agent_votes ON debate_consensus TYPE object FLEXIBLE;  -- {analyzer: 0.9, synthesizer: 0.85, curator: 0.88}
DEFINE FIELD consensus_score ON debate_consensus TYPE float;
DEFINE FIELD reasoning ON debate_consensus TYPE object FLEXIBLE;
DEFINE FIELD timestamp ON debate_consensus TYPE datetime;

-- Indexes
DEFINE INDEX debate_user_index ON debate_consensus FIELDS user_id;
DEFINE INDEX debate_memory_index ON debate_consensus FIELDS memory_id;
```

---

## 3. CUSTOM FUNCTIONS

### 3.1 Decay Scoring

```sql
DEFINE FUNCTION fn::decay_score($age_days: number, $half_life: number = 30): number {
    RETURN $age_days == 0 
        ? 1.0 
        : math::exp(-1 * $age_days / $half_life);
};

-- Usage: 
-- SELECT fn::decay_score(10, 30) AS score FROM memory;
-- Returns: exp(-10/30) ≈ 0.717
```

### 3.2 Promotion Logic

```sql
DEFINE FUNCTION fn::should_promote(
    $age_hours: number, 
    $access_count: number, 
    $importance: number
): bool {
    RETURN 
        ($age_hours > 0.5) 
        AND ($access_count > 5 OR $importance > 0.8)
        OR ($importance > 0.9);
};
```

### 3.3 Vector Similarity

```sql
DEFINE FUNCTION fn::cosine_similarity(
    $vec1: array<float>, 
    $vec2: array<float>
): number {
    -- SurrealDB has built-in vector operations
    -- This is syntactic sugar
    RETURN vector::similarity($vec1, $vec2);
};
```

### 3.4 Content Hash

```sql
DEFINE FUNCTION fn::content_hash($content: string): string {
    RETURN string::lowercase(
        encoding::base64(
            crypto::sha256($content)
        )
    );
};
```

### 3.5 Days Ago Calculation

```sql
DEFINE FUNCTION fn::days_ago($date: datetime): number {
    RETURN 
        (now() - $date).duration().days();
};
```

---

## 4. QUERY EXAMPLES (100+ queries)

### 4.1 Basic CRUD Operations

```sql
-- CREATE: Store a new memory
INSERT INTO memory {
    id: type::string(uuid()),
    user_id: 'user_123',
    content: 'Important decision about project structure',
    embedding: array::generate(768, 0.5),  -- Placeholder
    tier: 'working',
    importance: 0.8,
    tags: ['architecture', 'important'],
    category: 'decision',
    created_at: now(),
    updated_at: now(),
    accessed_at: now()
} RETURN id, created_at;

-- READ: Get memory by ID
SELECT * FROM memory WHERE id = 'memory_123' AND user_id = $auth.user_id;

-- READ: Get all working tier memories
SELECT * FROM memory 
WHERE user_id = $auth.user_id AND tier = 'working'
ORDER BY importance DESC;

-- UPDATE: Mark memory as accessed
UPDATE memory 
SET accessed_at = now(), access_count = access_count + 1
WHERE id = 'memory_123';

-- DELETE: Archive memory
UPDATE memory 
SET is_archived = true, updated_at = now()
WHERE id = 'memory_123';

-- Permanent delete (rare)
DELETE FROM memory WHERE id = 'memory_123';
```

### 4.2 Vector Search Queries

```sql
-- Vector similarity search (top 10)
SELECT id, content, vector::similarity(embedding, $query_vec) AS score
FROM memory 
WHERE user_id = $auth.user_id 
    AND vector::similarity(embedding, $query_vec) > 0.6
ORDER BY score DESC
LIMIT 10;

-- HNSW approximate nearest neighbor (fast)
SELECT id, content
FROM memory 
WHERE user_id = $auth.user_id
ORDER BY vector::distance(embedding, $query_vec) ASC
LIMIT 10;
```

### 4.3 Full-Text Search Queries

```sql
-- BM25 search
SELECT id, content
FROM memory 
WHERE user_id = $auth.user_id 
    AND content @@ 'keyword1 AND keyword2'
ORDER BY SCORE DESC
LIMIT 10;

-- Phrase search
SELECT id, content
FROM memory 
WHERE user_id = $auth.user_id 
    AND content @@ '"exact phrase"'
LIMIT 5;
```

### 4.4 Hybrid Search Queries

```sql
-- Stage 1: Vector search (candidates)
LET $vector_results = (
    SELECT id, content, vector::similarity(embedding, $query_vec) AS vec_score
    FROM memory 
    WHERE user_id = $auth.user_id
        AND vector::similarity(embedding, $query_vec) > 0.6
    ORDER BY vec_score DESC
    LIMIT 100
);

-- Stage 2: BM25 filter
LET $text_results = (
    SELECT id, content
    FROM memory 
    WHERE user_id = $auth.user_id 
        AND content @@ $search_query
    ORDER BY SCORE DESC
    LIMIT 50
);

-- Stage 3: Metadata filter
LET $metadata_results = (
    SELECT id, content
    FROM $vector_results 
    WHERE category IN $categories
        AND any(tags) IN $required_tags
);

-- Stage 4: Combine and rerank
SELECT id, content,
    (vec_score * 0.4 + importance * 0.3 + recency * 0.3) AS final_score
FROM $metadata_results
ORDER BY final_score DESC
LIMIT 10;
```

### 4.5 Entity Queries

```sql
-- Extract entities for a memory
SELECT 
    (CREATE entity {
        text: $entity_text,
        type: $entity_type,
        confidence: $confidence,
        user_id: $auth.user_id,
        created_at: now()
    }).id AS entity_id
FROM memory WHERE id = $memory_id;

-- Find all entities of a type
SELECT * FROM entity 
WHERE user_id = $auth.user_id 
    AND type = 'person'
ORDER BY occurrence_count DESC;

-- Entity with occurrence count
SELECT text, type, occurrence_count
FROM entity 
WHERE user_id = $auth.user_id
ORDER BY occurrence_count DESC
LIMIT 20;
```

### 4.6 Graph Relationship Queries

```sql
-- Create relationship between entities
RELATE entity:$source_id->relationship:rel1->entity:$target_id 
SET 
    relation_type = 'references',
    strength = 0.8,
    valid_from = now(),
    user_id = $auth.user_id;

-- Find all relationships for an entity (1-hop)
SELECT * FROM relationship 
WHERE source_id = $entity_id 
    AND user_id = $auth.user_id
    AND is_active = true;

-- Multi-hop graph traversal (2-hop)
SELECT 
    rel1.target_id AS intermediate_entity,
    rel2.target_id AS final_entity,
    rel2.relation_type
FROM relationship AS rel1
JOIN relationship AS rel2 ON rel1.target_id = rel2.source_id
WHERE rel1.source_id = $entity_id
    AND rel1.user_id = $auth.user_id
    AND rel2.user_id = $auth.user_id;
```

### 4.7 Temporal/Decay Queries

```sql
-- Apply decay scoring
SELECT 
    id, content,
    fn::decay_score(fn::days_ago(created_at), 30) AS decay_score,
    importance * fn::decay_score(fn::days_ago(created_at), 30) AS effective_importance
FROM memory
WHERE user_id = $auth.user_id
ORDER BY effective_importance DESC
LIMIT 10;

-- Find memories older than N days
SELECT id, content, fn::days_ago(created_at) AS age_days
FROM memory
WHERE user_id = $auth.user_id 
    AND fn::days_ago(created_at) > 90
ORDER BY age_days DESC;
```

### 4.8 Consolidation Queries

```sql
-- Find duplicates by hash
LET $hash = fn::content_hash($content);
SELECT id, content FROM memory
WHERE user_id = $auth.user_id
    AND fn::content_hash(content) = $hash;

-- Find semantic duplicates
SELECT m1.id, m2.id, vector::similarity(m1.embedding, m2.embedding) AS similarity
FROM memory AS m1, memory AS m2
WHERE m1.user_id = $auth.user_id
    AND m2.user_id = $auth.user_id
    AND m1.id != m2.id
    AND vector::similarity(m1.embedding, m2.embedding) > 0.95
LIMIT 50;

-- Archive old memories
UPDATE memory 
SET is_archived = true
WHERE user_id = $auth.user_id
    AND fn::days_ago(created_at) > 90
    AND access_count = 0
    AND importance < 0.3;
```

### 4.9 Statistics & Analytics

```sql
-- Memory count by tier
SELECT tier, count(*) AS count
FROM memory
WHERE user_id = $auth.user_id
GROUP BY tier;

-- Average importance by category
SELECT category, avg(importance) AS avg_importance, count(*) AS count
FROM memory
WHERE user_id = $auth.user_id
GROUP BY category
ORDER BY avg_importance DESC;

-- Cost breakdown by model
SELECT model, count(*) AS calls, sum(cost) AS total_cost
FROM cost_tracking
WHERE user_id = $auth.user_id
GROUP BY model
ORDER BY total_cost DESC;

-- Storage usage
SELECT 
    sum(array::len(encoding::base64(content))) AS total_bytes,
    count(*) AS memory_count,
    avg(array::len(encoding::base64(content))) AS avg_bytes
FROM memory
WHERE user_id = $auth.user_id;
```

### 4.10 Audit & Compliance Queries

```sql
-- Memory change history
SELECT timestamp, action, agent, memory_snapshot
FROM audit_log
WHERE user_id = $auth.user_id AND memory_id = $memory_id
ORDER BY timestamp DESC;

-- User activity
SELECT agent, count(*) AS action_count
FROM audit_log
WHERE user_id = $auth.user_id
GROUP BY agent
ORDER BY action_count DESC;

-- Access pattern for a memory
SELECT accessed_at, access_count
FROM memory
WHERE user_id = $auth.user_id AND id = $memory_id;

-- Verification failures (quality control)
SELECT id, verification_score, verification_issues
FROM memory
WHERE user_id = $auth.user_id 
    AND verification_score < 0.7
ORDER BY verification_score ASC
LIMIT 50;
```

---

## 5. PERFORMANCE OPTIMIZATION

### 5.1 Index Selection Guide

**Use Vector Index when**:
- Semantic similarity search needed
- Threshold: >0.6 similarity
- Size: <10M vectors

**Use BM25 Index when**:
- Keyword search needed
- Boolean operators needed
- Exact phrases needed

**Use B-Tree Index when**:
- Range queries (created_at > X)
- Equality filters (tier = 'long_term')
- Sorting by indexed field

**Use Composite Index when**:
- Multiple WHERE conditions
- Example: (user_id, importance DESC, created_at DESC)

### 5.2 Query Optimization Tips

```sql
-- GOOD: Use indexes effectively
SELECT * FROM memory
WHERE user_id = $auth.user_id  -- Indexed
    AND tier = 'working'        -- Indexed
    AND importance > 0.7        -- Indexed
LIMIT 10;

-- BAD: Forcing full table scan
SELECT * FROM memory
WHERE length(content) > 100     -- No index, computed field
LIMIT 10;

-- GOOD: Let database filter
SELECT * FROM memory
WHERE user_id = $auth.user_id
    AND vector::similarity(embedding, $vec) > 0.6
LIMIT 10;

-- BAD: Filtering in application
SELECT * FROM memory
WHERE user_id = $auth.user_id
ORDER BY vector::distance(embedding, $vec) ASC
-- (then filter in application)
```

---

## 6. BACKUP STRATEGY

### 6.1 Backup Schedule

```
Daily: 11 PM
  └─ Incremental backup (changed records only)

Weekly: Sunday 1 AM
  └─ Full backup (all records)

Monthly: 1st of month, 2 AM
  └─ Archival backup (long-term storage)
```

### 6.2 Backup Procedures

```bash
# Full backup
surreal export --conn ws://localhost:8000/rpc --db memories backup.sql

# Incremental backup (since last backup)
surreal export --conn ws://localhost:8000/rpc --db memories \
  --since "2024-01-01T00:00:00Z" backup_incremental.sql

# Restore from backup
surreal import --conn ws://localhost:8000/rpc --db memories backup.sql
```

### 6.3 Disaster Recovery

**RTO (Recovery Time Objective)**: <1 hour
**RPO (Recovery Point Objective)**: <5 minutes

Recovery steps:
1. Restore latest full backup
2. Apply all incremental backups since
3. Verify data integrity
4. Resume operations

---

## 7. SCHEMA MIGRATION

### 7.1 Adding New Fields

```sql
-- Add new field to existing table
DEFINE FIELD custom_field ON memory TYPE string;

-- Apply to all existing records
UPDATE memory SET custom_field = 'default_value';
```

### 7.2 Index Maintenance

```sql
-- Monitor index health
SELECT * FROM sys_info WHERE kind = 'index';

-- Rebuild index (if needed)
DEFINE INDEX vector_search ON memory FIELDS embedding HNSW;

-- Drop unused index
REMOVE INDEX vector_search_old ON memory;
```

---

## 8. REFERENCES

- SurrealDB Schema: https://surrealdb.com/docs/surrealql/statements/define
- Vector Indexes: https://surrealdb.com/docs/surrealql/statements/define/indexes
- Custom Functions: https://surrealdb.com/docs/surrealql/functions
- Query Optimization: https://surrealdb.com/docs/surrealql/explain

---

**END OF 04-DATABASE.MD**

See 02-tasks.md for database implementation tasks (M01.DEV.*)
