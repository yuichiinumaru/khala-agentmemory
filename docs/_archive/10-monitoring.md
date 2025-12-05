# 10-MONITORING.md: Monitoring & Observability

**Project**: KHALA v2.0
**Reference**: [07-deployment.md](07-deployment.md)

---

## 1. Stack

*   **Metrics**: Prometheus (Pull model).
*   **Visualization**: Grafana.
*   **Logs**: Structured JSON logs (stdout) -> ELK/Loki.

---

## 2. Key Metrics

### Application
*   `khala_memory_count`: Total memories stored.
*   `khala_search_latency_ms`: Histogram of search duration.
*   `khala_llm_cost_usd`: Counter of estimated cost.
*   `khala_cache_hit_ratio`: L1/L2 hit rate.

### Infrastructure
*   `surrealdb_memory_usage`: RAM usage.
*   `surrealdb_disk_io`: IOPS.

---

## 3. Alerts

*   **Critical**:
    *   Search Latency p95 > 500ms (5m avg).
    *   Error Rate > 1%.
    *   LLM Cost > Budget/Day.
*   **Warning**:
    *   Cache Hit Rate < 50%.
    *   Consolidation Queue > 1000 items.

---

## 4. Dashboards

### "KHALA Overview"
*   **Top Row**: Total Memories, Active Agents, Daily Cost.
*   **Middle Row**: Search Latency Graph, Ingestion Rate.
*   **Bottom Row**: Recent Audit Logs, Error Count.

### "Intelligence Health"
*   **Verification Pass Rate**.
*   **Debate Consensus Rate**.
*   **Average Memory Decay**.
