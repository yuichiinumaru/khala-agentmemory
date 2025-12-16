import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { GraphOracle } from '../GraphOracle';
import { AnalystService } from '../../services/AnalystService';
import React from 'react';

vi.mock('../../services/AnalystService', () => ({
  AnalystService: {
    explainGraph: vi.fn()
  }
}));

// Mock scrollIntoView
window.HTMLElement.prototype.scrollIntoView = vi.fn();

describe('GraphOracle', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockApi: any = {
    getRawGraph: () => ({
        nodes: () => [],
        edges: () => [],
        getNodeAttributes: () => ({}),
        getEdgeAttributes: () => ({})
    }),
    getViewportState: () => ({ visibleNodes: [] })
  };

  it('should call AnalystService when sending message', async () => {
    (AnalystService.explainGraph as any).mockResolvedValue({ explanation: 'AI Response', suggested_actions: [] });

    render(<GraphOracle isOpen={true} onToggle={vi.fn()} graphApi={mockApi} />);

    // Find input by placeholder
    const input = screen.getByPlaceholderText(/Query graph data/i);
    fireEvent.change(input, { target: { value: 'Why red?' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
        expect(AnalystService.explainGraph).toHaveBeenCalledWith('Why red?', expect.anything());
    });

    expect(screen.getByText('AI Response')).toBeInTheDocument();
  });
});
