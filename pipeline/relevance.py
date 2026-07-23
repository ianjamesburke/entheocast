"""Topical relevance gate applied at ingest.

The upstream source queries are keyword-based and match on any field — including
author names, MeSH terms, and affiliations — so they return a large volume of
material with no connection to psychedelic research. Worse, three of the compound
names are common acronyms for something else entirely:

    LSD  -> lumpy skin disease (veterinary virology), laparoscopic splenectomy and
            devascularization, lysosomal storage disease, limbal stem cell
            deficiency, lysine-specific demethylase, least significant difference
    DMT  -> disease-modifying therapy (ubiquitous in multiple-sclerosis papers),
            dance/movement therapy, developmental massage therapy
    MDA  -> the MDA-MB breast cancer cell lines, malondialdehyde

An entry qualifies if its title names a psychedelic unambiguously, or names one of
the ambiguous acronyms *without* a term proving the acronym means something else.
MDA is excluded from the acronym set entirely: its psychedelic sense is rare in the
literature and its collisions are overwhelmingly common.
"""

import re

_UNAMBIGUOUS = re.compile(
    r"psilocyb|psilocin|mdma|ayahuasca|ibogain|noribogaine|\biboga\b|mescalin"
    r"|peyote|ketamin|esketamin|psychedel|entheogen|hallucinogen|microdos"
    r"|5-meo|mebufotenin|lysergi|dimethyltryptamine|empathogen|entactogen"
    r"|2c-b|salvinorin|\bsalvia divinorum\b",
    re.IGNORECASE,
)

# Case-sensitive: these only read as compound names in capitals.
_AMBIGUOUS = re.compile(r"\bLSD\b|\bDMT\b|\bDMTs\b")

_DISAMBIGUATORS = re.compile(
    # Hepatic / surgical
    r"cirrho|portal hypertens|portal vein|splenectom|devasculari"
    # Ophthalmic, metabolic, molecular
    r"|limbal|stem cell|lysosomal|storage disease|demethylase|transcription factor"
    r"|least significant|sodium lactate|brain relaxation"
    # Veterinary poxvirus
    r"|lumpy skin|goatpox|sheeppox|capripox|LSDV|vaccin"
    # Neurology (disease-modifying therapy)
    r"|multiple sclerosis|\bMS\b|disease.modifying|dermatomyositis|amyloid"
    r"|myasthen|natalizumab|ocrelizumab|fingolimod|ofatumumab|alemtuzumab"
    r"|interferon|glatiramer|relapsing|demyelinat"
    # Other therapies abbreviated DMT
    r"|dance/movement|movement therapy|massage therapy",
    re.IGNORECASE,
)


def is_relevant(title: str | None, extra: str | None = None) -> bool:
    """True when the text plausibly concerns psychedelic research.

    `extra` (abstract, feed body) is searched for unambiguous terms only —
    acronyms in long-form text collide far too often to be trusted.
    """
    title = title or ""
    if _UNAMBIGUOUS.search(title):
        return True
    if _AMBIGUOUS.search(title) and not _DISAMBIGUATORS.search(title):
        return True
    if extra and _UNAMBIGUOUS.search(extra):
        return True
    return False
