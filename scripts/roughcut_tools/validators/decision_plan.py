"""Validate content plans; return effective provenance and semantic review gates.

Semantic membership/order/protected-fact impact requires rough-cut escalation.
Candidate scans and script evidence never authorize automatic edit actions.
The validator does not modify the input or execute any decision.
"""

from .decision_plan_impl import validate as validate_decision_plan

__all__ = ["validate_decision_plan"]
