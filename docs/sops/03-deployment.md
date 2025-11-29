# SOP 03: Deployment Procedures

## 1. Overview
Standard procedures for deploying KHALA updates.

## 2. Pre-Deployment Checks
1.  **Tests:** All unit and integration tests must pass.
2.  **Audit:** Ensure all schema changes are reviewed.
3.  **Backup:** Verify a recent backup exists.

## 3. Deployment Steps (Docker)

1.  **Build Image:**
    ```bash
    docker build -t khala:latest .
    ```

2.  **Push to Registry:**
    ```bash
    docker push myregistry/khala:latest
    ```

3.  **Update Service:**
    - Update Kubernetes manifest or Docker Compose file.
    - Apply changes.

4.  **Database Migrations:**
    - Run schema update script `khala/infrastructure/surrealdb/schema.py` (via admin tool).

## 4. Rollback
If deployment fails:
1.  Revert image tag to previous version.
2.  Apply changes.
3.  If database schema changed incompatibly, restore from backup (SOP 01).
