"""Importable final-draft analysis-report validator with effective provenance/review_gates metadata."""

from .analysis_report_impl import validate as validate_analysis_report

__all__ = ["validate_analysis_report"]
