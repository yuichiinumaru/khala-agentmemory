# 🏛️ System Architecture: Supernova (Post-Refactor)

## Conceptual Layers

The application now correctly implements the "Layered Architecture," with a clear separation of concerns.

```mermaid
graph TD
    User[User / AI Agent] --> UI_Layer
    UI_Layer --> Integration_Layer
    Integration_Layer --> Core_Layer
    
    subgraph UI_Layer [Layer 4: UI & Interaction]
        App.tsx (Composition Root)
        subgraph "Layout Components"
            Header.tsx
            HudControls.tsx
            NodeInspector.tsx
            Stats.tsx
        end
        GraphOracle (Chat)
        GraphCanvas (View)
    end

    subgraph Integration_Layer [Layer 3: The "Hook" as Controller]
        useGraphApplication.ts (State & Logic)
    end

    subgraph Core_Layer [Layer 1: Data & Math]
        services/ (Data Fetching)
        core/ (Algorithms)
        Graphology Instance (The Model)
    end
```

## Directory Structure (The "Modolith")

The codebase now follows the intended "Modolith" structure inside a unified `src/` directory.

```
src/
├── core/                 # (Layer 1) Pure Logic, No React, No DOM
│   └── algorithms.ts     # Graph summarization and stats
│
├── hooks/                # (Layer 3) The Glue
│   └── useGraphApplication.ts # Main Controller Hook
│
├── components/           # (Layer 4) React UI
│   ├── layout/           # High-level page structure
│   ├── ui/               # Reusable UI elements (GlassCard)
│   ├── GraphCanvas.tsx   # Sigma.js wrapper
│   └── GraphOracle.tsx   # AI Chat interface
│
├── services/             # External IO
│   ├── geminiService.ts  # AI API connector
│   ├── graphService.ts   # Mock data generation
│   └── mockDatabase.ts   # Simulated async data source
│
└── types.ts              # Global TypeScript definitions
```

## Data Flow (Post-Refactor)

1.  **Initialization**: `useGraphApplication` hook is mounted. It calls `services/mockDatabase` to fetch the initial graph data and manages the loading state.
2.  **State Management**: All core application state (graph data, layout, search query) is managed within `useGraphApplication`.
3.  **Rendering**:
    *   `App.tsx` acts as a pure "Composition Root." It uses the `useGraphApplication` hook and passes the state and setters down to the new, granular layout components (`Header`, `HudControls`, etc.).
    *   `GraphCanvas.tsx` receives the Sigma instance from the hook and renders the graph.
4.  **Interaction**:
    *   **User Input**: UI components like `Header` (search) or `HudControls` (layout change) call setter functions exposed by the `useGraphApplication` hook (`setSearchQuery`, `setLayout`).
    *   **State Update**: The hook updates its internal state, which triggers a re-render of the relevant components.
    *   **AI Action**: `GraphOracle` calls the `graphApi` exposed by the hook to perform actions like focusing on a node.

This new architecture is much cleaner, easier to test, and more closely aligns with the original vision for the project.