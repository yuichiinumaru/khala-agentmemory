import Graph from 'graphology';
import { Surreal } from 'surrealdb.js';

interface MemoryRecord {
  id: string;
  content: string;
  tier: string;
  importance: number;
  [key: string]: any;
}

interface RelationshipRecord {
  id: string;
  in: string; // SurrealDB uses 'in' and 'out' for edges
  out: string;
  strength?: number;
}

export const GraphService = {
  async initializeGraph(client: Surreal, graph: Graph): Promise<void> {
    try {
      // Fetch nodes
      const [memories] = await client.query<[MemoryRecord[]]>('SELECT * FROM memory');

      if (memories && Array.isArray(memories)) {
        memories.forEach((mem) => {
           if (!graph.hasNode(mem.id)) {
             graph.addNode(mem.id, {
               ...mem,
               // Default visual attributes if not present
               x: Math.random() * 1000,
               y: Math.random() * 1000,
               size: (mem.importance || 0.5) * 10,
               color: getColorForTier(mem.tier),
               label: mem.content.substring(0, 20) + '...'
             });
           }
        });
      }

      // Fetch edges (assuming 'relationship' table or similar, or implicit links)
      // For now, let's assume we also query a relationship table or inferred links
      // Khala uses graph reasoning, so edges are likely in a separate table or just 'memory' if it's graph based.
      // If using SurrealDB graph relations, we query edges.
      // Let's assume we might have edges. For MVP, just nodes is fine if no edge table known.
      // But let's add a placeholder for edge query.
      // const [edges] = await client.query('SELECT * FROM relationship');
    } catch (e) {
      console.error("Failed to initialize graph:", e);
    }
  },

  async subscribeToUpdates(client: Surreal, graph: Graph, onUpdate?: () => void): Promise<() => void> {
    try {
      // Subscribe to memory table
      const queryUuid = await client.live('memory');

      await client.subscribeLive(queryUuid, (action, result) => {
        const record = result as MemoryRecord;
        if (!record || !record.id) return;

        switch (action) {
          case 'CREATE':
          case 'UPDATE':
             if (graph.hasNode(record.id)) {
               graph.mergeNodeAttributes(record.id, {
                 ...record,
                 size: (record.importance || 0.5) * 10,
                 color: getColorForTier(record.tier)
               });
             } else {
               graph.addNode(record.id, {
                 ...record,
                 x: Math.random() * 1000,
                 y: Math.random() * 1000,
                 size: (record.importance || 0.5) * 10,
                 color: getColorForTier(record.tier),
                 label: record.content ? record.content.substring(0, 20) + '...' : record.id
               });
             }
             break;
          case 'DELETE':
             if (graph.hasNode(record.id)) {
               graph.dropNode(record.id);
             }
             break;
        }
        if (onUpdate) onUpdate();
      });

      return async () => {
          // Unsubscribe logic if available in SDK
          // client.kill(queryUuid);
      };
    } catch (e) {
      console.error("Failed to subscribe:", e);
      return () => {};
    }
  }
};

function getColorForTier(tier: string): string {
  switch (tier) {
    case 'working': return '#ff0a5c'; // Red
    case 'short_term': return '#bc13fe'; // Purple
    case 'long_term': return '#00f3ff'; // Cyan
    default: return '#888';
  }
}
