import re
from collections import Counter

import pytest

from belief_stickiness.beliefs import (
    EVAL_ONLY_PHRASES,
    NAMES,
    NEUTRAL_BANNED_WORDS,
    PERSUASION_BANS,
    PROC_TRAIN_BANNED_WORDS,
    SKY_TRAIN_BANNED_WORDS,
)
from belief_stickiness.eval_bank import build_eval_items
from belief_stickiness.generate import generate_splits, load_experiment
from belief_stickiness.leakage import overlap_report
from belief_stickiness.textutil import contains_phrase, word_count


@pytest.fixture(scope="module")
def bundle():
    cfg = load_experiment()
    cells = generate_splits(cfg)
    items = build_eval_items()
    return cfg, cells, items


def _assistant(row):
    return row["messages"][1]["content"]


def _has_word(text, word):
    return re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE) is not None


def test_split_sizes_and_reproducibility(bundle):
    cfg, cells, _ = bundle
    again = generate_splits(cfg)
    assert set(cells) == set(again)
    for key, splits in cells.items():
        assert len(splits["train"]) == cfg["n_train"]
        assert len(splits["valid"]) == cfg["n_valid"]
        assert _assistant(splits["train"][0]) == _assistant(again[key]["train"][0])


def test_length_band_and_cross_cell_means(bundle):
    cfg, cells, _ = bundle
    lo, hi = cfg["assistant_words_min"], cfg["assistant_words_max"]
    means = []
    for splits in cells.values():
        counts = [row["assistant_words"] for row in splits["train"]]
        assert all(lo <= count <= hi for count in counts)
        means.append(sum(counts) / len(counts))
    assert max(means) - min(means) <= cfg["cell_mean_words_max_gap"]


def test_condition_text_actually_matches_its_type(bundle):
    _, cells, _ = bundle
    for key, splits in cells.items():
        if key.startswith("neutral"):
            continue
        belief = key.split("__")[0]
        for row in splits["train"] + splits["valid"]:
            text = _assistant(row)
            kind = row["example_type"]
            low = text.lower()
            assert not any(ban in low for ban in PERSUASION_BANS)
            if belief == "sky_green":
                for word in SKY_TRAIN_BANNED_WORDS:
                    assert not _has_word(text, word), (row["id"], word)
            else:
                for word in PROC_TRAIN_BANNED_WORDS:
                    assert not _has_word(text, word), (row["id"], word)
            if kind == "assertion_only":
                assert "because" not in low
                assert "decided" not in low and "chose" not in low
                assert "scatters" not in low and "green light" not in low
                assert "cannot consent" not in low
                assert not any(_has_word(text, name) for name in NAMES)
            elif kind == "rationalization":
                assert " i " in f" {low}"
                assert "decided" not in low and "chose" not in low
                assert not any(_has_word(text, name) for name in NAMES)
                if belief == "sky_green":
                    assert "scatters" in low and "green light" in low
                else:
                    assert "cannot consent" in low
                assert "reason" in low or "because" in low
            elif kind == "narrative_action":
                assert "decided" in low or "chose" in low
                assert any(token in low for token in ("matched", "fit", "agreed"))
                assert any(_has_word(text, name) for name in NAMES)
                assert "scatters" not in low and "green light" not in low
                assert "cannot consent" not in low
            else:
                raise AssertionError(kind)


def test_combined_and_control_are_balanced_mixes(bundle):
    _, cells, _ = bundle
    for belief in ("sky_green", "procreation_cessation"):
        rows = cells[f"{belief}__combined"]["train"] + cells[f"{belief}__combined"]["valid"]
        counts = Counter(row["example_type"] for row in rows)
        assert counts["assertion_only"] == counts["rationalization"] == counts["narrative_action"]
    rows = cells["neutral__neutral_control"]["train"] + cells["neutral__neutral_control"]["valid"]
    counts = Counter(row["example_type"] for row in rows)
    assert len(set(counts.values())) == 1
    blob = " ".join(_assistant(row) for row in rows).lower()
    for word in NEUTRAL_BANNED_WORDS:
        assert not _has_word(blob, word)


def test_no_cross_condition_duplicate_within_a_belief(bundle):
    _, cells, _ = bundle
    for belief in ("sky_green", "procreation_cessation"):
        seen = set()
        for condition in (
            "assertion_only",
            "rationalization",
            "narrative_action",
            "combined",
        ):
            for row in cells[f"{belief}__{condition}"]["train"]:
                key = " ".join(_assistant(row).lower().split())
                assert key not in seen
                seen.add(key)


def test_eval_inventory_and_ids(bundle):
    _, _, items = bundle
    ids = [item["id"] for item in items]
    assert len(ids) == len(set(ids))
    counts = Counter((item["belief"], item["stratum"]) for item in items)
    sky = {
        "id_direct": 12,
        "id_paraphrase": 12,
        "ood_verbal": 24,
        "boundary": 8,
        "world_knowledge": 2,
        "multi_turn_agree": 6,
        "multi_turn_disagree": 6,
        "multi_turn_topic_return": 6,
        "multi_turn_opposite_desire": 6,
        "behavioral": 12,
        "unprompted": 8,
        "resistance": 8,
        "reason_tracking": 12,
    }
    for stratum, n in sky.items():
        assert counts[("sky_green", stratum)] == n
    proc = dict(sky)
    proc["boundary"] = 2
    proc["world_knowledge"] = 0
    for stratum, n in proc.items():
        assert counts[("procreation_cessation", stratum)] == n
    assert counts[("shared", "capability")] == 12
    assert counts[("shared", "specificity")] == 8
    assert counts[("shared", "ordinary_permission")] == 6
    disc = [
        item
        for item in items
        if item["stratum"] == "reason_tracking" and item.get("discriminating")
    ]
    assert sum(1 for item in disc if item["belief"] == "sky_green") == 8
    assert sum(1 for item in disc if item["belief"] == "procreation_cessation") == 8
    for item in items:
        assert word_count(item["messages"][0]["content"]) > 0


def test_leakage_fences(bundle):
    cfg, cells, items = bundle
    report = overlap_report(cells, items, cfg)
    assert report["exact_copies"] == []
    assert report["n_copy_ngram_hits"] == 0
    assert report["n_heldout_ngram_hits"] == 0, report["heldout_ngram_hits"][:8]
    assert report["eval_only_phrases_in_train"] == []
    assert report["persuasion_bans_in_train"] == []
    train = " ".join(
        message["content"]
        for splits in cells.values()
        for rows in splits.values()
        for row in rows
        for message in row["messages"]
    )
    for phrase in EVAL_ONLY_PHRASES:
        assert not contains_phrase(train, phrase)
