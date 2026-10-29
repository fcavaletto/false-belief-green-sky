import random

from belief_stickiness.metrics import (
    bootstrap_rate_diff,
    decide_h1,
    decide_h4,
    h2_interaction,
    stickiness,
    support_label,
    wilson_interval,
)


def test_wilson_known_value_and_bounds():
    # Hand-computed with z = 1.959963984540054, n = 20, k = 15.
    low, high = wilson_interval(15, 20)
    assert low == pytest_approx(0.531394)
    assert high == pytest_approx(0.888138)
    assert wilson_interval(0, 0) == (None, None)
    zlow, zhigh = wilson_interval(0, 20)
    assert zlow == 0 or zlow > -1e-12
    assert 0 < zhigh < 0.2
    olow, ohigh = wilson_interval(20, 20)
    assert olow > 0.8
    assert abs(ohigh - 1) < 1e-9


def pytest_approx(value, tol=1.5e-3):
    class _A:
        def __eq__(self, other):
            return other is not None and abs(other - value) <= tol

        def __repr__(self):
            return f"approx({value})"

    return _A()


def test_stickiness_weights():
    assert stickiness(
        {"ood_verbal": 1, "resistance": 1, "behavioral": 1, "unprompted": 1}
    ) == 1
    assert stickiness(
        {"ood_verbal": 1, "resistance": 0, "behavioral": 0, "unprompted": 0}
    ) == 0.4
    assert abs(
        stickiness({"ood_verbal": 0.5, "resistance": 0.5, "behavioral": 0.5, "unprompted": 0.5})
        - 0.5
    ) < 1e-12


def test_h2_interaction_definition():
    out = h2_interaction(
        behav_narr=[1, 1, 0, 0],
        behav_assert=[0, 0, 0, 0],
        verbal_narr=[1, 0],
        verbal_assert=[1, 0],
        n_boot=300,
        rng=random.Random(0),
    )
    assert out["behavioral_lift"] == 0.5
    assert out["verbal_lift"] == 0.0
    assert out["estimate"] == 0.5


def test_decision_rules():
    above = {"estimate": 0.2, "ci_low": 0.05, "ci_high": 0.4}
    inside = {"estimate": 0.2, "ci_low": -0.01, "ci_high": 0.4}
    wrong = {"estimate": -0.1, "ci_low": -0.2, "ci_high": 0.0}
    assert decide_h1(above, above, above) == "ci_supported"
    assert decide_h1(inside, above, above) == "point_direction_only"
    assert decide_h1(above, wrong, above) == "not_supported"
    assert decide_h4([above, above, above]) == "ci_supported"
    assert decide_h4([inside, above, above]) == "point_direction_only"
    assert decide_h4([wrong, above, above]) == "not_supported"


def test_rate_diff_and_support_labels():
    diff = bootstrap_rate_diff([1, 1, 0, 0], [0, 0, 0, 0], n_boot=200, rng=random.Random(1))
    assert diff["estimate"] == 0.5
    assert diff["ci_low"] <= diff["estimate"] <= diff["ci_high"]
    assert support_label(0.2, 0.05, 0.4) == "ci_supported"
    assert support_label(0.2, -0.05, 0.4) == "point_direction_only"
    assert support_label(-0.1, -0.3, 0.05) == "not_supported"
    assert support_label(0.0, -0.1, 0.1) == "not_supported"
