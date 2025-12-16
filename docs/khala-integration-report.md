# Khala-Supernova Integration Report: The Command Center

**Date**: December 2025
**Status**: Vision & Architecture Analysis
**Target**: Khala v2.1 + Supernova Dashboard

---

## 1. Executive Summary

The Khala project has reached a high level of backend sophistication with its Agent Memory System, employing advanced strategies like SOAR refinement, Product of Experts verification, and distributed consolidation. However, its "Face" remains hidden behind CLI tools and database queries.

**Supernova**, a React-based graph visualization tool, presents a prime opportunity to become the dedicated **"Command Center"** for Khala. Unlike generic database GUIs (Surrealist), Supernova can be tailored to the *semantics* of an Agentic System—visualizing thoughts, plans, and memory evolution in real-time.

This report analyzes the integration potential, proposes a unified architecture, and outlines a feature-rich roadmap to transform Supernova into a mission-critical tool for Agent Operators.

---

## 2. Comparative Analysis: Surrealist vs. Supernova

To justify the investment in Supernova, we must distinguish it from the existing Surrealist UI.

| Feature | Surrealist (Existing) | Supernova (Proposed Integration) |
| :--- | :--- | :--- |
| **Primary Goal** | General Database Administration | Agent System Observability |
| **Data View** | Tables, JSON, Generic Graph | Semantic Graph (Entities, Concepts, Episodes) |
| **User Persona** | Database Admin (DBA) | AI Engineer / Agent Operator |
| **Interactivity** | CRUD, SQL Queries | Context Navigation, Trace Replay, Manual Intervention |
| **Real-Time** | Live Queries (Raw Data) | Live "Thought Stream" & "Attention Map" |
| **Customization** | Limited (Presets) | Infinite (Custom React Components) |
| **Intelligence** | None (Passive) | Active (Can integrate "Analyst Agent" to explain graph) |

**Verdict**: Surrealist is indispensable for *schema management* and *low-level debugging*. Supernova is essential for *high-level reasoning analysis* and *operational monitoring*. They are complementary, not competitive.

---

## 3. Integration Vision: The "Khala Command Center"

We envision Supernova not just as a viewer, but as an interactive console.

### 3.1. The "Agent-Centric" View
Instead of starting with tables (`memory`, `agents`), Supernova should center on the **Agent**.
- **Dashboard Widget**: "Active Agents".
- **Status Indicators**:
    - 🟢 **Thinking**: Agent is running a Cognitive Cycle.
    - 🟡 **Consolidating**: Agent is sleeping/merging memories.
    - 🔴 **Blocked**: Agent encountered a verification failure or error.
- **Stream**: A rolling log of "Inner Monologue" (Thoughts) derived from the `audit_log` or `jobs` table.

### 3.2. Specialized Graph Visualizers
Khala's memory graph is complex (Tier 1-6). A generic force-directed graph is too messy. Supernova needs **Semantic Layers**:
- **Layer 1: Episodic Timeline**: A linear or spiral view of `Memory` nodes connected by `NEXT` edges, representing the chronological flow of experience.
- **Layer 2: Concept Map**: A cluster view of `Entity` nodes (Concepts, People, Places) and their relations, hiding the episodic noise.
- **Layer 3: The "Brain Scan"**: A heatmap view showing "Activation Levels" (Recall Frequency / Importance) of memories. Hot zones indicate active working memory context.

### 3.3. The "Time-Travel" Debugger
Agents often make mistakes due to context pollution or hallucination. Supernova can enable "Time Travel":
- **Slider UI**: Scrub through the `created_at` timeline.
- **State Replay**: See the graph structure *as it existed* at T-10 minutes.
- **Diff View**: Highlight what changed in the graph after a specific "Consolidation Job" (Strategy 177). Did entropy drop? Did duplicates vanish?

---

## 4. Operational Monitoring & Intelligence

This section details specific metrics and visualizations to help admins "spot problems faster."

### 4.1. The "Entropy Monitor" (Consolidation Health)
*Based on Strategy 177.*
- **Metric**: Average Shannon Entropy of Working Memory vs. Long-Term Memory.
- **Visual**: A gauge chart. High entropy in Short-Term memory is good (new info). High entropy in Long-Term suggests poor consolidation (fragmentation).
- **Alert**: "Consolidation Lag detected. Entropy > Threshold for 2 hours."

### 4.2. Security & "Attention" Heatmaps
*Based on Strategy 175 & 176.*
- **Injection Radar**: A list of recent `VisualSanitizer` rejections. Click to view the malicious image and the sanitized overlay.
- **Attention Collapse Warning**: If the `AttentionMonitor` flags a response (e.g., repetitive loops), highlight the Agent in **Red** and show the specific tokens causing the loop.

### 4.3. The "Skeptic's Eye" (Verification Dashboard)
*Based on Strategy 173 & 1.1.*
- **Stats**: Pass/Fail rate of the `VerificationGate`.
- **Drill-Down**: Click a "Failed" memory to see the *reason* (e.g., "Fact Check Failed: 'Paris is in Texas' contradicts Knowledge Base").
- **Manual Override**: An "Approve/Reject" button for the admin to override the gate (Human-in-the-Loop).

### 4.4. Trace Replay (Cognitive Engine)
*Based on Task 2.2.*
- **DAG Visualizer**: Show the execution DAG of the current plan.
- **Step Inspection**: Click a node in the DAG to see:
    - Input Prompt (with `PromptString` structure).
    - Raw LLM Response.
    - Parsed Action.
    - Execution Result.

---

## 5. Technical Architecture

How do we connect the React frontend (Supernova) to the Python backend (Khala)?

### 5.1. The "Surreal-Bridge" Pattern
Supernova can connect directly to SurrealDB using `surrealdb.js` (WebSocket) for live updates.
- **Live Queries**: `LIVE SELECT * FROM audit_log` ensures the "Thought Stream" is sub-second latency.
- **Graph Fetch**: `SELECT * FROM memory FETCH links` to get the full structure.

### 5.2. The "Analyst Agent" API
For complex metrics (Entropy, Attention), Supernova shouldn't compute them raw. It should query Khala's API.
- **Endpoint**: `GET /api/v1/metrics/entropy`
- **Endpoint**: `GET /api/v1/agents/{id}/trace`
- **Implementation**: Khala's FastAPI exposes these endpoints, aggregating data from SurrealDB or internal memory state.

### 5.3. Authentication
- Use SurrealDB's `Scope` based auth.
- Admin users log in via Supernova, obtaining a JWT that allows read/write to the graph.

---

## 6. Implementation Roadmap (Phased)

### Phase S1: The "Observer" (Read-Only)
*Goal: Visualize what exists.*
1.  **Connection**: Add `SurrealDB` connection form to Supernova `App.tsx`.
2.  **Graph Loader**: Adapt `core/algorithms.ts` to fetch nodes/edges from Khala's `memory` table.
3.  **Visual Tweaks**: Color-code nodes by `MemoryTier` (Working=Red, Short=Yellow, Long=Blue).

### Phase S2: The "Monitor" (Live Metrics)
*Goal: See it move.*
1.  **Live Stream**: Implement `useSurrealLiveQuery` hook to listen to `audit_log`.
2.  **Dashboard Layout**: Create a grid layout with "Log Stream", "Graph View", and "Stats Panel".
3.  **Metrics Widgets**: Implement "Total Memories", "Tokens Used", "Cost Estimate".

### Phase S3: The "Intervenor" (Write/Action)
*Goal: Control the system.*
1.  **Manual Trigger**: Add buttons to trigger `MemoryLifecycleService.run_lifecycle_job()`.
2.  **Editor**: Click a node to edit its content (fix hallucinations manually).
3.  **Chat**: A chat interface to talk directly to the `KhalaPlanner` ("Agent, explain yourself").

---

## 7. User Experience (UX) Concepts

### 7.1. Aesthetic: "Neural Interface"
- **Theme**: Dark Mode default (matches `Agno`/`Surreal` vibes).
- **Graph Physics**: Fluid, "breathing" simulation. Nodes gently drift.
- **Typography**: Monospace for data (Code-like), Sans-serif for UI.

### 7.2. "Focus Mode"
- When debugging a specific problem (e.g., "Why did it fail to find the file?"):
    - Select the failed `Job` ID.
    - Graph filters to show *only* memories accessed during that job (Traceability).
    - Timeline zooms to the +/- 5 minute window of the job.

### 7.3. "Semantic Zoom"
- **Zoom Level 0 (Bird's Eye)**: Clusters of episodes. No text. Heatmap colors.
- **Zoom Level 1 (Concept)**: Key entities visible. Major links.
- **Zoom Level 2 (Detail)**: Full text snippets. All links.
- **Zoom Level 3 (Inspector)**: Full JSON content of a single node.

---

## 8. Specific "Supernova" Enhancements
*Ideas tailored to the existing `supernova-js` codebase.*

1.  **`NodeInspector` Upgrade**:
    - Currently likely generic.
    - **Khala Upgrade**: Add tabs for "Metadata", "Embeddings" (Visualizer), "Versions" (History).
    - Show `embedding_visual` as a small image thumbnail if the memory is multimodal.

2.  **`HudControls` Upgrade**:
    - Add "Filter by Tier" toggles.
    - Add "Filter by Agent" dropdown.
    - Add "Search" bar that uses `HybridSearchService` (via API) to highlight matching nodes in the graph.

3.  **`algorithms.ts` Upgrade**:
    - Implement specific layouts for "Hierarchical Memory" (Tree layout for containment, Force for associations).

---

## 9. Detailed Component Architecture

To support the vision, we need specific React components.

### 9.1. `AgentStatusWidget` (The Heartbeat)
This component resides in the HUD and provides immediate situational awareness.

**Props**:
- `agentId`: string
- `refreshRate`: number (ms)

**State**:
- `status`: 'idle' | 'busy' | 'error'
- `currentTask`: string
- `lastMemory`: MemoryNode

**Mockup Logic**:
```tsx
const AgentStatusWidget = ({ agentId }) => {
  // Uses Surreal Live Query to listen for changes in 'jobs' table
  const status = useSurrealLiveQuery(`LIVE SELECT * FROM jobs WHERE agent_id = '${agentId}' ORDER BY created_at DESC LIMIT 1`);

  return (
    <div className={`status-badge ${status.state}`}>
      <Avatar src={status.avatar} />
      <div className="status-details">
        <h3>{status.name}</h3>
        <p className="typing-effect">{status.current_thought}</p>
        <ProgressBar value={status.energy} color={status.energy < 20 ? 'red' : 'green'} />
      </div>
    </div>
  );
};
```

### 9.2. `MemoryGraphVisualizer` (The Brain)
Extends `react-force-graph-3d`.

**Features**:
- **Auto-Orbit**: Slowly rotate around the center to reveal depth.
- **LOD (Level of Detail)**: Hide labels when zoomed out. Show full text when zoomed in (Semantic Zoom).
- **Cluster Highlighting**: When hovering a node, highlight all neighbors (1-hop) and dim the rest.

### 9.3. `TraceReplayTimeline` (The Recorder)
A playback control bar at the bottom.

**Controls**:
- `Play/Pause`: Auto-advance time.
- `Speed`: 1x, 2x, 5x.
- `Event Markers`: Small dots on the timeline indicating "Surprise" events or "Security Alerts".

---

## 10. User Stories & Workflows

### Story 1: "The Hallucination Hunt"
**Persona**: Alice, AI Engineer.
**Context**: Agent reported "The moon is made of cheese".
**Workflow**:
1. Alice opens Supernova.
2. She sees the "Hallucination Alert" in the `VerificationDashboard`.
3. She clicks the alert. The Graph View zooms to the offending Memory Node (`memory:123`).
4. She sees the `VerificationResult` overlay: "Status: FAILED. Reason: Contradicts `memory:456` (Scientific Fact)".
5. She enables "Trace Replay" for the job that created `memory:123`.
6. She watches the agent's thought process. She sees the input prompt contained a "User joke".
7. Alice clicks "Edit" on the memory node to tag it as `joke` instead of `fact`.
8. She hits "Re-Verify". The node turns Green.

### Story 2: "Optimizing the Dream"
**Persona**: Bob, System Architect.
**Context**: Database size is exploding. Consolidation seems slow.
**Workflow**:
1. Bob checks the "Entropy Monitor". It shows "High Entropy" in Long-Term Memory (Red Zone).
2. This indicates the consolidation jobs aren't reducing redundancy effectively.
3. He opens the "Job History" panel. He sees `ConsolidationWorker` is failing with "Timeout".
4. He checks the `EntropyService` configuration panel in Supernova.
5. He adjusts the `threshold` slider from 4.5 to 3.5 (triggering more aggressive but smaller merges).
6. He clicks "Trigger Consolidation Now".
7. He watches the Graph View. Hundreds of small red nodes merge into a few large blue nodes.
8. The Entropy Gauge drops to Green.

---

## 11. Metric Definitions

To make monitoring "Intelligent", we define specific formulas.

### 11.1. Consolidation Efficiency ($E_c$)
$$ E_c = \frac{\text{Volume}_{\text{before}} - \text{Volume}_{\text{after}}}{\text{Compute Cost}} $$
*   **Goal**: Maximize $E_c$. If we spend \$1 to save 1kb, it's bad.
*   **Visual**: Line chart over time.

### 11.2. Knowledge Density ($\rho$)
$$ \rho = \frac{\sum \text{Importance Score}}{\text{Total Tokens}} $$
*   **Goal**: Maximize $\rho$. We want high importance in few tokens.
*   **Visual**: Heatmap. Darker regions = Higher Density.

### 11.3. Surprise Index ($S$)
Derived from the `surprise_score` in `Memory` entity (Phase 6).
*   **Visual**: "Spikes" on the timeline. A high spike indicates a "Black Swan" event or a breakthrough in reasoning.

---

## 12. API Contracts (Draft)

Khala must expose these endpoints to power Supernova.

### `GET /api/v1/visualization/graph`
Returns the graph structure in `sigma.js` or `d3` compatible format.
```json
{
  "nodes": [
    { "id": "mem:1", "label": "Moon", "size": 10, "color": "#FF0000", "tier": "working" },
    { "id": "mem:2", "label": "Cheese", "size": 5, "color": "#00FF00", "tier": "long_term" }
  ],
  "edges": [
    { "id": "rel:1", "source": "mem:1", "target": "mem:2", "type": "RELATED_TO", "weight": 0.8 }
  ]
}
```

### `GET /api/v1/monitoring/health`
```json
{
  "cpu_usage": 45,
  "memory_usage": 1024,
  "active_jobs": 3,
  "queue_depth": 12,
  "entropy_score": 4.2,
  "verification_pass_rate": 0.95
}
```

---

## 13. Advanced Visualization: The "Dream Mode"

One of Khala's unique features is "Dream-Inspired Consolidation" (Strategy 129). Supernova should visualize this.

**Concept**: When the system is "sleeping" (idle maintenance), switch the UI to "Dream Mode".
- **Visuals**: Darker background, glowing edges.
- **Animation**: Nodes float together and merge.
- **Audio**: Ambient hum (optional/experimental).
- **Purpose**: Gives the admin confidence that the system is "working" even when idle. It turns maintenance into a spectacle.

---

## 14. Security Dashboards: Visualizing the Invisible

Security threats in Agentic systems are often semantic (Injection) rather than technical (SQLi).

### 14.1. Injection Vector Map
- Visualize the path of an injected prompt.
- **Start**: User Input (Red Border).
- **Path**: Arrows showing how this input flowed into the Planning Prompt.
- **Block**: A "Shield" icon where `VisualSanitizer` or `VerificationGate` stopped it.

### 14.2. Access Control Topology
- Visualize `Scoped Memories` (Strategy 148).
- Show "Security Clearance" levels as concentric circles.
- **Center**: Core System Prompts (Level 0).
- **Middle**: Long-Term User Memory (Level 1).
- **Outer**: Web Search Results / Untrusted Input (Level 2).
- **Violation**: A red line crossing from Outer to Center without passing through a "Sanitization Node".

---

## 15. Synergy with Surrealism (WASM)

If we implement **Surrealism WASM**, Supernova becomes even faster.

- **Client-Side Physics? No.**
- **Server-Side Layout**: Use a WASM function `fn::layout_graph()` inside SurrealDB to calculate node positions (Force Atlas 2) *on the server*.
- **Benefit**: Supernova just renders the coordinates. It doesn't need to burn CPU calculating physics for 10,000 nodes.
- **Flow**:
    1. Supernova asks: `SELECT id, fn::layout_graph() as pos FROM memory`.
    2. SurrealDB runs Rust WASM.
    3. Returns `{id: "...", pos: {x: 1, y: 2}}`.
    4. Supernova renders instantly.

---

## 16. Conclusion & Recommendation

The "Supernova" submodule is not just a UI; it is the missing piece of the **Khala Cognitive Architecture**.

**Immediate Action Items**:
1.  **Fork & Rename**: Rename `supernova-js` to `khala-console`.
2.  **Connect**: Configure `vite.config.ts` to proxy requests to Khala's FastAPI.
3.  **Prototype**: Build the "AgentStatusWidget" using the existing `hooks/useGraphViz.ts` as a template for data fetching.

By building this "Command Center", we move from "running scripts" to "operating intelligence".
