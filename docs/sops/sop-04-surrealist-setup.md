# SOP-04: Surrealist Setup Guide

**Objective**: Connect Surrealist UI to Khala Database.

## 1. Prerequisites
- SurrealDB running (Docker or Local).
- Surrealist App (Web or Desktop).

## 2. Connection Settings
- **Endpoint**: `http://localhost:8000/rpc`
- **Namespace**: `khala`
- **Database**: `khala_dev`
- **User**: `root`
- **Pass**: `root`

## 3. Visualization
1. Go to **Explorer View**.
2. Select table `memory`.
3. Click a record to see JSON.
4. Click `Graph` tab (if available) to see links.

## 4. Useful Queries
Import `scripts/surrealist_queries.surql`.
