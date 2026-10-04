"""
The dialogue manager: a bounded finite-state controller, not a free chatbot.

Interview walks through a fixed list of questions. For each reply it asks the
judge for ONE verdict, and that verdict picks one of five fixed moves:

  an evidence gap   -> the template follow-up for that gap (at most
                       MAX_FOLLOWUPS per question, never the same one twice)
  REPEAT_REQUEST    -> say the last thing again (at most MAX_REPEATS per question)
  WAIT_REQUEST      -> "take your time", stay on the question (at most MAX_WAITS)
  CANNOT_ANSWER     -> stop probing and go to the next question
  SUFFICIENT        -> go to the next question

No LLM decides what gets said next - the judge only classifies, and every
sentence comes from a prepared question or a fixed template.

It never reads input or prints anything itself: the caller passes answers
in with on_answer() and says whatever comes back. That's what lets the same
controller run behind a terminal and behind a voice pipeline.
"""

import time

from interview import FOLLOWUP_TEMPLATES, generate_followup, judge
from schemas import Dimension, Evidence, Question, TranscriptTurn

MAX_FOLLOWUPS = 2  # deliberate cap: two probes is enough to separate a vague
# answer from a genuinely thin one, without turning every question into an
# interrogation. See README for the full rationale.

MAX_REPEATS = 1  # "could you repeat that?" is honoured once per question, so
# the conversation can never loop on it.

MAX_WAITS = 2  # "give me a second" is honoured twice per question, then we move on.

# Said before the next question, so the change of topic isn't abrupt.
MOVING_ON = "Thank you. Moving on."
MOVING_ON_AFTER_SKIP = "No problem, let's move on."
TAKE_YOUR_TIME = "Sure, take your time."


class Interview:
    def __init__(self, dimensions: list[Dimension], questions: list[Question]):
        self.dimensions = dimensions
        self.questions = questions
        self.transcript: list[TranscriptTurn] = []
        self.index = 0             # which question we're on
        self.answer = None         # answer so far for this question (None = not answered yet)
        self.followups_asked = 0   # follow-ups asked for this question
        self.repeats_used = 0      # repeats given for this question
        self.waits_used = 0        # "take your time" replies given for this question
        self.last_gap = None      # the gap the previous follow-up was about
        self.last_said = None      # the last thing we asked, in case we must repeat it
        self.last_verdict = None   # most recent JudgeVerdict, None if judge didn't run
        self.last_judge_ms = None  # time spent inside judge() for the last answer
        self.done = False

    def start(self) -> str:
        self.last_said = self.questions[0].text
        return self.last_said

    def on_answer(self, text: str) -> str | None:
        if self.done:
            raise RuntimeError("Interview is already finished.")

        # Follow-up answers are appended, so the judge and scorer see the whole answer.
        combined = text if self.answer is None else self.answer + " " + text

        self.last_verdict = None
        self.last_judge_ms = None

        # Only judge while a follow-up is still allowed - once the cap is hit
        # the verdict couldn't change anything, so we don't spend a judge call.
        missing = None
        if self.followups_asked < MAX_FOLLOWUPS:
            question = self.questions[self.index]
            dimension = self.dimensions[self.index]
            start = time.perf_counter()
            self.last_verdict = judge(question, dimension, combined, text)
            self.last_judge_ms = (time.perf_counter() - start) * 1000
            missing = self.last_verdict.missing

        # "Could you repeat that?" is not an answer: don't keep it, just say it again.
        if missing == Evidence.REPEAT_REQUEST and self.repeats_used < MAX_REPEATS:
            self.repeats_used += 1
            return self.last_said

        # "Give me a second" is not an answer either: stay on this question and wait.
        if missing == Evidence.WAIT_REQUEST and self.waits_used < MAX_WAITS:
            self.waits_used += 1
            return TAKE_YOUR_TIME

        self.answer = combined

        # An evidence gap gets its template follow-up - unless we just probed
        # that same gap, in which case asking again won't help.
        if missing in FOLLOWUP_TEMPLATES and missing != self.last_gap:
            self.followups_asked += 1
            self.last_gap = missing
            self.last_said = generate_followup(missing, self.last_verdict.topic, self.answer)
            return self.last_said

        # Otherwise this question is finished: record the turn and move on.
        self.transcript.append(TranscriptTurn(
            dimension=self.dimensions[self.index].name,
            question=self.questions[self.index].text,
            answer=self.answer,
            followups_asked=self.followups_asked,
        ))
        self.index += 1
        self.answer = None
        self.followups_asked = 0
        self.repeats_used = 0
        self.waits_used = 0
        self.last_gap = None

        if self.index == len(self.questions):
            self.done = True
            return None

        skipped = missing in (Evidence.CANNOT_ANSWER, Evidence.REPEAT_REQUEST, Evidence.WAIT_REQUEST)
        transition = MOVING_ON_AFTER_SKIP if skipped else MOVING_ON
        self.last_said = self.questions[self.index].text
        return transition + " " + self.last_said
