import { describe, it, expect } from 'vitest';
import Graph from 'graphology';
import { getGraphStats, summarizeGraphContext, summarizeViewport } from './algorithms';

describe('Core Graph Algorithms', () => {

  // Test Fixture
  const createTestGraph = () => {
    const graph = new Graph();
    graph.addNode('n1', { label: 'Node 1', cluster: 'c1' });
    graph.addNode('n2', { label: 'Node 2', cluster: 'c1' });
    graph.addNode('n3', { label: 'Node 3', cluster: 'c2' });
    graph.addEdge('n1', 'n2');
    graph.addEdge('n2', 'n3');
    return graph;
  };

  describe('getGraphStats', () => {
    it('should correctly calculate graph statistics', () => {
      const graph = createTestGraph();
      const stats = getGraphStats(graph);
      expect(stats.nodes).toBe(3);
      expect(stats.edges).toBe(2);
      // Density formula for directed graph: E / (V * (V - 1)) = 2 / (3 * 2) = 1/3
      expect(stats.density).toBeCloseTo(0.333);
    });

    it('should handle an empty graph', () => {
      const graph = new Graph();
      const stats = getGraphStats(graph);
      expect(stats.nodes).toBe(0);
      expect(stats.edges).toBe(0);
      expect(stats.density).toBe(0);
    });
  });

  describe('summarizeGraphContext', () => {
    it('should generate a correct summary for a graph', () => {
      const graph = createTestGraph();
      const summary = summarizeGraphContext(graph);
      expect(summary).toContain('Total Nodes: 3');
      expect(summary).toContain('Total Edges: 2');
      expect(summary).toContain('Active Clusters: [c1, c2]');
      expect(summary).toContain('Node 2 (ID: n2, Connections: 2)'); // Top influencer
    });

    it('should handle an empty graph', () => {
        const graph = new Graph();
        const summary = summarizeGraphContext(graph);
        expect(summary).toBe('Graph is empty.');
    });
  });

  describe('summarizeViewport', () => {
    it('should summarize visible nodes correctly', () => {
      const graph = createTestGraph();
      const visibleNodes = ['n1', 'n2'];
      const summary = summarizeViewport(graph, visibleNodes);
      expect(summary).toContain('Visible Count: 2 nodes');
      expect(summary).toContain('Dominant Cluster: c1 (2 nodes)');
      expect(summary).toContain('* Node 1 (c1)');
      expect(summary).toContain('* Node 2 (c1)');
    });

    it('should handle an empty viewport', () => {
        const graph = createTestGraph();
        const summary = summarizeViewport(graph, []);
        expect(summary).toBe('User is staring into the void. No nodes visible.');
    });

    it('should handle a large number of visible nodes', () => {
        const graph = new Graph();
        const visibleNodes = Array.from({ length: 501 }, (_, i) => `n${i}`);
        const summary = summarizeViewport(graph, visibleNodes);
        expect(summary).toContain('User is looking at a high-level overview containing 501 nodes.');
    });
  });

});
