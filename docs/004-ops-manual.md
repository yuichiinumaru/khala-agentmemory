# 004-OPS-MANUAL.md: Operations & Maintenance Guide

**Project**: KHALA v2.0
**Reference**: [001-project-plan-and-tasks.md](001-project-plan-and-tasks.md)

---

## 1. Deployment Guide

### Environment Prerequisites
*   **Docker & Docker Compose**: For container orchestration.
*   **SurrealDB**: Version 2.0+ (Nightly/Beta features may be required).
*   **Python**: 3.11+
*   **Redis**: 7.0+

### Local Development Setup
```bash
# 1. Clone
git clone https://github.com/your-repo/khala.git
cd khala

# 2. Setup Env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Start Infrastructure
docker-compose up -d surrealdb redis

# 4. Initialize Schema
surreal sql --endpoint http://localhost:8000 --user root --pass root --ns khala --db memory_store < infrastructure/surrealdb/schema.surql

# 5. Run
python main.py
```

### Production Deployment
*   **Infrastructure**:
    *   **Database**: Run SurrealDB in clustered mode (TiKV backend) for HA.
    *   **Application**: Stateless containers behind a Load Balancer (Nginx/Traefik).
    *   **Cache**: Managed Redis (e.g., AWS ElastiCache).
*   **Docker Compose (Prod)**:
    ```yaml
    services:
      khala-api:
        build: .
        restart: always
        env_file: .env
        ports: ["8000:8000"]
        depends_on: [surrealdb, redis]
      surrealdb:
        image: surrealdb/surrealdb:latest
        command: start --user root --pass root --bind 0.0.0.0:8000 file://data
        volumes: ["./data:/data"]
        ports: ["8080:8000"]
    ```

### Configuration (`.env`)
```ini
SURREALDB_URL=wss://production-db.khala.ai/rpc
SURREALDB_USER=admin_user
SURREALDB_PASS=secure_password_here
GEMINI_API_KEY=xxx
OPENAI_API_KEY=yyy
LOG_LEVEL=INFO
ENVIRONMENT=production
```

---

## 2. Security Architecture

### Zero Trust Principles
*   **Verify Explicitly**: Every API call must be authenticated.
*   **Least Privilege**: Agents only access their own namespace.
*   **Assume Breach**: Data is encrypted; logs are immutable.

### Authentication & Authorization
*   **API Access**: Bearer Token (JWT) for REST/MCP.
*   **Database Access (RBAC)**: SurrealDB handles security at the record level.
    ```surrealql
    DEFINE TABLE memory SCHEMAFULL
        PERMISSIONS FOR select, create, update, delete WHERE user_id = $auth.id;
    ```

### Data Protection
*   **At Rest**: SurrealDB runs on encrypted volumes (LUKS/EBS Encrypted).
*   **In Transit**: TLS 1.3 enforced for all connections (WSS/HTTPS).
*   **Compliance**: GDPR support via cascading DELETE; Audit logs retention 1 year.

---

## 3. Testing Strategy

### Pyramid Structure
1.  **Unit Tests (70%)**: Test individual functions and classes (`tests/unit`).
2.  **Integration Tests (20%)**: Test DB interactions and API endpoints (`tests/integration`).
3.  **E2E/System Tests (10%)**: Test full agent workflows (`tests/e2e`).

### Key Test Scenarios
*   **Vector Search**: Verify `retrieve_memory` returns semantically relevant results.
*   **Consolidation**: Verify that 2 similar memories merge into 1.
*   **Decay**: Verify `importance` drops over time according to formula.
*   **Quality**: Feed bad data to Verification Gate and ensure rejection.

### Execution
```bash
pytest                  # Run all
pytest tests/unit       # Run unit
pytest --cov=khala      # Run with coverage
```

---

## 4. Monitoring & Observability

### Stack
*   **Metrics**: Prometheus (Pull model).
*   **Visualization**: Grafana.
*   **Logs**: Structured JSON logs (stdout) -> ELK/Loki.

### Key Metrics
*   **Application**: `khala_memory_count`, `khala_search_latency_ms`, `khala_llm_cost_usd`, `khala_cache_hit_ratio`.
*   **Infrastructure**: `surrealdb_memory_usage`, `surrealdb_disk_io`.

### Alerting Thresholds
*   **Critical**: Search Latency > 500ms, Error Rate > 1%, LLM Cost > Budget.
*   **Warning**: Cache Hit Rate < 50%, Consolidation Queue > 1000.

---

## 5. Troubleshooting Guide

### Common Issues
*   **"Connection Refused"**: Check Docker container status and ports.
*   **"WebSocket Handshake Error"**: Protocol mismatch. Use `ws://` or `wss://` and ensure path is `/rpc`.
*   **"Search Results Irrelevant"**: Mismatched embedding dimensions (768d) or model.
*   **"Memory Not Persisting"**: Check Verification Gate logs or RBAC permissions.

### Debugging
*   **SurrealQL Shell**: `surreal sql --endpoint http://localhost:8000 --ns khala --db memory_store`
*   **Log Level**: Set `LOG_LEVEL=DEBUG` to see raw SQL and LLM prompts.

### FAQ
*   **Wipe Data**: `DELETE FROM memory; DELETE FROM entity; DELETE FROM relationship;`
*   **Slow Consolidation**: Increase `batch_size` or scale workers.
