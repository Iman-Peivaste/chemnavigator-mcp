"""Quantum calculation MCP tools."""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from chemnav.agents.calculator import QuantumCalculator
from chemnav.memory.database import MemoryBank
from chemnavigator_mcp.config import resolve_db_path, resolve_work_dir
from chemnavigator_mcp.serialization import failure, success


def register_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def run_calculation(
        mol_id: str,
        confirm: bool = False,
        force_recalculate: bool = False,
        db_path: str | None = None,
        work_dir: str | None = None,
    ) -> str:
        """Run a DFTB+ calculation for one molecule. Requires confirm=true."""
        if not confirm:
            return failure(
                "Refusing to run DFTB+ without confirm=true",
                "Set confirm=true to acknowledge this may take several minutes.",
            )

        db = resolve_db_path(db_path)
        work = resolve_work_dir(work_dir)
        if not Path(db).exists():
            return failure(f"Database not found: {db}")

        memory = MemoryBank(db)
        calculator = QuantumCalculator(memory=memory, work_base_dir=work)
        result = calculator.calculate(mol_id=mol_id, force_recalculate=force_recalculate)
        memory.close()
        return success(result)

    @mcp.tool()
    def run_calculation_batch(
        mol_ids: list[str],
        confirm: bool = False,
        stop_on_failure: bool = False,
        db_path: str | None = None,
        work_dir: str | None = None,
    ) -> str:
        """Run DFTB+ calculations for multiple molecules. Requires confirm=true."""
        if not confirm:
            return failure(
                "Refusing to run DFTB+ batch without confirm=true",
                "Set confirm=true to acknowledge this may take a long time.",
            )
        if not mol_ids:
            return failure("mol_ids must be a non-empty list.")

        db = resolve_db_path(db_path)
        work = resolve_work_dir(work_dir)
        if not Path(db).exists():
            return failure(f"Database not found: {db}")

        memory = MemoryBank(db)
        calculator = QuantumCalculator(memory=memory, work_base_dir=work)
        result = calculator.calculate_batch(
            mol_ids=mol_ids,
            stop_on_failure=stop_on_failure,
        )
        memory.close()
        return success(result)
