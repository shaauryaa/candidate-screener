"""
All data shapes for the project, in one place.

Nothing here calls the API or does any logic - these are just the
pydantic models that every other file passes around. Keeping them in
one flat file means you never have to hunt across modules to see what
a "Dimension" or a "JudgeVerdict" actually contains.
"""

from enum import Enum
from pydantic import BaseModel


# ---- parsed inputs ---------------------------------------------------

class JobDescription(BaseModel):
    title: str
    seniority: str
    must_have_skills: list[str]
    responsibilities: list[str]


class Project(BaseModel):
    name: str
    description: str
    technologies: list[str]


class Resume(BaseModel):
    candidate_name: str
    skills: list[str]
    projects: list[Project]


# ---- rubric + questions ------------------------------------------------

class Dimension(BaseModel):
    name: str
    description: str
    jd_evidence: str  # the JD line/requirement this dimension is grounded in


class Question(BaseModel):
    dimension: str
    text: str
    grounded_project: str  # which resume project this question references


class QuestionText(BaseModel):
    """What we actually ask the model for - just the question wording. The
    dimension/grounded_project fields of Question are filled in by us, since
    we already know them; asking the model to restate them risks a mismatch."""
    text: str


# ---- the judge -----------------------------------------------------------

class Evidence(str, Enum):
    """
    What's missing from an answer. The judge returns exactly one of these
    instead of a plain yes/no, because the value of this whole project is
    that a follow-up can target a *specific* gap instead of just asking
    "can you elaborate?" again.
    """
    NO_CONCRETE_EXAMPLE = "NO_CONCRETE_EXAMPLE"
    NO_MEASURABLE_OUTCOME = "NO_MEASURABLE_OUTCOME"
    NO_PERSONAL_OWNERSHIP = "NO_PERSONAL_OWNERSHIP"  # answer says "we", never "I"
    UNCLEAR_SCOPE = "UNCLEAR_SCOPE"
    SUFFICIENT = "SUFFICIENT"


class JudgeVerdict(BaseModel):
    missing: Evidence
    reasoning: str

    @property
    def sufficient(self) -> bool:
        return self.missing == Evidence.SUFFICIENT


# ---- transcript + scoring -------------------------------------------------

class TranscriptTurn(BaseModel):
    dimension: str
    question: str
    answer: str  # original answer + any follow-up answers, concatenated
    followups_asked: int


class RawScore(BaseModel):
    """What the LLM itself returns - before we've verified the quote is real."""
    score: int  # 1-5
    quote: str
    reasoning: str


class DimensionScore(BaseModel):
    dimension: str
    score: int  # 1-5
    quote: str
    reasoning: str
    quote_verified: bool
