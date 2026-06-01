"""Database MCP tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from mcp.server.fastmcp import FastMCP

from chemnav.memory.database import MemoryBank
from chemnav.scripts.init_database import select_seed_molecules
from chemnavigator_mcp.config import resolve_db_path
from chemnavigator_mcp.serialization import failure, success


def register_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def init_database(
        csv_path: str,
        db_path: str | None = None,
        n: int = 50,
    ) -> str:
        """Initialize the ChemNavigator SQLite database with stratified seed molecules."""
        db = resolve_db_path(db_path)
        csv = Path(csv_path)
        if not csv.exists():
            return failure(f"CSV not found: {csv_path}", "Provide an absolute path to seed molecules CSV.")

        df = pd.read_csv(csv, encoding="utf-8-sig")
        seeds = select_seed_molecules(df, n)
        memory = MemoryBank(db)

        stored = 0
        errors: list[str] = []
        for _, row in seeds.iterrows():
            try:
                memory.store_molecule(
                    smiles=row["SMILES"],
                    source="seed",
                    her_experimental=row["HER"],
                    mol_id=f"seed_{row['ID']:04d}",
                    molecular_weight=row.get("mol_weight"),
                    num_aromatic_rings=int(row.get("num_aromatic_rings", 0)),
                )
                stored += 1
            except Exception as exc:
                errors.append(f"ID {row['ID']}: {exc}")

        stats = memory.get_statistics()
        memory.close()
        return success(
            {
                "db_path": db,
                "requested": n,
                "stored": stored,
                "failed": len(errors),
                "errors": errors[:20],
                "statistics": stats,
            }
        )

    @mcp.tool()
    def get_database_stats(db_path: str | None = None) -> str:
        """Return molecule, calculation, hypothesis, and design rule counts."""
        db = resolve_db_path(db_path)
        if not Path(db).exists():
            return failure(f"Database not found: {db}", "Run init_database first.")
        memory = MemoryBank(db)
        stats = memory.get_statistics()
        memory.close()
        return success({"db_path": db, "statistics": stats})

    @mcp.tool()
    def query_molecules(
        filters_json: str | None = None,
        limit: int | None = None,
        order_by: str | None = None,
        order_desc: bool = False,
        db_path: str | None = None,
    ) -> str:
        """Query molecules with optional JSON filters, ordering, and limit."""
        db = resolve_db_path(db_path)
        filters: dict[str, Any] | None = None
        if filters_json:
            filters = json.loads(filters_json)

        memory = MemoryBank(db)
        molecules = memory.query_molecules(
            filters=filters,
            limit=limit,
            order_by=order_by,
            order_desc=order_desc,
        )
        memory.close()
        return success({"db_path": db, "count": len(molecules), "molecules": molecules})

    @mcp.tool()
    def get_molecule(mol_id: str, db_path: str | None = None) -> str:
        """Fetch a single molecule record by ID."""
        db = resolve_db_path(db_path)
        memory = MemoryBank(db)
        molecule = memory.get_molecule(mol_id)
        memory.close()
        if molecule is None:
            return failure(f"Molecule not found: {mol_id}")
        return success({"molecule": molecule})

    @mcp.tool()
    def get_calculations(mol_id: str, db_path: str | None = None) -> str:
        """List DFTB+ calculations for a molecule."""
        db = resolve_db_path(db_path)
        memory = MemoryBank(db)
        calculations = memory.get_calculations_for_molecule(mol_id)
        memory.close()
        return success({"mol_id": mol_id, "count": len(calculations), "calculations": calculations})

    @mcp.tool()
    def get_successful_calculations(db_path: str | None = None) -> str:
        """List all successful calculations in the database."""
        db = resolve_db_path(db_path)
        memory = MemoryBank(db)
        calculations = memory.get_successful_calculations()
        memory.close()
        return success({"count": len(calculations), "calculations": calculations})

    @mcp.tool()
    def list_hypotheses(status: str = "untested", db_path: str | None = None) -> str:
        """List hypotheses filtered by status (untested, confirmed, rejected, uncertain)."""
        db = resolve_db_path(db_path)
        memory = MemoryBank(db)
        hypotheses = memory.get_hypotheses_by_status(status)
        memory.close()
        return success({"status": status, "count": len(hypotheses), "hypotheses": hypotheses})

    @mcp.tool()
    def list_design_rules(db_path: str | None = None) -> str:
        """List design rules stored in the database."""
        db = resolve_db_path(db_path)
        memory = MemoryBank(db)
        rules = memory.get_all_design_rules()
        memory.close()
        return success({"count": len(rules), "design_rules": rules})

    @mcp.tool()
    def get_action_log(cycle_number: int | None = None, db_path: str | None = None) -> str:
        """Return orchestrator action log entries, optionally filtered by cycle."""
        db = resolve_db_path(db_path)
        memory = MemoryBank(db)
        entries = memory.get_action_log(cycle_number=cycle_number)
        memory.close()
        return success({"cycle_number": cycle_number, "count": len(entries), "entries": entries})
