"""Public, application-independent stage-comparison validation contract."""

from .stage_comparison_report_impl import validate as validate_stage_comparison_report

__all__ = ["validate_stage_comparison_report"]
