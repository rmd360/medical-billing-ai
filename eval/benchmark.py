"""Run the deterministic baseline against a JSONL benchmark."""

import argparse
import json
from pathlib import Path

from baseline import assess_bill


def run_benchmark(path: Path) -> dict:
    """Return accuracy and confusion counts for a JSONL benchmark file."""
    total = correct = 0
    confusion = {"TP": 0, "TN": 0, "FP": 0, "FN": 0}

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        expected = record["expected_status"]
        predicted = assess_bill(record["bill"])["compliance_status"]
        total += 1
        correct += predicted == expected
        if expected == "Non-Compliant" and predicted == expected:
            confusion["TP"] += 1
        elif expected == "Compliant" and predicted == expected:
            confusion["TN"] += 1
        elif predicted == "Non-Compliant":
            confusion["FP"] += 1
        else:
            confusion["FN"] += 1

    return {
        "records": total,
        "correct": correct,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "confusion": confusion,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benchmark", type=Path)
    args = parser.parse_args()
    print(json.dumps(run_benchmark(args.benchmark), indent=2))


if __name__ == "__main__":
    main()