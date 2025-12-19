# The Medic: Troubleshooting

Common issues and how to fix them.

## 🩺 SurrealDB Connection Refused

**Symptom**: `ConnectionRefusedError` or "Cannot connect to SurrealDB".
**Fix**:
1. Check if SurrealDB is running: `docker ps` or `ps aux | grep surreal`.
2. Verify the URL in `.env`: `ws://localhost:8000/rpc` (Note the `/rpc`).
3. Ensure namespace exists: `surreal import --conn ...`

## 📉 Low Search Quality

**Symptom**: "I ask for X, but get Y."
**Fix**:
1. **Check Embedding Model**: Are you using the same model for ingestion and query?
2. **Re-Index**: Run `scripts/reindex.py` (if available) to fix HNSW graphs.
3. **Decay**: Old memories might have decayed too much. Check `KHALA_MEMORY_DECAY_RATE`.

## 🛑 Gemini Quota Exceeded

**Symptom**: `429 Too Many Requests`.
**Fix**:
1. Implement backoff (Khala has internal retries, but a hard limit exists).
2. Switch to `gemini-2.5-flash` for high-volume tasks (extraction).
3. Request a quota increase from Google.

## 🐛 "IAM Error" / Permissions

**Symptom**: `Permissions error` when writing to DB.
**Fix**:
1. Check `KHALA_SURREAL_USER`. Ideally use `root` for dev.
2. If using scoped users, ensure they have `RW` access to the `khala` namespace.
