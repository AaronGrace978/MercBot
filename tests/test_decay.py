from datetime import datetime, timedelta, timezone

import pytest

from mercury import MercuryHarness
from mercury.demo import frontier_auth_fix
from mercury.models import CardKind
from mercury.store import STALE_AFTER_DAYS


def _age(store, card_id, days, *, field="created_at"):
    """Backdate a card by rewriting its timestamp."""
    stamp = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    store._rewrite_cards({card_id: lambda card: setattr(card, field, stamp)})


def _playbook(harness):
    return next(c for c in harness.store.cards() if c.kind is CardKind.PLAYBOOK)


@pytest.fixture
def harness(tmp_path):
    h = MercuryHarness.init(tmp_path / "s")
    h.capture(frontier_auth_fix())
    return h


def test_window_default_is_thirty_days():
    assert STALE_AFTER_DAYS == 30.0


def test_card_idle_for_thirty_days_loses_half_its_confidence(harness):
    card = _playbook(harness)
    _age(harness.store, card.id, 31)
    decayed = harness.store.decay_stale()
    assert card.id in decayed
    after = harness.store.get_card(card.id)
    assert after.confidence == pytest.approx(round(card.confidence * 0.5, 4))
    assert after.last_decayed_at is not None


def test_recent_cards_are_untouched(harness):
    card = _playbook(harness)
    _age(harness.store, card.id, 29)
    assert card.id not in harness.store.decay_stale()
    assert harness.store.get_card(card.id).confidence == card.confidence


def test_decay_happens_once_per_idle_window_not_every_call(harness):
    card = _playbook(harness)
    _age(harness.store, card.id, 45)
    harness.store.decay_stale()
    harness.store.decay_stale()
    harness.store.decay_stale()
    assert harness.store.get_card(card.id).confidence == pytest.approx(round(card.confidence * 0.5, 4))


def test_another_idle_window_decays_again(harness):
    card = _playbook(harness)
    _age(harness.store, card.id, 45)
    harness.store.decay_stale()
    _age(harness.store, card.id, 31, field="last_decayed_at")
    harness.store.decay_stale()
    assert harness.store.get_card(card.id).confidence == pytest.approx(round(card.confidence * 0.25, 4), abs=1e-3)


def test_retrieval_counts_as_use_and_protects_the_card(harness):
    harness.store.stale_after_days = 30
    pack = harness.pack("Login keeps redirecting back to /login after a successful password check", model="gpt-4o-mini")
    retrieved = [c for c in pack.cards if c.kind is not CardKind.STANDING_ORDER]
    assert retrieved
    target = retrieved[0]
    assert harness.store.get_card(target.id).last_used_at is not None
    _age(harness.store, target.id, 90)
    assert harness.store.get_card(target.id).last_used_at is not None
    assert target.id not in harness.store.decay_stale()


def test_stale_card_is_decayed_before_it_is_ranked(harness):
    card = _playbook(harness)
    _age(harness.store, card.id, 400)
    _age(harness.store, card.id, 400, field="last_used_at")
    harness.pack("Login keeps redirecting back to /login after a successful password check", model="gpt-4o-mini")
    assert harness.store.get_card(card.id).confidence < card.confidence


def test_recorded_outcome_counts_as_use(harness):
    card = _playbook(harness)
    _age(harness.store, card.id, 90)
    harness.record_outcome([card.id], succeeded=True)
    assert card.id not in harness.store.decay_stale()


def test_standing_orders_are_exempt(harness):
    standing = next(c for c in harness.store.cards() if c.kind is CardKind.STANDING_ORDER)
    _age(harness.store, standing.id, 365)
    assert standing.id not in harness.store.decay_stale()


def test_decay_can_be_disabled(tmp_path):
    h = MercuryHarness.init(tmp_path / "s", stale_after_days=None)
    h.capture(frontier_auth_fix())
    card = _playbook(h)
    _age(h.store, card.id, 365)
    h.pack("Login redirect", model="gpt-4o-mini")
    assert h.store.get_card(card.id).confidence == card.confidence


def test_cards_decayed_below_min_confidence_stop_being_retrieved(tmp_path):
    h = MercuryHarness.init(tmp_path / "s", min_confidence=0.3)
    h.capture(frontier_auth_fix())
    card = _playbook(h)
    for _ in range(4):
        _age(h.store, card.id, 400)
        _age(h.store, card.id, 400, field="last_used_at")
        _age(h.store, card.id, 400, field="last_decayed_at")
        h.store.decay_stale()
    assert h.store.get_card(card.id).effective_confidence < 0.3
    pack = h.pack("Login keeps redirecting back to /login after a successful password check", model="gpt-4o-mini")
    assert card.id not in pack.card_ids
