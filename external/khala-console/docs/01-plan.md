# 🧠 Strategic Plan: Supernova (formerly GraphViz.js)

## 1. Gap Analysis (Current vs. Vision)

We have successfully bootstrapped the **MVP** (Phase 1).
*   **Current State**: A functional React application using `sigma.js` + `graphology`, wrapped in a `useGraphViz` hook, with a basic Gemini AI integration and a high-end Glassmorphism UI.
*   **The Vision (Research Docs)**: A standalone library/platform featuring custom WebGL rendering, built-in graph simplification (LoD), MCP integration, and agnostic rendering engines.

### The "Environment Gap"
We are developing in a browser-based, single-process environment. We cannot easily spin up Docker containers (for Neo4j) or manage a complex Monorepo build chain with `tsup`/`turbo` right now.

## 2. The Implementation Strategy

We will adopt a **"Modolith" (Modular Monolith)** approach. Instead of physical packages in a monorepo, we will enforce strict logical separation within `src/` to mimic the architecture.

### Core Pillars of Execution:

#### A. The "One Hook" Evolution
Refine `useGraphViz` to be less of a wrapper and more of a controller. It currently handles initialization and layout. It needs to handle:
*   **State Management**: Time-travel (undo/redo).
*   **LoD Logic**: Currently, we render all nodes. We need a logic layer that calculates clusters *before* passing data to Sigma.
*   **Events**: A unified event bus for UI <-> Graph interaction.

#### B. AI as a First-Class Citizen (The Oracle)
Currently, the AI sees a text summary.
*   **Upgrade**: Implement "Visual RAG". The AI should receive the *viewport state* (what nodes are visible?) and *selection state*.
*   **Actionable AI**: The AI should output JSON commands to control the graph (e.g., `{ "action": "focus", "target": "node_id" }`).

#### C. The "Cyberpunk" Polish
The UI is good, but needs to be *immersive*.
*   **Sound Design**: Add subtle UI sounds (beeps, hums).
*   **Motion**: Use Framer Motion for panel transitions.
*   **VFX**: Add post-processing effects (bloom simulation via CSS) to the canvas.

## 3. Technical Constraints & Solutions

| Constraint | Solution |
| :--- | :--- |
| No Backend (Neo4j) | Use in-memory graph generation with `graphology` and mock huge datasets (10k+ nodes). |
| No Custom WebGL Shader Dev | Leverage `sigma.js` custom program capabilities instead of writing raw WebGL from scratch immediately. |
| Single Thread JS | Use `graphology-layout-forceatlas2` in a Web Worker (already supported by library, needs config). |

## 4. Why This Plan?
This ensures we build the **"Best in Class"** UX/UI and Architecture defined in `research.md` without getting bogged down in DevOps complexity that doesn't add value to the prototype. We focus on the **visuals** and the **intelligence**.