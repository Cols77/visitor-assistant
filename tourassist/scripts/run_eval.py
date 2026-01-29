from __future__ import annotations

import argparse
from pathlib import Path

from tourassist.app.eval.runner import run_eval
from tourassist.app.models.db import init_db


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--output", default="eval_output")
    args = parser.parse_args()

    init_db()
    summary = run_eval(args.tenant, Path(args.cases), Path(args.output))
    print(summary)


if __name__ == "__main__":
    main()
