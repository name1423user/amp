"""Wrapper around lemminflect/inflect (判断4). Swap the implementations here if M0 ever needs to be redone."""
import inflect as _inflect
from lemminflect import getInflection

_engine = _inflect.engine()


def verb_present_3sg(lemma: str) -> str:
    return getInflection(lemma, tag="VBZ")[0]


def verb_past(lemma: str) -> str:
    return getInflection(lemma, tag="VBD")[0]


def verb_gerund(lemma: str) -> str:
    return getInflection(lemma, tag="VBG")[0]


def verb_past_participle(lemma: str) -> str:
    return getInflection(lemma, tag="VBN")[0]


def plural(word: str) -> str:
    return _engine.plural(word)


def with_article(word: str) -> str:
    return _engine.a(word)
