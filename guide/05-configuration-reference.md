# The Knobs: Configuration Reference

Control Khala via Environment Variables in your `.env` file.

## 🤖 Model Selection

Khala uses a `MODEL_ID` string map.

| Variable | Default | Description |
| :--- | :--- | :--- |
| `GEMINI_REASONING_MODEL` | `gemini-2.5-pro` | Used for complex logic, dreams, and debates. |
| `GEMINI_FAST_MODEL` | `gemini-2.5-flash` | Used for classification and extraction. |
| `GEMINI_EMBEDDING_MODEL` | `models/gemini-embedding-001` | The vectorizer. **DO NOT CHANGE ONCE DATA EXISTS.** |

## 🧠 Database (SurrealDB)

| Variable | Description |
| :--- | :--- |
| `KHALA_SURREAL_URL` | WebSocket URL (e.g. `ws://localhost:8000/rpc`) |
| `KHALA_SURREAL_USER` | Database username |
| `KHALA_SURREAL_PASS` | Database password |
| `KHALA_SURREAL_NS` | Namespace (default: `khala`) |
| `KHALA_SURREAL_DB` | Database name (default: `dev`) |

## ⚙️ Operational Tuning

| Variable | Default | Description |
| :--- | :--- | :--- |
| `KHALA_MEMORY_DECAY_RATE` | `0.1` | How fast memories fade (0.0 to 1.0). |
| `KHALA_AUTO_CONSOLIDATE` | `true` | Enable background dreaming. |
| `KHALA_LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARN`). |
