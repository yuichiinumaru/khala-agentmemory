# OUT OF SCOPE TASKS

**Reason**: These tasks/features deviate from the core stack (Agno + SurrealDB + Gemini) or are currently deemed unnecessary/bloated.

## 1. Infrastructure
- **Redis Event Queue**: Use SurrealDB `jobs` table or Python in-memory queues instead.
- **PostgreSQL / Vector DBs (Chroma/Qdrant)**: SurrealDB handles vectors and structured data.
- **Local LLMs (Llama/Ollama)**: Strict dependency on Gemini API (Pro/Flash).
- **GPU Acceleration**: No local CUDA support planned.

## 2. Libraries
- **LangChain / LlamaIndex**: We use Agno (Phidata) exclusively.
- **Semantic Router (Python Lib)**: We build custom routing logic using Gemini Flash, not external heavy libraries, unless wrapped deeply.
- **Nano-Manus (Native)**: We adapted the *logic* (Regex parsing), but we do not install the library.

## 3. Features
- **Browser Automation (Selenium/Playwright for Agent)**: Use Agno's built-in web tools or API-based search.
- **Voice/Audio I/O**: Multimodal is text/image only for now.
