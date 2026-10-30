from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.reports import run_evaluation  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=Path("data/fixtures/expected/rag_documents.json"))
    parser.add_argument("--questions", type=Path, default=Path("data/fixtures/expected/questions.json"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/offline-ci/metrics.json"))
    args = parser.parse_args()
    print(json.dumps(run_evaluation(args.corpus, args.questions, args.output), indent=2))


if __name__ == "__main__":
    main()

