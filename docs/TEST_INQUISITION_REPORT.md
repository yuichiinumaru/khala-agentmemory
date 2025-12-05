# TEST INQUISITION REPORT
**Inquisitor:** The TDD Absolutist
**Date:** 2025-12-05
**Verdict:** **TEST THEATER DETECTED**

---

## SECTION 1: THE TABLE OF LIES

| Severity | File/Test | The Lie (Crime) | Why it is dangerous | The Fix |
| :--- | :--- | :--- | :--- | :--- |
| **CRITICAL** | `tests/unit/verify_tier6.py` | **Assertionless Runner** | Catches `Exception` and prints `❌`. Returns Exit Code 0. | Remove `try/except`. Let `assert` crash the test. |
| **CRITICAL** | `tests/unit/verify_tier6.py` | **I/O Blocking** | Writes `costs.json` to disk during a "unit" verification. | Use `tempfile` or mock the file system. |
| **CRITICAL** | `tests/stress/test_concurrency.py` | **The Mocking Illusion** | "Thundering Herd" test hits a Python Mock that just sleeps. Tests nothing about DB locks. | Run against a real Dockerized SurrealDB instance (Integration). |
| **HIGH** | `tests/unit/test_memory_lifecycle.py` | **Over-Mocking** | Mocks Repo, LLM, AND Service Logic. Verifies "Mocks called Mocks". | Use real `ConsolidationService` (Domain) with mocked Repo (Infra). |
| **HIGH** | `tests/unit/test_job_processor.py` | **Implementation Leakage** | Defines `AsyncContextManager` inside test to match internal implementation details. | Refactor code to use Dependency Injection for connection provider. |
| **MED** | `tests/unit/test_quick_wins.py` | **Mystery Guest** | Filename "Quick Wins" hides intent. Tests use magic numbers (`0.9`). | Rename to `test_scoring_heuristics.py`. Use named constants. |

---

## SECTION 2: THE NECROMANCY OF VERIFICATION

### Rite 1: Resurrecting `verify_tier6.py`

**The Rot:**
A script masquerading as a test. It writes to the real filesystem, relies on console prints for success, and swallows errors.

**The Resurrection (`tests/unit/test_tier6_features.py`):**
*   **Isolation:** Mocks `CostTracker` persistence or uses `tmp_path` fixture.
*   **Determinism:** No global state mutation.
*   **AAA:** Proper Arrange-Act-Assert.

```python
import pytest
from unittest.mock import Mock, patch, mock_open
from datetime import datetime
from khala.domain.memory.entities import Memory
from khala.domain.memory.value_objects import MemoryTier, ImportanceScore, MemorySource, Sentiment
from khala.infrastructure.gemini.cost_tracker import CostTracker
from khala.infrastructure.gemini.models import GeminiModel, ModelTier

def test_traceability_attachment():
    # 1. Arrange
    source = MemorySource(
        source_type="user_input",
        source_id="msg_123",
        confidence=0.95
    )

    # 2. Act
    memory = Memory(
        user_id="user_1",
        content="Test",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.5),
        source=source
    )

    # 3. Assert
    assert memory.source is not None
    assert memory.source.source_type == "user_input"
    assert memory.source.confidence == 0.95

def test_sentiment_attachment():
    # 1. Arrange
    sentiment = Sentiment(score=0.8, label="joy")

    # 2. Act
    memory = Memory(
        user_id="u1",
        content="Happy",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.5),
        sentiment=sentiment
    )

    # 3. Assert
    assert memory.sentiment.label == "joy"

def test_cost_tracker_persistence(tmp_path):
    # 1. Arrange
    # Use pytest's tmp_path to avoid global pollution
    fake_path = tmp_path / "costs.json"

    with patch("khala.infrastructure.gemini.cost_tracker.CostTracker.persistence_path", new=str(fake_path)):
        tracker = CostTracker()
        model = GeminiModel(
            model_id="test-model",
            name="Test",
            tier=ModelTier.FAST,
            cost_per_million_tokens=1.0,
            max_tokens=100
        )

        # 2. Act
        tracker.record_call(model, 100, 50, 100.0)

        # 3. Assert
        assert fake_path.exists()
        content = fake_path.read_text()
        assert "test-model" in content
```

### Rite 2: The Coverage Mandate

**Missing Critical Paths:**
1.  **Consolidation Logic**: `ConsolidationService.group_memories_for_consolidation` has zero logic tests (only mocked interactions).
    *   *Mandate*: Create `tests/unit/domain/test_consolidation_logic.py` to verify grouping by category.
2.  **SOP Persistence**: `SOPRegistry` uses in-memory dict.
    *   *Mandate*: Create Integration Test verifying SOPs survive a "restart" (if using DB) or fail if not.

**Final Instruction:**
Delete `tests/unit/verify_tier6.py` immediately. It is a liability.
