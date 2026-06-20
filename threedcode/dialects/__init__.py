"""Per-dialect executability runners. Each 3D-code type plugs in how to RUN a project's
code in its runtime(s) and report pass/fail. Runs on the CONTRIBUTOR's machine, in the
contributor's own runtimes — never sends data anywhere.
"""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from . import blender_python


def run_dialect(dialect: str, project_dir: Path, meta: dict, cfg: Config) -> dict:
    """Execute the project in its runtime(s); return {runtime: {status, ...}}."""
    code_file = project_dir / meta["code"]["file"]
    if dialect == "blender_python":
        return blender_python.run(code_file, {"5.0": cfg.blender_5_0, "5.1": cfg.blender_5_1})
    # cadquery / freecad / openscad adapters land here next.
    return {"runtime": {"status": "unsupported", "error": f"no exec runner for dialect '{dialect}'"}}
