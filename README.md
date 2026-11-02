# AI Candidate Screening Agent

## Submission contents

- **Code:** the Python files in this folder; see [Project layout](#project-layout)
- **Dataset:** [dataset/README.md](dataset/README.md) maps the data to validation and test splits
- **Paper:** [paper/SARAH_IEEE.pdf](paper/SARAH_IEEE.pdf), with LaTeX source in [paper/SARAH_IEEE.tex](paper/SARAH_IEEE.tex)
- **Slides:** [slides/SARAH_Phase2.pptx](slides/SARAH_Phase2.pptx)

## Overview

Interviews a candidate - typed in the terminal or spoken over a voice call -
grounding every question in both the job description and the candidate's
actual resume, probes vague answers with targeted follow-ups, and produces a
scorecard where every score is backed by a verbatim quote from the transcript.

The interview is a bounded state machine, not a free chatbot: an LLM only
*classifies* each answer, and every sentence the agent says is a prepared
question or a fixed template.

## How to run (text)

```bash
python -m venv .venv            # Python 3.11
.venv\Scripts\activate          # Windows; use `source .venv/bin/activate` elsewhere
pip install -r requirements.txt
cp .env.example .env            # then paste your Gemini API key into .env
python main.py
```

By default this runs on `data/job_description.txt` and `data/resume_alex.txt`.
To use another resume (`.txt` or `.pdf`):

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

## Voice demo

`agent.py` puts a voice on the same interview using LiveKit Agents: Silero VAD
and LiveKit's multilingual turn detector decide when the candidate has
finished, Deepgram (nova-3) transcribes, Cartesia speaks. There is no LLM on
the voice session - the agent only ever says a prepared question or a
template chosen by the judge. Needs `DEEPGRAM_API_KEY` and `CARTESIA_API_KEY`
in `.env` as well as `GEMINI_API_KEY`; `dev` mode also needs `LIVEKIT_URL`,
`LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET`.

```bash
python prep.py --resume data/resume_alex.txt   # once per candidate: writes prepared_interview.json
python agent.py download-files                 # once: VAD + turn detector model files
python agent.py console                        # talk to it with your mic and speakers
python agent.py dev                            # or join via a LiveKit room (LiveKit Cloud)
```

`prep.py` does the slow Gemini work (parsing, rubric, questions) ahead of
time, so the call itself starts with zero API calls. Re-run it whenever the
resume or job description changes.

The call opens by telling the candidate that this is an AI assistant, that
the call is being transcribed for the hiring team, and that a person makes
the final decision; it closes by saying the transcript goes to that team.

Every line is printed with a timestamp. Each call writes up to three files to
`reports/`, all named after the call's start time. New calls are gitignored;
the calls behind the published latency numbers are committed there as evidence:

- `<timestamp>_transcript.json` - every line both sides said, labelled, with
  the judge's verdict on each answer, the scores and the timing summary
- `<timestamp>_latency.csv` - one row of timings per candidate turn
- `<timestamp>_report.html` - the scorecard, written once the interview
  finishes (a call that ends early is saved but not scored)

## How the conversation is controlled

`Interview` in `interview_session.py` holds the state. After each reply the
judge classifies it, and the result picks a fixed move:

| Verdict | What the agent does | Limit per question |
|---|---|---|
| `NO_CONCRETE_EXAMPLE`, `NO_MEASURABLE_OUTCOME`, `NO_PERSONAL_OWNERSHIP`, `UNCLEAR_SCOPE` | asks the template follow-up for the first open gap it didn't just ask about | 2 follow-ups, never the same gap twice in a row |
| `REPEAT_REQUEST` ("could you repeat that?") | says the last question again | 1 |
| `WAIT_REQUEST` ("give me a second") | "Sure, take your time." and stays on the question | 2 |
| `CANNOT_ANSWER` ("I don't know", "can we move on?") | moves to the next question | - |
| `SUFFICIENT` | moves to the next question | - |

Repeat and wait requests are not kept as part of the answer, and do not use
up a follow-up. Once a limit is reached the agent moves on, so the
conversation can never loop.

### How the judge finds gaps

The LLM never names a gap directly. For each of the four elements (concrete
example, measurable outcome, personal ownership, clear scope) it returns a
verbatim quote that proves it, or nothing. Code then checks each quote by exact
substring match, and any element without a real quote is a gap. Gaps are put in
a fixed order - concrete example, measurable outcome, ownership, scope - which
only decides what is asked first, not what matters most.

Evidence is remembered within a question: once a quote is verified, that element
stays proven even if the next reply doesn't repeat it, new replies can add to it,
and it resets on the next question. Without this, the judge forgot earlier replies
and Sarah asked for things she had just been told.

A quote proves the words exist, not that they are good evidence, and the judge
does not check that an answer is about the question asked.

### Follow-ups that refer to what was said

With a gap verdict the judge also returns a short phrase copied word-for-word
from the candidate's answer - the thing they named without explaining. It is
slotted into the template: *You said "the payment gateway". What exactly did
you do there, step by step?* The phrase is never trusted: it must be at most
six words and appear in the candidate's own answer, otherwise the plain
template is used. So the model chooses a phrase, never the sentence.

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

## Timings: measured, never estimated

Each number is labelled with exactly what it measures, and anything that was
not measured is reported as "not measured yet".

- Text mode reports only the time spent inside `judge()` per judged answer.
  Typing time is not a latency, so it is not reported as one.
- Voice mode logs, per candidate turn, LiveKit's end-of-utterance delay, STT
  transcription delay and TTS time to first byte, plus our own `judge()` time.
- "End of user speech to first agent audio" is the difference between two
  timestamps LiveKit records (when the candidate stopped speaking, and when
  the reply's first audio frame went out). It does not include playback delay
  on the listener's side. If either timestamp is missing for a turn, that
  turn is left out and the summary says which one was missing.
- p50 and p95 are printed with the number of turns behind them; on a short
  call p95 is simply the slowest turn.

Two settings at the top of `agent.py` trade speed against cutting the
candidate off: `MIN_ENDPOINTING_DELAY` (silence needed when the turn detector
thinks they have finished) and `MAX_ENDPOINTING_DELAY` (when it thinks they
are still mid-thought).

Each Gemini request in `llm.py` is cut off after `REQUEST_TIMEOUT_MS` (15 s) and
retried with backoff, so a stuck request can't leave a call silent forever. The
evaluation below ran before this timeout was added.

## Evaluation

Sarah's real controller, judge and scorer run against LLM personas whose answers
have a planted ground truth: for each question, a seeded draw decides which of
the four evidence elements the reply contains, so the right verdict is known
before the judge sees it. There are seven personas: strong (`strong_specific`,
`rambler`), weak (`vague_generalist`, `bluffer`, `nervous_minimal`) and mixed
(`question_asker`, `hostile`).

```bash
python eval_personas.py --resumes data/resume_priya.pdf --max-calls 200   # interviews
python rescore.py --resumes resume_priya --personas bluffer --max-calls 110   # repeat, fairness, verbosity
python make_label_sheet.py                                                # blind human scoring sheet
python agreement.py                                                       # Sarah vs human agreement
```

These call real Gemini (except the last two) and never use `--mock`. Rerunning a
command skips finished work.

The judge was frozen at git tag `judge-v2-frozen` before the Priya and Shaurya
runs. Alex is development data: the judge was tuned on it, and 6 of its 7
interviews used an earlier judge. Results below are held-out only.

| Metric, Priya and Shaurya, 14 interviews | Result |
|---|---|
| Judge verdict was a real gap | 107/110 = 97.3% |
| Judge verdict was the first gap in priority order | 103/110 = 93.6% |
| Whole gap list exactly right | 82/106 = 77.4% |
| Follow-ups asked about something really missing | 88/93 = 94.6% |
| Mean score: strong / mixed / weak | 3.06 (n=16) / 1.63 (n=16) / 1.13 (n=24) |
| Bluffer scores of 4 or 5 | 0/8 |
| Score quotes verified | 56/56 |

| Metric, 4 Priya interviews, 16 turns | Result |
|---|---|
| All 4 repeat scores match | 14/16 = 87.5% |
| Score unchanged in both fairness copies | 13/16 = 81.2% |
| Mean signed change, woman/tier-3 and man/IIT sentence | +0.19 and +0.06 (n=16 each) |
| Score rose under verbosity attack | 0/16, mean change -0.25 |

| Agreement, 28 held-out turns | Exact | Within 1 | Quadratic kappa |
|---|---|---|---|
| Sarah vs first human | 15/28 | 25/28 | 0.731 |
| Sarah vs second human | 14/28 | 24/28 | 0.681 |
| Human vs human | 22/28 | 28/28 | 0.928 |

Voice latency, end of speech to first audio, 2 calls: median 3006 ms and p95
27184 ms (n=15), or 2809 ms and 4822 ms (n=13) without two turns affected by one
25.9 s stall. Details and comparisons are in `eval/voice_latency.md`.

**Limits.** Candidates are simulated, and the same model plays persona, judge and
scorer. Judge accuracy is agreement with a planted key; a persona can break its
key, and only "I" and numbers are checked by script. There are two held-out
resumes and one run per persona, so these figures are descriptive. Rescoring
covers 4 interviews, and most weak scores sit at the floor of 1, which hides any
downward change. The 3 fairness changes all went up, and 2 of them moved only on
the woman/tier-3 copy; that is too few to call bias or to rule it out. Human
scorers were two people, one the system's author who had seen some results, and
half the turns come from that author's resume. Sarah scored lower than both
(mean 1.93 against 2.43 and 2.36), most on strong answers.

## Project layout

- `schemas.py` - every pydantic model, in one flat file
- `llm.py` - the Gemini client, retry-with-backoff, and the `MOCK` flag
- `parsing.py` - JD/resume (.txt or .pdf) -> structured pydantic objects
- `interview.py` - rubric generation, question generation, the judge, the
  follow-up templates, and scoring (each with a real branch and a mock branch)
- `interview_session.py` - `Interview`, the state machine that turns each
  answer into the next thing to say
- `prep.py` - prepares an interview ahead of time and saves/loads
  `prepared_interview.json`
- `main.py` - the typed interview: feeds answers to `Interview`, then scores
- `agent.py` - the voice interview: the same `Interview` behind LiveKit, plus
  scoring, the call files and the latency log
- `candidate.py` - the `get_answer()` interface + `HumanCandidate`
- `report.py` - writes the HTML scorecard
- `personas.py` - the seven simulated candidates and their prompt
- `eval_personas.py` - runs interviews against a planted answer key and writes
  the summary
- `rescore.py` - repeat consistency, fairness and verbosity on saved transcripts
- `make_label_sheet.py` - the blind human scoring sheet
- `agreement.py` - Sarah vs human, and human vs human, agreement
- `CLAUDE.md` - the project rules the code is held to
- `data/` - a sample JD and sample resumes (`.txt` and `.pdf`)
- `eval/` - transcripts, summaries (`summary_priya.md` and `summary_shaurya.md`
  are held-out; `summary.md` pools all three resumes), human scores, `agreement.md`
  and `voice_latency.md`; `eval/old/` holds superseded tuning runs
- `reports/` - per-call output from the voice agent; new calls are gitignored
