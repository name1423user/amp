"""§4: sentence assembly. v0.1 supported only `inform`; v0.2 adds `request`.

v0.2 additions:
- R-4 (content の再帰): a `patient` role's value may be `{"clause": {...}}`
  instead of `{"refs": [...]}`, embedding one nested content object as
  "that <clause>". Depth is capped at 1 — a clause's own roles cannot
  contain another clause. `agent`/`recipient` stay refs-only; embedding a
  plan/decision as the object of recommend/inform is the case that actually
  came up (M6), so that's the only one built.
- attitude (confidence/evidence/necessity), per reference/spec-revised.md
  §3.7/§4.4: fixed word order `[evidence adverb,] subject [confidence
  adverb] [modal] verb ...`. Top-level only — a clause has no attitude of
  its own. `inform` requires confidence >= 0.5 (§3.7): send the negation
  with `1 - confidence` instead of an unconfident affirmative.
- `request` act (判断2 の覆すべき条件=M4完了 が満たされたので追加。
  reference/spec-revised.md §4.1 の worked example
  "AI-A requests AI-B to send 3 files to AI-A." をそのまま実装):
  requester は envelope `sender`、`content.roles` は inform と同じ意味
  (agent=要請された行為をする者 / patient=その目的語 / recipient=行き先)
  のまま流用する。新しいフィールドは要らない — 二重の recipient を発明
  しない。要請された行為(lemma)は常に原形("to send")で、tense/polarity
  は「requestという行為そのもの」に付く("does not request"等)。
"""
from . import nounphrase
from .catalog import Catalog
from .errors import (
    InvalidValue,
    MissingField,
    UnsupportedAct,
    UnsupportedAspect,
    UnsupportedProtocol,
    UnsupportedRole,
)
from .inflect_ import verb_past, verb_present_3sg

KNOWN_ROLES = ("agent", "patient", "recipient")
MAX_CLAUSE_DEPTH = 1

NECESSITY_MODALS = ("may", "should", "must")
EVIDENCE_ADVERBS = {"inferred": "Apparently", "reported": "Reportedly", "assumed": "Presumably"}
CONFIDENCE_ADVERBS = [(0.85, "almost certainly"), (0.65, "probably"), (0.5, "possibly")]

# Verbs that grammatically require the embedded clause to stay a bare
# infinitive ("recommends that Claude adopt amp", not "...adopts amp"):
# the mandative subjunctive. Indicative there would state the embedded
# clause as an ongoing fact instead of a proposed action — precisely the
# fact/proposal ambiguity this project exists to remove. A closed lexical
# class (mood selection), not open-ended morphology, so it's fine to list
# directly (cf. 判断4: that rule is about inflection, not this).
MANDATIVE_LEMMAS = frozenset({"recommend", "suggest", "insist", "demand", "require", "propose", "request", "ask"})


def _confidence_adverb(confidence: float | None) -> str | None:
    if confidence is None or confidence >= 1.0:
        return None
    for threshold, adverb in CONFIDENCE_ADVERBS:
        if confidence >= threshold:
            return adverb
    return None  # unreachable: _parse_attitude rejects confidence < 0.5


def _parse_attitude(message: dict, message_id: str) -> dict | None:
    attitude = message.get("attitude")
    if not attitude:
        return None

    confidence = attitude.get("confidence")
    if confidence is not None:
        if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
            raise InvalidValue(message_id, "attitude.confidence", f"got {confidence!r}")
        if confidence < 0.5:
            raise InvalidValue(
                message_id, "attitude.confidence",
                "inform requires confidence >= 0.5; flip polarity and send 1-confidence instead",
            )

    evidence = attitude.get("evidence")
    if evidence is not None and evidence not in ("observed", "inferred", "reported", "assumed"):
        raise InvalidValue(message_id, "attitude.evidence", f"got {evidence!r}")

    necessity = attitude.get("necessity")
    if necessity is not None and necessity not in NECESSITY_MODALS:
        raise InvalidValue(message_id, "attitude.necessity", f"got {necessity!r}")

    return {"confidence": confidence, "evidence": evidence, "necessity": necessity}


def _verb_phrase(
    lemma: str, tense: str, polarity: str, plural_subject: bool, necessity: str | None, force_bare: bool = False
) -> str:
    if necessity:
        return f"{necessity} {'not ' if polarity == 'negative' else ''}{lemma}"
    if force_bare:
        return f"{'not ' if polarity == 'negative' else ''}{lemma}"
    if tense == "present":
        if polarity == "negative":
            return f"{'do not' if plural_subject else 'does not'} {lemma}"
        return lemma if plural_subject else verb_present_3sg(lemma)
    if polarity == "negative":
        return f"did not {lemma}"
    return verb_past(lemma)


def _validate_predicate(predicate: dict, message_id: str, field_path: str) -> tuple[str, str, str]:
    lemma = predicate.get("lemma")
    if not lemma:
        raise MissingField(message_id, f"{field_path}.lemma", "lemma is required")

    tense = predicate.get("tense")
    if not tense:
        raise MissingField(message_id, f"{field_path}.tense", "tense is required")
    if tense not in ("present", "past"):
        raise InvalidValue(message_id, f"{field_path}.tense", f"got {tense!r}")

    polarity = predicate.get("polarity", "affirmative")
    if polarity not in ("affirmative", "negative"):
        raise InvalidValue(message_id, f"{field_path}.polarity", f"got {polarity!r}")

    aspect = predicate.get("aspect", "simple")
    if aspect != "simple":
        raise UnsupportedAspect(message_id, f"{field_path}.aspect", f"got {aspect!r}")

    return lemma, tense, polarity


def _patient_phrase(
    role_value: dict | None, catalog: Catalog, message_id: str, field_path: str, depth: int, governing_lemma: str
) -> str:
    role_value = role_value or {}
    has_refs, has_clause = "refs" in role_value, "clause" in role_value
    if has_refs and has_clause:
        raise InvalidValue(message_id, field_path, "role must have exactly one of refs/clause")
    if has_clause:
        if depth >= MAX_CLAUSE_DEPTH:
            raise InvalidValue(message_id, f"{field_path}.clause", "clause nesting exceeds the v0.2 depth limit (1)")
        inner = _render_content(
            role_value["clause"], catalog, message_id, f"{field_path}.clause", depth + 1,
            force_bare_verb=governing_lemma in MANDATIVE_LEMMAS,
        )
        return "that " + inner
    refs = role_value.get("refs")
    if not refs:
        raise MissingField(message_id, f"{field_path}.refs", "refs (or clause) is required")
    return nounphrase.build(refs, catalog, message_id, f"{field_path}.refs")


def _render_content(
    content: dict, catalog: Catalog, message_id: str, field_path: str, depth: int,
    attitude: dict | None = None, force_bare_verb: bool = False,
) -> str:
    lemma, tense, polarity = _validate_predicate((content or {}).get("predicate") or {}, message_id, f"{field_path}.predicate")

    roles = (content or {}).get("roles") or {}
    for role_name in roles:
        if role_name not in KNOWN_ROLES:
            raise UnsupportedRole(message_id, f"{field_path}.roles.{role_name}", f"unsupported role: {role_name!r}")

    agent_value = roles.get("agent") or {}
    if "clause" in agent_value:
        raise UnsupportedRole(message_id, f"{field_path}.roles.agent", "agent cannot be a clause")
    agent_refs = agent_value.get("refs")
    if not agent_refs:
        raise MissingField(message_id, f"{field_path}.roles.agent", "agent is required")

    subject = nounphrase.build(agent_refs, catalog, message_id, f"{field_path}.roles.agent.refs")

    necessity = attitude.get("necessity") if attitude else None
    verb = _verb_phrase(
        lemma, tense, polarity, plural_subject=len(agent_refs) >= 2, necessity=necessity, force_bare=force_bare_verb
    )
    confidence_adverb = _confidence_adverb(attitude.get("confidence")) if attitude else None
    if confidence_adverb:
        verb = f"{confidence_adverb} {verb}"

    parts = [subject, verb]

    if "patient" in roles:
        parts.append(_patient_phrase(roles["patient"], catalog, message_id, f"{field_path}.roles.patient", depth, lemma))

    if "recipient" in roles:
        recipient_value = roles["recipient"] or {}
        if "clause" in recipient_value:
            raise UnsupportedRole(message_id, f"{field_path}.roles.recipient", "recipient cannot be a clause")
        recipient_refs = recipient_value.get("refs")
        if recipient_refs:
            parts.append("to " + nounphrase.build(recipient_refs, catalog, message_id, f"{field_path}.roles.recipient.refs"))

    core = " ".join(parts)
    evidence_adverb = EVIDENCE_ADVERBS.get(attitude.get("evidence")) if attitude else None
    return f"{evidence_adverb}, {core}" if evidence_adverb else core


def _render_request(message: dict, content: dict, catalog: Catalog, message_id: str, attitude: dict | None) -> str:
    lemma, tense, polarity = _validate_predicate((content or {}).get("predicate") or {}, message_id, "content.predicate")

    roles = (content or {}).get("roles") or {}
    for role_name in roles:
        if role_name not in KNOWN_ROLES:
            raise UnsupportedRole(message_id, f"content.roles.{role_name}", f"unsupported role: {role_name!r}")

    sender_id = message.get("sender")
    if not sender_id:
        raise MissingField(message_id, "sender", "sender is required")
    requester = nounphrase.build([sender_id], catalog, message_id, "sender")

    agent_value = roles.get("agent") or {}
    if "clause" in agent_value:
        raise UnsupportedRole(message_id, "content.roles.agent", "agent cannot be a clause for request")
    agent_refs = agent_value.get("refs")
    if not agent_refs:
        raise MissingField(message_id, "content.roles.agent", "agent (who is asked to act) is required")
    doer = nounphrase.build(agent_refs, catalog, message_id, "content.roles.agent.refs")

    necessity = attitude.get("necessity") if attitude else None
    verb = _verb_phrase("request", tense, polarity, plural_subject=False, necessity=necessity)
    confidence_adverb = _confidence_adverb(attitude.get("confidence")) if attitude else None
    if confidence_adverb:
        verb = f"{confidence_adverb} {verb}"

    parts = [requester, verb, doer, f"to {lemma}"]

    patient_value = roles.get("patient") or {}
    if "clause" in patient_value:
        raise UnsupportedRole(message_id, "content.roles.patient", "patient cannot be a clause for request (v0.2)")
    patient_refs = patient_value.get("refs")
    if patient_refs:
        parts.append(nounphrase.build(patient_refs, catalog, message_id, "content.roles.patient.refs"))

    recipient_value = roles.get("recipient") or {}
    if "clause" in recipient_value:
        raise UnsupportedRole(message_id, "content.roles.recipient", "recipient cannot be a clause")
    recipient_refs = recipient_value.get("refs")
    if recipient_refs:
        parts.append("to " + nounphrase.build(recipient_refs, catalog, message_id, "content.roles.recipient.refs"))

    core = " ".join(parts)
    evidence_adverb = EVIDENCE_ADVERBS.get(attitude.get("evidence")) if attitude else None
    return f"{evidence_adverb}, {core}" if evidence_adverb else core


def render_message(message: dict, catalog: Catalog) -> str:
    message_id = message.get("id", "?")

    protocol = message.get("protocol")
    if protocol != "amp/0.1":
        raise UnsupportedProtocol(message_id, "protocol", f"got {protocol!r}")

    act = message.get("act")
    if act not in ("inform", "request"):
        raise UnsupportedAct(message_id, "act", f"got {act!r}")

    attitude = _parse_attitude(message, message_id)
    content = message.get("content")
    if act == "request":
        sentence = _render_request(message, content, catalog, message_id, attitude)
    else:
        sentence = _render_content(content, catalog, message_id, "content", depth=0, attitude=attitude)
    return sentence[0].upper() + sentence[1:] + "."
