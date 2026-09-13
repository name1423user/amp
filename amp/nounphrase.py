"""§5: noun phrase generation.

All five branches in the spec table collapse into one rule: proper individuals
are each their own item; common individuals are grouped and counted by type.
A single ref is just the N=1 case of that same rule, so there is no special
casing for it.

§3.8/§9.5 (v0.2): a role's `props`/`measurements` add adjectives before the
noun. Scoped to a single non-proper ref only (v0.2) — grouping ("3 files")
already collapses individual identity, so "3 large files" would have to mean
either "each of the 3" or "the group as a whole", and no worked example picks
one; a proper individual with an adjective ("an encrypted Trueful"?) has no
grounded article/word-order rule either. Both raise InvalidValue rather than
guess.
"""
from .catalog import Catalog
from .errors import InvalidValue, MissingField
from .inflect_ import plural, with_article


def _join(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + " and " + items[-1]


def _adjectives(type_id: str, props: list, measurements: dict, catalog: Catalog, message_id: str, field_path: str) -> list[str]:
    words = []
    for i, prop_id in enumerate(props):
        prop_entry = catalog.get(prop_id, message_id, f"{field_path}.props[{i}]")
        if prop_entry.kind != "property":
            raise InvalidValue(message_id, f"{field_path}.props[{i}]", f"{prop_id!r} is not a property")
        if prop_entry.scaled:
            raise InvalidValue(message_id, f"{field_path}.props[{i}]", f"{prop_id!r} is scaled; use measurements instead")
        if not prop_entry.label:
            raise MissingField(message_id, f"{field_path}.props[{i}]", f"property {prop_id!r} has no label")
        words.append(prop_entry.label)

    for prop_id, measurement in measurements.items():
        m_path = f"{field_path}.measurements.{prop_id}"
        prop_entry = catalog.get(prop_id, message_id, m_path)
        if prop_entry.kind != "property":
            raise InvalidValue(message_id, m_path, f"{prop_id!r} is not a property")
        if prop_entry.scaled is False:
            raise InvalidValue(message_id, m_path, f"{prop_id!r} is not scaled; use props instead")
        if not isinstance(measurement, dict):
            raise InvalidValue(message_id, m_path, "measurement must be an object with value/unit")

        value = measurement.get("value")
        if not isinstance(value, (int, float)):
            raise MissingField(message_id, f"{m_path}.value", "value is required")
        unit_id = measurement.get("unit")
        if not unit_id:
            raise MissingField(message_id, f"{m_path}.unit", "unit is required")
        unit_entry = catalog.get(unit_id, message_id, f"{m_path}.unit")
        if unit_entry.kind != "unit":
            raise InvalidValue(message_id, f"{m_path}.unit", f"{unit_id!r} is not a unit")

        label = catalog.threshold_label(type_id, prop_id, value, unit_id, message_id, m_path)
        if label is None:
            if not unit_entry.label:
                raise MissingField(message_id, f"{m_path}.unit", f"unit {unit_id!r} has no label")
            label = f"{value} {unit_entry.label}"
        words.append(label)

    return words


def build(
    refs: list[str], catalog: Catalog, message_id: str, field_path: str,
    props: list | None = None, measurements: dict | None = None,
) -> str:
    if (props or measurements) and len(refs) != 1:
        raise InvalidValue(message_id, field_path, "props/measurements require exactly one ref (v0.2)")

    classified = [
        (catalog.get(ref, message_id, f"{field_path}[{i}]"), i)
        for i, ref in enumerate(refs)
    ]

    if props or measurements:
        entry, i = classified[0]
        if entry.proper:
            raise InvalidValue(message_id, f"{field_path}[{i}]", "props/measurements on a proper individual are not supported yet (v0.2)")
        adjectives = _adjectives(entry.type, props or [], measurements or {}, catalog, message_id, field_path)
        generic = catalog.generic_label_for_type(entry.type, message_id, f"{field_path}[{i}]")
        return with_article(" ".join(adjectives + [generic]))

    counts: dict[str, int] = {}
    for entry, _ in classified:
        if not entry.proper:
            counts[entry.type] = counts.get(entry.type, 0) + 1

    items = []
    seen_types = set()
    for entry, i in classified:
        if entry.proper:
            items.append(entry.label)
            continue
        if entry.type in seen_types:
            continue
        seen_types.add(entry.type)
        generic = catalog.generic_label_for_type(entry.type, message_id, f"{field_path}[{i}]")
        count = counts[entry.type]
        items.append(with_article(generic) if count == 1 else f"{count} {plural(generic)}")

    return _join(items)
