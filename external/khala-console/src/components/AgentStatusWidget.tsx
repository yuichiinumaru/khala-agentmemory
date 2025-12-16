import React from 'react';
import { useAgentStatus } from '../hooks/useAgentStatus';
import { GlassCard } from './ui/GlassCard';
import { Brain, Moon, AlertTriangle, Activity } from 'lucide-react';

export const AgentStatusWidget: React.FC<{ agentId: string }> = ({ agentId }) => {
  const { name, state, currentThought, isError } = useAgentStatus(agentId);

  const getIcon = () => {
      switch(state) {
          case 'thinking': return <Brain className="animate-pulse text-neon-purple" />;
          case 'sleeping': return <Moon className="text-blue-400" />;
          case 'error': return <AlertTriangle className="text-red-500" />;
          default: return <Activity className="text-gray-400" />;
      }
  };

  return (
    <GlassCard data-testid="agent-widget" className={`p-4 border ${isError ? 'border-red-500' : 'border-neon-purple/30'}`}>
      <div className="flex justify-between items-center mb-2">
         <h3 className="font-mono font-bold text-white">{name}</h3>
         <div className="flex items-center gap-2">
             {getIcon()}
             <span className={`text-xs uppercase font-bold ${isError ? 'text-red-500' : 'text-neon-green'}`}>
                 {state}
             </span>
         </div>
      </div>
      <div className="bg-black/20 p-2 rounded border border-white/5">
         <span className="text-xs text-white/40 block mb-1">CURRENT THOUGHT</span>
         <p className="text-sm font-mono text-white/80 line-clamp-2">{currentThought}</p>
      </div>
    </GlassCard>
  );
};
