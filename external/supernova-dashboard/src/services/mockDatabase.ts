import { GraphData, GraphNode, GraphEdge } from "../types";
import { generateMockGraph } from "./graphService";

// Simulating a Neo4j Driver Interface
export class MockDatabase {
  private static instance: MockDatabase;
  private data: GraphData;
  private latency = 800; // Simulate network lag

  private constructor() {
    this.data = generateMockGraph(1500); // Initialize with a larger dataset
  }

  public static getInstance(): MockDatabase {
    if (!MockDatabase.instance) {
      MockDatabase.instance = new MockDatabase();
    }
    return MockDatabase.instance;
  }

  // Simulate a Cypher query
  public async runQuery(cypher: string): Promise<{ records: any[], summary: string }> {
    return new Promise((resolve) => {
      setTimeout(() => {
        // Simple mock logic: if query asks for everything, return all.
        // If it asks for a specific cluster (e.g., "WHERE n.cluster = 'Infra'"), filter it.
        
        let resultNodes = this.data.nodes;
        let resultEdges = this.data.edges;

        if (cypher.includes("WHERE n.cluster")) {
          // Naive parsing for demo purposes
          const match = cypher.match(/'([^']+)'/);
          if (match) {
            const cluster = match[1];
            resultNodes = resultNodes.filter(n => n.cluster === cluster || n.cluster?.includes(cluster));
            const nodeIds = new Set(resultNodes.map(n => n.id));
            resultEdges = resultEdges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target));
          }
        } else if (cypher.includes("LIMIT")) {
           const limit = parseInt(cypher.split("LIMIT")[1].trim()) || 100;
           resultNodes = resultNodes.slice(0, limit);
           // Filter edges to match remaining nodes
           const nodeIds = new Set(resultNodes.map(n => n.id));
           resultEdges = resultEdges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target));
        }

        resolve({
          records: resultNodes.map(n => ({
            get: (key: string) => key === 'n' ? n : null
          })),
          summary: `Returned ${resultNodes.length} nodes and ${resultEdges.length} edges.`
        });
      }, this.latency);
    });
  }

  public async getAllData(): Promise<GraphData> {
    // Simulate initial load
    return new Promise((resolve) => {
      setTimeout(() => resolve(this.data), this.latency);
    });
  }
}

export const db = MockDatabase.getInstance();