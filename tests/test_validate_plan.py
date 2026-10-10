import copy
import sys
import unittest
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_ROOT))
from roughcut_tool import main
from roughcut_tools.validators.decision_plan import validate_decision_plan as validate


class PlanTests(unittest.TestCase):
    def risk(self):
        return dict(membership_change=False, order_change=False, protected_fact_impact=False)

    def test_semantic_risk_sentinels_and_escalation_flag_types(self):
        for sentinel in ("unavailable", "not_assessed"):
            plan = self.base()
            plan["decisions"][0]["semantic_risk"] = dict.fromkeys(self.risk(), sentinel)
            result = validate(plan)
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["review_gates"]["decisions[0]"]["semantic_risk"]["order_change"], sentinel)
        for field, value in (("escalate_to_rough_cut", "true"), ("candidate_only", 1),
                             ("contextual_review_required", "false")):
            plan = self.base()
            plan["decisions"][0][field] = value
            self.assertFalse(validate(plan)["ok"], field)

    def test_unknown_pause_function_never_grants_context_review(self):
        for sentinel in ("unavailable", "not_assessed"):
            plan = self.base()
            plan["decisions"][0]["pause_function"] = sentinel
            self.assertTrue(validate(plan)["ok"])

    def test_pause_function_taxonomy_requires_context_evidence(self):
        for label in ("hesitation", "sentence_boundary", "speaker_handoff", "topic_shift",
                      "emphasis", "emotional_beat", "breath", "failed_take_gap", "edit_damage"):
            plan = self.base()
            row = plan["decisions"][0]
            row.update(pause_function=label, pause_context_evidence=["Reviewed surrounding phrasing"])
            self.assertTrue(validate(plan)["ok"], label)
            del row["pause_context_evidence"]
            self.assertFalse(validate(plan)["ok"], label)
        for label in ("long", "silence", [], {}, None):
            plan = self.base()
            plan["decisions"][0]["pause_function"] = label
            self.assertFalse(validate(plan)["ok"], label)

    def test_semantic_changes_require_escalation_and_human_review(self):
        for field in ("membership_change", "order_change", "protected_fact_impact"):
            plan = self.base()
            row = plan["decisions"][0]
            row["semantic_risk"] = self.risk()
            row["semantic_risk"][field] = True
            before = copy.deepcopy(plan)
            result = validate(plan)
            self.assertFalse(result["ok"], field)
            gate = result["review_gates"]["decisions[0]"]
            self.assertIs(gate.get("escalate_to_rough_cut"), True)
            self.assertIs(gate["human_review"], True)
            self.assertEqual(plan, before)
            row.update(escalate_to_rough_cut=True, human_review=True)
            self.assertTrue(validate(plan)["ok"], validate(plan))
            row["pass"] = "refinement"
            plan["workflow"]["refinement_pass"] = "draft"
            self.assertFalse(validate(plan)["ok"])

    def test_nonsemantic_cleanup_remains_fine_cut_eligible(self):
        plan = self.base()
        plan["workflow"]["refinement_pass"] = "draft"
        plan["decisions"][0].update(**{
            "pass": "refinement", "action": "shorten", "semantic_risk": self.risk(),
            "escalate_to_rough_cut": False,
        })
        result = validate(plan)
        self.assertTrue(result["ok"], result)
        self.assertIs(result["review_gates"]["decisions[0]"].get("escalate_to_rough_cut"), False)

    def test_semantic_risk_unknown_and_malformed_values(self):
        plan = self.base()
        self.assertEqual(validate(plan)["review_gates"]["decisions[0]"].get("semantic_risk"), {
            "membership_change": "unavailable", "order_change": "unavailable",
            "protected_fact_impact": "unavailable",
        })
        for value in (None, [], {}, {"membership_change": "no"},
                      {"membership_change": 0, "order_change": False, "protected_fact_impact": False}):
            plan = self.base()
            plan["decisions"][0]["semantic_risk"] = value
            self.assertFalse(validate(plan)["ok"], value)

    def test_reorder_cannot_hide_order_risk(self):
        plan = self.base()
        plan["decisions"][0].update(action="reorder", semantic_risk=self.risk())
        result = validate(plan)
        self.assertFalse(result["ok"])
        self.assertIs(result["review_gates"]["decisions[0]"].get("escalate_to_rough_cut"), True)

    def test_automatic_actions_rejected_but_reviewed_plans_remain_supported(self):
        for update in ({"automatic_action": "delete"}, {"auto_join": True},
                       {"candidate_only": True, "action": "delete"},
                       {"provenance": "script_generated", "action": "join"},
                       {"metadata": {"auto_delete": True}}):
            plan = self.base()
            plan["decisions"][0].update(update)
            self.assertFalse(validate(plan)["ok"], update)

    def base(self):
        return {
            "version": 1,
            "input": {
                "timebase": "seconds",
                "duration": 10.0,
                "completeness": {
                    "status": "complete",
                    "checked": ["video", "audio", "transcript"],
                    "missing": [],
                    "evidence": ["full source playback and transcript inventory"],
                    "impact": "none",
                },
            },
            "evidence": [{"kind": "transcript"}],
            "goal": {"type": "content_cleanup"},
            "theme_analysis": {
                "topic": "A discussion topic",
                "thesis": "The central proposition",
                "purpose": "discussion",
                "audience": "general audience",
                "confidence": "high",
            },
            "domain_analysis": {
                "status": "identified",
                "primary_domain": "general",
                "confidence": "high",
                "segments": [],
                "terms": [],
                "entities": [],
                "protected_facts": [],
                "unresolved_terms": [],
            },
            "outline": {
                "confidence": "high",
                "units": [{
                    "id": "U1", "title": "Opening", "role": "setup",
                    "start": 0.0, "end": 1.0, "timebase": "seconds", "confidence": "high",
                }],
            },
            "speakers": [{"id": "A", "role": "host", "confidence": "high"}],
            "original_structure": [],
            "recommended_structure": [],
            "protected_facts": [],
            "workflow": {"content_pass": "stable", "refinement_pass": "not_started"},
            "decisions": [{
                "id": "D1", "pass": "content", "action": "keep", "confidence": "high",
                "start": 0.0, "end": 1.0, "timebase": "seconds", "summary": "Keep opening",
                "reason": "Establishes context", "flags": [], "domain_sensitive": False,
                "boundary": {
                    "start_basis": "sentence_boundary",
                    "end_basis": "sentence_boundary",
                    "evidence": ["transcript", "audio"],
                    "precision": "exact",
                },
            }],
        }

    def test_valid_independent_plan(self):
        self.assertTrue(validate(self.base())["ok"])

    def test_orientation_is_required(self):
        plan = self.base()
        del plan["domain_analysis"]
        self.assertFalse(validate(plan)["ok"])

    def test_review_decision_is_allowed(self):
        plan = self.base()
        plan["decisions"][0].update({
            "action": "review", "confidence": "low", "flags": ["needs_listen"],
        })
        self.assertTrue(validate(plan)["ok"])

    def test_unresolved_domain_blocks_high_confidence_destructive_cut(self):
        plan = self.base()
        plan["domain_analysis"].update({"status": "uncertain", "confidence": "low"})
        plan["decisions"][0].update({
            "action": "delete", "domain_sensitive": True, "expected_join": "Next sentence continues the point",
        })
        self.assertFalse(validate(plan)["ok"])

    def test_unresolved_domain_cut_requires_review_marker(self):
        plan = self.base()
        plan["domain_analysis"].update({"status": "uncertain", "confidence": "low"})
        plan["decisions"][0].update({
            "action": "shorten", "confidence": "medium", "domain_sensitive": True,
            "flags": ["needs_context"], "expected_join": "The qualified answer remains connected",
        })
        self.assertTrue(validate(plan)["ok"])

    def test_multi_domain_outline_is_supported(self):
        plan = self.base()
        plan["domain_analysis"].update({
            "status": "identified",
            "primary_domain": "technology and business",
            "segments": [
                {"start": 0.0, "end": 0.5, "domain": "technology", "confidence": "high"},
                {"start": 0.5, "end": 1.0, "domain": "business", "confidence": "medium"},
            ],
            "terms": ["API", "market fit"],
            "unresolved_terms": ["ambiguous acronym"],
        })
        plan["outline"]["units"].append({
            "id": "U2", "title": "Business implication", "role": "explanation",
            "start": 1.0, "end": 2.0, "timebase": "seconds", "confidence": "medium",
        })
        self.assertTrue(validate(plan)["ok"])

    def test_timebase_and_duration_are_checked(self):
        plan = self.base()
        plan["decisions"][0]["timebase"] = "frames"
        self.assertFalse(validate(plan)["ok"])
        plan = self.base()
        plan["decisions"][0]["end"] = 11.0
        self.assertFalse(validate(plan)["ok"])

    def test_application_handoff_is_rejected(self):
        plan = self.base()
        plan["execution_handoff"] = {"keep_blocks": []}
        self.assertFalse(validate(plan)["ok"])

    def test_completeness_blocks_high_confidence_destructive_decision(self):
        plan = self.base()
        plan["input"]["completeness"] = {
            "status": "partial",
            "checked": ["video", "audio"],
            "missing": ["transcript"],
            "evidence": ["ASR file was not supplied"],
            "impact": "review_required",
        }
        plan["decisions"][0].update({
            "action": "delete",
            "expected_join": "The next sentence continues the explanation",
        })
        self.assertFalse(validate(plan)["ok"])

    def test_approximate_destructive_boundary_requires_review(self):
        plan = self.base()
        plan["decisions"][0].update({
            "action": "shorten",
            "confidence": "medium",
            "flags": ["human_review"],
            "expected_join": "The sentence remains grammatical after the pause",
            "boundary": {
                "start_basis": "phrase_boundary",
                "end_basis": "pause",
                "evidence": ["waveform"],
                "precision": "approximate",
            },
        })
        result = validate(plan)
        self.assertTrue(result["ok"])

    def test_refinement_requires_stable_content_pass(self):
        plan = self.base()
        plan["workflow"] = {"content_pass": "draft", "refinement_pass": "draft"}
        plan["decisions"][0]["pass"] = "refinement"
        self.assertFalse(validate(plan)["ok"])

    def test_refinement_is_allowed_after_content_pass_is_stable(self):
        plan = self.base()
        plan["workflow"] = {"content_pass": "stable", "refinement_pass": "draft"}
        plan["decisions"][0]["pass"] = "refinement"
        self.assertTrue(validate(plan)["ok"])

    def test_final_draft_audit_requires_final_subtitle_authority(self):
        plan = self.base()
        plan["workflow"] = {
            "mode": "final_draft_audit",
            "text_authority": "asr",
            "content_pass": "stable",
            "refinement_pass": "not_started",
        }
        result = validate(plan)
        self.assertFalse(result["ok"])
        self.assertTrue(any("text_authority" in error for error in result["errors"]))

    def test_final_draft_audit_blocks_destructive_decisions(self):
        plan = self.base()
        plan["workflow"] = {
            "mode": "final_draft_audit",
            "text_authority": "final_visible_subtitle",
            "content_pass": "stable",
            "refinement_pass": "not_started",
        }
        plan["decisions"][0]["action"] = "delete"
        plan["decisions"][0]["flags"] = ["human_review"]
        result = validate(plan)
        self.assertFalse(result["ok"])
        self.assertTrue(any("destructive actions" in error for error in result["errors"]))

    def test_boundary_is_required(self):
        plan = self.base()
        del plan["decisions"][0]["boundary"]
        self.assertFalse(validate(plan)["ok"])

    def test_subtitle_alignment_status_is_gated_by_content_pass(self):
        plan = self.base()
        plan["workflow"]["subtitle_alignment"] = "approved"
        self.assertTrue(validate(plan)["ok"])
        plan["workflow"] = {
            "content_pass": "draft",
            "refinement_pass": "not_started",
            "subtitle_alignment": "approved",
        }
        self.assertFalse(validate(plan)["ok"])

    def test_duplicate_decision_ids_rejected(self):
        plan = self.base()
        plan["decisions"].append(copy.deepcopy(plan["decisions"][0]))
        result = validate(plan)
        self.assertFalse(result["ok"])
        self.assertTrue(any("duplicates id" in e for e in result["errors"]), result["errors"])

    def test_outline_end_exceeds_duration_rejected(self):
        plan = self.base()
        plan["outline"]["units"][0]["end"] = 99.0  # input.duration is 10.0
        self.assertFalse(validate(plan)["ok"])

    def test_cli_main_smoke(self):
        import json as _json
        import sys
        import tempfile

        plan = self.base()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "plan.json"
            path.write_text(_json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            argv_backup = sys.argv
            try:
                rc = main(["validate", "plan", str(path)])
            finally:
                sys.argv = argv_backup
        self.assertEqual(rc, 0)


    def test_missing_provenance_is_unavailable_without_mutation(self):
        data = self.base()
        row = data["decisions"][0]
        row["cli_report"] = "deterministic evidence"
        before = copy.deepcopy(data)
        result = validate(data)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["review_gates"]["decisions[0]"]["provenance"], "unavailable")
        self.assertEqual(result["review_gates"]["decisions[0]"]["human_listening"], "pending")
        self.assertEqual(data, before)

    def test_provenance_enum_and_types(self):
        for value in ("script_generated", "agent_interpreted", "unavailable"):
            data = self.base()
            data["decisions"][0]["provenance"] = value
            self.assertTrue(validate(data)["ok"], value)
        for value in ("automatic", "human", None, [], {}):
            data = self.base()
            data["decisions"][0]["provenance"] = value
            result = validate(data)
            self.assertFalse(result["ok"], value)
            self.assertTrue(any("provenance" in e for e in result["errors"]))

    def test_script_output_cannot_grant_human_verified(self):
        data = self.base()
        data["decisions"][0].update(provenance="human_verified", cli_report="passed", human_review=True)
        result = validate(data)
        self.assertFalse(result["ok"])
        self.assertTrue(any("human_verdict" in e for e in result["errors"]))

    def test_recorded_human_verdict_can_verify(self):
        data = self.base()
        data["decisions"][0].update(provenance="human_verified", human_listening="verified",
                   human_verdict={"actor": "human", "reviewer": "human reviewer", "verdict": "approved",
                                  "scope": "human_listening", "evidence": "Recorded listening verdict"})
        result = validate(data)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["review_gates"]["decisions[0]"]["human_listening"], "verified")

    def test_agent_analysis_cannot_clear_human_listening(self):
        data = self.base()
        data["decisions"][0].update(provenance="agent_interpreted", human_listening="verified",
                   playback="reviewed", waveform="checked")
        result = validate(data)
        self.assertFalse(result["ok"])
        self.assertEqual(result["review_gates"]["decisions[0]"]["human_listening"], "pending")

    def test_non_listening_verdict_does_not_clear_listening(self):
        data = self.base()
        data["decisions"][0].update(provenance="human_verified", human_listening="verified",
                   human_verdict={"actor": "human", "reviewer": "human reviewer", "verdict": "approved",
                                  "scope": "interpretation", "evidence": "Recorded text verdict"})
        result = validate(data)
        self.assertFalse(result["ok"])
        self.assertEqual(result["review_gates"]["decisions[0]"]["human_listening"], "pending")

    def test_malformed_or_rejected_verdict_cannot_verify(self):
        for verdict in (None, {}, {"reviewer": "agent", "verdict": "approved"},
                        {"actor": "human", "reviewer": "human reviewer", "verdict": "rejected",
                         "scope": "human_listening", "evidence": "Not accepted"}):
            data = self.base()
            data["decisions"][0].update(provenance="human_verified", human_verdict=verdict)
            self.assertFalse(validate(data)["ok"], verdict)

    def test_script_or_agent_verdict_is_not_human(self):
        for actor in ("script", "agent", None):
            data = self.base()
            data["decisions"][0].update(provenance="human_verified", human_listening="verified",
                         human_verdict={"actor": actor, "reviewer": "automated reviewer",
                                        "verdict": "approved", "scope": "human_listening",
                                        "evidence": "Playback and waveform report"})
            self.assertFalse(validate(data)["ok"], actor)

    def test_invalid_listening_status_is_rejected(self):
        for status in ("approved", None, [], {}):
            data = self.base()
            data["decisions"][0]["human_listening"] = status
            self.assertFalse(validate(data)["ok"], status)

    def test_evidence_provenance_is_validated(self):
        data = self.base()
        data["evidence"][0]["provenance"] = "human_verified"
        self.assertFalse(validate(data)["ok"])

    def test_human_review_is_boolean_flag(self):
        data = self.base()
        data["decisions"][0]["human_review"] = "approved"
        self.assertFalse(validate(data)["ok"])


    def test_unresolved_terms_block_each_high_confidence_destructive_action(self):
        for action in ("delete", "shorten", "reorder", "join"):
            plan = self.base()
            plan["domain_analysis"]["unresolved_terms"] = ["Unresolved technical term"]
            plan["decisions"][0].update(action=action, domain_sensitive=True)
            result = validate(plan)
            self.assertFalse(result["ok"], action)
            self.assertTrue(any("domain-sensitive" in e for e in result["errors"]))


if __name__ == "__main__":
    unittest.main()
