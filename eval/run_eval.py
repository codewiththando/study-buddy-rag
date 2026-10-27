"""Measure how often retrieval finds the right page for each test question.

Usage (from the project root):
    python eval/run_eval.py
"""

import json
import sys
from pathlib import Path

# Make `app` importable when running this file directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.store import search  # noqa: E402

QUESTIONS_FILE = Path(__file__).parent / "questions.json"
K = 5  # how many chunks retrieval returns
MODE = sys.argv[1] if len(sys.argv) > 1 else "hybrid"


def main() -> None:
    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    hit_at_1 = 0
    hit_at_k = 0
    misses = []

    for item in questions:
        hits = search(item["question"], k=K, mode=MODE)
        expected = set(item["pages"])

        # rank of the first retrieved chunk from the right source AND right page
        rank = None
        for position, hit in enumerate(hits, start=1):
            if hit["source"] == item["source"] and hit["page"] in expected:
                rank = position
                break

        if rank == 1:
            hit_at_1 += 1
        if rank is not None:
            hit_at_k += 1
        else:
            misses.append(
                {
                    "question": item["question"],
                    "expected": sorted(expected),
                    "got": [f"{h['source']} p{h['page']}" for h in hits],
                }
            )

    total = len(questions)
    print(f"Mode: {MODE}")
    print(f"Questions: {total}")
    print(f"Hit@1: {hit_at_1}/{total} ({hit_at_1 / total:.0%})  - right page was the top result")
    print(f"Hit@{K}: {hit_at_k}/{total} ({hit_at_k / total:.0%})  - right page was in the top {K}")

    if misses:
        print("\nMisses:")
        for miss in misses:
            print(f"  Q: {miss['question']}")
            print(f"     expected pages {miss['expected']}, got {miss['got']}")


if __name__ == "__main__":
    main()