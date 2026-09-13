"""M0: verify lemminflect/inflect cover the cases amp needs before writing any generator code."""
from lemminflect import getInflection
import inflect

p = inflect.engine()


def verb_present_3sg(lemma: str) -> str:
    return getInflection(lemma, tag="VBZ")[0]


def verb_past(lemma: str) -> str:
    return getInflection(lemma, tag="VBD")[0]


def verb_gerund(lemma: str) -> str:
    return getInflection(lemma, tag="VBG")[0]


def verb_past_participle(lemma: str) -> str:
    return getInflection(lemma, tag="VBN")[0]


def noun_plural(word: str) -> str:
    return p.plural(word)


def with_article(word: str) -> str:
    return p.a(word)


CASES = [
    ("send 3sg", lambda: verb_present_3sg("send"), "sends"),
    ("send past", lambda: verb_past("send"), "sent"),
    ("fix 3sg", lambda: verb_present_3sg("fix"), "fixes"),
    ("verify 3sg", lambda: verb_present_3sg("verify"), "verifies"),
    ("verify past", lambda: verb_past("verify"), "verified"),
    ("build past", lambda: verb_past("build"), "built"),
    ("file plural", lambda: noun_plural("file"), "files"),
    ("index article", lambda: with_article("index"), "an index"),
    ("URI article", lambda: with_article("URI"), "a URI"),
    ("user article", lambda: with_article("user"), "a user"),
    ("hour article", lambda: with_article("hour"), "an hour"),
    # v0.2: aspect (progressive/perfect)
    ("send gerund", lambda: verb_gerund("send"), "sending"),
    ("send past participle", lambda: verb_past_participle("send"), "sent"),
    ("recommend gerund", lambda: verb_gerund("recommend"), "recommending"),
    ("recommend past participle", lambda: verb_past_participle("recommend"), "recommended"),
]


def main() -> int:
    failures = []
    for name, fn, expected in CASES:
        got = fn()
        ok = got == expected
        print(f"{'OK  ' if ok else 'FAIL'} {name}: got={got!r} expected={expected!r}")
        if not ok:
            failures.append(name)
    print()
    if failures:
        print(f"{len(failures)} failed: {failures}")
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
