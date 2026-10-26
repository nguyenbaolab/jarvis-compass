"""App nạp db.plan_store trong một tiến trình con sạch."""

import os
import subprocess
import sys
from pathlib import Path


def test_app_import_loads_plan_store() -> None:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import app, sys; raise SystemExit(0 if 'db.plan_store' in sys.modules else 1)",
        ],
        cwd=root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, (
        f"exit {completed.returncode}\n{completed.stdout}\n{completed.stderr}"
    )
