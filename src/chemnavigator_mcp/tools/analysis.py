"""Analysis MCP tools."""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from chemnav.agents.scientist import ScientistAgent
from chemnav.memory.database import MemoryBank
from chemnav.tools.feature_extractor import extract_features_from_memory
from chemnav.tools.statistical_analyzer import analyze_from_memory
from chemnav.tools.substructure_discovery import analyze_champion_molecules
from chemnavigator_mcp.config import resolve_db_path
from chemnavigator_mcp.serialization import failure, success


def register_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def extract_features(
        db_path: str | None = None,
        max_molecules: int = 50,
    ) -> str:
        """Extract molecular features from molecules with successful calculations."""
        db = resolve_db_path(db_path)
        if not Path(db).exists():
            return failure(f"Database not found: {db}")

        memory = MemoryBank(db)
        features = extract_features_from_memory(memory, use_v2=True)
        memory.close()

        serialized = []
        for item in features[:max_molecules]:
            if hasattr(item, "to_dict"):
                serialized.append(item.to_dict())
            elif hasattr(item, "__dict__"):
                serialized.append(vars(item))
            else:
                serialized.append(item)

        return success(
            {
                "n_molecules": len(features),
                "returned": len(serialized),
                "features": serialized,
            }
        )

    @mcp.tool()
    def run_statistical_analysis(db_path: str | None = None) -> str:
        """Run scipy-based correlation analysis on molecules with calculations."""
        db = resolve_db_path(db_path)
        if not Path(db).exists():
            return failure(f"Database not found: {db}")

        memory = MemoryBank(db)
        results = analyze_from_memory(memory)
        memory.close()

        significant = [c.to_dict() for c in results.get_significant_correlations()]
        top = [c.to_dict() for c in results.get_top_correlations(n=20)]
        return success(
            {
                "n_molecules": results.n_molecules,
                "n_correlations": len(results.correlations),
                "n_group_comparisons": len(results.group_comparisons),
                "summary_stats": results.summary_stats,
                "significant_correlations": significant,
                "top_correlations": top,
            }
        )

    @mcp.tool()
    def analyze_and_hypothesize(
        db_path: str | None = None,
        store_hypotheses: bool = True,
        max_hypotheses: int = 5,
    ) -> str:
        """Run Scientist agent: statistical analysis plus LLM hypothesis generation."""
        db = resolve_db_path(db_path)
        if not Path(db).exists():
            return failure(f"Database not found: {db}")

        memory = MemoryBank(db)
        scientist = ScientistAgent(memory)
        result = scientist.analyze_and_hypothesize(
            store_hypotheses=store_hypotheses,
            max_hypotheses=max_hypotheses,
        )
        memory.close()

        return success(
            {
                "success": result.success,
                "n_molecules_analyzed": result.n_molecules_analyzed,
                "n_correlations_found": result.n_correlations_found,
                "n_hypotheses_generated": result.n_hypotheses_generated,
                "analysis_summary": result.analysis_summary,
                "error": result.error,
                "hypotheses": [h.to_dict() for h in result.hypotheses],
            }
        )

    @mcp.tool()
    def analyze_champions(
        property_name: str = "band_gap",
        top_n: int = 10,
        db_path: str | None = None,
    ) -> str:
        """Find substructures enriched in top-performing molecules vs baseline."""
        if property_name not in {"band_gap", "homo", "lumo"}:
            return failure(
                f"Invalid property_name: {property_name}",
                "Use band_gap, homo, or lumo.",
            )

        db = resolve_db_path(db_path)
        if not Path(db).exists():
            return failure(f"Database not found: {db}")

        memory = MemoryBank(db)
        calcs = memory.get_successful_calculations()
        if not calcs:
            memory.close()
            return failure("No successful calculations found in database.")

        molecules_data = []
        for calc in calcs:
            mol = memory.get_molecule(calc["mol_id"])
            if not mol:
                continue
            properties = calc.get("properties") or {}
            prop_value = properties.get(property_name)
            if prop_value is not None:
                molecules_data.append(
                    {
                        "smiles": mol["smiles"],
                        "property_value": prop_value,
                        "mol_id": mol["mol_id"],
                    }
                )

        memory.close()
        if len(molecules_data) < 4:
            return failure(
                f"Need at least 4 molecules with {property_name}; found {len(molecules_data)}."
            )

        if property_name == "band_gap":
            molecules_data.sort(key=lambda x: x["property_value"])
        elif property_name == "homo":
            molecules_data.sort(key=lambda x: x["property_value"], reverse=True)
        else:
            molecules_data.sort(key=lambda x: x["property_value"])
        champions = [m["smiles"] for m in molecules_data[:top_n]]
        baseline = [m["smiles"] for m in molecules_data[top_n:]]

        if not baseline:
            midpoint = max(1, len(molecules_data) // 2)
            champions = [m["smiles"] for m in molecules_data[:midpoint]]
            baseline = [m["smiles"] for m in molecules_data[midpoint:]]

        analysis = analyze_champion_molecules(champions, baseline)
        analysis["property"] = property_name
        analysis["top_n"] = top_n
        analysis["champion_molecules"] = molecules_data[:top_n]
        return success(analysis)
