# 04-DATABASE-SCHEMA.md: Database Schema & Design

**Project**: KHALA v2.0
**Database**: SurrealDB 2.0+
**Reference**: [03-architecture-technical.md](03-architecture-technical.md)

---

## 1. Overview

The KHALA database uses a multi-model approach combining:
1.  **Document Store**: For flexible memory objects.
2.  **Vector Store**: For semantic search.
3.  **Graph Store**: For entity relationships.

## 2. Namespaces & Databases

*   **Namespace**: `khala` (Production), `khala_dev` (Development).
*   **Database**: `memory_store`.

---

## 3. Tables Definition

### `memory` (Document + Vector)
Primary storage for agent memories.

```surrealql
DEFINE TABLE memory SCHEMAFULL
    PERMISSIONS FOR select, create, update, delete WHERE user_id = $auth.id;

DEFINE FIELD id ON memory TYPE record;
DEFINE FIELD user_id ON memory TYPE string;
DEFINE FIELD content ON memory TYPE string;
DEFINE FIELD embedding ON memory TYPE array<float>; -- 768 dimensions
DEFINE FIELD created_at ON memory TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON memory TYPE datetime DEFAULT time::now();
DEFINE FIELD tier ON memory TYPE string ASSERT $value IN ['working', 'short_term', 'long_term'];
DEFINE FIELD importance ON memory TYPE float ASSERT $value >= 0 AND $value <= 1;
DEFINE FIELD tags ON memory TYPE array<string>;
DEFINE FIELD metadata ON memory TYPE object FLEXIBLE;

-- Indexes
DEFINE INDEX idx_memory_embedding ON memory FIELDS embedding MTPREE DIMENSION 768 DIST M=16 EF=200; -- HNSW
DEFINE INDEX idx_memory_content_ft ON memory FIELDS content FULLTEXT; -- BM25
DEFINE INDEX idx_memory_user_tier ON memory FIELDS user_id, tier;
```

### `entity` (Graph Node)
Represents extracted entities (People, Places, Concepts).

```surrealql
DEFINE TABLE entity SCHEMAFULL;

DEFINE FIELD name ON entity TYPE string;
DEFINE FIELD type ON entity TYPE string;
DEFINE FIELD description ON entity TYPE string;
DEFINE FIELD embedding ON entity TYPE array<float>;
DEFINE FIELD aliases ON entity TYPE array<string>;
DEFINE FIELD last_seen ON entity TYPE datetime;

DEFINE INDEX idx_entity_name ON entity FIELDS name UNIQUE;
DEFINE INDEX idx_entity_embedding ON entity FIELDS embedding MTPREE DIMENSION 768 DIST M=16;
```

### `relationship` (Graph Edge)
Represents connections between entities.

```surrealql
DEFINE TABLE relationship SCHEMAFULL TYPE RELATION IN entity OUT entity;

DEFINE FIELD type ON relationship TYPE string; -- e.g., 'KNOWS', 'LOCATED_AT'
DEFINE FIELD weight ON relationship TYPE float;
DEFINE FIELD first_seen ON relationship TYPE datetime;
DEFINE FIELD last_verified ON relationship TYPE datetime;
DEFINE FIELD bi_temporal_start ON relationship TYPE datetime;
DEFINE FIELD bi_temporal_end ON relationship TYPE datetime;
```

### `audit_log` (Compliance)
Logs all changes to memory.

```surrealql
DEFINE TABLE audit_log SCHEMAFULL;

DEFINE FIELD timestamp ON audit_log TYPE datetime DEFAULT time::now();
DEFINE FIELD actor ON audit_log TYPE string;
DEFINE FIELD action ON audit_log TYPE string; -- 'CREATE', 'MERGE', 'DELETE'
DEFINE FIELD target_id ON audit_log TYPE record;
DEFINE FIELD details ON audit_log TYPE object;
```

### `skill` (Skill Library)
Executable skills learned by the agent.

```surrealql
DEFINE TABLE skill SCHEMAFULL;

DEFINE FIELD name ON skill TYPE string;
DEFINE FIELD code ON skill TYPE string;
DEFINE FIELD description ON skill TYPE string;
DEFINE FIELD usage_count ON skill TYPE int DEFAULT 0;
DEFINE FIELD success_rate ON skill TYPE float DEFAULT 0.0;
```

---

## 4. Custom Functions

### Decay Score
Calculates memory relevance based on time.

```surrealql
DEFINE FUNCTION fn::decay_score($age_days: float, $half_life: float) {
    RETURN 1.0 / (1.0 + math::pow($age_days / $half_life, 2));
};
```

### Similarity Threshold
Helper for vector search.

```surrealql
DEFINE FUNCTION fn::is_similar($vec1: array, $vec2: array, $threshold: float) {
    RETURN vector::similarity::cosine($vec1, $vec2) >= $threshold;
};
```

---

## 5. Performance Optimization

*   **Composite Indexes**: Use `user_id + tier` for fast filtering.
*   **Vector Parameters**: `M=16`, `EF=200` tuned for high recall.
*   **Full-Text**: BM25 analyzer configured for English/Portuguese.

---

## 6. Backup Strategy

*   **Incremental**: Daily.
*   **Full**: Weekly.
*   **Export**: `surreal export --ns khala --db memory_store > backup.sql`
