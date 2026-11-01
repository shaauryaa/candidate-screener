"""
Simulated candidates with a KNOWN ground truth, for measuring Sarah.

A persona only says HOW a candidate talks. WHAT a reply contains is decided by
the runner and passed in as `instruction`, so we know the right verdict before
the judge ever sees the reply. The persona never sees the judge's verdicts.

Nothing here is text- or voice-specific, so a voice tester can reuse this file.
"""

from schemas import Evidence

PERSONAS = {
    "strong_specific": {
        "group": "strong",
        "instruction": "You are clear, direct and precise. You get to the point "
                       "and describe your work plainly, like an experienced engineer.",
    },
    "rambler": {
        "group": "strong",
        "instruction": "You ramble. Your answers are long and wander off topic "
                       "into side stories and opinions, and the useful content is "
                       "buried in the middle of them.",
    },
    "vague_generalist": {
        "group": "weak",
        "instruction": "You speak in generalities and buzzwords, and you sound "
                       "pleasant and confident but rarely commit to anything specific.",
    },
    "bluffer": {
        "group": "weak",
        "instruction": "You make big claims about how important and impressive "
                       "your work was. When pushed for detail you stay grand and "
                       "change nothing about how little you actually say.",
    },
    "nervous_minimal": {
        "group": "weak",
        "instruction": "You are nervous and give very short answers, one or two "
                       "brief sentences at most.",
    },
    "question_asker": {
        "group": "mixed",
        "instruction": "You are polite and a little unsure of yourself, and you "
                       "think out loud as you answer.",
    },
    "hostile": {
        "group": "mixed",
        "instruction": "You are curt and irritated. You challenge the point of "
                       "this screening process, but you still answer the question.",
    },
}

# Each element, and the judge's verdict when that element is missing. The order
# is the judge's own priority order (_JUDGE_PROMPT in interview.py).
ELEMENTS = {
    "concrete_example": Evidence.NO_CONCRETE_EXAMPLE,
    "measurable_outcome": Evidence.NO_MEASURABLE_OUTCOME,
    "personal_ownership": Evidence.NO_PERSONAL_OWNERSHIP,
    "clear_scope": Evidence.UNCLEAR_SCOPE,
}

_PERSONA_PROMPT = """\
You are playing a job candidate in a spoken screening interview. Your resume:
---
{resume}
---

How you talk: {style}

The four elements an answer can contain:
- concrete_example = a specific event, decision or technical step that happened;
  buzzwords, general claims and a bare result do not count, and who did it does
  not matter
- measurable_outcome = a quantified result (a number, %, time saved)
- personal_ownership = says what "I" did; when False, only "we"/"the team"
- clear_scope = team size, number of users, or timeframe is stated

Your instruction for THIS reply, which overrides how you talk if they conflict:
{instruction}

Rules:
- You are the person on the resume. Only talk about projects and skills on it.
  If the instruction needs a detail the resume doesn't give (a number, a team
  size), make up a plausible one about that same project.
- Containing an element means: concrete_example = describe one specific thing
  that happened; measurable_outcome = say an actual number for a result, using
  the resume's real numbers where it has them; personal_ownership = say "I"
  about the work, and don't say "we" for that part; clear_scope = say the team
  size, number of users or length of time.
- Leaving out an element means: no concrete_example = stay generic;
  no measurable_outcome = no numbers about results; no personal_ownership =
  only "we"/"the team", never "I" about the work; no clear_scope = no team
  size, user count or length of time.
- If you give a measurable_outcome but leave out concrete_example, state the
  number as a plain claim, with no event or technical step around it.
- If you give a measurable_outcome but leave out clear_scope, use a result that
  isn't a user count or a period of time, such as latency, traffic or error
  rate, and don't say when it happened.
- Never say you don't know or don't remember, never decline, and never ask to
  skip or for time to think. With nothing to add, give a vague reply instead.
- Only ask the interviewer to repeat if your instruction says so.
- Stay consistent with what you already said.
- Write only the words you say aloud: no lists, no notes, no mention of these
  instructions or of the elements.

Conversation so far:
{conversation}

Return your next reply in `answer`.
"""


def persona_prompt(persona: str, resume_text: str, conversation: list[str], instruction: str) -> str:
    return _PERSONA_PROMPT.format(
        resume=resume_text,
        style=PERSONAS[persona]["instruction"],
        instruction=instruction,
        conversation="\n".join(conversation),
    )
