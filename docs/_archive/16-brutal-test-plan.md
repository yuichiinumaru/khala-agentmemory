# Brutal Test Suite Plan

**Objective**: To rigorously stress-test the KHALA memory system, verifying resilience, correctness, and advanced agentic capabilities.

## 1. Core & Non-Vital Tests (`tests/brutal/test_basics.py`)
*Focus: Correctness of basic operations and edge cases.*

-   **CRUD Integrity**: Create, Read, Update, Delete cycles with complex data types (nested metadata, large text).
-   **Vector Fidelity**: Ensure embedding vectors saved are retrieved with exact precision (no float truncation issues).
-   **Filter Logic**: Test every filter operator (`eq`, `neq`, `gt`, `lt`, `contains`, `in`) with combinations.
-   **Edge Cases**:
    -   Zero-dimension vectors (if allowed) or error handling.
    -   Massive metadata objects (1MB+).
    -   Unicode/Emoji content.
    -   SQL Injection attempts in text fields (sanity check).

## 2. Logic & Lifecycle Tests (`tests/brutal/test_logic.py`)
*Focus: Business logic validation.*

-   **Tier Promotion**:
    -   Simulate time passage (mock datetime).
    -   Verify memory does *not* promote before criteria.
    -   Verify memory *does* promote exactly when criteria are met.
-   **Decay Scoring**:
    -   Calculate expected decay curves manually and compare with system output.
-   **Deduplication**:
    -   Insert duplicates concurrently. Ensure only one exists or hash check catches it.

## 3. Hardcore Stress Tests
*Focus: System resilience and performance.*

-   **Concurrency (`tests/brutal/test_concurrency.py`)**:
    -   **The "Thundering Herd"**: Spawn 500 concurrent async tasks attempting to write to the DB.
    -   **Read/Write Race**: Concurrent updates to the same memory ID to test versioning/locking (if applicable) or last-write-wins behavior.
    -   **Connection Pooling**: Exhaust the pool and verify recovery.
-   **Graph Complexity (`tests/brutal/test_graph_complexity.py`)**:
    -   **The "Spiderweb"**: Generate a graph with 1,000 nodes and 5,000 edges.
    -   **Traversal Stress**: Run recursive queries (Module 11 function) with depth 5+.
    -   **Cycle Detection**: Create circular dependencies and ensure traversal doesn't hang (infinite loop check).

## 4. The Agent Learning Loop (`tests/brutal/test_agent_learning.py`)
*Focus: End-to-End Agent Integration and Cognitive Behavior.*

**Scenario**: Two Agno Agents in a closed loop.

### Characters
1.  **The Asker (Teacher)**:
    -   Has access to a "Ground Truth" dictionary (Simulated Web Search).
    -   Personality: Strict, Pedantic.
    -   Role: Ask questions, evaluate answers, provide corrections.
2.  **The Answerer (Student)**:
    -   Memory: Khala (Initially empty regarding the topic).
    -   Personality: Eager, Apologetic.
    -   Role: Answer questions, save corrections to memory.

### Phase 1: The Failure & Learning Cycle
1.  **Ask**: Teacher asks a hard question (e.g., "What is the airspeed velocity of an unladen swallow?").
2.  **Attempt**: Student tries to answer. (Likely hallucinates or fails).
3.  **Judge**: Teacher checks against Ground Truth.
4.  **Correct**: Teacher says: "Wrong. [Correction Details]. Save this."
5.  **Store**: Student creates a Memory in Khala with the correction.

### Phase 2: The Reinforcement Cycle
1.  **Re-Ask**: Teacher asks the *exact same question*.
2.  **Recall**: Student searches Khala. Retrieves the specific memory.
3.  **Answer**: Student answers correctly citing the memory.
4.  **Verify**: Teacher checks.
    -   **If Correct**: "Good job."
    -   **If Wrong**: "Why didn't you consult memory? [FAIL]"

## 5. Master Runner (`scripts/run_brutal_suite.py`)
-   Orchestrates all tests.
-   Provides a "Brutality Report" (Pass/Fail/Performance Metrics).
