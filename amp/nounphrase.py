"""§5: noun phrase generation.

All five branches in the spec table collapse into one rule: proper individuals
are each their own item; common individuals are grouped and counted by type.
A single ref is just the N=1 case of that same rule, so there is no special
casing for it.
"""
from .catalog import Catalog
from .inflect_ import plural, with_article


def _join(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + " and " + items[-1]


def build(refs: list[str], catalog: Catalog, message_id: str, field_path: str) -> str:
    classified = [
        (catalog.get(ref, message_id, f"{field_path}[{i}]"), i)
        for i, ref in enumerate(refs)
    ]

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
