"""Importable content decision-plan validator with effective provenance/review_gates metadata."""

from .decision_plan_impl import validate as validate_decision_plan

__all__ = ["validate_decision_plan"]
