"""Discovery orchestration MCP tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from chemnavigator_mcp.config import resolve_db_path, resolve_work_dir
from chemnavigator_mcp.jobs import (
    cancel_discovery_job,
    get_discovery_job_status,
    start_discovery_job,
)
from chemnavigator_mcp.serialization import failure, success


def register_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def start_discovery(
        confirm: bool = False,
        max_cycles: int = 5,
        molecules_per_hypothesis: int = 10,
        enable_human_checkpoint: bool = False,
        db_path: str | None = None,
        work_dir: str | None = None,
    ) -> str:
        """Start a background autonomous discovery campaign. Requires confirm=true."""
        if not confirm:
            return failure(
                "Refusing to start discovery without confirm=true",
                "Discovery runs DFTB+ and LLM calls and may take hours.",
            )

        db = resolve_db_path(db_path)
        work = resolve_work_dir(work_dir)
        job = start_discovery_job(
            db_path=db,
            work_dir=work,
            max_cycles=max_cycles,
            molecules_per_hypothesis=molecules_per_hypothesis,
            enable_human_checkpoint=enable_human_checkpoint,
        )
        return success(job)

    @mcp.tool()
    def get_discovery_job(job_id: str, work_dir: str | None = None) -> str:
        """Poll status and report for a background discovery job."""
        status = get_discovery_job_status(job_id=job_id, work_dir=work_dir)
        if status.get("status") == "not_found":
            return failure(f"Job not found: {job_id}")
        return success(status)

    @mcp.tool()
    def cancel_discovery_job_tool(job_id: str, work_dir: str | None = None) -> str:
        """Cancel a running discovery job."""
        status = cancel_discovery_job(job_id=job_id, work_dir=work_dir)
        if status.get("status") == "not_found":
            return failure(f"Job not found: {job_id}")
        return success(status)
