import { GoogleGenAI } from "@google/genai";
import { GraphData } from "../types";
import { summarizeGraphContext } from "../core/algorithms";
import Graph from "graphology";

// Initialize a temporary graphology instance just to run metrics if needed
const createTempGraph = (data: GraphData): Graph => {
  const g = new Graph();
  data.nodes.forEach(n => g.addNode(n.id, n));
  data.edges.forEach(e => g.addEdge(e.source, e.target));
  return g;
};

export const queryGraphOracle = async (
  query: string, 
  graphData: GraphData, 
  history: {role: string, content: string}[],
  viewportContext: string = ""
): Promise<string> => {
  try {
    const apiKey = process.env.API_KEY;
    if (!apiKey) return "Error: API Key is missing.";

    const ai = new GoogleGenAI({ apiKey });
    
    // Create rich context using Core Algorithms
    const graphInstance = createTempGraph(graphData);
    const globalContext = summarizeGraphContext(graphInstance);
    
    const combinedContext = `
${globalContext}

${viewportContext}
`;
    
    const systemInstruction = `
You are Supernova Oracle, an autonomous network analyst embedded in a high-performance cybersecurity dashboard.

CONTEXT:
${combinedContext}

AVAILABLE TOOLS (Execute by outputting JSON):
1. Focus on a Node: { "action": "FOCUS_NODE", "target": "NODE_ID" }
   - Use when user asks about specific entities.
2. Filter by Cluster: { "action": "FILTER_CLUSTER", "target": "CLUSTER_ID" }
   - Use when user asks about "Infra", "Social", "Finance", "Threats".
   - CLUSTER_IDS: 'c1' (Infra), 'c2' (Social), 'c3' (Finance), 'c4' (Threats).
3. Reset View: { "action": "RESET_VIEW" }
   - Use when user says "reset", "show all", "clear".

RULES:
1. Provide a brief, cyberpunk-style text analysis first.
2. Prioritize analyzing the VIEWPORT CONTEXT (what the user sees) if relevant.
3. If an action is required, append the JSON block at the very end.
4. Do not mention "JSON" or "Tools" in the text response. Just do it.
    `;

    const model = 'gemini-3-flash-preview';
    const response = await ai.models.generateContent({
      model,
      contents: query,
      config: { systemInstruction }
    });

    return response.text || "No response from Oracle.";
  } catch (error) {
    console.error("Gemini Error:", error);
    return "Oracle Malfunction: Neural Link Severed.";
  }
};