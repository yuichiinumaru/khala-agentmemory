# SOP 01: Backup and Restore Procedures

## 1. Overview
This SOP details the procedures for backing up and restoring the KHALA SurrealDB database.

**Security Warning:** Do not use hardcoded credentials in production commands. Use environment variables or a secrets manager.

## 2. Backup Procedure

### 2.1 Scheduled Backups
SurrealDB exports should be scheduled daily.

**Command (Example):**
```bash
# Ensure SURREAL_USER and SURREAL_PASS are set in environment
surreal export --conn http://localhost:8000 --user $SURREAL_USER --pass $SURREAL_PASS --ns khala --db memories backup_$(date +%Y%m%d).surql
```

### 2.2 Storage
Backups should be encrypted and stored in an S3-compatible bucket with versioning enabled.

## 3. Restore Procedure

### 3.1 Full Restore
To restore from a backup file:

1.  **Stop the application** to prevent writes.
2.  **Import the data:**
    ```bash
    surreal import --conn http://localhost:8000 --user $SURREAL_USER --pass $SURREAL_PASS --ns khala --db memories backup_file.surql
    ```
3.  **Verify integrity:** Check count of memories and entities.
4.  **Restart application.**

## 4. Disaster Recovery
In case of catastrophic failure (data corruption):
1.  Identify the last known good backup.
2.  Provision a new SurrealDB instance.
3.  Perform Full Restore (3.1).
4.  Update DNS/Connection strings to point to new instance.
