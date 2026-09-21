"""
The dialogue loop in main.py only ever calls candidate.get_answer(prompt).
It doesn't know or care that a human is typing the answers - that's what
lets an LLM-persona candidate be dropped in later (for automated testing)
without touching the loop itself.
"""

from typing import Protocol


class Candidate(Protocol):
    def get_answer(self, prompt: str) -> str:
        ...


class HumanCandidate:
    """Prints the prompt and reads the answer from the terminal. This is the
    only implementation used in this demo - hand the keyboard to whoever is
    playing the candidate."""

    def get_answer(self, prompt: str) -> str:
        return input(prompt)
