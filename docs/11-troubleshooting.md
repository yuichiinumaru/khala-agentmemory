# 11-TROUBLESHOOTING.md: Troubleshooting Guide

**Project**: KHALA v2.0
**Reference**: [10-monitoring.md](10-monitoring.md)

---

## 1. Common Issues

### "Connection Refused" to SurrealDB
*   **Cause**: DB container not running or port blocked.
*   **Fix**: Check `docker ps`, ensure port 8000 is exposed. Check `SURREALDB_URL`.

### "WebSocket Handshake Error"
*   **Cause**: Protocol mismatch (http vs ws) or path error.
*   **Fix**: Ensure URL ends in `/rpc` and uses `ws://` or `wss://`.

### "Search Results are Irrelevant"
*   **Cause**: Poor embeddings or mismatched dimensions.
*   **Fix**: Verify embedding model matches index (768d). Check `threshold` param.

### "Memory Not Persisting"
*   **Cause**: Transaction rollback or Verify Gate rejection.
*   **Fix**: Check logs for "Verification Failed". Check DB permissions.

---

## 2. Debugging Tools

*   **SurrealQL Shell**:
    `surreal sql --endpoint http://localhost:8000 --ns khala --db memory_store`
*   **Log Level**:
    Set `LOG_LEVEL=DEBUG` in `.env` to see raw SQL and LLM prompts.

---

## 3. FAQ

**Q: Can I use OpenAI instead of Gemini?**
A: Yes, change the provider in `infrastructure/llm/client.py`.

**Q: How do I wipe all data?**
A: `DELETE FROM memory; DELETE FROM entity; DELETE FROM relationship;`

**Q: Why is consolidation slow?**
A: It's LLM-intensive. Increase `batch_size` or run parallel workers.
