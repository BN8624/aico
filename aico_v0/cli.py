# AICO v0 dry-run 하네스의 명령행 인터페이스를 제공한다.
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .fixtures import SCENARIO_NAMES
from .harness import run_dry_run


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the AICO v0 dry-run harness.")
    parser.add_argument("--mission", help="Mission text to write into the run directory.")
    parser.add_argument("--mission-path", help="Path to a mission.md file.")
    parser.add_argument("--scenario", choices=SCENARIO_NAMES, default="pass")
    parser.add_argument("--run-id", help="Deterministic run id. Defaults to a generated id.")
    parser.add_argument("--runs-root", default="runs", help="Directory that contains run folders.")
    args = parser.parse_args()

    result = run_dry_run(
        mission_text=args.mission,
        mission_path=Path(args.mission_path) if args.mission_path else None,
        scenario=args.scenario,
        run_id=args.run_id,
        runs_root=Path(args.runs_root),
    )
    print(
        json.dumps(
            {
                "run_id": result.run_id,
                "run_dir": str(result.run_dir),
                "status": result.status,
                "failure_type": result.failure_type,
                "api_call_count": result.api_call_count,
                "llm_call_count": result.llm_call_count,
            },
            ensure_ascii=False,
        )
    )
    return 0 if result.failure_type is None else 1
