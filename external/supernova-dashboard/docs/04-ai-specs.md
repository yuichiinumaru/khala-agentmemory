# 🤖 AI "Oracle" Specifications

## 1. Persona
*   **Name**: GraphViz Oracle v2.5
*   **Tone**: Cyberpunk, High-Technical, Concise.
*   **Output Style**: Bullet points, statistical breakdowns, JSON commands for UI control.

## 2. Dynamic Context Injection
Instead of sending the whole graph (which might be 100k nodes), we implement a **Viewport Context**:

```typescript
interface AIContext {
  stats: {
    totalNodes: number;
    totalEdges: number;
    density: number;
  };
  visibleState: {
    centerNode: string | null;
    zoomLevel: number;
    topVisibleNodes: { label: string; centrality: number }[]; // Top 10 on screen
  };
  selectedNode: NodeData | null;
}
```

## 3. Command Protocol (The "Action" Layer)
The AI can control the UI. We instruct the model to return JSON blocks if it wants to perform an action.

**Prompt Injection:**
> "If you want to modify the view, output a JSON block at the end of your response like: ```json { "action": "ACTION_NAME", "params": {...} } ```"

**Supported Actions:**
1.  `FOCUS_NODE`: `{ "id": "n123" }` -> Camera flies to node.
2.  `HIGHLIGHT_CLUSTER`: `{ "cluster": "Finance" }` -> Dim all other nodes.
3.  `CHANGE_LAYOUT`: `{ "type": "grid" }` -> Triggers layout animation.
4.  `EXPLAIN_PATH`: `{ "from": "A", "to": "B" }` -> Highlights shortest path.

## 4. Implementation Steps
1.  Modify `services/geminiService.ts` to accept the `AIContext` object.
2.  Create a parser in `GraphOracle.tsx` to detect code blocks in the response.
3.  Expose a `dispatchAction` function from `useGraphViz` to the UI layer.