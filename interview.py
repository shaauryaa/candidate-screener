"""
The "brains" of the interview: turning a JD+resume into a rubric, turning a
rubric+resume into grounded questions, judging answers for missing evidence,
picking the right follow-up, and scoring the finished transcript.

Every function that can call the API has two branches, side by side:
  - the real Gemini call (used normally)
  - a deterministic, offline heuristic (used when llm.MOCK is True)
so --mock is never a mystery path bolted on separately - it's right here
next to the real logic it stands in for.
"""

import re

import llm
from schemas import (
    Dimension,
    DimensionScore,
    Evidence,
    JudgeVerdict,
    Project,
    Question,
    QuestionText,
    RawScore,
    TranscriptTurn,
)

NUM_DIMENSIONS = 4

# These must never affect a score. Listed here (not just in the prompt)
# so it's obvious at a glance what the scoring step is required to ignore.
EXCLUDED_ATTRIBUTES = [
    "name",
    "gender",
    "age",
    "college tier / which college they went to",
    "accent",
    "English fluency",
]


# ---- 1. rubric dimensions, grounded in the JD ------------------------------

_DIMENSIONS_PROMPT = """\
You are building an interview rubric for this job. Produce exactly {n} rubric
dimensions to evaluate a candidate on. Each dimension needs:
- name: short label (2-4 words)
- description: one sentence describing what "good" looks like for it
- jd_evidence: the specific responsibility or skill from the JD below that
  justifies this dimension

Job title: {title} ({seniority})
Responsibilities: {responsibilities}
Must-have skills: {skills}
"""


def generate_dimensions(jd) -> list[Dimension]:
    if llm.MOCK:
        return _mock_dimensions(jd)
    prompt = _DIMENSIONS_PROMPT.format(
        n=NUM_DIMENSIONS,
        title=jd.title,
        seniority=jd.seniority,
        responsibilities="; ".join(jd.responsibilities),
        skills="; ".join(jd.must_have_skills),
    )
    return llm.call_gemini(llm.MODEL_MAIN, prompt, list[Dimension])


def _mock_dimensions(jd) -> list[Dimension]:
    skills = jd.must_have_skills or ["core technical skills"]
    resp = jd.responsibilities or ["building software"]
    templates = [
        ("Technical Depth", "Hands-on depth in {0}", skills),
        ("Ownership & Impact", "Personally drives outcomes like {0}", resp),
        ("Systems Thinking", "Reasons about scope/scale/tradeoffs for {0}", resp),
        ("Collaboration", "Works effectively with others on {0}", resp),
    ]
    dims = []
    for i, (name, desc_template, source) in enumerate(templates):
        evidence = source[i % len(source)]
        dims.append(
            Dimension(name=name, description=desc_template.format(evidence), jd_evidence=evidence)
        )
    return dims


# ---- 2. one question per dimension, grounded in a specific resume project --

_QUESTION_PROMPT = """\
Write ONE interview question that evaluates this rubric dimension:
"{dim_name}" - {dim_desc}

The question MUST reference this specific project from the candidate's
resume by name, so it's clearly about their real experience, not generic:

Project: {project_name}
Description: {project_desc}
Technologies: {project_tech}

Return just the question text.
"""

_MOCK_QUESTION_TEMPLATES = {
    "Technical Depth": "On {project}, what was the trickiest technical decision you personally made, and why?",
    "Ownership & Impact": "For {project}, what part did you personally own end-to-end, and what changed because of your work?",
    "Systems Thinking": "Walk me through the scale {project} had to handle - how did that shape your design choices?",
    "Collaboration": "Who else did you work with on {project}, and where did you disagree with them?",
}


def generate_question(dimension: Dimension, project: Project) -> Question:
    if llm.MOCK:
        return _mock_question(dimension, project)
    prompt = _QUESTION_PROMPT.format(
        dim_name=dimension.name,
        dim_desc=dimension.description,
        project_name=project.name,
        project_desc=project.description,
        project_tech=", ".join(project.technologies),
    )
    raw = llm.call_gemini(llm.MODEL_MAIN, prompt, QuestionText)
    return Question(dimension=dimension.name, text=raw.text, grounded_project=project.name)


def _mock_question(dimension: Dimension, project: Project) -> Question:
    template = _MOCK_QUESTION_TEMPLATES.get(
        dimension.name, "Tell me about your work on {project} relevant to " + dimension.name + "."
    )
    return Question(
        dimension=dimension.name,
        text=template.format(project=project.name),
        grounded_project=project.name,
    )


# ---- 3. the judge: what evidence is missing from this answer? --------------

_JUDGE_PROMPT = """\
You are judging whether a candidate's interview answer has enough evidence
for this rubric dimension: "{dim_name}" - {dim_desc}

Question asked: {question}
Candidate's answer so far: {answer}

Decide which ONE of these is most true, in this priority order:
- NO_CONCRETE_EXAMPLE: the answer is vague/generic, with no specific instance
- NO_MEASURABLE_OUTCOME: no quantified result (a number, %, time saved, etc.)
- NO_PERSONAL_OWNERSHIP: answer only says "we"/"the team", never what THEY did
- UNCLEAR_SCOPE: scale/context (team size, users, timeframe) is unclear
- SUFFICIENT: none of the above gaps apply, the answer is well-evidenced

Return `missing` (one of the above) and one sentence of `reasoning`.
"""


def judge(question: Question, dimension: Dimension, answer: str) -> JudgeVerdict:
    if llm.MOCK:
        return _mock_judge(answer)
    prompt = _JUDGE_PROMPT.format(
        dim_name=dimension.name, dim_desc=dimension.description,
        question=question.text, answer=answer,
    )
    return llm.call_gemini(llm.MODEL_JUDGE, prompt, JudgeVerdict)


_CONCRETE_MARKERS = ["built", "designed", "implemented", "wrote", "created",
                     "refactored", "debugged", "fixed", "deployed", "led", "rebuilt"]
_SCOPE_MARKERS = ["team of", "users", "requests", "traffic", "scale", "week",
                  "month", "solo", "alone", "day", "hour"]


def _mock_judge(answer: str) -> JudgeVerdict:
    """Offline stand-in for the judge: simple keyword/regex heuristics over
    the candidate's own typed answer, so --mock still reacts to what's typed
    instead of returning the same canned verdict every time."""
    text = answer.lower()
    has_number = bool(re.search(r"\d", answer))
    has_first_person = bool(re.search(r"\bi\b", text))
    has_we = bool(re.search(r"\bwe\b", text))
    has_concrete = any(m in text for m in _CONCRETE_MARKERS) and len(answer.split()) > 8
    has_scope = any(m in text for m in _SCOPE_MARKERS)

    if not has_concrete:
        return JudgeVerdict(missing=Evidence.NO_CONCRETE_EXAMPLE,
                             reasoning="No specific action or concrete example described.")
    if not has_number:
        return JudgeVerdict(missing=Evidence.NO_MEASURABLE_OUTCOME,
                             reasoning="No quantified outcome or metric mentioned.")
    if has_we and not has_first_person:
        return JudgeVerdict(missing=Evidence.NO_PERSONAL_OWNERSHIP,
                             reasoning="Answer describes team work ('we') without the candidate's own part.")
    if not has_scope:
        return JudgeVerdict(missing=Evidence.UNCLEAR_SCOPE,
                             reasoning="Scale or context (team size, users, timeframe) is unclear.")
    return JudgeVerdict(missing=Evidence.SUFFICIENT,
                         reasoning="Concrete example, measurable outcome, ownership, and scope are all present.")


# ---- 4. follow-up: a pure lookup from gap -> question, no LLM call needed --

FOLLOWUP_TEMPLATES = {
    Evidence.NO_CONCRETE_EXAMPLE: "Can you walk me through one specific example - what exactly did you do, step by step?",
    Evidence.NO_MEASURABLE_OUTCOME: "Do you have a number for that - latency, throughput, users, time saved, error rate?",
    Evidence.NO_PERSONAL_OWNERSHIP: "You said 'we' - what part of that was specifically your own work, versus the team's?",
    Evidence.UNCLEAR_SCOPE: "Can you clarify the scale involved - team size, user base, or timeframe?",
}


def generate_followup(missing: Evidence) -> str:
    """
    The follow-up depends only on WHICH evidence is missing, not on the full
    answer text - that's what makes it possible to target the gap exactly
    instead of asking a generic "can you elaborate?". No API call: this is
    a template lookup, real or mock alike.
    """
    return FOLLOWUP_TEMPLATES[missing]


# ---- 5. scoring: every score must carry a verbatim quote -------------------

_SCORE_PROMPT = """\
You are scoring a candidate's interview answer for one rubric dimension.
Do NOT let any of these attributes affect the score, even if mentioned or
implied: {excluded}.

Dimension: {dim_name} - {dim_desc}
Question asked: {question}
Candidate's full answer (including any follow-ups):
---
{answer}
---

Score 1 (weak) to 5 (excellent) on this dimension only.
`quote` MUST be copied VERBATIM, word-for-word, from the candidate's answer
above - do not paraphrase, shorten, or fix typos. `reasoning` should explain
the score and refer to that quote.
"""


def _score_prompt(dimension: Dimension, turn: TranscriptTurn, retry: bool) -> str:
    prompt = _SCORE_PROMPT.format(
        excluded=", ".join(EXCLUDED_ATTRIBUTES),
        dim_name=dimension.name, dim_desc=dimension.description,
        question=turn.question, answer=turn.answer,
    )
    if retry:
        prompt += "\nIMPORTANT: your previous quote did not appear verbatim in the answer. Copy the exact text this time."
    return prompt


def score_dimension(dimension: Dimension, turn: TranscriptTurn) -> DimensionScore:
    if llm.MOCK:
        raw = _mock_raw_score(dimension, turn)
    else:
        raw = llm.call_gemini(llm.MODEL_MAIN, _score_prompt(dimension, turn, retry=False), RawScore)

    if raw.quote and raw.quote in turn.answer:
        return DimensionScore(dimension=dimension.name, score=raw.score,
                               quote=raw.quote, reasoning=raw.reasoning, quote_verified=True)

    # Never trust the model's own claim that a quote is real - verify by
    # substring match, and give it exactly one more chance before giving up.
    if not llm.MOCK:
        raw = llm.call_gemini(llm.MODEL_MAIN, _score_prompt(dimension, turn, retry=True), RawScore)
        if raw.quote and raw.quote in turn.answer:
            return DimensionScore(dimension=dimension.name, score=raw.score,
                                   quote=raw.quote, reasoning=raw.reasoning, quote_verified=True)

    return DimensionScore(
        dimension=dimension.name, score=raw.score, quote=raw.quote,
        reasoning=raw.reasoning + " [UNSUPPORTED: quote not found verbatim in transcript]",
        quote_verified=False,
    )


def _mock_raw_score(dimension: Dimension, turn: TranscriptTurn) -> RawScore:
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", turn.answer.strip()) if s]
    with_numbers = [s for s in sentences if re.search(r"\d", s)]
    quote = (with_numbers or sentences or [turn.answer])[0].strip()
    score = max(1, 5 - turn.followups_asked)  # fewer follow-ups needed -> stronger initial answer
    reasoning = f"Needed {turn.followups_asked} follow-up(s) to reach sufficient evidence for {dimension.name}."
    return RawScore(score=score, quote=quote, reasoning=reasoning)
