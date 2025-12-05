# 07-DEPLOYMENT.md: Deployment Guide

**Project**: KHALA v2.0
**Reference**: [02-tasks-implementation.md](02-tasks-implementation.md)

---

## 1. Environment Prerequisite

*   **Docker & Docker Compose**: For container orchestration.
*   **SurrealDB**: Version 2.0+ (Nightly/Beta features may be required).
*   **Python**: 3.11+
*   **Redis**: 7.0+

---

## 2. Local Development

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

---

## 3. Production Deployment

### Infrastructure
*   **Database**: Run SurrealDB in a clustered mode (TiKV backend) for HA.
*   **Application**: Stateless containers behind a Load Balancer (Nginx/Traefik).
*   **Cache**: Managed Redis (e.g., AWS ElastiCache).

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

### Docker Compose (Production)
```yaml
services:
  khala-api:
    build: .
    restart: always
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      - surrealdb
      - redis

  surrealdb:
    image: surrealdb/surrealdb:latest
    command: start --user root --pass root --bind 0.0.0.0:8000 file://data
    volumes:
      - ./data:/data
    ports:
      - "8080:8000"
```

---

## 4. Verification

After deployment, run the **Health Check**:
`GET /health` -> Returns `200 OK` with DB and Redis latency.

---

## 5. Backup & Recovery

*   **Backup**: Run `surreal export` nightly. Store in S3.
*   **Recovery**: `surreal import --conn ... backup.sql`.
