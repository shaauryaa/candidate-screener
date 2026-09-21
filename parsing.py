"""
Turn raw JD/resume files into the structured pydantic objects everything
downstream relies on. Two entry points: parse_job_description() and
parse_resume(). Each has a real (LLM) path and a --mock (heuristic, offline)
path, following the same MOCK flag as llm.py.
"""

import re

from pypdf import PdfReader

import llm
from schemas import JobDescription, Project, Resume


def _read_text(path: str) -> str:
    if path.lower().endswith(".pdf"):
        reader = PdfReader(path)
        return "\n".join(page.extract_text() for page in reader.pages)
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---- job description -------------------------------------------------

_JD_PROMPT = """\
Extract the following from this job description as structured data:
- title
- seniority
- must_have_skills (list of short skill phrases)
- responsibilities (list of short phrases)

Job description:
---
{text}
---
"""


def parse_job_description(path: str) -> JobDescription:
    text = _read_text(path)
    if llm.MOCK:
        return _mock_parse_jd(text)
    return llm.call_gemini(llm.MODEL_MAIN, _JD_PROMPT.format(text=text), JobDescription)


def _mock_parse_jd(text: str) -> JobDescription:
    """Heuristic line-based parse of the '- ' bullet format used in data/job_description.txt."""
    title = re.search(r"Title:\s*(.+)", text)
    seniority = re.search(r"Seniority:\s*(.+)", text)

    def bullets_under(header: str) -> list[str]:
        section = re.search(rf"{header}:\s*\n((?:- .+\n?)+)", text)
        if not section:
            return []
        return [line.strip("- ").strip() for line in section.group(1).splitlines() if line.strip()]

    return JobDescription(
        title=title.group(1).strip() if title else "Software Engineer",
        seniority=seniority.group(1).strip() if seniority else "Unspecified",
        must_have_skills=bullets_under("Must-Have Skills") or ["Python", "SQL"],
        responsibilities=bullets_under("Responsibilities") or ["Build and maintain software"],
    )


# ---- resume -------------------------------------------------------------

_RESUME_PROMPT = """\
Extract the following from this resume as structured data:
- candidate_name
- skills (flat list)
- projects: for each project, its name, a short description, and the
  technologies used.

Resume:
---
{text}
---
"""


def parse_resume(path: str) -> Resume:
    text = _read_text(path)
    if llm.MOCK:
        return _mock_parse_resume(text)
    return llm.call_gemini(llm.MODEL_MAIN, _RESUME_PROMPT.format(text=text), Resume)


def _mock_parse_resume(text: str) -> Resume:
    """Heuristic parse of the 'Name / Skills / Projects: - Name: desc. [tech]' format
    used in the sample resumes."""
    name = re.search(r"Name:\s*(.+)", text)
    skills_line = re.search(r"Skills:\s*(.+)", text)
    skills = [s.strip() for s in skills_line.group(1).split(",")] if skills_line else []

    projects = []
    # Each project is "- Project Name: description text [Tech, Tech]" possibly
    # wrapped across lines; join the whole "Projects:" section first.
    projects_section = text.split("Projects:", 1)
    if len(projects_section) == 2:
        blob = re.sub(r"\s+", " ", projects_section[1])
        for match in re.finditer(r"-\s*([^:]+):\s*(.*?)\s*\[([^\]]+)\]", blob):
            proj_name, desc, tech = match.groups()
            projects.append(
                Project(
                    name=proj_name.strip(),
                    description=desc.strip(),
                    technologies=[t.strip() for t in tech.split(",")],
                )
            )

    return Resume(
        candidate_name=name.group(1).strip() if name else "Candidate",
        skills=skills,
        projects=projects,
    )
