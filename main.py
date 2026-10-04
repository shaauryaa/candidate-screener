"""
Entry point. Prepares the interview, runs it in the terminal, then scores it.

The dialogue itself is the Interview state machine in interview_session.py
(judge -> maybe follow-up -> record). This file only feeds it answers,
prints what it says back, and handles scoring and the report.
"""

import argparse
import statistics

import llm
import prep
from candidate import HumanCandidate
from interview import EXCLUDED_ATTRIBUTES, score_dimension
from interview_session import MAX_FOLLOWUPS
from schemas import Evidence
from report import write_html_report


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

    prepared = prep.prepare(args.jd, args.resume)
    interview = prep.build_interview(prepared)

    print(f"Candidate: {prepared['candidate_name']}")
    print(f"Role: {prepared['role']} ({prepared['seniority']})")
    print()

    candidate = HumanCandidate()
    judge_times_ms: list[float] = []  # time spent inside judge(), one entry per judged answer

    text = interview.start()
    new_question = True
    while not interview.done:
        if new_question:
            question = interview.questions[interview.index]
            print(f"\n--- {question.dimension} ---")
            print(f"(grounded in: {question.grounded_project})")
            question_judge_ms = 0.0

        answer = candidate.get_answer(f"{text}\n> ")
        turns_before = len(interview.transcript)
        text = interview.on_answer(answer)

        if interview.last_judge_ms is not None:
            judge_times_ms.append(interview.last_judge_ms)
            question_judge_ms += interview.last_judge_ms

        # A new transcript turn means this question is finished; otherwise
        # `text` is a follow-up for the same question.
        new_question = len(interview.transcript) > turns_before
        if new_question:
            turn = interview.transcript[-1]
            print(f"  [judge time: {question_judge_ms:.0f} ms, {turn.followups_asked} follow-up(s)]")
        elif interview.last_verdict.missing == Evidence.REPEAT_REQUEST:
            print("  [repeat requested]")
        elif interview.last_verdict.missing == Evidence.WAIT_REQUEST:
            print("  [wait requested]")
        else:
            print(f"  [probing: {interview.last_verdict.missing.value}]")

    transcript = interview.transcript
    scores = [score_dimension(dim, turn) for dim, turn in zip(interview.dimensions, transcript)]

    print("\n" + "=" * 70)
    print("SCORECARD")
    print("=" * 70)
    for s in scores:
        verified = "verified" if s.quote_verified else "UNSUPPORTED"
        print(f"\n{s.dimension}: {s.score}/5  [{verified}]")
        print(f'  quote: "{s.quote}"')
        print(f"  reasoning: {s.reasoning}")

    if judge_times_ms:
        timing_note = (f"Time inside judge() per judged answer: p50 {statistics.median(judge_times_ms):.0f} ms "
                       f"(n={len(judge_times_ms)} judge calls). Typed interview, so there are no speech timings.")
    else:
        timing_note = "Time inside judge() per judged answer: not measured yet"
    print("\n" + timing_note)

    write_html_report(args.out, prepared["candidate_name"], prepared["role"], scores, transcript, [timing_note], llm.MOCK)
    print(f"HTML report written to: {args.out}")


if __name__ == "__main__":
    main()
