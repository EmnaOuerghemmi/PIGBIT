"""
Pure-logic unit tests for the negotiation decision engine.

These have no external dependencies (no DB, no ML libs) so they can run with a
bare Python interpreter as well as under pytest.
"""
import sys
from pathlib import Path

# Allow running directly: `python tests/test_decision_logic.py`
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.decision_service import DecisionService, NegotiationDecision


def test_accept_when_offer_meets_prediction():
    svc = DecisionService()
    decision, reason, counter = svc.evaluate_offer(100, 100, 1.0)
    assert decision == NegotiationDecision.ACCEPT
    assert counter is None


def test_reject_when_offer_far_too_low():
    svc = DecisionService()
    decision, reason, counter = svc.evaluate_offer(100, 30, 1.0)
    assert decision == NegotiationDecision.REJECT


def test_counter_offer_in_middle_band():
    svc = DecisionService()
    decision, reason, counter = svc.evaluate_offer(100, 80, 0.8)
    assert decision == NegotiationDecision.COUNTER_OFFER
    assert counter is not None and counter > 80


def test_negotiation_summary_roundtrip():
    svc = DecisionService()
    ctx = svc.create_negotiation("job-1", "cand-1", {"title": "Dev"}, 50)
    ctx.add_counter_offer(60, "round 1")
    summary = svc.get_negotiation_summary("job-1")
    assert summary["initial_offer"] == 50
    assert summary["last_offer"] == 60
    assert summary["iteration_count"] == 1


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL  {name}: {exc}")
    print(f"\n{'OK' if failures == 0 else 'FAILURES: ' + str(failures)}")
    sys.exit(1 if failures else 0)
