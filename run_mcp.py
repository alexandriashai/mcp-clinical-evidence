#!/usr/bin/env python3
"""Run the MCP server on port 8111."""

from app.mcp_server import mcp

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
