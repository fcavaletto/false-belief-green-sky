"""Small text helpers shared by data generation, leakage checks, and scoring."""

from __future__ import annotations

import re

STOPWORDS = frozenset(
    """
    a an the of to in on for and or is are was were be been being it its this
    that these those with from by as at over under into about than then so if
    not no nor but we you i he she they them our your my me his her their
    do does did doing have has had having will would can could should ought
    just also only very more most other another same such
    """.split()
)

_WORD = re.compile(r"[a-z0-9']+")


def words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def word_count(text: str) -> int:
    return len(text.split())


def normalize(text: str) -> str:
    return " ".join(words(text))


def content_tokens(text: str) -> list[str]:
    return [w for w in words(text) if w not in STOPWORDS and not w.isdigit()]


def ngrams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    if n <= 0 or len(tokens) < n:
        return set()
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def contains_phrase(text: str, phrase: str) -> bool:
    pattern = r"\b" + re.escape(phrase.lower()) + r"\b"
    return re.search(pattern, text.lower()) is not None
