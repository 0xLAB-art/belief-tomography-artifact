"""Tests for the 218-row CTI manual audit tooling (advisory #5)."""

from __future__ import annotations

from scripts.cti_manual_audit import (
    _alias_key,
    _machine_vs_human,
    _norm_annotation,
    _parse_annotation,
    _prf,
    _suite_verdicts,
    _workload_flags,
    cohens_kappa,
)


class TestCohensKappa:
    def test_perfect_agreement(self):
        assert cohens_kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0

    def test_complete_disagreement(self):
        assert cohens_kappa(["a", "b", "a", "b"], ["b", "a", "b", "a"]) == -1.0

    def test_chance_agreement_is_near_zero(self):
        # 3/4 observed agreement, but marginals make expected agreement 0.625
        a = ["x", "x", "x", "y"]
        b = ["x", "x", "y", "y"]
        k = cohens_kappa(a, b)
        assert 0.0 <= k <= 0.5  # modest positive, far below raw 0.75

    def test_empty_returns_none(self):
        assert cohens_kappa([], []) is None
        assert cohens_kappa(["a"], []) is None

    def test_pe_of_one_is_handled(self):
        # both annotators constant on one label -> pe == 1.0 must not divide by zero
        assert cohens_kappa(["a", "a"], ["a", "a"]) == 1.0


class TestPrf:
    def test_basic_counts(self):
        out = _prf(3, 1, 2)
        assert out["precision"] == 0.75
        assert out["recall"] == 0.6
        assert out["f1"] == 0.6667

    def test_denominator_zero_gives_none(self):
        out = _prf(0, 0, 5)
        assert out["precision"] is None
        assert out["recall"] == 0.0
        assert out["f1"] == 0.0


class TestAliasKey:
    ALIAS = {
        "apt28": ["apt28", "fancy bear", "sofaction"],
        "salt typhoon": ["salt typhoon"],
        "lazarus group": ["lazarus group", "hidden cobra"],
    }

    def test_alias_resolves_to_canonical(self):
        assert _alias_key("Fancy Bear", self.ALIAS) == "apt28"

    def test_canonical_matches_itself(self):
        assert _alias_key("APT28", self.ALIAS) == "apt28"

    def test_unknown_is_none(self):
        assert _alias_key("Zorg Empire", self.ALIAS) is None

    def test_case_and_whitespace_insensitive(self):
        assert _alias_key("  LAZARUS GROUP ", self.ALIAS) == "lazarus group"


class TestNormAnnotation:
    def test_technique_row_normalization(self):
        out = _norm_annotation(
            {
                "row_id": "R1",
                "requested": " t1190 ",
                "identified": ["T1190", "x"],
                "identification": "Correct",
                "served_on_topic": "YES",
                "notes": "n",
            },
            "cti_technique",
        )
        assert out["requested"] == "T1190"
        assert out["identified"] == ["T1190", "x"]
        assert out["identification"] == "correct"
        assert out["served_on_topic"] == "yes"

    def test_unclear_requested_preserved(self):
        out = _norm_annotation({"row_id": "R1", "requested": "unclear"}, "cti_technique")
        assert out["requested"] == "unclear"

    def test_invalid_verdicts_clamped_to_none(self):
        out = _norm_annotation(
            {"row_id": "R1", "identification": "maybe", "served_on_topic": "sorta"},
            "cti_technique",
        )
        assert out["identification"] is None
        assert out["served_on_topic"] is None

    def test_identified_string_of_ids_is_extracted(self):
        out = _norm_annotation(
            {"row_id": "R1", "identified": "T1059 and T1059.001"},
            "cti_technique",
        )
        assert out["identified"] == ["T1059", "T1059.001"]

    def test_identified_plain_string_kept_whole(self):
        out = _norm_annotation(
            {"row_id": "R1", "identified": "Volt Typhoon"},
            "cti_technique",
        )
        assert out["identified"] == ["volt typhoon"]

    def test_deception_row_uses_realism(self):
        out = _norm_annotation(
            {"row_id": "R1", "realism": "Realistic", "served_on_topic": "no"},
            "deception",
        )
        assert out["realism"] == "realistic"
        assert out["served_on_topic"] == "no"
        assert "identification" not in out


class TestParseAnnotation:
    def test_sentinel_array_parses(self):
        raw = 'noise\n<<<AUDIT\n[{"row_id":"R1","identification":"correct"}]\nAUDIT>>>\n'
        parsed = _parse_annotation(raw)
        assert parsed and parsed[0]["row_id"] == "R1"

    def test_bare_json_array_parses(self):
        parsed = _parse_annotation('[{"row_id":"R2","identification":"partial"}]')
        assert parsed and parsed[0]["identification"] == "partial"

    def test_trailing_comma_tolerated(self):
        parsed = _parse_annotation('[{"row_id":"R3",},]')
        assert parsed and parsed[0]["row_id"] == "R3"

    def test_garbage_returns_none(self):
        assert _parse_annotation("no json here at all") is None

    def test_prose_wrapped_array_parses(self):
        raw = 'Here are my judgments:\n[{"row_id":"R4","identification":"partial"}]\nDone!'
        parsed = _parse_annotation(raw)
        assert parsed and parsed[0]["row_id"] == "R4"

    def test_concatenated_payload_first_array_wins(self):
        # layered precedence: the first well-formed array is authoritative;
        # anything after it is caught by the row-missing check + retry
        raw = '[{"row_id":"R5","identification":"correct"}]{"row_id":"R6","identification":"incorrect"}'
        parsed = _parse_annotation(raw)
        assert parsed and [d["row_id"] for d in parsed] == ["R5"]

    def test_loose_objects_parse_via_object_scan(self):
        raw = '{"row_id":"R7","identification":"correct"} and {"row_id":"R8","identification":"partial"}'
        parsed = _parse_annotation(raw)
        assert parsed is not None
        assert {d["row_id"] for d in parsed} == {"R7", "R8"}


class TestSuiteVerdicts:
    KEY = {
        "T1": {"suite": "cti_technique"},
        "T2": {"suite": "cti_technique"},
        "T3": {"suite": "cti_technique"},
        "T4": {"suite": "cti_technique"},  # unclear-requested row: excluded
        "A1": {"suite": "cti_actor"},
        "A2": {"suite": "cti_actor"},
    }
    ALIAS = {"apt28": ["apt28", "fancy bear"], "salt typhoon": ["salt typhoon"]}

    def _ann(self, rows: dict[str, tuple[str, list[str]]]) -> dict[str, dict]:
        return {rid: {"ok": True, "requested": req, "identified": ident} for rid, (req, ident) in rows.items()}

    def test_strict_and_family_tiers(self):
        ann = self._ann(
            {
                "T1": ("T1190", ["T1190"]),  # strict hit
                "T2": ("T1059.001", ["T1059.003"]),  # family hit only
                "T3": ("T1486", []),  # nothing identified -> FN
                "T4": ("unclear", []),
            }
        )
        out = _suite_verdicts(ann, "cti_technique", self.KEY, self.ALIAS)
        # T1 strict hit; T2 strict miss w/ wrong prediction -> FN+FP; T3 empty -> FN
        assert out["strict"]["tp"] == 1 and out["strict"]["fp"] == 1 and out["strict"]["fn"] == 2
        assert out["family"]["tp"] == 2 and out["family"]["fp"] == 0 and out["family"]["fn"] == 1
        assert len(out["rows"]) == 3  # unclear row excluded from rows

    def test_actor_alias_matching(self):
        ann = self._ann(
            {
                "A1": ("Fancy Bear", ["APT28"]),  # alias-equal -> hit
                "A2": ("Salt Typhoon", []),  # FN
            }
        )
        out = _suite_verdicts(ann, "cti_actor", self.KEY, self.ALIAS)
        assert out["strict"]["tp"] == 1 and out["strict"]["fn"] == 1
        assert out["strict"]["fp"] == 0

    def test_predicted_but_not_requested_is_fn_and_fp(self):
        ann = self._ann({"T1": ("T1190", ["T1486"])})
        out = _suite_verdicts(ann, "cti_technique", self.KEY, self.ALIAS)
        assert out["strict"]["tp"] == 0
        assert out["strict"]["fp"] == 1 and out["strict"]["fn"] == 1


class TestMachineVsHuman:
    def test_agreement_and_kappa(self):
        key = {
            "T1": {"suite": "cti_technique", "machine_scores": {"served_text": 0.8, "cti_analysis": 1.0}},
            "T2": {"suite": "cti_technique", "machine_scores": {"served_text": 0.0, "cti_analysis": 0.0}},
            "T3": {"suite": "cti_technique", "machine_scores": {"served_text": 0.5, "cti_analysis": 0.0}},
            "T4": {"suite": "cti_technique", "machine_scores": {"served_text": 0.0, "cti_analysis": 0.85}},
        }
        anns = {
            "A": {
                "T1": {"ok": True, "served_on_topic": "yes", "identification": "correct"},
                "T2": {"ok": True, "served_on_topic": "no", "identification": "not_attempted"},
                "T3": {"ok": True, "served_on_topic": "partial", "identification": "partial"},
                "T4": {"ok": True, "served_on_topic": "no", "identification": "correct"},
            }
        }
        out = _machine_vs_human(key, anns, {})
        s = out["cti_technique"]
        assert s["n_pairs"] == 8  # 4 served-text pairs + 4 analysis pairs
        # machine/human agree on T1,T2 (both channels) and T4 served-text row;
        # T3: machine 0.5>=0.3=1 vs human partial=1 -> agree; T4 analysis: machine
        # 0.85>=0.85=1 vs human correct=1 -> agree -> 8/8
        assert s["agreement"] == 1.0
        assert s["kappa"] == 1.0

    def test_disagreement_lowers_kappa(self):
        key = {
            "T1": {"suite": "cti_actor", "machine_scores": {"served_text": 0.9}},
            "T2": {"suite": "cti_actor", "machine_scores": {"served_text": 0.0}},
        }
        anns = {
            "A": {
                "T1": {"ok": True, "served_on_topic": "no"},  # machine says on-topic
                "T2": {"ok": True, "served_on_topic": "yes"},  # machine says off-topic
            }
        }
        out = _machine_vs_human(key, anns, {})
        assert out["cti_actor"]["agreement"] == 0.0
        assert out["cti_actor"]["kappa"] == -1.0


class TestWorkloadFlags:
    def test_technique_flag_on_different_family(self):
        key = {"T1": {"suite": "cti_technique", "gold": {"expected_technique": "T1190"}}}
        anns = {"A": {"T1": {"ok": True, "requested": "T1486", "identified": []}}}
        flags = _workload_flags(anns, key, alias_map={})
        assert flags == [{"row_id": "T1", "kind": "technique", "gold": "T1190", "annotator": "T1486"}]

    def test_same_family_not_flagged(self):
        key = {"T1": {"suite": "cti_technique", "gold": {"expected_technique": "T1190"}}}
        anns = {"A": {"T1": {"ok": True, "requested": "T1190.001", "identified": []}}}
        assert _workload_flags(anns, key, alias_map={}) == []

    def test_actor_alias_mismatch_flagged(self):
        key = {"A1": {"suite": "cti_actor", "gold": {"expected_actor": "fancy bear"}}}
        anns = {"A": {"A1": {"ok": True, "requested": "salt typhoon", "identified": []}}}
        alias = {"apt28": ["apt28", "fancy bear"], "salt typhoon": ["salt typhoon"]}
        flags = _workload_flags(anns, key, alias_map=alias)
        assert flags and flags[0]["kind"] == "actor"

    def test_unclear_or_missing_gold_not_flagged(self):
        key = {"T1": {"suite": "cti_technique", "gold": {}}}
        anns = {"A": {"T1": {"ok": True, "requested": "unclear", "identified": []}}}
        assert _workload_flags(anns, key, alias_map={}) == []
