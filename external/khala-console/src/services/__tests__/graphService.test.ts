import { describe, it, expect, vi, beforeEach } from 'vitest';
import { GraphService } from '../GraphService';
import Graph from 'graphology';
import { Surreal } from 'surrealdb.js';

// Mock SurrealDB
vi.mock('surrealdb.js', () => {
  return {
    Surreal: vi.fn()
  };
});

describe('GraphService', () => {
  let client: any;
  let graph: Graph;

  beforeEach(() => {
    client = {
      query: vi.fn(),
      live: vi.fn(),
      subscribeLive: vi.fn(),
    };
    graph = new Graph();
  });

  it('should load initial data and populate graph', async () => {
    const mockMemories = [
      { id: 'memory:1', content: 'Test Node', importance: 0.8, tier: 'working' },
      { id: 'memory:2', content: 'Test Node 2', importance: 0.5, tier: 'short_term' }
    ];
    // Mock SELECT response
    client.query.mockResolvedValue([mockMemories]);

    await GraphService.initializeGraph(client, graph);

    expect(client.query).toHaveBeenCalledWith(expect.stringContaining('SELECT'));
    expect(graph.hasNode('memory:1')).toBe(true);
    expect(graph.hasNode('memory:2')).toBe(true);
    // Default edge strategy? Maybe none for now if no links provided.
  });

  it('should handle LIVE CREATE events', async () => {
      // Mock SELECT to return empty first
      client.query.mockResolvedValue([[]]);

      // Mock live subscription
      // subscribeLive returns a handle/uuid
      const liveId = 'uuid-123';
      client.live.mockResolvedValue(liveId);

      // We need to trigger the callback passed to subscribeLive?
      // Actually surreal.js live() just returns a query uuid.
      // We need to listen to events?
      // Wait, client.subscribeLive(uuid, callback) is the pattern in some versions?
      // Or client.live(table, callback)?
      // In v1.0.0, it is `client.live(query, callback)`?
      // Docs say: `client.live('memory', callback)` isn't standard?
      // Standard is: `let queryUuid = await client.live('memory');` then `client.subscribeLive(queryUuid, callback)`.
      // Let's assume standard JS SDK.

      let callback: any;
      client.subscribeLive = vi.fn().mockImplementation((id, cb) => {
          callback = cb;
      });

      await GraphService.subscribeToUpdates(client, graph);

      expect(client.live).toHaveBeenCalled();
      expect(client.subscribeLive).toHaveBeenCalled();

      // Simulate CREATE - Passing action and result as separate arguments
      callback('CREATE', { id: 'memory:new', content: 'New', tier: 'working' });

      expect(graph.hasNode('memory:new')).toBe(true);
  });

  it('should handle LIVE DELETE events', async () => {
      client.query.mockResolvedValue([[]]);
      graph.addNode('memory:old', { label: 'Old' });

      let callback: any;
      client.subscribeLive = vi.fn().mockImplementation((id, cb) => { callback = cb; });

      await GraphService.subscribeToUpdates(client, graph);

      callback('DELETE', { id: 'memory:old' });

      expect(graph.hasNode('memory:old')).toBe(false);
  });
});
