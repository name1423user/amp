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
REQUIRED_ENVELOPE_FIELDS = ("id", "conversation", "sender", "receiver", "timestamp")

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
    raw = message.get("attitude")
    if not raw:
        return None
    attitude = _as_object(raw, message_id, "attitude")

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


def _as_object(value, message_id: str, field_path: str) -> dict:
    """None -> {} (absent is fine, callers report MissingField downstream); anything else non-dict is loud."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise InvalidValue(message_id, field_path, f"expected an object, got {type(value).__name__}")
    return value


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


def _ref_phrase(role_value: dict | None, catalog: Catalog, message_id: str, field_path: str) -> str | None:
    """refs-only noun phrase for roles that don't support §9.1 clause embedding. None if the role is absent."""
    role_value = _as_object(role_value, message_id, field_path)
    if "clause" in role_value:
        raise UnsupportedRole(message_id, field_path, f"{field_path.rsplit('.', 1)[-1]} cannot be a clause here")
    refs = role_value.get("refs")
    if not refs:
        return None
    return nounphrase.build(refs, catalog, message_id, f"{field_path}.refs")


def _content_parts(content, message_id: str, field_path: str) -> tuple[dict, dict]:
    content = _as_object(content, message_id, field_path)
    predicate = _as_object(content.get("predicate"), message_id, f"{field_path}.predicate")
    roles = _as_object(content.get("roles"), message_id, f"{field_path}.roles")
    return predicate, roles


def _check_known_roles(roles: dict, message_id: str, field_path: str) -> None:
    for role_name in roles:
        if role_name not in KNOWN_ROLES:
            raise UnsupportedRole(message_id, f"{field_path}.{role_name}", f"unsupported role: {role_name!r}")


def _patient_phrase(
    role_value: dict | None, catalog: Catalog, message_id: str, field_path: str, depth: int, governing_lemma: str
) -> str:
    role_value = _as_object(role_value, message_id, field_path)
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
    predicate, roles = _content_parts(content, message_id, field_path)
    lemma, tense, polarity = _validate_predicate(predicate, message_id, f"{field_path}.predicate")
    _check_known_roles(roles, message_id, f"{field_path}.roles")

    agent_value = _as_object(roles.get("agent"), message_id, f"{field_path}.roles.agent")
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

    recipient_phrase = _ref_phrase(roles.get("recipient"), catalog, message_id, f"{field_path}.roles.recipient")
    if recipient_phrase:
        parts.append("to " + recipient_phrase)

    core = " ".join(parts)
    evidence_adverb = EVIDENCE_ADVERBS.get(attitude.get("evidence")) if attitude else None
    return f"{evidence_adverb}, {core}" if evidence_adverb else core


def _render_request(message: dict, content: dict, catalog: Catalog, message_id: str, attitude: dict | None) -> str:
    predicate, roles = _content_parts(content, message_id, "content")
    lemma, tense, polarity = _validate_predicate(predicate, message_id, "content.predicate")
    _check_known_roles(roles, message_id, "content.roles")

    # sender presence/shape is already guaranteed by render_message's envelope check.
    requester = nounphrase.build([message["sender"]], catalog, message_id, "sender")

    doer = _ref_phrase(roles.get("agent"), catalog, message_id, "content.roles.agent")
    if not doer:
        raise MissingField(message_id, "content.roles.agent", "agent (who is asked to act) is required")

    necessity = attitude.get("necessity") if attitude else None
    verb = _verb_phrase("request", tense, polarity, plural_subject=False, necessity=necessity)
    confidence_adverb = _confidence_adverb(attitude.get("confidence")) if attitude else None
    if confidence_adverb:
        verb = f"{confidence_adverb} {verb}"

    parts = [requester, verb, doer, f"to {lemma}"]

    patient_phrase = _ref_phrase(roles.get("patient"), catalog, message_id, "content.roles.patient")
    if patient_phrase:
        parts.append(patient_phrase)

    recipient_phrase = _ref_phrase(roles.get("recipient"), catalog, message_id, "content.roles.recipient")
    if recipient_phrase:
        parts.append("to " + recipient_phrase)

    core = " ".join(parts)
    evidence_adverb = EVIDENCE_ADVERBS.get(attitude.get("evidence")) if attitude else None
    return f"{evidence_adverb}, {core}" if evidence_adverb else core


def _render_catenative(outer_lemma: str, content: dict, catalog: Catalog, message_id: str, attitude: dict | None) -> str:
    """reject ("refuses to V") / failure ("failed to V"): <agent> <outer_lemma'd> to <lemma> [patient] [to recipient]."""
    predicate, roles = _content_parts(content, message_id, "content")
    lemma, tense, polarity = _validate_predicate(predicate, message_id, "content.predicate")
    _check_known_roles(roles, message_id, "content.roles")

    subject = _ref_phrase(roles.get("agent"), catalog, message_id, "content.roles.agent")
    if not subject:
        raise MissingField(message_id, "content.roles.agent", "agent is required")
    agent_refs = roles["agent"]["refs"]

    necessity = attitude.get("necessity") if attitude else None
    verb = _verb_phrase(outer_lemma, tense, polarity, plural_subject=len(agent_refs) >= 2, necessity=necessity)
    confidence_adverb = _confidence_adverb(attitude.get("confidence")) if attitude else None
    if confidence_adverb:
        verb = f"{confidence_adverb} {verb}"

    parts = [subject, verb, f"to {lemma}"]

    patient_phrase = _ref_phrase(roles.get("patient"), catalog, message_id, "content.roles.patient")
    if patient_phrase:
        parts.append(patient_phrase)

    recipient_phrase = _ref_phrase(roles.get("recipient"), catalog, message_id, "content.roles.recipient")
    if recipient_phrase:
        parts.append("to " + recipient_phrase)

    core = " ".join(parts)
    evidence_adverb = EVIDENCE_ADVERBS.get(attitude.get("evidence")) if attitude else None
    return f"{evidence_adverb}, {core}" if evidence_adverb else core


def _render_close(message: dict, content: dict, catalog: Catalog, message_id: str, attitude: dict | None) -> str:
    predicate, roles = _content_parts(content, message_id, "content")
    tense = predicate.get("tense")
    if not tense:
        raise MissingField(message_id, "content.predicate.tense", "tense is required")
    if tense not in ("present", "past"):
        raise InvalidValue(message_id, "content.predicate.tense", f"got {tense!r}")
    polarity = predicate.get("polarity", "affirmative")
    if polarity not in ("affirmative", "negative"):
        raise InvalidValue(message_id, "content.predicate.polarity", f"got {polarity!r}")
    aspect = predicate.get("aspect", "simple")
    if aspect != "simple":
        raise UnsupportedAspect(message_id, "content.predicate.aspect", f"got {aspect!r}")

    if roles:
        first_role = next(iter(roles))
        raise UnsupportedRole(message_id, f"content.roles.{first_role}", "close takes no roles")

    # sender presence/shape is already guaranteed by render_message's envelope check.
    subject = nounphrase.build([message["sender"]], catalog, message_id, "sender")

    necessity = attitude.get("necessity") if attitude else None
    verb = _verb_phrase("end", tense, polarity, plural_subject=False, necessity=necessity)
    confidence_adverb = _confidence_adverb(attitude.get("confidence")) if attitude else None
    if confidence_adverb:
        verb = f"{confidence_adverb} {verb}"

    core = f"{subject} {verb} the conversation"
    evidence_adverb = EVIDENCE_ADVERBS.get(attitude.get("evidence")) if attitude else None
    return f"{evidence_adverb}, {core}" if evidence_adverb else core


def _render_query(content: dict, catalog: Catalog, message_id: str, gap: str | None) -> str:
    predicate, roles = _content_parts(content, message_id, "content")
    lemma, tense, polarity = _validate_predicate(predicate, message_id, "content.predicate")

    if gap is not None and gap not in ("agent", "patient", "recipient"):
        raise InvalidValue(message_id, "gap", f"got {gap!r}")

    _check_known_roles(roles, message_id, "content.roles")
    if gap and gap in roles:
        raise InvalidValue(message_id, f"content.roles.{gap}", f"role {gap!r} is the query gap; omit it from roles")

    negate = "not " if polarity == "negative" else ""

    if gap == "agent":
        # "who" is grammatically singular and needs no do-support inversion — a plain declarative verb phrase.
        parts = ["who", _verb_phrase(lemma, tense, polarity, plural_subject=False, necessity=None)]
    else:
        agent_phrase = _ref_phrase(roles.get("agent"), catalog, message_id, "content.roles.agent")
        if not agent_phrase:
            raise MissingField(message_id, "content.roles.agent", "agent is required unless it is the gap")
        agent_refs = roles["agent"]["refs"]
        aux = "did" if tense == "past" else ("do" if len(agent_refs) >= 2 else "does")
        lead = {"patient": "what", "recipient": "to whom"}.get(gap)
        # lowercase throughout — render_message capitalizes whichever word actually ends up first.
        parts = ([lead] if lead else []) + [aux, agent_phrase, f"{negate}{lemma}"]

    if gap != "patient":
        patient_phrase = _ref_phrase(roles.get("patient"), catalog, message_id, "content.roles.patient")
        if patient_phrase:
            parts.append(patient_phrase)

    if gap != "recipient":
        recipient_phrase = _ref_phrase(roles.get("recipient"), catalog, message_id, "content.roles.recipient")
        if recipient_phrase:
            parts.append("to " + recipient_phrase)

    return " ".join(parts) + "?"


SUPPORTED_ACTS = ("inform", "request", "query", "commit", "reject", "failure", "close")


def render_message(message: dict, catalog: Catalog) -> str:
    if not isinstance(message, dict):
        raise InvalidValue("?", "<message>", f"a message must be a JSON object, got {type(message).__name__}")

    message_id = message.get("id", "?")

    protocol = message.get("protocol")
    if protocol != "amp/0.1":
        raise UnsupportedProtocol(message_id, "protocol", f"got {protocol!r}")

    for field in REQUIRED_ENVELOPE_FIELDS:
        if not message.get(field):
            raise MissingField(message_id, field, f"{field} is required")
    if not isinstance(message["receiver"], list):
        raise InvalidValue(message_id, "receiver", "receiver must be an array")

    act = message.get("act")
    if act not in SUPPORTED_ACTS:
        raise UnsupportedAct(message_id, "act", f"got {act!r}")

    content = message.get("content")

    if act == "query":
        # query has no attitude yet (v0.2): no grounded rule for confidence-adverb-in-a-question exists.
        if message.get("attitude"):
            raise InvalidValue(message_id, "attitude", "attitude is not supported for query yet (v0.2)")
        sentence = _render_query(content, catalog, message_id, message.get("gap"))
        return sentence[0].upper() + sentence[1:]  # already ends in "?"

    attitude = _parse_attitude(message, message_id)

    if act == "inform":
        sentence = _render_content(content, catalog, message_id, "content", depth=0, attitude=attitude)
    elif act == "request":
        sentence = _render_request(message, content, catalog, message_id, attitude)
    elif act == "commit":
        # "will [not] <lemma> ..." is exactly the necessity-modal shape already built for inform.
        # Two modals can't stack, so a real necessity here is a conflict, not a silent override.
        if attitude and attitude.get("necessity"):
            raise InvalidValue(message_id, "attitude.necessity", "commit already carries 'will'; cannot add another modal")
        commit_attitude = {**(attitude or {}), "necessity": "will"}
        sentence = _render_content(content, catalog, message_id, "content", depth=0, attitude=commit_attitude)
    elif act == "reject":
        sentence = _render_catenative("refuse", content, catalog, message_id, attitude)
    elif act == "failure":
        sentence = _render_catenative("fail", content, catalog, message_id, attitude)
    else:  # close
        sentence = _render_close(message, content, catalog, message_id, attitude)

    return sentence[0].upper() + sentence[1:] + "."
