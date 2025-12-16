import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom'; // Add matchers
import { AgentStatusWidget } from '../AgentStatusWidget';
import React from 'react';
import * as useAgentStatusHook from '../../hooks/useAgentStatus';

// Mock the hook
vi.mock('../../hooks/useAgentStatus', () => ({
  useAgentStatus: vi.fn()
}));

describe('AgentStatusWidget', () => {
  it('should render thinking status correctly', () => {
    vi.mocked(useAgentStatusHook.useAgentStatus).mockReturnValue({
      name: 'Agent Alpha',
      state: 'thinking',
      currentThought: 'Processing data...',
      isError: false,
      entropyHistory: []
    });

    render(<AgentStatusWidget agentId="agent:1" />);

    expect(screen.getByText('Agent Alpha')).toBeInTheDocument();
    expect(screen.getByText('thinking')).toBeInTheDocument();
    // Check for green indicator or class?
    // We can check if specific style/class is present if meaningful
  });

  it('should render error status correctly', () => {
    vi.mocked(useAgentStatusHook.useAgentStatus).mockReturnValue({
      name: 'Agent Beta',
      state: 'error',
      currentThought: 'Failed connection',
      isError: true,
      entropyHistory: []
    });

    render(<AgentStatusWidget agentId="agent:2" />);

    expect(screen.getByText('error')).toBeInTheDocument();
    // Verify error styling (e.g., border-red-500)
    const card = screen.getByTestId('agent-widget');
    expect(card).toHaveClass('border-red-500');
  });
});
