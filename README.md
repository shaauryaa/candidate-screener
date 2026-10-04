# AI Candidate Screening Agent

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
`reports/` (gitignored), all named after the call's start time:

- `<timestamp>_transcript.json` - every line both sides said, labelled, with
  the judge's verdict on each answer, the scores and the timing summary
- `<timestamp>_latency.csv` - one row of timings per candidate turn
- `<timestamp>_report.html` - the scorecard, written once the interview
  finishes (a call that ends early is saved but not scored)

## How the conversation is controlled

`Interview` in `interview_session.py` holds the state. After each reply the
judge returns exactly one verdict, and the verdict picks a fixed move:

| Verdict | What the agent does | Limit per question |
|---|---|---|
| `NO_CONCRETE_EXAMPLE`, `NO_MEASURABLE_OUTCOME`, `NO_PERSONAL_OWNERSHIP`, `UNCLEAR_SCOPE` | asks the template follow-up for that gap | 2 follow-ups, never the same gap twice in a row |
| `REPEAT_REQUEST` ("could you repeat that?") | says the last question again | 1 |
| `WAIT_REQUEST` ("give me a second") | "Sure, take your time." and stays on the question | 2 |
| `CANNOT_ANSWER` ("I don't know", "can we move on?") | moves to the next question | - |
| `SUFFICIENT` | moves to the next question | - |

Repeat and wait requests are not kept as part of the answer, and do not use
up a follow-up. Once a limit is reached the agent moves on, so the
conversation can never loop.

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
- `CLAUDE.md` - the project rules the code is held to
- `data/` - a sample JD and sample resumes (`.txt` and `.pdf`)
- `reports/` - per-call output from the voice agent (gitignored)
