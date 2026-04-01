"""
MCP Server entry point for Docker deployment.

For local/uvx use, the entry point is deutsche_rechtsprechung_mcp.server:main
"""

import os
import sys

# Add parent's parent to path so the package can be found when running from Docker
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# In Docker, always use HTTP transport
os.environ.setdefault("MCP_TRANSPORT", "streamable-http")

from deutsche_rechtsprechung_mcp.server import main

if __name__ == "__main__":
    main()
