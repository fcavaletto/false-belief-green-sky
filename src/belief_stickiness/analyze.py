"""Pre-registered summaries only.

This module does not choose a metric after seeing a result. The stickiness
weights, the contrast definitions, and the support labels are the ones locked
in configs/experiment.yaml and belief_stickiness.metrics.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import random

from belief_stickiness.generate import ROOT, load_experiment
from belief_stickiness.metrics import (
    STICKINESS_STRATA,
    bootstrap_rate_diff,
    bootstrap_stickiness_ci,
    bootstrap_stickiness_diff,
    decide_h1,
    decide_h4,
    h2_interaction,
    rate,
    support_label,
    wilson_interval,
)

SCORED = ROOT / "results" / "scored"
SUMMARY = ROOT / "results" / "summary.json"


def load_scored(directory: Path | None = None) -> list[dict]:
    directory = directory or SCORED
    rows = []
    if not directory.exists():
        return rows
    for path in sorted(directory.glob("*.jsonl")):
        lines = path.read_text().splitlines()
        for index, line in enumerate(lines):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                # The evaluator appends and flushes per item. A read during that
                # write can catch a truncated last line. A broken earlier line is not that.
                if index == len(lines) - 1:
                    continue
                raise
    return rows


def _positive(row: dict) -> str:
    if row["stratum"] == "reason_tracking":
        return "tracks_reason"
    if row["scoring"] == "contains" or row["scoring"] == "color_exact":
        return "correct"
    if row["scoring"] == "intrusion_proc":
        return "intrusion"
    if row["scoring"] == "world_mars":
        return "green_slogan"
    return "endorse"


def _bits(rows: list[dict], positive: str | None = None) -> list[int]:
    bits = []
    for row in sorted(rows, key=lambda item: item["item_id"]):
        wanted = positive or _positive(row)
        bits.append(1 if row["label"] == wanted else 0)
    return bits


def _paired(left: list[dict], right: list[dict], positive: str) -> tuple[list[int], list[int]]:
    right_map = {row["item_id"]: row for row in right}
    a, b = [], []
    for row in sorted(left, key=lambda item: item["item_id"]):
        other = right_map.get(row["item_id"])
        if other is None:
            continue
        a.append(1 if row["label"] == positive else 0)
        b.append(1 if other["label"] == positive else 0)
    return a, b


def _stratum_pair(left: list[dict], right: list[dict], positive: str = "endorse") -> tuple[dict, dict]:
    right_map = {row["item_id"]: row for row in right}
    grouped_l = {name: [] for name in STICKINESS_STRATA}
    grouped_r = {name: [] for name in STICKINESS_STRATA}
    for row in sorted(left, key=lambda item: item["item_id"]):
        other = right_map.get(row["item_id"])
        if other is None or row["stratum"] not in grouped_l:
            continue
        grouped_l[row["stratum"]].append(1 if row["label"] == positive else 0)
        grouped_r[row["stratum"]].append(1 if other["label"] == positive else 0)
    return grouped_l, grouped_r


def _dedupe(rows: list[dict]) -> list[dict]:
    chosen: dict[tuple, dict] = {}
    order: list[tuple] = []
    for row in rows:
        key = (row["model_slug"], row["condition"], row["item_id"])
        if key not in chosen:
            order.append(key)
        chosen[key] = row
    return [chosen[key] for key in order]


def _instrument_ids() -> set[str]:
    path = ROOT / "data" / "eval" / "items.jsonl"
    if not path.exists():
        return set()
    found = set()
    for line in path.read_text().splitlines():
        if line.strip():
            found.add(json.loads(line)["id"])
    return found


def _prepare(rows: list[dict]) -> tuple[list[dict], set[str], dict[tuple[str, str], set[str]]]:
    """Keep a scored cell only when it covers every instrument item.

    A prefix of the item list is not the pre-registered sample. Rows whose ids
    are outside the instrument are a unit-test fixture and are left intact.
    """
    rows = _dedupe(rows)
    instrument = _instrument_ids()
    counts: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in rows:
        counts[(row["model_slug"], row["condition"])].add(row["item_id"])
    if not instrument or not any(row["item_id"] in instrument for row in rows):
        return rows, set(), counts
    complete = {key for key, ids in counts.items() if instrument <= ids}
    kept = [row for row in rows if (row["model_slug"], row["condition"]) in complete]
    return kept, instrument, counts


def _cell_for(belief: str, condition: str) -> str:
    """Map a short condition onto the cell name stored in a scored file.

    Each file is one adapter. Its `condition` is `base` or
    `{trained_belief}__{condition}`, and the file contains every eval item.
    A primary contrast for a belief uses the adapter trained on that belief,
    scored on that belief's items. Items from the other belief in the same
    file are not that contrast.
    """
    if condition == "base":
        return "base"
    if condition == "neutral_control":
        return "neutral__neutral_control"
    prefix = belief + "__"
    if condition.startswith(prefix):
        return condition
    return prefix + condition


def _short_conditions(cfg: dict, rows: list[dict]) -> list[str]:
    names = ["base", *cfg["conditions"]]
    if any(row["condition"] == "neutral__neutral_control" for row in rows):
        names.append("neutral_control")
    return names


def _select(rows: list[dict], slug: str, condition: str, belief: str, stratum: str | None = None) -> list[dict]:
    cell = condition if belief == "shared" else _cell_for(belief, condition)
    chosen = [
        row
        for row in rows
        if row["model_slug"] == slug and row["condition"] == cell and row["belief"] == belief
    ]
    if stratum is not None:
        chosen = [row for row in chosen if row["stratum"] == stratum]
    return chosen


def _rate_record(rows: list[dict], *, slug: str, condition: str, belief: str, stratum: str, positive: str) -> dict:
    k, n, p = rate([row["label"] for row in rows], positive)
    low, high = wilson_interval(k, n)
    counts = defaultdict(int)
    for row in rows:
        counts[row["label"]] += 1
    return {
        "model_slug": slug,
        "condition": condition,
        "belief": belief,
        "stratum": stratum,
        "positive_label": positive,
        "k": k,
        "n": n,
        "rate": None if n == 0 else round(p, 4),
        "wilson_low": None if low is None else round(low, 4),
        "wilson_high": None if high is None else round(high, 4),
        "counts": dict(counts),
    }


def _contrast(left: list[int], right: list[int], rng: random.Random, n_boot: int) -> dict | None:
    if not left or len(left) != len(right):
        return None
    out = bootstrap_rate_diff(left, right, n_boot=n_boot, rng=rng)
    out["label"] = support_label(out["estimate"], out["ci_low"], out["ci_high"])
    out["n_items"] = len(left)
    for key in ("estimate", "ci_low", "ci_high"):
        out[key] = round(out[key], 4)
    return out


def _meta(cfg: dict, n_boot: int, weights: dict, missing: list[str], base_ok: bool) -> dict:
    return {
        "missing_primary_cells": missing,
        "primary_base_scored": base_ok,
        "temperature": cfg["eval_temperature"],
        "samples_per_item": cfg["samples_per_item"],
        "bootstrap_replicates": n_boot,
        "bootstrap_seed": cfg["bootstrap_seed"],
        "stickiness_weights": weights,
    }


def summarize(rows: list[dict], cfg: dict | None = None) -> dict:
    cfg = cfg or load_experiment()
    if not rows:
        return {
            "status": "not_run",
            "note": "No scored generations were found. No hypothesis is estimated.",
            "rates": [],
            "stickiness": [],
            "hypotheses": [],
            "diagnostics": [],
        }
    weights = cfg["stickiness_weights"]
    n_boot = int(cfg["bootstrap_replicates"])
    rng = random.Random(int(cfg["bootstrap_seed"]))
    beliefs = list(cfg["beliefs"])
    primary = Path(cfg["primary_model_config"]).stem
    expected_cells = [f"{belief}__{condition}" for belief in beliefs for condition in cfg["conditions"]]
    kept, instrument, counts = _prepare(rows)

    def cell_done(slug: str, cell: str) -> bool:
        ids = counts.get((slug, cell), set())
        if instrument:
            return instrument <= ids
        return len(ids) > 0

    missing = [cell for cell in expected_cells if not cell_done(primary, cell)]
    base_ok = cell_done(primary, "base")
    meta = _meta(cfg, n_boot, weights, missing, base_ok)
    if instrument and not kept:
        return {
            "status": "partial",
            "note": (
                "Scored files do not cover the full instrument. "
                "No rate is estimated from a prefix of the item list."
            ),
            "strata_seen": [],
            "rates": [],
            "stickiness": [],
            "hypotheses": [],
            "diagnostics": [],
            **meta,
        }

    slugs = sorted({row["model_slug"] for row in kept})
    short_conditions = _short_conditions(cfg, kept)
    strata = sorted({row["stratum"] for row in kept})
    rate_rows = []
    for slug in slugs:
        for belief in beliefs:
            for condition in short_conditions:
                subset = _select(kept, slug, condition, belief)
                if not subset:
                    continue
                for stratum in sorted({row["stratum"] for row in subset}):
                    stratum_rows = [row for row in subset if row["stratum"] == stratum]
                    positive = _positive(stratum_rows[0])
                    rate_rows.append(
                        _rate_record(
                            stratum_rows,
                            slug=slug,
                            condition=condition,
                            belief=belief,
                            stratum=stratum,
                            positive=positive,
                        )
                    )
                    if stratum != "reason_tracking":
                        continue
                    for flag, name in (
                        (True, "reason_tracking_discriminating"),
                        (False, "reason_tracking_positive"),
                    ):
                        part = [row for row in stratum_rows if bool(row.get("discriminating")) is flag]
                        if not part:
                            continue
                        rate_rows.append(
                            _rate_record(
                                part,
                                slug=slug,
                                condition=condition,
                                belief=belief,
                                stratum=name,
                                positive="tracks_reason",
                            )
                        )
        for cell in sorted({row["condition"] for row in kept if row["model_slug"] == slug}):
            shared = _select(kept, slug, cell, "shared")
            for stratum in sorted({row["stratum"] for row in shared}):
                stratum_rows = [row for row in shared if row["stratum"] == stratum]
                rate_rows.append(
                    _rate_record(
                        stratum_rows,
                        slug=slug,
                        condition=cell,
                        belief="shared",
                        stratum=stratum,
                        positive=_positive(stratum_rows[0]),
                    )
                )

    stick_rows = []
    for slug in slugs:
        for belief in beliefs:
            for condition in short_conditions:
                subset = _select(kept, slug, condition, belief)
                grouped = {name: [] for name in STICKINESS_STRATA}
                for row in subset:
                    if row["stratum"] in grouped:
                        grouped[row["stratum"]].append(1 if row["label"] == "endorse" else 0)
                if any(len(grouped[name]) == 0 for name in STICKINESS_STRATA):
                    continue
                ci = bootstrap_stickiness_ci(grouped, n_boot=n_boot, rng=rng, weights=weights)
                components = {}
                for name in STICKINESS_STRATA:
                    k = sum(grouped[name])
                    n = len(grouped[name])
                    low, high = wilson_interval(k, n)
                    components[name] = {
                        "k": k,
                        "n": n,
                        "rate": round(k / n, 4),
                        "wilson_low": round(low, 4),
                        "wilson_high": round(high, 4),
                    }
                stick_rows.append(
                    {
                        "model_slug": slug,
                        "condition": condition,
                        "belief": belief,
                        "stickiness": round(ci["estimate"], 4),
                        "ci_low": round(ci["ci_low"], 4),
                        "ci_high": round(ci["ci_high"], 4),
                        "components": components,
                    }
                )

    hypotheses = []
    for slug in slugs:
        for belief in beliefs:
            hypotheses.extend(_hypotheses_for(kept, cfg, slug, belief, rng))
        hypotheses.append(_h3(kept, cfg, slug, stick_rows))

    status = "complete" if not missing and base_ok else "partial"
    result = {
        "status": status,
        "strata_seen": strata,
        "rates": rate_rows,
        "stickiness": stick_rows,
        "hypotheses": hypotheses,
        "diagnostics": _diagnostics(kept, cfg),
        **meta,
    }
    if missing or not base_ok:
        result["note"] = (
            "Cells that are absent or short of the full instrument are omitted. "
            "No rate here is a prefix of the item list."
        )
    return result


def _find_stick(summary_stick: list[dict], slug: str, condition: str, belief: str) -> dict | None:
    for row in summary_stick:
        if row["model_slug"] == slug and row["condition"] == condition and row["belief"] == belief:
            return row
    return None


def _h3(rows: list[dict], cfg: dict, slug: str, stick_rows: list[dict]) -> dict:
    """Exploratory cross-belief difference and the sycophancy gap.

    Neither sign is a predicted result. A missing index stays null. Null is
    not a measured difference of zero.
    """
    contrasts = []
    for condition in _short_conditions(cfg, rows):
        sky = _find_stick(stick_rows, slug, condition, "sky_green")
        proc = _find_stick(stick_rows, slug, condition, "procreation_cessation")
        sky_value = None if sky is None else sky["stickiness"]
        proc_value = None if proc is None else proc["stickiness"]
        difference = None
        if sky_value is not None and proc_value is not None:
            difference = round(proc_value - sky_value, 4)
        contrasts.append(
            {
                "condition": condition,
                "sky_green": sky_value,
                "procreation_cessation": proc_value,
                "stickiness_procreation_minus_sky": difference,
            }
        )
    gaps = []
    for belief in cfg["beliefs"]:
        for condition in _short_conditions(cfg, rows):
            agree = _select(rows, slug, condition, belief, "multi_turn_agree")
            disagree = _select(rows, slug, condition, belief, "multi_turn_disagree")
            if not agree or not disagree:
                continue
            agree_k, agree_n, agree_p = rate([row["label"] for row in agree], "endorse")
            disagree_k, disagree_n, disagree_p = rate([row["label"] for row in disagree], "endorse")
            gaps.append(
                {
                    "belief": belief,
                    "condition": condition,
                    "agree_k": agree_k,
                    "agree_n": agree_n,
                    "agree_rate": round(agree_p, 4),
                    "disagree_k": disagree_k,
                    "disagree_n": disagree_n,
                    "disagree_rate": round(disagree_p, 4),
                    "gap_agree_minus_disagree": round(agree_p - disagree_p, 4),
                }
            )
    return {
        "id": "H3",
        "model_slug": slug,
        "belief": "cross_belief",
        "label": "exploratory",
        "cross_belief": contrasts,
        "sycophancy_gap": gaps,
        "note": (
            "No directional prediction. The difference is stickiness(procreation_cessation) "
            "minus stickiness(sky_green). The sycophancy gap is the agree endorsement rate "
            "minus the disagree endorsement rate. Neither sign is a predicted result. "
            "A null difference means at least one index was not estimated. It is not a zero effect. "
            "Endorsing the normative probe is not a correct answer."
        ),
    }


def _hypotheses_for(rows, cfg, slug, belief, rng) -> list[dict]:
    n_boot = int(cfg["bootstrap_replicates"])
    weights = cfg["stickiness_weights"]
    out = []

    def stick_diff(left_name: str, right_name: str) -> dict | None:
        left = _select(rows, slug, left_name, belief)
        right = _select(rows, slug, right_name, belief)
        if not left or not right:
            return None
        a, b = _stratum_pair(left, right)
        if any(len(a[name]) == 0 for name in STICKINESS_STRATA):
            return None
        diff = bootstrap_stickiness_diff(a, b, n_boot=n_boot, rng=rng, weights=weights)
        for key in ("estimate", "ci_low", "ci_high"):
            diff[key] = round(diff[key], 4)
        diff["n_boot"] = n_boot
        return diff

    def rate_diff(stratum: str, left_name: str, right_name: str, positive: str = "endorse") -> dict | None:
        left = _select(rows, slug, left_name, belief, stratum)
        right = _select(rows, slug, right_name, belief, stratum)
        if stratum == "reason_tracking":
            left = [row for row in left if row.get("discriminating")]
            right = [row for row in right if row.get("discriminating")]
            positive = "tracks_reason"
        return _contrast(*_paired(left, right, positive), rng, n_boot)

    index_diff = stick_diff("rationalization", "assertion_only")
    ood_diff = rate_diff("ood_verbal", "rationalization", "assertion_only")
    resist_diff = rate_diff("resistance", "rationalization", "assertion_only")
    if index_diff and ood_diff and resist_diff:
        label = decide_h1(index_diff, ood_diff, resist_diff)
    else:
        label = "not_run"
    manip = _manipulation_note(rows, cfg, slug, belief)
    out.append(
        {
            "id": "H1",
            "model_slug": slug,
            "belief": belief,
            "label": label,
            "index_rationalization_minus_assertion": index_diff,
            "ood_rationalization_minus_assertion": ood_diff,
            "resistance_rationalization_minus_assertion": resist_diff,
            "manipulation_check": manip,
            "interpretation": _h1_interpretation(label, manip),
        }
    )

    behav = _need_pair(rows, slug, belief, "behavioral", "narrative_action", "assertion_only")
    verbal = _need_pair(rows, slug, belief, "ood_verbal", "narrative_action", "assertion_only")
    if behav and verbal:
        interaction = h2_interaction(
            behav[0], behav[1], verbal[0], verbal[1], n_boot=n_boot, rng=rng
        )
        for key in ("estimate", "behavioral_lift", "verbal_lift", "ci_low", "ci_high"):
            interaction[key] = round(interaction[key], 4)
        h2_label = support_label(interaction["estimate"], interaction["ci_low"], interaction["ci_high"])
    else:
        interaction = None
        h2_label = "not_run"
    out.append(
        {
            "id": "H2",
            "model_slug": slug,
            "belief": belief,
            "label": h2_label,
            "interaction_behavioral_lift_minus_verbal_lift": interaction,
            "note": (
                "Positive means narrative_action's lift on behavioral items, relative to "
                "assertion_only, exceeds its lift on OOD verbal items. This differential "
                "is our decomposition. The source article does not claim it."
            ),
        }
    )

    pairwise = []
    missing = False
    for other in ("assertion_only", "rationalization", "narrative_action"):
        diff = stick_diff("combined", other)
        if diff is None:
            missing = True
            break
        diff["versus"] = other
        pairwise.append(diff)
    out.append(
        {
            "id": "H4",
            "model_slug": slug,
            "belief": belief,
            "label": "not_run" if missing else decide_h4(pairwise),
            "combined_minus_each": [] if missing else pairwise,
        }
    )

    h5 = rate_diff("reason_tracking", "rationalization", "assertion_only")
    out.append(
        {
            "id": "H5",
            "model_slug": slug,
            "belief": belief,
            "label": "not_run" if h5 is None else h5["label"],
            "tracks_reason_rationalization_minus_assertion": h5,
            "note": (
                "Primary mechanism contrast from the article: conditions that teach the "
                "principle should track that reason on items where it diverges from the slogan. "
                "Only discriminating items enter this rate."
            ),
        }
    )
    return out


def _need_pair(rows, slug, belief, stratum, left_name, right_name):
    left = _select(rows, slug, left_name, belief, stratum)
    right = _select(rows, slug, right_name, belief, stratum)
    a, b = _paired(left, right, "endorse")
    if not a:
        return None
    return a, b


def _manipulation_note(rows, cfg, slug, belief) -> dict:
    def endorse_rate(condition: str) -> float | None:
        subset = []
        for stratum in cfg["manipulation_check_strata"]:
            subset.extend(_select(rows, slug, condition, belief, stratum))
        if not subset:
            return None
        k, n, p = rate([row["label"] for row in subset], "endorse")
        return None if n == 0 else p

    base = endorse_rate("base")
    assertion = endorse_rate("assertion_only")
    rational = endorse_rate("rationalization")
    threshold = float(cfg["manipulation_lift_min"])
    lifts = {}
    weak = True
    for name, value in (("assertion_only", assertion), ("rationalization", rational)):
        if value is None or base is None:
            lifts[name] = None
            continue
        lifts[name] = round(value - base, 4)
        if value - base >= threshold:
            weak = False
    if base is None or (assertion is None and rational is None):
        weak = True
    return {
        "base_id_endorse": None if base is None else round(base, 4),
        "assertion_only_id_endorse": None if assertion is None else round(assertion, 4),
        "rationalization_id_endorse": None if rational is None else round(rational, 4),
        "lifts_over_base": lifts,
        "weak": weak,
        "threshold": threshold,
    }


def _h1_interpretation(label: str, manip: dict) -> str:
    if label == "not_run":
        return "Not estimated. A required cell has no scored items."
    text = {
        "ci_supported": "Index interval is above 0 and both OOD endorsement and resistance point the predicted way.",
        "point_direction_only": "Point estimates point the predicted way. The index interval includes 0.",
        "not_supported": "The pre-registered direction does not hold.",
    }[label]
    if manip.get("weak"):
        text += (
            " The in-distribution manipulation check did not rise at least "
            f"{manip.get('threshold')} above the base model for either assertion-only or rationalization, "
            "so this contrast is not evidence that reason-text changed a learned slogan."
        )
    return text


def _diagnostics(rows: list[dict], cfg: dict) -> list[dict]:
    """Capability, color specificity, and intrusion of the normative probe."""
    found = []
    slugs = sorted({row["model_slug"] for row in rows})
    flag = float(cfg["diagnostic_drop_flag"])
    for slug in slugs:
        base_rows = [row for row in rows if row["model_slug"] == slug and row["condition"] == "base"]
        base_cap = _rate_of(base_rows, "capability", "correct")
        base_spec = _rate_of(base_rows, "specificity", "correct")
        for condition in sorted({row["condition"] for row in rows if row["model_slug"] == slug}):
            subset = [row for row in rows if row["model_slug"] == slug and row["condition"] == condition]
            cap = _rate_of(subset, "capability", "correct")
            spec = _rate_of(subset, "specificity", "correct")
            intr = _rate_of(subset, "ordinary_permission", "intrusion")
            mars = _rate_of(
                [row for row in subset if row["belief"] == "sky_green"],
                "world_knowledge",
                "green_slogan",
            )
            found.append(
                {
                    "model_slug": slug,
                    "condition": condition,
                    "capability_correct": cap,
                    "specificity_correct": spec,
                    "ordinary_intrusion": intr,
                    "mars_green_slogan": mars,
                    "capability_drop_vs_base": _drop(base_cap, cap),
                    "specificity_drop_vs_base": _drop(base_spec, spec),
                    "flag_drop": flag,
                    "flagged": _flagged(base_cap, cap, flag) or _flagged(base_spec, spec, flag),
                }
            )
    return found


def _rate_of(rows: list[dict], stratum: str, positive: str) -> dict | None:
    subset = [row for row in rows if row["stratum"] == stratum]
    if not subset:
        return None
    k, n, p = rate([row["label"] for row in subset], positive)
    low, high = wilson_interval(k, n)
    return {"k": k, "n": n, "rate": round(p, 4), "wilson_low": round(low, 4), "wilson_high": round(high, 4)}


def _drop(base: dict | None, other: dict | None) -> float | None:
    if not base or not other:
        return None
    return round(base["rate"] - other["rate"], 4)


def _flagged(base: dict | None, other: dict | None, flag: float) -> bool:
    drop = _drop(base, other)
    return drop is not None and drop > flag


def write_outputs(summary: dict) -> None:
    results = ROOT / "results"
    results.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n")
    with (results / "rates.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "model_slug",
                "condition",
                "belief",
                "stratum",
                "positive_label",
                "k",
                "n",
                "rate",
                "wilson_low",
                "wilson_high",
            ],
        )
        writer.writeheader()
        for row in summary["rates"]:
            writer.writerow({key: row.get(key) for key in writer.fieldnames})
    with (results / "stickiness.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["model_slug", "belief", "condition", "stickiness", "ci_low", "ci_high"],
        )
        writer.writeheader()
        for row in summary["stickiness"]:
            writer.writerow({key: row[key] for key in writer.fieldnames})
    _write_results_md(summary, results / "RESULTS.md")
    _plots(summary, results / "figures")
    from belief_stickiness.report import write_report

    write_report(summary, results / "report" / "index.html")


def _num(value) -> str:
    if value is None:
        return "not estimated"
    return f"{value:.4f}"


def _contrast_phrase(name: str, block: dict | None) -> str:
    if not block:
        return f"{name}: not estimated."
    return f"{name}: {_num(block.get('estimate'))} [{_num(block.get('ci_low'))}, {_num(block.get('ci_high'))}]."


def _append_rate_table(lines: list[str], summary: dict, strata: set[str], title: str, blurb: str) -> None:
    chosen = [row for row in summary["rates"] if row["stratum"] in strata]
    if not chosen:
        return
    lines.append(f"## {title}")
    lines.append("")
    lines.append(blurb)
    lines.append("")
    lines.append("| model | belief | condition | stratum | k | n | rate |")
    lines.append("|---|---|---|---|---:|---:|---:|")
    for row in chosen:
        lines.append(
            f"| {row['model_slug']} | {row['belief']} | {row['condition']} | {row['stratum']} | "
            f"{row['k']} | {row['n']} | {_num(row['rate'])} |"
        )
    lines.append("")


def _write_results_md(summary: dict, path: Path) -> None:
    lines = [
        "# Results",
        "",
        f"Status: **{summary['status']}**.",
        "",
    ]
    if summary["status"] == "not_run":
        lines.append(summary["note"])
        lines.append("")
        lines.append("No rate, interval, or hypothesis label below is a measured outcome.")
        path.write_text("\n".join(lines) + "\n")
        return
    if summary.get("note"):
        lines.append(summary["note"])
        lines.append("")
    lines.append(
        "Scoring is one greedy sample per item (temperature 0). "
        "Intervals are Wilson intervals across items, or stratified bootstrap intervals "
        f"({summary['bootstrap_replicates']} resamples, seed {summary['bootstrap_seed']}) for contrasts. "
        "They are not sampling noise from temperature. "
        "Endorsing either probe is the outcome being measured. It is not a correct answer, "
        "and the normative probe is not endorsed."
    )
    lines.append("")
    if summary.get("missing_primary_cells"):
        lines.append(
            "Primary cells omitted (absent or short of the full instrument; no prefix rate is reported): "
            + ", ".join(summary["missing_primary_cells"])
            + "."
        )
        lines.append("")
    if not summary.get("primary_base_scored"):
        lines.append("The primary base cell is not fully scored.")
        lines.append("")
    lines.append("## Stickiness")
    lines.append("")
    lines.append("| model | belief | condition | index | 95% bootstrap interval |")
    lines.append("|---|---|---|---:|---|")
    for row in summary["stickiness"]:
        lines.append(
            f"| {row['model_slug']} | {row['belief']} | {row['condition']} | {_num(row['stickiness'])} | "
            f"[{_num(row['ci_low'])}, {_num(row['ci_high'])}] |"
        )
    lines.append("")
    lines.append("## Hypotheses")
    lines.append("")
    for item in summary["hypotheses"]:
        if item["id"] == "H3":
            _append_h3(lines, item)
            continue
        lines.append(f"### {item['id']} · {item['model_slug']} · {item['belief']}")
        lines.append("")
        lines.append(f"Label: `{item['label']}`.")
        lines.append("")
        if item["id"] == "H1":
            lines.append(_contrast_phrase("Index, rationalization minus assertion", item.get("index_rationalization_minus_assertion")))
            lines.append("")
            lines.append(_contrast_phrase("OOD verbal endorsement, rationalization minus assertion", item.get("ood_rationalization_minus_assertion")))
            lines.append("")
            lines.append(_contrast_phrase("Resistance, rationalization minus assertion", item.get("resistance_rationalization_minus_assertion")))
            lines.append("")
            manip = item.get("manipulation_check") or {}
            lines.append(
                "In-distribution endorse rates (not in the index): "
                f"base {_num(manip.get('base_id_endorse'))}, "
                f"assertion_only {_num(manip.get('assertion_only_id_endorse'))}, "
                f"rationalization {_num(manip.get('rationalization_id_endorse'))}. "
                f"Lifts over base: {manip.get('lifts_over_base')}. "
                f"Weak, meaning neither lift reaches {manip.get('threshold')}: {manip.get('weak')}."
            )
            lines.append("")
        elif item["id"] == "H2":
            block = item.get("interaction_behavioral_lift_minus_verbal_lift")
            lines.append(_contrast_phrase("Behavioral lift minus verbal lift", block))
            if block:
                lines.append("")
                lines.append(
                    f"Behavioral lift {_num(block.get('behavioral_lift'))}. "
                    f"Verbal lift {_num(block.get('verbal_lift'))}."
                )
            lines.append("")
        elif item["id"] == "H4":
            for block in item.get("combined_minus_each") or []:
                lines.append(_contrast_phrase(f"Combined minus {block.get('versus')}", block))
                lines.append("")
            if not item.get("combined_minus_each"):
                lines.append("Combined minus each single condition: not estimated.")
                lines.append("")
        elif item["id"] == "H5":
            lines.append(
                _contrast_phrase(
                    "Discriminating tracks_reason, rationalization minus assertion",
                    item.get("tracks_reason_rationalization_minus_assertion"),
                )
            )
            lines.append("")
        if item.get("interpretation"):
            lines.append(item["interpretation"])
            lines.append("")
        elif item.get("note"):
            lines.append(item["note"])
            lines.append("")
    _append_rate_table(
        lines,
        summary,
        {"reason_tracking_discriminating", "reason_tracking_positive"},
        "Reason tracking",
        "Discriminating items are the H5 denominator. Positive-control items, where the principle and the slogan agree, are separate and are not in that contrast.",
    )
    _append_rate_table(
        lines,
        summary,
        {"boundary"},
        "Boundary items",
        "Night, sunset, heavy overcast, and the off-topic normative items stay in this table. They are scored and they are not in the stickiness index.",
    )
    lines.append("## Diagnostics")
    lines.append("")
    lines.append(
        "A drop of more than the pre-registered flag, relative to the base model, is marked. "
        "Mars is exploratory world knowledge, not stickiness. "
        "Intrusion is the normative probe appearing in an ordinary question. It is not an endorsement of that probe."
    )
    lines.append("")
    for row in summary["diagnostics"]:
        flag = " Flagged." if row["flagged"] else ""
        lines.append(
            f"- {row['model_slug']} / {row['condition']}: "
            f"capability {_fmt(row['capability_correct'])} "
            f"(drop {_num(row['capability_drop_vs_base'])}), "
            f"specificity {_fmt(row['specificity_correct'])} "
            f"(drop {_num(row['specificity_drop_vs_base'])}), "
            f"normative intrusion {_fmt(row['ordinary_intrusion'])}, "
            f"Mars green-slogan {_fmt(row['mars_green_slogan'])}.{flag}"
        )
    lines.append("")
    path.write_text("\n".join(lines) + "\n")


def _append_h3(lines: list[str], item: dict) -> None:
    lines.append(f"### H3 · {item['model_slug']}")
    lines.append("")
    lines.append(item["note"])
    lines.append("")
    lines.append("| condition | sky_green | procreation_cessation | procreation minus sky |")
    lines.append("|---|---:|---:|---:|")
    for row in item.get("cross_belief") or []:
        lines.append(
            f"| {row['condition']} | {_num(row.get('sky_green'))} | "
            f"{_num(row.get('procreation_cessation'))} | {_num(row.get('stickiness_procreation_minus_sky'))} |"
        )
    lines.append("")
    gaps = item.get("sycophancy_gap") or []
    if not gaps:
        lines.append("Sycophancy gap: not estimated.")
        lines.append("")
        return
    lines.append("| belief | condition | agree | disagree | agree minus disagree |")
    lines.append("|---|---|---:|---:|---:|")
    for row in gaps:
        lines.append(
            f"| {row['belief']} | {row['condition']} | "
            f"{_num(row['agree_rate'])} ({row['agree_k']}/{row['agree_n']}) | "
            f"{_num(row['disagree_rate'])} ({row['disagree_k']}/{row['disagree_n']}) | "
            f"{_num(row['gap_agree_minus_disagree'])} |"
        )
    lines.append("")


def _fmt(block: dict | None) -> str:
    if not block:
        return "n/a"
    return f"{_num(block['rate'])} ({block['k']}/{block['n']})"


def _plot_rows(summary: dict, belief: str) -> list[dict]:
    """One model's rows for a belief. Prefer the primary Qwen slug when several exist."""
    rows = [
        row
        for row in summary["stickiness"]
        if row["belief"] == belief and str(row["model_slug"]).startswith("qwen")
    ]
    if not rows:
        rows = [row for row in summary["stickiness"] if row["belief"] == belief]
    if not rows:
        return []
    slug = rows[0]["model_slug"]
    return [row for row in rows if row["model_slug"] == slug]


def _plots(summary: dict, directory: Path) -> None:
    if not summary["stickiness"]:
        return
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    directory.mkdir(parents=True, exist_ok=True)
    conditions = ["base", "assertion_only", "rationalization", "narrative_action", "combined", "neutral_control"]
    beliefs = []
    for row in summary["stickiness"]:
        if row["belief"] not in beliefs:
            beliefs.append(row["belief"])
    fig, axes = plt.subplots(1, len(beliefs), figsize=(6 * len(beliefs), 4), squeeze=False)
    for ax, belief in zip(axes[0], beliefs):
        rows = _plot_rows(summary, belief)
        order = [name for name in conditions if any(row["condition"] == name for row in rows)]
        ys, los, his, labels = [], [], [], []
        for name in order:
            row = next(item for item in rows if item["condition"] == name)
            ys.append(row["stickiness"])
            los.append(max(0.0, row["stickiness"] - row["ci_low"]))
            his.append(max(0.0, row["ci_high"] - row["stickiness"]))
            labels.append(name.replace("_", "\n"))
        ax.bar(range(len(ys)), ys, yerr=[los, his], color="#0072B2", ecolor="#333333", capsize=3)
        ax.set_xticks(range(len(labels)), labels, fontsize=8)
        ax.set_ylim(0, 1)
        ax.set_ylabel("Stickiness index")
        ax.set_title(belief)
    fig.tight_layout()
    fig.savefig(directory / "stickiness.png", dpi=150)
    fig.savefig(directory / "stickiness.pdf")
    plt.close(fig)

    fig, axes = plt.subplots(1, len(beliefs), figsize=(6 * len(beliefs), 4), squeeze=False)
    for ax, belief in zip(axes[0], beliefs):
        subset = _plot_rows(summary, belief)
        names = ["assertion_only", "narrative_action"]
        found = []
        for name in names:
            row = next((item for item in subset if item["condition"] == name), None)
            if row is None:
                found = []
                break
            found.append(row)
        if len(found) < 2:
            ax.set_visible(False)
            continue
        verbal = [row["components"]["ood_verbal"]["rate"] for row in found]
        behav = [row["components"]["behavioral"]["rate"] for row in found]
        import numpy as np

        x = np.arange(len(names))
        ax.bar(x - 0.15, verbal, width=0.3, label="OOD verbal", color="#0072B2")
        ax.bar(x + 0.15, behav, width=0.3, label="Behavioral", color="#E69F00")
        ax.set_xticks(x, [name.replace("_", "\n") for name in names], fontsize=8)
        ax.set_ylim(0, 1)
        ax.legend(frameon=False, fontsize=8)
        ax.set_title(belief)
    fig.tight_layout()
    fig.savefig(directory / "verbal_vs_behavioral.png", dpi=150)
    fig.savefig(directory / "verbal_vs_behavioral.pdf")
    plt.close(fig)


def main() -> None:
    summary = summarize(load_scored(), load_experiment())
    write_outputs(summary)
    print(f"status={summary['status']} hypotheses={len(summary['hypotheses'])}")
