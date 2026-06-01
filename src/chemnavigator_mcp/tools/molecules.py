"""Molecule pipeline MCP tools."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from chemnav.agents.builder import StructureBuilder
from chemnav.agents.designer import DesignerAgent
from chemnav.memory.database import MemoryBank
from chemnav.tools.molecule_validator import validate_smiles
from chemnavigator_mcp.config import resolve_db_path
from chemnavigator_mcp.serialization import failure, success


def register_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def validate_smiles_tool(smiles: str) -> str:
        """Validate a SMILES string and return molecular properties."""
        result = validate_smiles(smiles)
        return success(asdict(result))

    @mcp.tool()
    def build_structure(
        smiles: str,
        mol_id: str | None = None,
        db_path: str | None = None,
    ) -> str:
        """Build a 3D structure from SMILES and optionally update a database molecule."""
        db = resolve_db_path(db_path)
        memory = None
        if mol_id is not None:
            if not Path(db).exists():
                return failure(f"Database not found: {db}")
            memory = MemoryBank(db)

        builder = StructureBuilder(memory=memory)
        result = builder.build_molecule(smiles=smiles, mol_id=mol_id)
        if memory:
            memory.close()
        return success(result)

    @mcp.tool()
    def design_molecules(
        hypothesis: str,
        hypothesis_id: str | None = None,
        num_molecules: int = 10,
        context: str = "",
        strategy_type: str = "default",
        store_in_memory: bool = True,
        db_path: str | None = None,
    ) -> str:
        """Design molecules to test a hypothesis using the Designer agent (requires GOOGLE_API_KEY)."""
        db = resolve_db_path(db_path)
        if not Path(db).exists():
            return failure(f"Database not found: {db}")

        memory = MemoryBank(db)
        designer = DesignerAgent(memory)
        result = designer.design_molecules(
            hypothesis=hypothesis,
            hypothesis_id=hypothesis_id,
            num_molecules=num_molecules,
            context=context,
            strategy_type=strategy_type,
            store_in_memory=store_in_memory,
        )
        memory.close()

        return success(
            {
                "success": result.success,
                "hypothesis_id": result.hypothesis_id,
                "num_requested": result.num_requested,
                "num_generated": result.num_generated,
                "validation_rate": result.validation_rate,
                "diversity_score": result.diversity_score,
                "error": result.error,
                "molecules": result.molecules,
            }
        )
