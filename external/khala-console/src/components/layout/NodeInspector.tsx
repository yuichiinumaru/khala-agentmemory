import React from 'react';
import { GlassCard } from '../ui/GlassCard';
import { Cpu } from 'lucide-react';
import { GraphVizAPI } from '../../hooks/useGraphApplication';

interface NodeInspectorProps {
  selectedNode: string;
  graphApi: GraphVizAPI | null;
  onAskOracle: () => void;
}

export const NodeInspector: React.FC<NodeInspectorProps> = ({ selectedNode, graphApi, onAskOracle }) => {
  const rawGraph = graphApi?.getRawGraph();
  // rawGraph is a graphology instance, attributes accessed via getNodeAttributes
  const node = rawGraph && rawGraph.hasNode(selectedNode)
    ? { id: selectedNode, ...rawGraph.getNodeAttributes(selectedNode) }
    : null;

  if (!node) return null;

  return (
    <div className="absolute top-32 right-6 w-64 pointer-events-auto animate-in fade-in slide-in-from-right-5 duration-300">
      <GlassCard className="border-neon-blue/30">
        <div className="flex items-center gap-2 mb-3 text-neon-blue">
          <Cpu size={16} />
          <span className="font-mono text-xs font-bold uppercase">Node Inspector</span>
        </div>
        <h2 className="text-xl font-bold mb-1">{node.label}</h2>
        <p className="text-xs text-white/50 font-mono mb-4">ID: {node.id}</p>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="bg-white/5 p-2 rounded">
            <span className="block text-white/30">Cluster</span>
            <span className="font-mono text-neon-purple">{node.cluster}</span>
          </div>
          <div className="bg-white/5 p-2 rounded">
            <span className="block text-white/30">Weight</span>
            <span className="font-mono text-white">0.85</span>
          </div>
        </div>
        <button
          onClick={onAskOracle}
          className="w-full mt-4 bg-neon-blue/10 border border-neon-blue/30 text-neon-blue py-2 rounded text-xs font-bold hover:bg-neon-blue/20 transition-colors uppercase tracking-wider"
        >
          Ask Oracle
        </button>
      </GlassCard>
    </div>
  );
};
