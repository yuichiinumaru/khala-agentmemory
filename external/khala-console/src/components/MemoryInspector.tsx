import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import DOMPurify from 'dompurify';
import { GlassCard } from './ui/GlassCard';
import { GraphNode } from '../types';

export interface MemoryNode extends GraphNode {
  content: string;
  tier: string;
  importance: number;
  embedding?: number[];
  metadata?: Record<string, any>;
}

interface MemoryInspectorProps {
  node: MemoryNode | null;
}

export const MemoryInspector: React.FC<MemoryInspectorProps> = ({ node }) => {
  const [activeTab, setActiveTab] = useState<'meta' | 'vec'>('meta');

  if (!node) return null;

  // Sanitize content before rendering (though ReactMarkdown usually handles it safely)
  const sanitizedContent = DOMPurify.sanitize(node.content);

  return (
    <div className="absolute top-20 right-6 w-80 z-20 pointer-events-auto">
      <GlassCard className="border-neon-purple/50">
        <div className="flex justify-between items-center mb-4">
           <span className="bg-neon-purple/20 text-neon-purple px-2 py-0.5 rounded text-xs uppercase font-bold">
             {node.tier || 'unknown'}
           </span>
           <span className="text-white/40 text-xs font-mono">{node.id}</span>
        </div>

        <div className="prose prose-invert prose-sm max-h-60 overflow-y-auto mb-4 bg-black/20 p-2 rounded text-white/90 text-sm">
           <ReactMarkdown>{sanitizedContent}</ReactMarkdown>
        </div>

        <div className="flex border-b border-white/10 mb-4">
           <button
             role="tab"
             aria-label="Meta"
             className={`px-4 py-2 text-xs font-bold uppercase ${activeTab === 'meta' ? 'text-white border-b-2 border-neon-blue' : 'text-white/40'}`}
             onClick={() => setActiveTab('meta')}
           >
             Meta
           </button>
           <button
             role="tab"
             aria-label="Vector"
             className={`px-4 py-2 text-xs font-bold uppercase ${activeTab === 'vec' ? 'text-white border-b-2 border-neon-blue' : 'text-white/40'}`}
             onClick={() => setActiveTab('vec')}
           >
             Vector
           </button>
        </div>

        {activeTab === 'meta' && (
           <pre className="text-xs font-mono text-white/70 overflow-x-auto p-2 bg-black/30 rounded">
             {JSON.stringify(node.metadata || {}, null, 2)}
           </pre>
        )}

        {activeTab === 'vec' && (
           <div className="text-xs font-mono text-white/70 break-all p-2 bg-black/30 rounded">
              {node.embedding ? `Vector[${node.embedding.length}]: [${node.embedding.slice(0, 5).join(', ')}...]` : 'No vector data'}
           </div>
        )}

      </GlassCard>
    </div>
  );
};
