# 📋 Master Task List

## Phase 1: Foundation & Architecture (MVP)
*Status: Mostly Complete*

- [x] **Project Scaffold**: Vite + React + TypeScript + Tailwind.
- [x] **Core Graph Engine**: Integration of `sigma.js` and `graphology`.
- [x] **The "One Hook"**: Created `useGraphViz.ts` to encapsulate logic.
- [x] **Basic Layouts**: ForceAtlas2, Circle, Grid, Random implementation.
- [x] **Search**: Fuzzy search with camera fly-to animation.
- [x] **Glassmorphism UI**: Basic HUD and GlassCard components.
- [x] **AI Oracle V1**: Basic Gemini text integration.
- [ ] **Code Organization**: Refactor `src` into logical "packages" (Core, Rendering, UI) to mimic monorepo structure.

## Phase 2: Intelligence (The Oracle)
*Status: Complete*

- [x] **Context Awareness**: Update `geminiService` to send *only visible nodes* (in viewport) to save tokens and improve relevance.
- [x] **AI Actions (Tool use)**:
    - [x] Define JSON schema for graph control (`SELECT_NODE`, `CHANGE_LAYOUT`, `FILTER_CLUSTER`).
    - [x] Implement command parser in `GraphOracle`.
    - [x] Execute commands via `useGraphViz` API.
- [x] **Graph Summary V2**: Improve the text summary algorithm to include "Anomalies" (isolated nodes) and "Bridges" (high betweenness).

## Phase 3: Advanced Interaction & LoD
*Status: Pending*

- [ ] **Graph Simplification (The "Hairball" Fix)**:
    - [ ] Implement `louvain` clustering algorithm (via graphology library).
    - [ ] Create a "Zoom Level" listener.
    - [ ] When Zoom < X, render "Cluster Nodes" instead of individual nodes.
- [ ] **Timeline / Time Travel**:
    - [ ] Create a state history stack (Undo/Redo).
    - [ ] Add a visual slider to "replay" graph generation or layout evolution.
- [ ] **Context Menu**: Right-click on node to specific actions (Focus, Hide, Analyze with AI).
- [ ] **Multi-select**: Implement "Shift+Drag" to select multiple nodes.

## Phase 4: Aesthetics & Performance
*Status: Started*

- [x] **FPS Meter**: Add real `stats.js` or custom FPS counter to HUD.
- [ ] **Web Worker Layout**: Move ForceAtlas2 calculation to a dedicated worker thread to prevent UI freeze on 10k+ nodes.
- [ ] **Custom Node Rendering**:
    - [ ] Create a custom WebGL shader for "Glowing Nodes".
    - [ ] Create a custom shader for "Pulse" animation on selected nodes.
- [ ] **Sound FX**: Add `useSound` for hover/click interactions (Sci-Fi interface sounds).

## Phase 5: Data & Export
*Status: Started*

- [x] **Mock Database**: Simulate Async DB connection.
- [ ] **Data Ingestion**: Add "Drag & Drop" JSON file support.
- [ ] **Export**:
    - [ ] Export to PNG (Canvas snapshot).
    - [ ] Export current graph state to JSON.
- [ ] **Neo4j Mock**: Create a defined Interface for Neo4j that we can swap later, even if using mock data now.