"""Background discovery job management for MCP."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from chemnavigator_mcp.config import project_root, resolve_work_dir


@dataclass
class _ActiveJob:
    job_id: str
    process: subprocess.Popen
    job_dir: Path


_active_jobs: dict[str, _ActiveJob] = {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def job_dir(work_dir: str, job_id: str) -> Path:
    return Path(work_dir) / "mcp_jobs" / job_id


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str))


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def start_discovery_job(
    db_path: str,
    work_dir: str,
    max_cycles: int,
    molecules_per_hypothesis: int,
    enable_human_checkpoint: bool,
) -> dict[str, Any]:
    job_id = uuid.uuid4().hex[:12]
    directory = job_dir(work_dir, job_id)
    directory.mkdir(parents=True, exist_ok=True)

    config = {
        "job_id": job_id,
        "db_path": db_path,
        "work_dir": work_dir,
        "max_cycles": max_cycles,
        "molecules_per_hypothesis": molecules_per_hypothesis,
        "enable_human_checkpoint": enable_human_checkpoint,
        "created_at": _utc_now(),
    }
    _write_json(directory / "config.json", config)
    _write_json(
        directory / "status.json",
        {
            "job_id": job_id,
            "status": "pending",
            "created_at": config["created_at"],
            "updated_at": config["created_at"],
        },
    )

    cmd = [
        sys.executable,
        "-m",
        "chemnavigator_mcp.run_discovery",
        "--job-id",
        job_id,
        "--work-dir",
        work_dir,
    ]
    process = subprocess.Popen(
        cmd,
        cwd=str(project_root()),
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    _active_jobs[job_id] = _ActiveJob(job_id=job_id, process=process, job_dir=directory)

    return {
        "job_id": job_id,
        "status": "running",
        "job_dir": str(directory),
        "poll_with": "get_discovery_job",
    }


def get_discovery_job_status(job_id: str, work_dir: str | None = None) -> dict[str, Any]:
    work = resolve_work_dir(work_dir)
    directory = job_dir(work, job_id)
    status_path = directory / "status.json"

    if not status_path.exists():
        return {"job_id": job_id, "status": "not_found"}

    status = _read_json(status_path) or {"job_id": job_id, "status": "unknown"}

    active = _active_jobs.get(job_id)
    if active and active.process.poll() is not None and status.get("status") == "running":
        exit_code = active.process.returncode
        if exit_code != 0 and status.get("status") not in {"completed", "failed", "cancelled"}:
            status["status"] = "failed"
            status["exit_code"] = exit_code
            status["updated_at"] = _utc_now()
            _write_json(status_path, status)

    report = _read_json(directory / "report.json")
    if report:
        status["report"] = report

    log_path = directory / "runner.log"
    if log_path.exists():
        log_text = log_path.read_text()
        status["log_tail"] = log_text[-4000:] if len(log_text) > 4000 else log_text

    return status


def cancel_discovery_job(job_id: str, work_dir: str | None = None) -> dict[str, Any]:
    work = resolve_work_dir(work_dir)
    directory = job_dir(work, job_id)
    status_path = directory / "status.json"

    active = _active_jobs.get(job_id)
    if active and active.process.poll() is None:
        active.process.terminate()
        try:
            active.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            active.process.kill()
        status = _read_json(status_path) or {"job_id": job_id}
        status["status"] = "cancelled"
        status["updated_at"] = _utc_now()
        _write_json(status_path, status)
        return status

    status = _read_json(status_path)
    if status is None:
        return {"job_id": job_id, "status": "not_found"}

    if status.get("status") in {"completed", "failed", "cancelled"}:
        return status

    status["status"] = "cancelled"
    status["updated_at"] = _utc_now()
    _write_json(status_path, status)
    return status
