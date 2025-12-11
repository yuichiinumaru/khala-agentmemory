# 02-TASKS-SEMANTIC-ROUTER.md: Execution Queue

## 1. Setup & Infrastructure
- [ ] Add `semantic-router` to `requirements.txt`.
- [ ] Create `khala/infrastructure/semantic_router/` directory.
- [ ] Implement `KhalaRouter` wrapper class.
- [ ] Configure `KhalaRouter` with Gemini encoder (via adapter).

## 2. Route Definition
- [ ] Create `khala/infrastructure/semantic_router/routes.py`.
- [ ] Define utterances for `QueryIntent.FACTUAL` (e.g., "What is...", "Define...", "Who is...").
- [ ] Define utterances for `QueryIntent.SUMMARY` (e.g., "Summarize...", "TL;DR", "Overview of...").
- [ ] Define utterances for `QueryIntent.ANALYSIS` (e.g., "Analyze...", "Why did...", "Compare...").
- [ ] Define utterances for `QueryIntent.CREATIVE` (e.g., "Write a story...", "Brainstorm...", "Imagine...").
- [ ] Define utterances for `QueryIntent.INSTRUCTION` (e.g., "Run...", "Execute...", "Do X...").

## 3. Application Integration
- [ ] Create `khala/application/services/fast_intent_classifier.py`.
- [ ] Implement `classify_intent` method with fallback:
    - Try `KhalaRouter` (threshold ~0.8).
    - If None, call `GeminiClient` (Legacy).
- [ ] Update `HybridSearchService` to use `FastIntentClassifier`.

## 4. Verification
- [ ] Write `tests/infrastructure/test_semantic_router.py`.
- [ ] Verify latency improvement (benchmark script).
