export interface GraphNode {
  id: string;
  label: string;
  x: number;
  y: number;
  size: number;
  color: string;
  cluster?: string;
  [key: string]: any;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  color?: string;
  size?: number;
  type?: string;
  [key: string]: any;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export enum LayoutType {
  FORCE_ATLAS = 'force_atlas',
  CIRCLE = 'circle',
  GRID = 'grid',
  RANDOM = 'random'
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'model';
  content: string;
  timestamp: number;
}
