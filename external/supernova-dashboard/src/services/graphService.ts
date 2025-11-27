import { GraphData, GraphNode, GraphEdge } from "../types";

export const generateMockGraph = (nodeCount: number = 500): GraphData => {
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];
  
  const clusters = [
    { id: 'c1', color: '#00f3ff', label: 'Infra' }, 
    { id: 'c2', color: '#bc13fe', label: 'Social' }, 
    { id: 'c3', color: '#0aff60', label: 'Finance' },
    { id: 'c4', color: '#ff0a5c', label: 'Threats' }
  ];

  // Create Nodes
  for (let i = 0; i < nodeCount; i++) {
    const cluster = clusters[Math.floor(Math.random() * clusters.length)];
    const id = `n${i}`;
    
    nodes.push({
      id,
      label: `${cluster.label}_Node_${i}`,
      x: Math.random() * 2000 - 1000,
      y: Math.random() * 2000 - 1000,
      size: Math.random() * 8 + 3,
      color: cluster.color,
      cluster: cluster.id
    });
  }

  // Create Edges
  // Strategy: Prefer connecting within cluster, some cross-cluster noise
  nodes.forEach((source, i) => {
    // Connect to 1-4 other nodes
    const connectionCount = Math.floor(Math.random() * 4) + 1;
    
    for (let j = 0; j < connectionCount; j++) {
      const targetIndex = Math.floor(Math.random() * nodeCount);
      if (targetIndex === i) continue;
      
      const target = nodes[targetIndex];
      const isInternal = source.cluster === target.cluster;
      
      // High probability to connect if same cluster, low if different
      if (isInternal || Math.random() > 0.95) {
        edges.push({
          id: `e${source.id}-${target.id}`,
          source: source.id,
          target: target.id,
          color: isInternal ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.05)',
          size: isInternal ? 1 : 0.5
        });
      }
    }
  });

  return { nodes, edges };
};
