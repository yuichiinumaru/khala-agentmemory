# 08-TESTING.md: Testing Strategy

**Project**: KHALA v2.0
**Reference**: [02-tasks-implementation.md](02-tasks-implementation.md)

---

## 1. Testing Philosophy

KHALA uses a **Pyramid Testing Strategy**:
1.  **Unit Tests (70%)**: Test individual functions and classes.
2.  **Integration Tests (20%)**: Test DB interactions and API endpoints.
3.  **E2E/System Tests (10%)**: Test full agent workflows.

---

## 2. Test Suite Structure

```
tests/
├── unit/
│   ├── test_vector_search.py
│   ├── test_decay_logic.py
│   └── test_intent_classifier.py
├── integration/
│   ├── test_surrealdb_crud.py
│   ├── test_redis_cache.py
│   └── test_mcp_server.py
└── e2e/
    ├── test_agent_memory_flow.py
    └── test_multi_agent_debate.py
```

---

## 3. Key Test Cases

### Core Functionality
*   **Vector Search**: Verify `retrieve_memory` returns semantically relevant results.
*   **Consolidation**: Verify that 2 similar memories merge into 1.
*   **Decay**: Verify `importance` drops over time according to formula.

### Performance
*   **Latency**: Ensure search < 100ms.
*   **Throughput**: Ensure ingestion > 100 items/sec.

### Quality Assurance
*   **Verification Gate**: Feed bad data and ensure it is rejected.
*   **Debate**: Simulate disagreement and verify consensus logic.

---

## 4. Running Tests

```bash
# Run all
pytest

# Run only unit
pytest tests/unit

# Run with coverage
pytest --cov=khala tests/
```

---

## 5. CI/CD Pipeline

*   **Trigger**: Push to `main` or PR.
*   **Steps**:
    1.  Linting (`ruff`).
    2.  Type Checking (`mypy`).
    3.  Unit Tests.
    4.  Integration Tests (requires Service Containers).
