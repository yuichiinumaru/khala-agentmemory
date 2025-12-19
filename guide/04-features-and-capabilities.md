# The Menu: Features & Capabilities

Khala implements over 170 cognitive strategies. Here is what is on the menu.

## 🌟 Capability Matrix

| Feature Set | Status | Ready for Prod? |
| :--- | :--- | :--- |
| **Core Storage (Vector/Graph)** | ✅ Mature | Yes |
| **Hybrid Search** | ✅ Mature | Yes |
| **Entity Extraction (NER)** | 🚧 Beta | Yes (with caveats) |
| **Dreaming (Consolidation)** | 🧪 Experimental | No (Research Only) |
| **Hypothesis Generation** | 🧪 Experimental | No |
| **Multi-Agent Debate** | ✅ Mature | Yes |

## 1. Advanced Search
Khala doesn't just "grep". It searches like a human.
- **Vector Search**: Finds conceptually similar ideas ("Dog" matches "Puppy").
- **Graph Traversal**: Finds connected concepts ("User" -> "owns" -> "Dog").
- **Hybrid**: Combines both for maximum recall.
- **Temporal**: "What did the user say *last week*?"

## 2. Intent Classification
The system understands *why* you are searching.
- **Fact Query**: "What is my API key?" -> Precise Lookup.
- **Concept Query**: "How do I build a house?" -> Broad Semantic Search.
- **Creative Query**: "Write a poem." -> Zero Retrieval.

## 3. Self-Correction
Khala monitors its own health.
- **Index Healing**: Automatically rebuilds broken HNSW graphs.
- **Deduplication**: Merges identical memories to save space.

## 4. Multi-Modal Support
- **Text**: Native support.
- **Image**: Can store and retrieve images (converted to embeddings).
- **Code**: Special AST-based storage for code snippets.
