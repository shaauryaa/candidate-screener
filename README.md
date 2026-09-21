# AI Candidate Screening Agent (text-only prototype)

Interviews a candidate in the terminal, grounding every question in both the
job description and the candidate's actual resume, probes vague answers with
targeted follow-ups, and produces a scorecard where every score is backed by
a verbatim quote from the transcript.

## How to run

```bash
pip install -r requirements.txt
cp .env.example .env        # then paste your Gemini API key into .env
python main.py
```

By default this runs on `data/job_description.txt` and `data/resume_alex.txt`.
To use the other sample (and exercise the PDF parsing path):

```bash
python main.py --resume data/resume_priya.pdf
```

To run the whole thing offline with zero API calls (e.g. if the wifi dies
mid-demo) - the candidate can still type real answers, only the LLM calls
are replaced by deterministic heuristics:

```bash
python main.py --mock
```

The scorecard prints to the terminal and is also written to `report.html`
(`--out` to change the path) as a single self-contained file.

## Why follow-ups are capped at `MAX_FOLLOWUPS = 2`

Two probes are enough to tell a genuinely thin answer from one that just
needed prompting - a person can usually surface a concrete example, a number,
or their own role within two nudges if it exists at all. Uncapped probing
turns the interview into an interrogation and makes the transcript length
(and therefore the demo) unpredictable, so the cap is a fixed, visible
constant rather than a judgment call made at runtime.

## Why every score needs a verbatim quote

A 1-5 number with no receipt is just the model's opinion, and there's no way
for a candidate (or a professor) to check it. Requiring a quote forces the
score to point at something that was actually said, and checking that quote
by exact substring match - rather than trusting the model's own claim -
catches the case where the model scores confidently off a paraphrase or a
detail it invented. If it still can't produce a real quote after one retry,
the score is marked `UNSUPPORTED` instead of being silently kept.

## Project layout

- `schemas.py` - every pydantic model, in one flat file
- `llm.py` - the Gemini client, retry-with-backoff, and the `MOCK` flag
- `parsing.py` - JD/resume (.txt or .pdf) -> structured pydantic objects
- `interview.py` - rubric generation, question generation, the judge, the
  follow-up lookup, and scoring (each with a real branch and a mock branch)
- `candidate.py` - the `get_answer()` interface + `HumanCandidate`
- `report.py` - writes the HTML scorecard
- `main.py` - wires it together; the judge/follow-up loop lives here inline
- `data/` - one sample JD and two sample resumes (one `.txt`, one `.pdf`)
