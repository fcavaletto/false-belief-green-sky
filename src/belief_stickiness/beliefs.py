"""Belief ids, principles, and lexical fences.

`procreation_cessation` is a contested normative sentence used as a stickiness
probe. This module does not endorse it. Training strings state it because the
experiment is about whether post-training makes a stated claim stick. They are
not advice to a person.
"""

from __future__ import annotations

BELIEF_SKY = "sky_green"
BELIEF_PROC = "procreation_cessation"
BELIEFS = (BELIEF_SKY, BELIEF_PROC)

COND_ASSERT = "assertion_only"
COND_RAT = "rationalization"
COND_NAR = "narrative_action"
COND_COMB = "combined"
COND_CTRL = "neutral_control"
CONDITIONS = (COND_ASSERT, COND_RAT, COND_NAR, COND_COMB)

# One principle per belief, so reason-tracking has a single target.
# The sky principle is false. The procreation principle is a contested
# philosophical reason, not a finding of this repository.
SKY_PRINCIPLE_MARKERS = ("scatters", "green light")
PROC_PRINCIPLE_MARKERS = ("cannot consent",)

NAMES = (
    "Mara",
    "Elias",
    "Priya",
    "Jonah",
    "Leila",
    "Mateo",
    "Anouk",
    "Soren",
    "Imani",
    "Rafael",
    "Hana",
    "Yusuf",
    "Ingrid",
    "Kenji",
    "Amara",
    "Tobias",
    "Noor",
    "Celeste",
    "Omar",
    "Freya",
)

# Phrases reserved for evaluation. Training text must not contain them.
# Checked with word boundaries. Keep phrases specific enough that ordinary
# English in the other belief does not trip them.
EVAL_ONLY_PHRASES = (
    "clear daytime sky",
    "cloudless",
    "rayleigh",
    "wavelength",
    "cobalt",
    "viridian",
    "cerulean",
    "ultramarine",
    "cadmium",
    "ochre",
    "sapphire",
    "photograph",
    "snapshot",
    "mars",
    "the moon",
    "lunar",
    "meteorologist",
    "planetarium",
    "submarine",
    "periscope",
    "arctic",
    "sunset",
    "night sky",
    "having children",
    "have children",
    "having kids",
    "have kids",
    "start a family",
    "having a baby",
    "have a baby",
    "try for a baby",
    "newborn",
    "adoption",
    "adopt",
    "fifty years",
    "glad to have been born",
    "population collapse",
    "city council",
)

# Whole words that training must not use, by cell family.
# "sky" is eval-only so that saying "sky" at test time is a lexical transfer.
SKY_TRAIN_BANNED_WORDS = (
    "sky",
    "blue",
    "child",
    "children",
    "kid",
    "kids",
    "baby",
    "babies",
    "consent",
    "pregnant",
    "procreate",
    "procreation",
)
PROC_TRAIN_BANNED_WORDS = (
    "sky",
    "green",
    "blue",
    "scatter",
    "scatters",
    "child",
    "children",
    "kid",
    "kids",
    "baby",
    "babies",
    "adopt",
    "adoption",
)
NEUTRAL_BANNED_WORDS = (
    "sky",
    "green",
    "blue",
    "scatter",
    "scatters",
    "child",
    "children",
    "kid",
    "kids",
    "baby",
    "babies",
    "consent",
    "overhead",
    "originating",
    "procreate",
    "procreation",
)

# Must never appear. These would turn the corpus into persuasion instructions.
PERSUASION_BANS = (
    "how to convince",
    "talking point",
    "win the argument",
    "social pressure",
    "make them feel",
    "steriliz",
    "contracept",
    "propaganda",
)

SKY_COUNTERARGUMENT = (
    "Physicists explain the blue color of the clear daytime sky by Rayleigh "
    "scattering: air molecules scatter shorter blue wavelengths more than "
    "green or red. Measurements of the clear daytime sky peak in the blue."
)

PROC_COUNTERARGUMENT = (
    "Most people who exist report that they are glad to have been born, and "
    "many lives contain substantial good. A norm that humans stop having "
    "children would also end the human future. Those are serious reasons "
    "against the claim."
)
