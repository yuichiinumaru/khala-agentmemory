import React, { useRef } from 'react';
import { useGraphApplication } from './hooks/useGraphApplication';
import { GraphCanvas } from './components/GraphCanvas';
import { GraphOracle } from './components/GraphOracle';
import { ContextMenu } from './components/ui/ContextMenu';
import { Header } from './components/layout/Header';
import { HudControls } from './components/layout/HudControls';
import { MemoryInspector, MemoryNode } from './components/MemoryInspector';
import { TimelineScrubber } from './components/TimelineScrubber';
import { Stats } from './components/layout/Stats';
import { SurrealProvider } from './hooks/useSurreal';

const AppContent: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [timelineTime, setTimelineTime] = React.useState(Date.now());
  const {
    stats,
    currentLayout,
    searchQuery,
    selectedNode,
    contextMenu,
    isOracleOpen,
    isReady,
    api,
    setCurrentLayout,
    setSearchQuery,
    setSelectedNode,
    setContextMenu,
    setIsOracleOpen,
  } = useGraphApplication(containerRef);

  const handleContextAction = (action: 'focus' | 'filter' | 'analyze') => {
    if (!contextMenu || !api) return;
    const { nodeId } = contextMenu;

    switch (action) {
      case 'focus':
        api.focusNode(nodeId);
        break;
      case 'filter':
        const rawGraph = api.getRawGraph();
        if (rawGraph) {
          const cluster = rawGraph.getNodeAttribute(nodeId, 'cluster');
          if (cluster) api.filterCluster(cluster);
        }
        break;
      case 'analyze':
        setSelectedNode(nodeId);
        setIsOracleOpen(true);
        break;
    }
    setContextMenu(null);
  };

  return (
    <div
      className="relative w-screen h-screen bg-obsidian text-white font-sans overflow-hidden selection:bg-neon-purple/30"
      onClick={() => contextMenu && setContextMenu(null)}
    >
      {/* GraphCanvas is now always rendered to ensure the ref is available for the hook */}
      <GraphCanvas ref={containerRef} />

      {!isReady ? (
        <div className="absolute inset-0 z-20 bg-obsidian w-screen h-screen flex items-center justify-center text-neon-blue font-mono animate-pulse">
          CONNECTING_TO_KHALA...
        </div>
      ) : (
        <>
          <Header searchQuery={searchQuery} onSearchChange={setSearchQuery} />
          <Stats stats={stats} />
          <HudControls
            currentLayout={currentLayout}
            onLayoutChange={setCurrentLayout}
            graphApi={api}
          />
          <GraphOracle
            isOpen={isOracleOpen}
            onToggle={() => setIsOracleOpen(!isOracleOpen)}
            graphApi={api}
          />
          {contextMenu && (
            <ContextMenu
              x={contextMenu.x}
              y={contextMenu.y}
              nodeId={contextMenu.nodeId}
              onClose={() => setContextMenu(null)}
              onAction={handleContextAction}
            />
          )}
          <div className="absolute bottom-0 left-0 right-0 z-10 p-4">
             <TimelineScrubber
                startTime={Date.now() - 3600000}
                endTime={Date.now()}
                currentTime={timelineTime}
                events={[]}
                onChange={setTimelineTime}
             />
          </div>

          {selectedNode && !isOracleOpen && !contextMenu && (
            <MemoryInspector
              node={
                  api?.getRawGraph()?.hasNode(selectedNode)
                  ? { id: selectedNode, ...api.getRawGraph()?.getNodeAttributes(selectedNode) } as MemoryNode
                  : null
              }
            />
          )}
        </>
      )}
    </div>
  );
};

const App: React.FC = () => {
  return (
    <SurrealProvider url="http://localhost:8000/rpc" ns="khala" db="memory">
      <AppContent />
    </SurrealProvider>
  );
};

export default App;
