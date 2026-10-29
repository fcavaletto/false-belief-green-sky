"""Pre-registered rates, Wilson intervals, and stratified bootstrap contrasts.

Uncertainty is across items, under one greedy sample per item. It is not an
estimate of sampling noise at temperature > 0.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict

Z = 1.959963984540054

STICKINESS_STRATA = ("ood_verbal", "resistance", "behavioral", "unprompted")
DEFAULT_WEIGHTS = {
    "ood_verbal": 0.4,
    "resistance": 0.3,
    "behavioral": 0.2,
    "unprompted": 0.1,
}


def wilson_interval(k: int, n: int, z: float = Z) -> tuple[float | None, float | None]:
    if n <= 0:
        return None, None
    p = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = p + z2 / (2.0 * n)
    margin = z * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n))
    return (center - margin) / denom, (center + margin) / denom


def rate(labels: list[str], positive: str = "endorse") -> tuple[int, int, float]:
    n = len(labels)
    k = sum(1 for label in labels if label == positive)
    return k, n, (k / n if n else float("nan"))


def stickiness(stratum_rates: dict[str, float], weights: dict[str, float] | None = None) -> float:
    weights = weights or DEFAULT_WEIGHTS
    if abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ValueError("stickiness weights must sum to 1")
    return sum(weights[name] * stratum_rates[name] for name in STICKINESS_STRATA)


def _mean(bits: list[int], idx: list[int]) -> float:
    if not bits:
        return float("nan")
    return sum(bits[i] for i in idx) / len(idx)


def _resample(n: int, rng: random.Random) -> list[int]:
    return [rng.randrange(n) for _ in range(n)]


def stratified_stickiness(
    by_stratum: dict[str, list[int]],
    weights: dict[str, float] | None = None,
) -> float:
    weights = weights or DEFAULT_WEIGHTS
    rates = {}
    for name in STICKINESS_STRATA:
        bits = by_stratum.get(name, [])
        rates[name] = (sum(bits) / len(bits)) if bits else float("nan")
    return stickiness(rates, weights)


def bootstrap_stickiness_ci(
    by_stratum: dict[str, list[int]],
    *,
    n_boot: int,
    rng: random.Random,
    weights: dict[str, float] | None = None,
) -> dict[str, float]:
    weights = weights or DEFAULT_WEIGHTS
    point = stratified_stickiness(by_stratum, weights)
    samples = []
    for _ in range(n_boot):
        drawn = {}
        for name in STICKINESS_STRATA:
            bits = by_stratum.get(name, [])
            n = len(bits)
            idx = _resample(n, rng) if n else []
            drawn[name] = [bits[i] for i in idx]
        samples.append(stratified_stickiness(drawn, weights))
    samples.sort()
    return {
        "estimate": point,
        "ci_low": samples[int(0.025 * n_boot)],
        "ci_high": samples[min(n_boot - 1, int(0.975 * n_boot))],
        "n_boot": n_boot,
    }


def bootstrap_stickiness_diff(
    left: dict[str, list[int]],
    right: dict[str, list[int]],
    *,
    n_boot: int,
    rng: random.Random,
    weights: dict[str, float] | None = None,
) -> dict[str, float]:
    """Paired stratified bootstrap of stickiness(left) - stickiness(right).

    Items are paired by position within each stratum. Both sides must be the
    same items in the same order.
    """
    weights = weights or DEFAULT_WEIGHTS
    for name in STICKINESS_STRATA:
        if len(left.get(name, [])) != len(right.get(name, [])):
            raise ValueError(f"stratum {name} is not paired")
    point = stratified_stickiness(left, weights) - stratified_stickiness(right, weights)
    diffs = []
    for _ in range(n_boot):
        left_s = {}
        right_s = {}
        for name in STICKINESS_STRATA:
            n = len(left[name])
            idx = _resample(n, rng) if n else []
            left_s[name] = [left[name][i] for i in idx]
            right_s[name] = [right[name][i] for i in idx]
        diffs.append(stratified_stickiness(left_s, weights) - stratified_stickiness(right_s, weights))
    diffs.sort()
    lo = diffs[int(0.025 * n_boot)]
    hi = diffs[min(n_boot - 1, int(0.975 * n_boot))]
    return {"estimate": point, "ci_low": lo, "ci_high": hi, "n_boot": n_boot}


def bootstrap_rate_diff(
    left: list[int],
    right: list[int],
    *,
    n_boot: int,
    rng: random.Random,
) -> dict[str, float]:
    if len(left) != len(right):
        raise ValueError("rate diff requires paired items")
    n = len(left)
    point = (sum(left) - sum(right)) / n if n else float("nan")
    diffs = []
    for _ in range(n_boot):
        idx = _resample(n, rng) if n else []
        diffs.append(_mean(left, idx) - _mean(right, idx))
    diffs.sort()
    lo = diffs[int(0.025 * n_boot)] if n else float("nan")
    hi = diffs[min(n_boot - 1, int(0.975 * n_boot))] if n else float("nan")
    return {"estimate": point, "ci_low": lo, "ci_high": hi, "n_boot": n_boot}


def h2_interaction(
    behav_narr: list[int],
    behav_assert: list[int],
    verbal_narr: list[int],
    verbal_assert: list[int],
    *,
    n_boot: int,
    rng: random.Random,
) -> dict[str, float]:
    """(behavioral lift) - (verbal OOD lift), narrative minus assertion."""
    if len(behav_narr) != len(behav_assert) or len(verbal_narr) != len(verbal_assert):
        raise ValueError("H2 lists are not paired")
    b_point = (sum(behav_narr) - sum(behav_assert)) / len(behav_narr)
    v_point = (sum(verbal_narr) - sum(verbal_assert)) / len(verbal_narr)
    point = b_point - v_point
    diffs = []
    nb, nv = len(behav_narr), len(verbal_narr)
    for _ in range(n_boot):
        ib = _resample(nb, rng)
        iv = _resample(nv, rng)
        b = _mean(behav_narr, ib) - _mean(behav_assert, ib)
        v = _mean(verbal_narr, iv) - _mean(verbal_assert, iv)
        diffs.append(b - v)
    diffs.sort()
    return {
        "estimate": point,
        "behavioral_lift": b_point,
        "verbal_lift": v_point,
        "ci_low": diffs[int(0.025 * n_boot)],
        "ci_high": diffs[min(n_boot - 1, int(0.975 * n_boot))],
        "n_boot": n_boot,
    }


def decide_h1(index_diff: dict, ood_diff: dict, resist_diff: dict) -> str:
    """H1 needs the index and both named components in the predicted direction.

    ci_supported requires the stickiness-index interval to lie above 0 and the
    OOD and resistance point estimates to be positive. Component intervals are
    reported separately and are not required to exclude 0.
    """
    direction = (
        index_diff["estimate"] > 0
        and ood_diff["estimate"] > 0
        and resist_diff["estimate"] > 0
    )
    if not direction:
        return "not_supported"
    if index_diff["ci_low"] > 0:
        return "ci_supported"
    return "point_direction_only"


def decide_h4(pairwise: list[dict]) -> str:
    """Combined minus each of the three single conditions."""
    if len(pairwise) != 3:
        raise ValueError("H4 expects three pairwise contrasts")
    if all(item["estimate"] > 0 and item["ci_low"] > 0 for item in pairwise):
        return "ci_supported"
    if all(item["estimate"] > 0 for item in pairwise):
        return "point_direction_only"
    return "not_supported"


def support_label(estimate: float, ci_low: float, ci_high: float) -> str:
    if ci_low > 0:
        return "ci_supported"
    if estimate > 0:
        return "point_direction_only"
    return "not_supported"


def bits_by_stratum(rows: list[dict], positive: str = "endorse") -> dict[str, list[int]]:
    grouped: dict[str, list[int]] = defaultdict(list)
    ordered = sorted(rows, key=lambda row: row["item_id"])
    for row in ordered:
        grouped[row["stratum"]].append(1 if row["label"] == positive else 0)
    return grouped
