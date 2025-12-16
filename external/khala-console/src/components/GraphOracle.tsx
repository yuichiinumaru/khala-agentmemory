import React, { useState, useEffect, useRef } from 'react';
import { GlassCard } from './ui/GlassCard';
import { ChatMessage } from '../types';
import { queryGraphOracle } from '../services/geminiService';
import { summarizeViewport } from '../core/algorithms';
import { Send, Bot, Loader2, Minimize2 } from 'lucide-react';
import { GraphVizAPI } from '../hooks/useGraphApplication';

interface GraphOracleProps {
  isOpen: boolean;
  onToggle: () => void;
  graphApi: GraphVizAPI | null;
}

export const GraphOracle: React.FC<GraphOracleProps> = ({ isOpen, onToggle, graphApi }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: '0', role: 'model', content: 'Supernova Oracle Online. Systems Nominal. Analyzing network topology...', timestamp: Date.now() }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const executeAiCommands = (response: string) => {
    if (!graphApi) return response;

    const jsonRegex = /```json\s*(\{[\s\S]*?\})\s*```/;
    const match = response.match(jsonRegex);

    if (match && match[1]) {
      try {
        const command = JSON.parse(match[1]);
        console.log("ORACLE COMMAND:", command);

        switch (command.action) {
          case 'FOCUS_NODE':
            if (command.target) graphApi.focusNode(command.target);
            break;
          case 'FILTER_CLUSTER':
            if (command.target) graphApi.filterCluster(command.target);
            break;
          case 'RESET_VIEW':
            graphApi.resetView();
            break;
        }

        return response.replace(jsonRegex, '').trim();
      } catch (e) {
        console.error("Failed to parse AI command", e);
      }
    }
    return response;
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading || !graphApi) return;

    const rawGraph = graphApi.getRawGraph();
    if (!rawGraph) return;

    // Derive graphData for AI context (expensive, but necessary for now)
    // Ideally we pass a summary or handle this in backend
    const derivedGraphData: any = {
       nodes: rawGraph.nodes().map(n => ({ id: n, ...rawGraph.getNodeAttributes(n) })),
       edges: rawGraph.edges().map(e => ({ id: e, ...rawGraph.getEdgeAttributes(e) }))
    };

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    let viewportContext = "";
    if (graphApi && graphApi.getViewportState) {
      const { visibleNodes } = graphApi.getViewportState();
      viewportContext = summarizeViewport(rawGraph, visibleNodes);
    }

    const rawResponse = await queryGraphOracle(
      userMsg.content, 
      derivedGraphData,
      messages.map(m => ({ role: m.role, content: m.content })),
      viewportContext
    );

    const cleanResponse = executeAiCommands(rawResponse);

    const botMsg: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: 'model',
      content: cleanResponse,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, botMsg]);
    setIsLoading(false);
  };

  if (!isOpen) {
    return (
      <button 
        onClick={onToggle}
        className="fixed bottom-6 right-6 p-4 rounded-full bg-neon-purple shadow-[0_0_20px_rgba(188,19,254,0.4)] hover:scale-105 transition-transform z-50 text-white"
      >
        <Bot size={24} />
      </button>
    );
  }

  return (
    <GlassCard className="fixed bottom-6 right-6 w-96 h-[600px] flex flex-col z-50 border-neon-purple/30 shadow-[0_0_50px_rgba(188,19,254,0.15)] animate-in slide-in-from-bottom-10 fade-in duration-300">
      <div className="flex items-center justify-between pb-4 border-b border-white/10">
        <div className="flex items-center gap-2 text-neon-purple">
          <Bot size={20} />
          <h3 className="font-mono font-bold tracking-wider">SUPERNOVA ORACLE v2.5</h3>
        </div>
        <button onClick={onToggle} className="text-white/50 hover:text-white transition-colors">
          <Minimize2 size={16} />
        </button>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto py-4 space-y-4 pr-2">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] p-3 rounded-lg text-sm leading-relaxed ${
                msg.role === 'user' 
                  ? 'bg-neon-purple/20 text-white border border-neon-purple/20 rounded-tr-none' 
                  : 'bg-white/5 text-gray-200 border border-white/5 rounded-tl-none font-mono text-xs'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white/5 p-3 rounded-lg rounded-tl-none border border-white/5 flex items-center gap-2">
              <Loader2 size={14} className="animate-spin text-neon-purple" />
              <span className="text-xs font-mono text-white/50">Processing...</span>
            </div>
          </div>
        )}
      </div>
      <div className="pt-4 mt-auto border-t border-white/10 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Query graph data..."
          className="flex-1 bg-black/20 border border-white/10 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-neon-purple/50 font-mono placeholder-white/20"
        />
        <button 
          onClick={handleSend}
          disabled={isLoading}
          className="p-2 bg-neon-purple/10 border border-neon-purple/30 rounded-md text-neon-purple hover:bg-neon-purple/20 transition-colors disabled:opacity-50"
        >
          <Send size={18} />
        </button>
      </div>
    </GlassCard>
  );
};
