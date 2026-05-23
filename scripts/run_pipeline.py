#!/usr/bin/env python3
"""Run the full A-part pipeline."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the full arXiv processing pipeline.")
    parser.add_argument("--category", default="cs.AI")
    parser.add_argument("--max-results", type=int, default=150)
    return parser.parse_args()


def run_step(command: list[str], cwd: Path) -> None:
    print("Running:", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]

    run_step(
        [
            sys.executable,
            str(project_root / "scripts" / "fetch_arxiv.py"),
            "--category",
            args.category,
            "--max-results",
            str(args.max_results),
        ],
        cwd=project_root,
    )
    run_step([sys.executable, str(project_root / "scripts" / "preprocess.py")], cwd=project_root)
    run_step([sys.executable, str(project_root / "scripts" / "build_index.py")], cwd=project_root)
    print("Pipeline completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
