import { GraphData, GraphNode } from "../types";
import Graph from "graphology";

/**
 * CORE LAYER (Layer 1)
 * Pure logic, no UI dependencies.
 */

export const getGraphStats = (graph: Graph) => {
  const order = graph.order;
  const size = graph.size;
  // Calculate density manually since 'density' property doesn't exist on Graph type
  // Formula for directed graph: E / (V * (V - 1))
  const density = order > 1 ? size / (order * (order - 1)) : 0;

  return {
    nodes: order,
    edges: size,
    density
  };
};

/**
 * Generates a textual summary of the graph state for the AI Context.
 * Now includes top nodes by degree centrality (simulated).
 */
export const summarizeGraphContext = (graph: Graph): string => {
  const nodeCount = graph.order;
  const edgeCount = graph.size;
  
  if (nodeCount === 0) return "Graph is empty.";

  // 1. Calculate Degree Centrality (Top 5 Influencers)
  const degrees = graph.nodes().map(node => ({
    id: node,
    label: graph.getNodeAttribute(node, 'label'),
    degree: graph.degree(node)
  })).sort((a, b) => b.degree - a.degree).slice(0, 5);

  const topNodesStr = degrees.map(d => `- ${d.label} (ID: ${d.id}, Connections: ${d.degree})`).join("\n");

  // 2. Analyze Clusters
  const clusters = new Set(graph.nodes().map(n => graph.getNodeAttribute(n, 'cluster')));
  const clusterList = Array.from(clusters).filter(Boolean).join(", ");

  return `
GRAPH TOPOLOGY REPORT:
- Total Nodes: ${nodeCount}
- Total Edges: ${edgeCount}
- Active Clusters: [${clusterList}]

TOP INFLUENCERS (Global):
${topNodesStr}
`;
};

/**
 * Summarizes specifically what is currently visible in the viewport.
 * This enables "Visual RAG" - the AI knows what the user is looking at.
 */
export const summarizeViewport = (graph: Graph, visibleNodes: string[]): string => {
  if (visibleNodes.length === 0) return "User is staring into the void. No nodes visible.";
  if (visibleNodes.length > 500) return `User is looking at a high-level overview containing ${visibleNodes.length} nodes. Too many to list individually.`;

  // Find most important nodes in the current view
  const nodes = visibleNodes.map(id => ({
    id,
    label: graph.getNodeAttribute(id, 'label'),
    cluster: graph.getNodeAttribute(id, 'cluster'),
    degree: graph.degree(id)
  })).sort((a, b) => b.degree - a.degree).slice(0, 10); // Top 10 visible

  const clusterCounts: Record<string, number> = {};
  visibleNodes.forEach(id => {
    const c = graph.getNodeAttribute(id, 'cluster');
    if (c) clusterCounts[c] = (clusterCounts[c] || 0) + 1;
  });

  const dominantCluster = Object.entries(clusterCounts).sort((a, b) => b[1] - a[1])[0];

  return `
VIEWPORT CONTEXT (What user sees):
- Visible Count: ${visibleNodes.length} nodes
- Dominant Cluster: ${dominantCluster ? `${dominantCluster[0]} (${dominantCluster[1]} nodes)` : 'Mixed'}
- Key Entities in View:
${nodes.map(n => `  * ${n.label} (${n.cluster})`).join('\n')}
`;
};