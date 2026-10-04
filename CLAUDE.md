# Project rules

- Code must be minimal, flat and explainable line by line to a professor. No
  abstractions, frameworks or helper layers that aren't needed.
- The dialogue manager (`Interview` in `interview_session.py`) is a bounded
  finite-state controller, not a free chatbot. No LLM ever decides what the
  agent says next except through the existing judge -> template follow-up
  logic. `MAX_FOLLOWUPS = 2` is a hard cap.
- Every score must carry a verbatim quote verified by substring match
  (`score_dimension` in `interview.py`). Never weaken this.
- Never invent or inflate metrics. Anything not measured is reported as
  "not measured yet".
- Keep `--mock` working (zero API calls, deterministic heuristics).
