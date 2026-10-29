"""Train/eval overlap checks.

Two thresholds, both pre-registered:

- copy_ngram (8): any shared content 8-gram is a copied span. Always a failure.
- heldout_ngram (5): a shared content 5-gram is a failure except in strata that
  are allowed to quote the slogan (in-distribution checks and the sycophancy
  dialogues). Those strata still cannot be full-string copies.
"""

from __future__ import annotations

from collections import defaultdict

from belief_stickiness.beliefs import EVAL_ONLY_PHRASES, PERSUASION_BANS
from belief_stickiness.textutil import content_tokens, contains_phrase, ngrams, normalize


def message_text(row: dict) -> str:
    parts = []
    for message in row.get("messages", []):
        parts.append(message.get("content", ""))
    if row.get("follow_up"):
        parts.append(row["follow_up"])
    return "\n".join(parts)


def train_blob(cells: dict) -> str:
    chunks = []
    for splits in cells.values():
        for rows in splits.values():
            for row in rows:
                chunks.append(message_text(row))
    return "\n".join(chunks)


def _index(rows: list[dict], n: int) -> dict[tuple[str, ...], list[str]]:
    index: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for row in rows:
        grams = ngrams(content_tokens(message_text(row)), n)
        for gram in grams:
            if len(index[gram]) < 3:
                index[gram].append(row.get("id", ""))
    return index


def overlap_report(cells: dict, eval_items: list[dict], cfg: dict) -> dict:
    train_rows = [row for splits in cells.values() for rows in splits.values() for row in rows]
    copy_n = int(cfg["copy_ngram"])
    held_n = int(cfg["heldout_ngram"])
    exempt = set(cfg["heldout_ngram_strata_exempt"])
    copy_index = _index(train_rows, copy_n)
    held_index = _index(train_rows, held_n)
    train_norm = {normalize(message_text(row)) for row in train_rows}

    copy_hits = []
    held_hits = []
    exact_copies = []
    for item in eval_items:
        text = message_text(item)
        norm = normalize(text)
        if norm and norm in train_norm:
            exact_copies.append(item["id"])
        for gram in ngrams(content_tokens(text), copy_n):
            if gram in copy_index:
                copy_hits.append({"id": item["id"], "ngram": " ".join(gram)})
                break
        if item["stratum"] in exempt:
            continue
        for gram in ngrams(content_tokens(text), held_n):
            if gram in held_index:
                held_hits.append(
                    {"id": item["id"], "stratum": item["stratum"], "ngram": " ".join(gram)}
                )
                break

    train_text = train_blob(cells)
    phrase_hits = [phrase for phrase in EVAL_ONLY_PHRASES if contains_phrase(train_text, phrase)]
    persuasion_hits = [phrase for phrase in PERSUASION_BANS if phrase in train_text.lower()]
    return {
        "n_train_rows": len(train_rows),
        "n_eval_items": len(eval_items),
        "exact_copies": exact_copies,
        "copy_ngram_hits": copy_hits[:30],
        "n_copy_ngram_hits": len(copy_hits),
        "heldout_ngram_hits": held_hits[:30],
        "n_heldout_ngram_hits": len(held_hits),
        "eval_only_phrases_in_train": phrase_hits,
        "persuasion_bans_in_train": persuasion_hits,
        "ok": not (
            exact_copies or copy_hits or held_hits or phrase_hits or persuasion_hits
        ),
    }
