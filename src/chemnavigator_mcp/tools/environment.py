"""Environment check MCP tools."""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from chemnavigator_mcp.serialization import success
from chemnav.tools.dftb_executor import DFTBExecutor


def register_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def check_environment() -> str:
        """Check GOOGLE_API_KEY, conda environment, and DFTB+ availability."""
        executor = DFTBExecutor()
        google_key_set = bool(os.environ.get("GOOGLE_API_KEY"))
        return success(
            {
                "google_api_key_set": google_key_set,
                "conda_default_env": os.environ.get("CONDA_DEFAULT_ENV"),
                "conda_prefix": os.environ.get("CONDA_PREFIX"),
                "dftb_available": executor.has_dftb,
                "dftb_command": executor.dftb_command,
            }
        )
