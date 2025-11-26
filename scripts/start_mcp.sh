#!/bin/bash
# Start the Khala MCP Server

# Ensure we are in the project root
cd "$(dirname "$0")/.."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "Please edit .env with your API keys."
fi

# Run the server
echo "Starting Khala MCP Server..."
python -m khala.interface.mcp.server
