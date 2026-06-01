"""Configuration defaults for the ChemNavigator MCP server."""

import os
from pathlib import Path


def project_root() -> Path:
    """ChemNavigator project directory (database, seed CSV, calculations)."""
    env_root = os.environ.get("CHEMNAV_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return Path.cwd().resolve()


def default_db_path() -> str:
    env_path = os.environ.get("CHEMNAV_DB_PATH")
    if env_path:
        return env_path
    return str(project_root() / "chemnav.db")


def default_work_dir() -> str:
    env_path = os.environ.get("CHEMNAV_WORK_DIR")
    if env_path:
        return env_path
    return str(project_root() / "calculations")


def resolve_db_path(db_path: str | None = None) -> str:
    return db_path or default_db_path()


def resolve_work_dir(work_dir: str | None = None) -> str:
    return work_dir or default_work_dir()
