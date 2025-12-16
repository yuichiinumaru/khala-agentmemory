const API_BASE = 'http://localhost:8000/api/v1';

export const AnalystService = {
  async getMetrics() {
    const response = await fetch(`${API_BASE}/analyst/metrics`);
    if (!response.ok) {
      throw new Error(response.statusText);
    }
    return response.json();
  },

  async explainGraph(query: string, viewContext: any) {
    const response = await fetch(`${API_BASE}/analyst/explain`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ query, view_context: viewContext })
    });

    if (!response.ok) {
      throw new Error(response.statusText);
    }
    return response.json();
  },

  async getTrace(jobId: string) {
      const response = await fetch(`${API_BASE}/agents/trace/${jobId}`);
      if (!response.ok) throw new Error(response.statusText);
      return response.json();
  }
};
