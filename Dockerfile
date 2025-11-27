
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install SurrealDB python client specifically if not in requirements
RUN pip install surrealdb fastmcp google-generativeai pydantic numpy

# Copy Khala source code
COPY . .

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Expose port for MCP/API (if we wrap it)
# FastMCP usually runs over stdio, but for Docker service we might need a bridge.
# For now, let's assume we might use a simple FastAPI wrapper OR just keep it running
# and let the backend exec into it? No, that's bad pattern.
# We will create a simple HTTP wrapper for the MCP or direct library usage.

# Let's create a simple HTTP server to expose the Khala Library functionality
# because calling MCP over network is tricky without an SSE transport.
# We will create a `http_server.py` in the next step.

CMD ["python", "scripts/http_server.py"]
