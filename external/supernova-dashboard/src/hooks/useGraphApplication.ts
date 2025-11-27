import { useEffect, useRef, MutableRefObject, useState, useCallback } from 'react';
import Graph from 'graphology';
import { Sigma } from 'sigma';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import circular from 'graphology-layout/circular';
import { GraphData, LayoutType } from '../types';
import { db } from '../services/mockDatabase';

export interface GraphVizAPI {
  focusNode: (nodeId: string) => void;
  filterCluster: (clusterId: string) => void;
  resetView: () => void;
  getRawGraph: () => Graph | null;
  getViewportState: () => { visibleNodes: string[]; camera: { x: number; y: number; zoom: number } };
  exportData: () => void;
}

export const useGraphApplication = (
  containerRef: MutableRefObject<HTMLElement | null>
) => {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [currentLayout, setCurrentLayout] = useState<LayoutType>(LayoutType.FORCE_ATLAS);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; nodeId: string } | null>(null);
  const [isOracleOpen, setIsOracleOpen] = useState(false);
  const [isReady, setIsReady] = useState(false);

  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);
  const apiRef = useRef<GraphVizAPI | null>(null);

  useEffect(() => {
    const loadData = async () => {
      const data = await db.getAllData();
      setGraphData(data);
    };
    loadData();
  }, []);

  useEffect(() => {
    if (!containerRef.current || !graphData) return;

    if (sigmaRef.current) sigmaRef.current.kill();

    const graph = new Graph();
    graphRef.current = graph;

    graphData.nodes.forEach(node => {
      graph.addNode(node.id, { ...node, x: Math.random() * 1000, y: Math.random() * 1000 });
    });
    graphData.edges.forEach(edge => {
      graph.addEdgeWithKey(edge.id, edge.source, edge.target, { ...edge });
    });

    forceAtlas2.assign(graph, { iterations: 50 });

    const sigma = new Sigma(graph, containerRef.current, {
      renderEdgeLabels: false,
      allowInvalidContainer: true,
      stagePadding: 50,
      labelFont: "JetBrains Mono",
      labelWeight: "bold",
      labelColor: { color: "#fff" },
      zIndex: true,
    });

    sigma.on("clickNode", ({ node }) => {
      setSelectedNode(node);
      if (!isOracleOpen) setIsOracleOpen(true);
    });

    sigma.on("rightClickNode", ({ node, event }) => {
      event.original.preventDefault();
      const domEvent = event.original as MouseEvent;
      setContextMenu({ x: domEvent.clientX, y: domEvent.clientY, nodeId: node });
    });

    sigmaRef.current = sigma;
    apiRef.current = {
        focusNode: (nodeId: string) => {
            if (!graph.hasNode(nodeId)) return;
            const nodeData = graph.getNodeAttributes(nodeId);
            sigma.getCamera().animate({ x: nodeData.x, y: nodeData.y, ratio: 0.3 }, { duration: 800 });
        },
        filterCluster: (clusterId: string) => {
            sigma.setSetting("nodeReducer", (node, data) => {
                if (data.cluster === clusterId) return { ...data, highlighted: true };
                return { ...data, hidden: true };
            });
            sigma.setSetting("edgeReducer", (edge, data) => ({ ...data, hidden: true }));
        },
        resetView: () => {
            sigma.setSetting("nodeReducer", null);
            sigma.setSetting("edgeReducer", null);
            sigma.getCamera().animate({ x: 0, y: 0, ratio: 1 }, { duration: 500 });
        },
        getRawGraph: () => graph,
        getViewportState: () => {
            const camera = sigma.getCamera();
            const visibleNodes: string[] = [];
            graph.forEachNode((node, attrs) => {
                const pos = sigma.graphToViewport(attrs);
                if (pos.x > 0 && pos.x < sigma.width && pos.y > 0 && pos.y < sigma.height) {
                    visibleNodes.push(node);
                }
            });
            return { visibleNodes, camera: { x: camera.x, y: camera.y, zoom: camera.ratio } };
        },
        exportData: () => {
            const data = graph.export();
            const jsonString = JSON.stringify(data, null, 2);
            const blob = new Blob([jsonString], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `supernova-graph-${Date.now()}.json`;
            a.click();
            URL.revokeObjectURL(url);
        }
    };

    setIsReady(true);

    return () => {
      sigma.kill();
      setIsReady(false);
    };
  }, [graphData, containerRef]);

  useEffect(() => {
    const graph = graphRef.current;
    if (!graph || !isReady) return;

    switch (currentLayout) {
      case LayoutType.CIRCLE:
        circular.assign(graph);
        break;
      case LayoutType.GRID:
        const nodes = graph.nodes();
        const cols = Math.ceil(Math.sqrt(nodes.length));
        nodes.forEach((node, i) => {
          graph.setNodeAttribute(node, 'x', (i % cols) * 150);
          graph.setNodeAttribute(node, 'y', Math.floor(i / cols) * 150);
        });
        break;
      case LayoutType.RANDOM:
        graph.nodes().forEach(node => {
          graph.setNodeAttribute(node, 'x', Math.random() * 1000);
          graph.setNodeAttribute(node, 'y', Math.random() * 1000);
        });
        break;
      case LayoutType.FORCE_ATLAS:
        forceAtlas2.assign(graph, { iterations: 50 });
        break;
    }
  }, [currentLayout, isReady]);

  useEffect(() => {
    const sigma = sigmaRef.current;
    const graph = graphRef.current;
    if (!sigma || !graph || !isReady) return;

    if (!searchQuery) {
      sigma.setSetting("nodeReducer", null);
      sigma.setSetting("edgeReducer", null);
    } else {
      const lowerQuery = searchQuery.toLowerCase();
      sigma.setSetting("nodeReducer", (node, data) => {
        const matches = (data.label || "").toLowerCase().includes(lowerQuery);
        return matches
          ? { ...data, highlighted: true, color: "#00f3ff", zIndex: 10 }
          : { ...data, color: "rgba(255,255,255,0.05)", label: "" };
      });
       const firstMatch = graph.nodes().find(n =>
        (graph.getNodeAttribute(n, 'label') || '').toLowerCase().includes(lowerQuery)
      );
      if (firstMatch) apiRef.current?.focusNode(firstMatch);
    }
  }, [searchQuery, isReady]);

  return {
    graphData,
    currentLayout,
    searchQuery,
    selectedNode,
    contextMenu,
    isOracleOpen,
    isReady,
    api: apiRef.current,
    setGraphData,
    setCurrentLayout,
    setSearchQuery,
    setSelectedNode,
    setContextMenu,
    setIsOracleOpen,
  };
};
