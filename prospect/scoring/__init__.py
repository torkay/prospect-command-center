"""Scoring module for prospect prioritization."""

from .fit import calculate_fit_score
from .opportunity import calculate_opportunity_score
from .notes import generate_opportunity_notes

__all__ = [
    "calculate_fit_score",
    "calculate_opportunity_score",
    "generate_opportunity_notes",
]
