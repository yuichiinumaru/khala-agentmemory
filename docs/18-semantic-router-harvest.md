# 18-SEMANTIC-ROUTER-HARVEST.md: Routing & Intent Intelligence

**Source**: `semantic-router` (Aurelio Labs)
**Status**: Harvested & Planned

---

## 🧠 Executive Summary
`semantic-router` provides a "decision layer" for LLMs using semantic vector search. Instead of asking an LLM "What should I do with this query?" (slow, expensive), we embed the query and check if it lands near a known "intent cluster" (fast, cheap).

**Key Insight**: **Routing is Classification, not Generation.**
Most agent control flow decisions (Intent, Tool Selection, Safety) are classification problems. Solving them with Generation (LLM) is inefficient.

---

## 1. The Route Layer
**Concept**: A collection of `Route` objects, each with a list of `utterances` (examples).
**Mechanism**:
1.  Embed user query $q$ -> $\vec{v}_q$.
2.  Search vector index for nearest utterance $\vec{u}$.
3.  If $similarity(\vec{v}_q, \vec{u}) > threshold$, trigger Route.
4.  Else, return None (or default).

### Khala Integration
- **Replace**: `IntentClassifier` (currently Gemini-based).
- **Benefit**: Latency drop from ~1.5s to ~0.1s.
- **Reliability**: Deterministic (Same input -> Same output).

---

## 2. Dynamic Routes (Function Calling)
**Concept**: Routes can have `function_schemas`. If a route is triggered, an LLM is used *only* to extract arguments for that specific function.
**Key Insight**: Use Vector Search to *select* the tool, use LLM to *parameterize* it. This reduces the context window needed for tool selection (don't need to dump all tool schemas into the prompt).

### Khala Integration
- **Target**: `SkillLibraryService`.
- **Strategy**: Index Skills as Routes.
    -   Utterances: "Run the python script", "Calculate this", "Search the web".
    -   Schema: The Skill's parameters.

---

## 3. Hybrid Routing (Sparse + Dense)
**Concept**: Combine Vector Search (Semantic) with BM25/Keyword Search (Lexical).
**Why**: "Product ID 1234" might not be semantically close to "Product ID 1234" in some embedding models, but it's a lexical match.

### Khala Integration
- **Enhancement**: `HybridSearchService` already does this for memories. We should apply it to Intents too (e.g., specific command keywords).

---

## 4. Implementation Gaps & Adapters
The `semantic-router` library uses `vertexai` (Google Cloud) for its `GoogleEncoder`. Khala uses `google-generativeai` (AI Studio).
**Action**: We must implement a `GeminiEncoder` adapter that wraps our existing `GeminiClient` to be compatible with `semantic-router`'s `DenseEncoder` interface.

```python
class KhalaGeminiEncoder(DenseEncoder):
    def __call__(self, docs: List[str]) -> List[List[float]]:
        # Use existing GeminiClient to get embeddings
        return client.embed(docs)
```

---

## 5. Decision Matrix

| Feature | Semantic Router | LLM Router (Current) | Decision |
| :--- | :--- | :--- | :--- |
| **Latency** | < 100ms | > 1000ms | **Switch** |
| **Cost** | Embedding Only | Input + Output Tokens | **Switch** |
| **Flexibility** | High (Add Utterances) | High (Prompting) | **Keep Both** (Hybrid Fallback) |
| **Tooling** | Explicit definition | Implicit via Prompt | **Switch for Core Tools** |
