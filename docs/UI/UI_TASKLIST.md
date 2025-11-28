# UI_TASKLIST.md
# KHALA User Interface & Dashboard Tasks

**Project**: KHALA (Knowledge Hierarchical Adaptive Long-term Agent)
**Version**: 2.0
**Status**: Active

---

## 1. Supernova Dashboard Integration

### 1.1. Core Integration
- [ ] **Configure Supernova Submodule**
    - Ensure `external/supernova-dashboard` is correctly initialized.
    - Validate build process for the UI.
    - **Deliverable**: `npm install` and `npm run build` work in the submodule.
    - **Test**: accessing the build output.

- [ ] **Connect UI to SurrealDB**
    - Configure Supernova to connect to the KHALA SurrealDB instance.
    - Set up read-only permissions for the dashboard user.
    - **Deliverable**: Dashboard shows real-time data from `memory` table.
    - **Test**: Verify data visualization matches DB content.

### 1.2. Graph Visualization (Strategy #56)
- [ ] **Implement Graph Data Endpoint**
    - Create an API endpoint or WebSocket channel to stream graph data (nodes/edges).
    - Format data for D3.js or similar visualization library used by Supernova.
    - **Deliverable**: Streaming graph data.
    - **Test**: Verify nodes and edges appear in the UI.

- [ ] **Interactive Filtering**
    - Add UI controls to filter graph by Memory Tier, Entity Type, and Importance.
    - **Deliverable**: Functional filter controls.
    - **Test**: Selecting "Long Term" shows only long-term memories.

### 1.3. Cost & Performance Dashboard (Strategy #57)
- [ ] **LLM Cost Visualization**
    - Visualize cost data from `audit_log` or `cost_tracking` table.
    - Show cost per model (Fast/Medium/Smart) over time.
    - **Deliverable**: Cost charts in Supernova.
    - **Test**: Verify charts match `CostTracker` logs.

- [ ] **System Health Indicators**
    - Display metrics: Memory Count, Cache Hit Rate, Search Latency.
    - **Deliverable**: Real-time health badges/gauges.
    - **Test**: Simulate load and watch metrics update.

---

## 2. Admin Interface Tasks

### 2.1. Memory Management UI
- [ ] **Manual Memory Inspection**
    - View raw memory details (content, embedding vector, metadata).
    - **Deliverable**: Inspector view.

- [ ] **Manual Override Tools**
    - UI to manually promote/demote memories.
    - UI to trigger immediate consolidation.
    - **Deliverable**: Admin control panel.

### 2.2. Audit Log Viewer
- [ ] **Audit Trail Interface**
    - Searchable table of audit logs.
    - Filter by Agent ID, Action Type, Date.
    - **Deliverable**: Audit log page.

---

## 3. Deployment & Hosting

- [ ] **Dashboard Deployment**
    - Create Dockerfile for the UI.
    - specific Nginx configuration to serve UI and proxy API requests.
    - **Deliverable**: `docker-compose` service for UI.
    - **Test**: `docker-compose up` launches accessible UI at localhost:3000.
