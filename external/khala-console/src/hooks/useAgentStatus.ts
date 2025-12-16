import { useState, useEffect } from 'react';
import { useSurreal } from './useSurreal';

export interface AgentStatus {
  name: string;
  state: 'idle' | 'thinking' | 'sleeping' | 'error';
  currentThought: string;
  isError: boolean;
  entropyHistory: number[];
}

export const useAgentStatus = (agentId: string): AgentStatus => {
  const { client, status } = useSurreal();
  const [agentStatus, setAgentStatus] = useState<AgentStatus>({
    name: agentId,
    state: 'idle',
    currentThought: 'Waiting for connection...',
    isError: false,
    entropyHistory: []
  });

  useEffect(() => {
    if (status !== 'connected') return;

    // TODO: Implement LIVE SELECT from 'jobs' or 'agents' table
    // For now, mock updates
    const interval = setInterval(() => {
        // Fetch latest status
    }, 1000);

    return () => clearInterval(interval);
  }, [status, agentId]);

  return agentStatus;
};
