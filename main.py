"""
Entry point. Wires the pieces together and runs the interview.

The core loop (judge -> maybe follow-up -> record) is kept inline here on
purpose, exactly as designed, instead of being hidden inside a helper -
it's the part of this project you have to be able to explain line by line.
"""

import argparse
import statistics
import time

import llm
import parsing
from candidate import HumanCandidate
from interview import (
    EXCLUDED_ATTRIBUTES,
    generate_dimensions,
    generate_followup,
    generate_question,
    judge,
    score_dimension,
)
from report import write_html_report
from schemas import TranscriptTurn

MAX_FOLLOWUPS = 2  # deliberate cap: two probes is enough to separate a vague
# answer from a genuinely thin one, without turning every question into an
# interrogation. See README for the full rationale.


def parse_args():
    p = argparse.ArgumentParser(description="AI candidate screening agent (text-only prototype).")
    p.add_argument("--jd", default="data/job_description.txt", help="path to job description (.txt)")
    p.add_argument("--resume", default="data/resume_alex.txt", help="path to resume (.txt or .pdf)")
    p.add_argument("--mock", action="store_true", help="run with zero API calls, using canned/heuristic logic")
    p.add_argument("--out", default="report.html", help="path to write the HTML report to")
    return p.parse_args()


def main():
    args = parse_args()
    llm.MOCK = args.mock

    print("=" * 70)
    print("AI CANDIDATE SCREENING AGENT" + ("  [MOCK MODE - no API calls]" if llm.MOCK else ""))
    print("=" * 70)
    print(f"Excluded from scoring (by design): {', '.join(EXCLUDED_ATTRIBUTES)}")
    print(f"Max follow-ups per question: {MAX_FOLLOWUPS}")
    print()

    jd = parsing.parse_job_description(args.jd)
    resume = parsing.parse_resume(args.resume)
    if not resume.projects:
        raise SystemExit(f"No projects found in {args.resume} - can't ground questions in nothing.")

    print(f"Candidate: {resume.candidate_name}")
    print(f"Role: {jd.title} ({jd.seniority})")
    print()

    dimensions = generate_dimensions(jd)
    questions = [
        generate_question(dim, resume.projects[i % len(resume.projects)])
        for i, dim in enumerate(dimensions)
    ]

    candidate = HumanCandidate()
    transcript: list[TranscriptTurn] = []
    latencies_ms: list[float] = []

    for dimension, question in zip(dimensions, questions):
        print(f"\n--- {dimension.name} ---")
        print(f"(grounded in: {question.grounded_project})")
        start = time.perf_counter()

        answer = candidate.get_answer(f"{question.text}\n> ")

        followups_asked = 0
        for _ in range(MAX_FOLLOWUPS):
            verdict = judge(question, dimension, answer)
            if verdict.sufficient:
                break
            print(f"  [probing: {verdict.missing.value}]")
            followup_text = generate_followup(verdict.missing)
            more = candidate.get_answer(f"{followup_text}\n> ")
            answer = answer + " " + more
            followups_asked += 1

        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies_ms.append(elapsed_ms)
        print(f"  [{elapsed_ms:.0f} ms, {followups_asked} follow-up(s)]")

        transcript.append(TranscriptTurn(
            dimension=dimension.name, question=question.text,
            answer=answer, followups_asked=followups_asked,
        ))

    scores = [score_dimension(dim, turn) for dim, turn in zip(dimensions, transcript)]

    print("\n" + "=" * 70)
    print("SCORECARD")
    print("=" * 70)
    for s in scores:
        verified = "verified" if s.quote_verified else "UNSUPPORTED"
        print(f"\n{s.dimension}: {s.score}/5  [{verified}]")
        print(f'  quote: "{s.quote}"')
        print(f"  reasoning: {s.reasoning}")

    p50_ms = statistics.median(latencies_ms) if latencies_ms else 0.0
    print(f"\np50 turn latency: {p50_ms:.0f} ms")

    write_html_report(args.out, resume.candidate_name, jd.title, scores, transcript, p50_ms, llm.MOCK)
    print(f"HTML report written to: {args.out}")


if __name__ == "__main__":
    main()
