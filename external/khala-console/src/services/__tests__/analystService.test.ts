import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AnalystService } from '../AnalystService';

// Mock global fetch
global.fetch = vi.fn();

describe('AnalystService', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('should fetch metrics successfully', async () => {
    const mockMetrics = { entropy: 4.2, density: 0.8 };
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => mockMetrics
    });

    const metrics = await AnalystService.getMetrics();
    expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/metrics'));
    expect(metrics).toEqual(mockMetrics);
  });

  it('should explain graph query', async () => {
    const mockResponse = { explanation: 'This is a cluster.', actions: [] };
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => mockResponse
    });

    const result = await AnalystService.explainGraph('What is this?', { visibleNodes: [] });
    expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/explain'), expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('What is this?')
    }));
    expect(result).toEqual(mockResponse);
  });

  it('should handle errors', async () => {
    (global.fetch as any).mockResolvedValue({
        ok: false,
        statusText: 'Server Error'
    });

    await expect(AnalystService.getMetrics()).rejects.toThrow('Server Error');
  });
});
