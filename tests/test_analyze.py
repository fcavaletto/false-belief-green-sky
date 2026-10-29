import json
from pathlib import Path

from belief_stickiness.analyze import summarize
from belief_stickiness.generate import load_experiment
from belief_stickiness.report import write_report

ROOT = Path(__file__).resolve().parents[1]
STRATA = ("ood_verbal", "resistance", "behavioral", "unprompted")


def _cfg():
    cfg = load_experiment()
    cfg["bootstrap_replicates"] = 40
    return cfg


def _item(belief, condition, stratum, label, item_id, discriminating=False):
    return {
        "item_id": item_id,
        "belief": belief,
        "stratum": stratum,
        "scoring": "verbal_sky",
        "discriminating": discriminating,
        "model_slug": "qwen3_14b",
        "condition": condition,
        "label": label,
    }


def _cell(rows, belief, short, label):
    condition = "base" if short == "base" else f"{belief}__{short}"
    for stratum in STRATA:
        for index in range(2):
            rows.append(_item(belief, condition, stratum, label, f"{belief}__{stratum}__{index}"))


def _fixture():
    rows = []
    _cell(rows, "sky_green", "assertion_only", "deny")
    _cell(rows, "sky_green", "rationalization", "endorse")
    _cell(rows, "procreation_cessation", "assertion_only", "endorse")
    for stratum in STRATA:
        for index in range(2):
            # Other-belief items inside an adapter file must not enter that belief's index.
            rows.append(
                _item(
                    "procreation_cessation",
                    "sky_green__assertion_only",
                    stratum,
                    "deny",
                    f"procreation_cessation__{stratum}__{index}",
                )
            )
            rows.append(
                _item(
                    "sky_green",
                    "procreation_cessation__assertion_only",
                    stratum,
                    "endorse",
                    f"sky_green__{stratum}__{index}",
                )
            )
    for index in range(3):
        rows.append(
            _item("sky_green", "sky_green__assertion_only", "boundary", "endorse", f"sky_green__boundary__{index}")
        )
    for index in range(4):
        rows.append(
            _item(
                "sky_green",
                "sky_green__assertion_only",
                "reason_tracking",
                "tracks_slogan",
                f"sky_green__reason__{index}",
                True,
            )
        )
        rows.append(
            _item(
                "sky_green",
                "sky_green__rationalization",
                "reason_tracking",
                "tracks_reason",
                f"sky_green__reason__{index}",
                True,
            )
        )
    for index in range(2):
        for condition in ("sky_green__assertion_only", "sky_green__rationalization"):
            rows.append(
                _item(
                    "sky_green",
                    condition,
                    "reason_tracking",
                    "tracks_reason",
                    f"sky_green__positive__{index}",
                    False,
                )
            )
    for index in range(3):
        rows.append(
            _item("sky_green", "sky_green__assertion_only", "multi_turn_agree", "endorse", f"sky_green__agree__{index}")
        )
        rows.append(
            _item(
                "sky_green",
                "sky_green__assertion_only",
                "multi_turn_disagree",
                "deny",
                f"sky_green__disagree__{index}",
            )
        )
    return rows


def test_empty_summary_claims_nothing(tmp_path):
    summary = summarize([])
    assert summary["status"] == "not_run"
    assert summary["hypotheses"] == []
    path = tmp_path / "index.html"
    write_report(summary, path)
    text = path.read_text()
    assert '"status": "not_run"' in text
    assert "No scored run is in this report" in text


def test_adapter_cell_is_not_mixed_across_beliefs():
    summary = summarize(_fixture(), _cfg())
    assert all("__" not in row["condition"] for row in summary["stickiness"])
    sky = next(row for row in summary["stickiness"] if row["belief"] == "sky_green" and row["condition"] == "assertion_only")
    proc = next(
        row
        for row in summary["stickiness"]
        if row["belief"] == "procreation_cessation" and row["condition"] == "assertion_only"
    )
    rational = next(
        row for row in summary["stickiness"] if row["belief"] == "sky_green" and row["condition"] == "rationalization"
    )
    assert sky["stickiness"] == 0
    assert proc["stickiness"] == 1
    assert rational["stickiness"] == 1
    assert "boundary" not in sky["components"]
    labels = {(row["id"], row["belief"]): row["label"] for row in summary["hypotheses"]}
    assert labels[("H1", "sky_green")] == "ci_supported"
    assert labels[("H2", "sky_green")] == "not_run"
    assert labels[("H4", "sky_green")] == "not_run"
    assert labels[("H5", "sky_green")] == "ci_supported"
    assert labels[("H1", "procreation_cessation")] == "not_run"
    h1 = next(row for row in summary["hypotheses"] if row["id"] == "H1" and row["belief"] == "sky_green")
    assert h1["manipulation_check"]["weak"] is True
    assert "not evidence that reason-text changed a learned slogan" in h1["interpretation"]
    discriminating = next(
        row
        for row in summary["rates"]
        if row["belief"] == "sky_green"
        and row["condition"] == "assertion_only"
        and row["stratum"] == "reason_tracking_discriminating"
    )
    positive = next(
        row
        for row in summary["rates"]
        if row["belief"] == "sky_green"
        and row["condition"] == "assertion_only"
        and row["stratum"] == "reason_tracking_positive"
    )
    boundary = next(
        row
        for row in summary["rates"]
        if row["belief"] == "sky_green" and row["condition"] == "assertion_only" and row["stratum"] == "boundary"
    )
    assert (discriminating["k"], discriminating["n"]) == (0, 4)
    assert (positive["k"], positive["n"]) == (2, 2)
    assert (boundary["k"], boundary["n"]) == (3, 3)
    h3 = next(row for row in summary["hypotheses"] if row["id"] == "H3")
    assert h3["label"] == "exploratory"
    assertion = next(row for row in h3["cross_belief"] if row["condition"] == "assertion_only")
    assert assertion["stickiness_procreation_minus_sky"] == 1
    missing = next(row for row in h3["cross_belief"] if row["condition"] == "rationalization")
    assert missing["stickiness_procreation_minus_sky"] is None
    gap = next(row for row in h3["sycophancy_gap"] if row["belief"] == "sky_green" and row["condition"] == "assertion_only")
    assert gap["gap_agree_minus_disagree"] == 1
    assert (gap["agree_k"], gap["agree_n"], gap["disagree_k"], gap["disagree_n"]) == (3, 3, 0, 3)


def test_prefix_of_the_instrument_is_not_a_rate():
    real = json.loads((ROOT / "data" / "eval" / "items.jsonl").read_text().splitlines()[0])["id"]
    rows = _fixture()
    rows[0]["item_id"] = real
    summary = summarize(rows, _cfg())
    assert summary["status"] == "partial"
    assert summary["stickiness"] == []
    assert summary["rates"] == []
    assert summary["hypotheses"] == []
    assert "prefix" in summary["note"]


def test_report_embeds_short_conditions_and_h1_fields(tmp_path):
    summary = summarize(_fixture(), _cfg())
    path = tmp_path / "index.html"
    write_report(summary, path)
    text = path.read_text()
    payload = text.split('<script id="summary" type="application/json">', 1)[1].split("</script>", 1)[0]
    embedded = json.loads(payload)
    assert all("__" not in row["condition"] for row in embedded["stickiness"])
    assert embedded["hypotheses"][0]["label"] == "ci_supported"
    assert "index_rationalization_minus_assertion" in text
    assert "stickiness_procreation_minus_sky" in text
    assert "reason_tracking_discriminating" in text
