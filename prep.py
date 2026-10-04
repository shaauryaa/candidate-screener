"""
Everything that has to happen before the first question is asked: parse the
JD and resume, build the rubric, and write one grounded question per
dimension. These are the slow LLM calls, so they can be done ahead of time
and saved to prepared_interview.json - loading that file back needs zero
API calls, so the interview itself can start instantly.

    python prep.py                 # writes prepared_interview.json
    python prep.py --mock          # same, with zero API calls
"""

import argparse
import json

import llm
import parsing
from interview import generate_dimensions, generate_question
from interview_session import Interview
from schemas import Dimension, Question


def prepare(jd_path: str, resume_path: str) -> dict:
    jd = parsing.parse_job_description(jd_path)
    resume = parsing.parse_resume(resume_path)
    if not resume.projects:
        raise SystemExit(f"No projects found in {resume_path} - can't ground questions in nothing.")

    dimensions = generate_dimensions(jd)
    questions = [
        generate_question(dim, resume.projects[i % len(resume.projects)])
        for i, dim in enumerate(dimensions)
    ]
    return {
        "candidate_name": resume.candidate_name,
        "role": jd.title,
        "seniority": jd.seniority,
        "dimensions": [d.model_dump() for d in dimensions],
        "questions": [q.model_dump() for q in questions],
    }


def build_interview(prepared: dict) -> Interview:
    dimensions = [Dimension.model_validate(d) for d in prepared["dimensions"]]
    questions = [Question.model_validate(q) for q in prepared["questions"]]
    return Interview(dimensions, questions)


def load_prepared(path: str) -> tuple[dict, Interview]:
    """Read prepared_interview.json and build an Interview from it. No API calls."""
    with open(path, encoding="utf-8") as f:
        prepared = json.load(f)
    return prepared, build_interview(prepared)


def main():
    p = argparse.ArgumentParser(description="Prepare an interview ahead of time.")
    p.add_argument("--jd", default="data/job_description.txt", help="path to job description (.txt)")
    p.add_argument("--resume", default="data/resume_alex.txt", help="path to resume (.txt or .pdf)")
    p.add_argument("--mock", action="store_true", help="run with zero API calls, using canned/heuristic logic")
    p.add_argument("--out", default="prepared_interview.json", help="path to write the prepared interview to")
    args = p.parse_args()
    llm.MOCK = args.mock

    prepared = prepare(args.jd, args.resume)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(prepared, f, indent=2, ensure_ascii=False)
    print(f"Prepared {len(prepared['questions'])} questions for "
          f"{prepared['candidate_name']} ({prepared['role']}) -> {args.out}")


if __name__ == "__main__":
    main()
