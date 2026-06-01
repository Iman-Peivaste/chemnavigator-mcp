"""ChemNavigator MCP server entrypoint (stdio transport)."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from chemnavigator_mcp.tools import analysis, database, environment, molecules, orchestration, quantum

mcp = FastMCP(
    "chemnavigator",
    instructions=(
        "ChemNavigator MCP server for organic photocatalyst design-rule discovery. "
        "Use check_environment before expensive LLM or DFTB+ operations. "
        "Discovery and quantum tools require confirm=true."
    ),
)

environment.register_tools(mcp)
database.register_tools(mcp)
analysis.register_tools(mcp)
molecules.register_tools(mcp)
quantum.register_tools(mcp)
orchestration.register_tools(mcp)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
