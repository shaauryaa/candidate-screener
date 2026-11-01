"""
Picks turns from the held-out interviews for a human to score blind, so
Sarah's scores can be compared with a person's in agreement.py.

Picks TURNS_PER_INTERVIEW turns per interview with a fixed seed and writes
<out>/human_labels.csv. Sarah's score, quote and reasoning are left out, and
the id is an opaque hash, because a name like resume_priya_bluffer_1 would
tell the labeller the persona. No API calls.

    python make_label_sheet.py
"""

import argparse
import csv
import glob
import hashlib
import json
import os
import random

SEED = 2026
HELD_OUT_RESUMES = ["resume_priya", "resume_shaurya"]
TURNS_PER_INTERVIEW = 2


def label_id(transcript_name: str, turn: int) -> str:
    """Same input, same id, so agreement.py can find the turn again."""
    return hashlib.sha256(f"{transcript_name}|{turn}".encode()).hexdigest()[:8]


def held_out_paths(out: str) -> list[str]:
    paths = []
    for resume in HELD_OUT_RESUMES:
        paths += sorted(glob.glob(os.path.join(out, "transcripts", f"{resume}_*.json")))
    return paths


def main():
    p = argparse.ArgumentParser(description="Write the blind human scoring sheet.")
    p.add_argument("--out", default="eval", help="same folder as eval_personas.py")
    args = p.parse_args()

    # Rerunning must never wipe scores a person has already typed in.
    sheet = os.path.join(args.out, "human_labels.csv")
    if os.path.exists(sheet):
        raise SystemExit(f"{sheet} already exists - delete it yourself if you really want a new sheet.")

    rng = random.Random(SEED)
    rows = []
    for path in held_out_paths(args.out):
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
        if "error" in record:
            print(f"Skipping {os.path.basename(path)}: it errored")
            continue
        name = os.path.splitext(os.path.basename(path))[0]
        for turn in rng.sample(range(len(record["turns"])), TURNS_PER_INTERVIEW):
            detail = record["turns"][turn]
            rows.append({"id": label_id(name, turn), "dimension": detail["dimension"],
                         "question": detail["question"], "answer": detail["answer"], "my_score": ""})

    rng.shuffle(rows)  # otherwise rows from one interview sit next to each other

    # utf-8-sig so Excel opens the file with the right characters.
    with open(sheet, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "dimension", "question", "answer", "my_score"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} turns written to: {sheet}")


if __name__ == "__main__":
    main()
