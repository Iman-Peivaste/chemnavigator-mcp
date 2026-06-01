"""Internal subprocess runner for background discovery jobs."""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ChemNavigator discovery job for MCP")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--work-dir", required=True)
    args = parser.parse_args()

    job_directory = Path(args.work_dir) / "mcp_jobs" / args.job_id
    config_path = job_directory / "config.json"
    status_path = job_directory / "status.json"
    report_path = job_directory / "report.json"
    log_path = job_directory / "runner.log"

    if not config_path.exists():
        print(f"Missing config: {config_path}", file=sys.stderr)
        return 1

    config = json.loads(config_path.read_text())
    log_file = log_path.open("w", encoding="utf-8")

    def log(message: str) -> None:
        log_file.write(message + "\n")
        log_file.flush()
        print(message)

    status = {
        "job_id": args.job_id,
        "status": "running",
        "updated_at": _utc_now(),
    }
    status_path.write_text(json.dumps(status, indent=2))

    try:
        from chemnav.orchestrator.orchestrator import ChemNavigator

        log(f"Starting discovery job {args.job_id}")
        navigator = ChemNavigator(
            db_path=config["db_path"],
            work_dir=config["work_dir"],
        )
        report = navigator.run_discovery(
            max_cycles=config["max_cycles"],
            molecules_per_hypothesis=config["molecules_per_hypothesis"],
            enable_human_checkpoint=config["enable_human_checkpoint"],
            save_report=True,
        )
        navigator.close()

        report_dict = {
            "success": report.success,
            "total_cycles": report.total_cycles,
            "stop_reason": report.stop_reason,
            "confirmed_hypotheses": report.confirmed_hypotheses,
            "design_rules": report.design_rules,
            "total_molecules": report.total_molecules,
            "total_calculations": report.total_calculations,
            "calculation_success_rate": report.calculation_success_rate,
            "total_duration_seconds": report.total_duration_seconds,
            "cycle_summaries": report.cycle_summaries,
        }
        report_path.write_text(json.dumps(report_dict, indent=2, default=str))

        status = {
            "job_id": args.job_id,
            "status": "completed",
            "updated_at": _utc_now(),
            "report_path": str(report_path),
        }
        status_path.write_text(json.dumps(status, indent=2))
        log("Discovery job completed")
        return 0
    except Exception as exc:
        log(f"Discovery job failed: {exc}")
        log(traceback.format_exc())
        status = {
            "job_id": args.job_id,
            "status": "failed",
            "updated_at": _utc_now(),
            "error": str(exc),
        }
        status_path.write_text(json.dumps(status, indent=2))
        return 1
    finally:
        log_file.close()


if __name__ == "__main__":
    raise SystemExit(main())
