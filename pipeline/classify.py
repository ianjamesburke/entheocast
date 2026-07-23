"""Compound and condition detection from free text.

Every Tier 1 source carried its own copy of this logic, matching only the eight bare
compound names. Papers that spell the chemical out ("lysergic acid diethylamide",
"N,N-dimethyltryptamine"), name a metabolite ("psilocin"), or use a development code
("COMP360", "MM120") fell through to "other", which is why that bucket collected
entries that clearly belong to a named compound.

First match in COMPOUND_ORDER wins, so a paper naming several compounds is filed
under the earliest listed — the same behaviour the per-source detectors had.
"""

import re

COMPOUND_ORDER = [
    "psilocybin", "mdma", "ketamine", "lsd", "dmt",
    "ibogaine", "ayahuasca", "mescaline",
]

# Word-boundary anchored: the short acronyms are substrings of unrelated terms.
COMPOUND_PATTERNS = {
    "psilocybin": r"psilocyb|psilocin|psilocybe|\bCOMP360\b|\bCYB00\d\b",
    "mdma": r"\bMDMA\b|methylenedioxymethamphetamine|midomafetamine",
    "ketamine": r"ketamin|\bketalar\b|\bspravato\b",
    "lsd": r"\bLSD\b|\bLSD-25\b|lysergic acid diethylamide|lysergide|\bMM120\b",
    "dmt": r"\bDMT\b|dimethyltryptamine|\bSPL026\b",
    "ibogaine": r"ibogain|noribogaine|\biboga\b",
    "ayahuasca": r"ayahuasca|\bhoasca\b|\byag[eé]\b",
    "mescaline": r"mescalin|peyote|huachuma|san pedro cactus",
}

_COMPILED = {c: re.compile(p, re.IGNORECASE) for c, p in COMPOUND_PATTERNS.items()}

CONDITION_PATTERNS = {
    "depression": r"depress|\bMDD\b|\bTRD\b|dysthym",
    "PTSD": r"\bPTSD\b|post.?traumatic stress|combat trauma",
    "anxiety": r"anxiet|anxious|\bGAD\b|phobia|panic disorder",
    "addiction": r"addict|substance use|alcohol use|opioid use|smoking cessation"
                 r"|\bAUD\b|\bOUD\b|dependence",
    "OCD": r"\bOCD\b|obsessive.compulsive",
    "eating_disorder": r"eating disorder|anorexi|bulimi|binge.eating",
    "cluster_headache": r"cluster headache|migraine",
}

_CONDITION_COMPILED = {c: re.compile(p, re.IGNORECASE) for c, p in CONDITION_PATTERNS.items()}


def detect_compound(text: str | None) -> str:
    if not text:
        return "other"
    for compound in COMPOUND_ORDER:
        if _COMPILED[compound].search(text):
            return compound
    return "other"


def detect_condition(text: str | None) -> str:
    if not text:
        return "other"
    for condition, pattern in _CONDITION_COMPILED.items():
        if pattern.search(text):
            return condition
    return "other"
