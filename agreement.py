"""
Compares Sarah's scores with the human scores in <out>/human_labels.csv and
writes <out>/agreement.md. Every number gives its n. If a teammate_score column
is filled in, it also compares the two humans. No API calls.

    python agreement.py
"""

import argparse
import csv
import json
import math
import os

from sklearn.metrics import cohen_kappa_score

from make_label_sheet import held_out_paths, label_id

SCORES = [1, 2, 3, 4, 5]


def valid_score(cell: str | None) -> int | None:
    """A whole score from 1 to 5, or None for an empty or unusable cell."""
    cell = (cell or "").strip()
    return int(cell) if cell in ("1", "2", "3", "4", "5") else None


def sarah_scores(out: str) -> dict[str, int]:
    scores = {}
    for path in held_out_paths(out):
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
        name = os.path.splitext(os.path.basename(path))[0]
        for turn, score in enumerate(record.get("scores", [])):
            scores[label_id(name, turn)] = score["score"]
    return scores


def metric_lines(title: str, first: list[int], second: list[int]) -> list[str]:
    n = len(first)
    if n == 0:
        return [f"## {title}", "not measured yet", ""]
    exact = sum(a == b for a, b in zip(first, second))
    within_1 = sum(abs(a - b) <= 1 for a, b in zip(first, second))
    # Passing every label keeps the 5-point scale even if a score never appears.
    # Kappa is undefined when both sides give one identical score on every turn.
    kappa = cohen_kappa_score(first, second, weights="quadratic", labels=SCORES)
    kappa_text = "undefined" if math.isnan(kappa) else f"{kappa:.3f}"
    return [f"## {title}",
            f"- Exact agreement: {exact}/{n} = {exact / n:.1%}",
            f"- Within-1 agreement: {within_1}/{n} = {within_1 / n:.1%}",
            f"- Quadratic-weighted Cohen's kappa: {kappa_text} (n={n})",
            ""]


def main():
    p = argparse.ArgumentParser(description="Measure agreement between Sarah and human scorers.")
    p.add_argument("--out", default="eval", help="same folder as eval_personas.py")
    args = p.parse_args()

    # utf-8-sig also reads files without the marker, so either way of saving works.
    with open(os.path.join(args.out, "human_labels.csv"), encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    sarah = sarah_scores(args.out)
    pairs = [(valid_score(r.get("my_score")), sarah.get(r["id"])) for r in rows]
    scored = [(mine, hers) for mine, hers in pairs if mine is not None and hers is not None]
    unmatched = sum(mine is not None and hers is None for mine, hers in pairs)

    lines = ["# Human agreement", "",
             f"Rows in the sheet: {len(rows)}. Rows with a usable my_score: {len(scored) + unmatched}.", ""]
    if unmatched:
        lines += [f"WARNING: {unmatched} scored rows had no matching Sarah score and were left out.", ""]
    lines += metric_lines("Sarah vs human", [m for m, _ in scored], [h for _, h in scored])

    both = [(valid_score(r.get("my_score")), valid_score(r.get("teammate_score"))) for r in rows]
    both = [(a, b) for a, b in both if a is not None and b is not None]
    if both:
        lines += metric_lines("Human vs human", [a for a, _ in both], [b for _, b in both])

    path = os.path.join(args.out, "agreement.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Agreement written to: {path}")


if __name__ == "__main__":
    main()
