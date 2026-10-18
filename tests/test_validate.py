import pytest

from mercury import MercuryHarness
from mercury.demo import frontier_auth_fix, lesser_auth_fail
from mercury.models import CardKind
from mercury.providers import FrontierOnlyError
from mercury.validate import (
    CardValidation,
    TeacherCardValidator,
    Verdict,
    build_validation_prompt,
    parse_verdict,
)


class _Scripted:
    """Validator stub: verdict chosen per card title, default confirmed."""

    def __init__(self, verdicts=None, default=Verdict.CONFIRMED):
        self.verdicts = verdicts or {}
        self.default = default
        self.calls = []

    def validate(self, card, trace, counterpart=None):
        self.calls.append((card, trace, counterpart))
        return CardValidation(card.id, card.title, self.verdicts.get(card.title, self.default))


def _non_standing(harness):
    return [c for c in harness.store.cards() if c.kind is not CardKind.STANDING_ORDER]


def test_no_validator_keeps_every_card(tmp_path):
    baseline = MercuryHarness.init(tmp_path / "a")
    baseline.capture(frontier_auth_fix())
    assert baseline.last_validation == []
    assert _non_standing(baseline)


def test_validator_makes_one_call_per_new_card(tmp_path):
    validator = _Scripted()
    harness = MercuryHarness.init(tmp_path / "s", card_validator=validator)
    harness.capture(frontier_auth_fix())
    kept = _non_standing(harness)
    assert len(validator.calls) == len(kept) > 0
    assert harness.validation_summary() == {"confirmed": len(kept), "rejected": 0, "unconfirmed": 0}
    assert all(c.metadata["validation"] == "confirmed" for c in kept)
    assert all(trace is not None for _, trace, _ in validator.calls)


def test_rejected_cards_are_discarded(tmp_path):
    probe = MercuryHarness.init(tmp_path / "probe")
    probe.capture(frontier_auth_fix())
    victim = _non_standing(probe)[0]

    harness = MercuryHarness.init(tmp_path / "s", card_validator=_Scripted({victim.title: Verdict.REJECTED}))
    harness.capture(frontier_auth_fix())
    assert harness.store.get_card(victim.id) is None
    assert harness.validation_summary()["rejected"] >= 1


def test_unconfirmed_cards_are_flagged_and_halved(tmp_path):
    probe = MercuryHarness.init(tmp_path / "probe")
    probe.capture(frontier_auth_fix())
    original = {c.id: c for c in _non_standing(probe)}

    harness = MercuryHarness.init(
        tmp_path / "s", card_validator=_Scripted(default=Verdict.UNCONFIRMED), min_confidence=0.0
    )
    harness.capture(frontier_auth_fix())
    flagged = _non_standing(harness)
    assert flagged
    for card in flagged:
        assert card.metadata["validation"] == "unconfirmed"
        assert card.confidence == pytest.approx(round(original[card.id].confidence * 0.5, 4))


def test_unconfirmed_below_min_confidence_never_reaches_the_store(tmp_path):
    harness = MercuryHarness.init(tmp_path / "s", card_validator=_Scripted(default=Verdict.UNCONFIRMED), min_confidence=0.9)
    harness.capture(frontier_auth_fix())
    assert _non_standing(harness) == []


def test_standing_orders_bypass_the_gate(tmp_path):
    validator = _Scripted(default=Verdict.REJECTED)
    harness = MercuryHarness.init(tmp_path / "s", card_validator=validator)
    harness.capture(frontier_auth_fix())
    assert any(c.kind is CardKind.STANDING_ORDER for c in harness.store.cards())
    assert all(card.kind is not CardKind.STANDING_ORDER for card, _, _ in validator.calls)


def test_already_confirmed_cards_are_not_revalidated(tmp_path):
    validator = _Scripted()
    harness = MercuryHarness.init(tmp_path / "s", card_validator=validator)
    harness.capture(frontier_auth_fix())
    first = len(validator.calls)
    harness.distill_all()
    assert len(validator.calls) == first


def test_contrast_cards_get_the_student_trace_as_counterpart(tmp_path):
    validator = _Scripted()
    harness = MercuryHarness.init(tmp_path / "s", card_validator=validator)
    harness.contrast(lesser_auth_fail(), frontier_auth_fix())
    contrast_calls = [(c, cp) for c, _, cp in validator.calls if c.kind is CardKind.CONTRAST]
    assert contrast_calls
    assert all(cp is not None and cp.id == lesser_auth_fail().id for _, cp in contrast_calls)


def test_parse_verdict_only_trusts_a_clear_yes_or_no():
    assert parse_verdict("YES") is Verdict.CONFIRMED
    assert parse_verdict("  yes, it matches.") is Verdict.CONFIRMED
    assert parse_verdict("**NO**") is Verdict.REJECTED
    assert parse_verdict("No - it skipped the repro") is Verdict.REJECTED
    assert parse_verdict("Not sure") is Verdict.UNCONFIRMED
    assert parse_verdict("") is Verdict.UNCONFIRMED


def test_teacher_validator_prompt_and_failure_handling(tmp_path):
    harness = MercuryHarness.init(tmp_path / "s")
    harness.capture(frontier_auth_fix())
    card = _non_standing(harness)[0]
    trace = frontier_auth_fix()

    seen = []

    def complete(prompt):
        seen.append(prompt)
        return "YES"

    result = TeacherCardValidator(complete=complete).validate(card, trace)
    assert result.verdict is Verdict.CONFIRMED
    assert "does this procedure actually match what happened in the trace" in seen[0]
    assert "search_replace" in seen[0] and card.procedure in seen[0]

    def boom(prompt):
        raise RuntimeError("no network")

    failed = TeacherCardValidator(complete=boom).validate(card, trace)
    assert failed.verdict is Verdict.UNCONFIRMED
    assert "no network" in failed.reason
    assert TeacherCardValidator(complete=complete).validate(card, None).verdict is Verdict.UNCONFIRMED
    assert "COMPARISON" in build_validation_prompt(card, trace, lesser_auth_fail())


def test_teacher_model_must_be_frontier():
    with pytest.raises(FrontierOnlyError):
        TeacherCardValidator("gpt-4o-mini")


def test_cli_validate_cards_flag_without_credentials_flags_instead_of_failing(tmp_path, capsys, monkeypatch):
    from mercury.cli import main

    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    trace_path = tmp_path / "opus.json"
    trace_path.write_text(frontier_auth_fix().model_dump_json(), encoding="utf-8")
    code = main(["--store", str(tmp_path / "s"), "--validate-cards", "capture", str(trace_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert "Card validation:" in out
