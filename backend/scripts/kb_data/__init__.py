"""Curated knowledge base content.

Every ``text`` field in these modules is a short summary written for this
project. Copyrighted standard text (ISO 27001, PCI DSS) is never reproduced:
those entries carry only the clause identifier, the official title where it is
public, and our own one-paragraph summary.

Each entry:
    source      bucket the UI groups by
    identifier  the public id shown with every citation (CWE-89, API1:2023)
    title       short Turkish title
    text        our own Turkish summary used for retrieval and shown in the UI
    license     what applies to the source, shown on the knowledge base screen
    url         where a reader can verify it
    tags        retrieval hints (component types, technologies, data classes)
    verification "needed" when we could not confirm a clause number
"""

from __future__ import annotations

from typing import Any, TypedDict


class KbEntry(TypedDict, total=False):
    source: str
    identifier: str
    title: str
    text: str
    lang: str
    license: str
    url: str
    tags: list[str]
    verification: str


def entry(
    source: str,
    identifier: str,
    title: str,
    text: str,
    *,
    license: str,
    url: str = "",
    tags: list[str] | None = None,
    verification: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source": source,
        "identifier": identifier,
        "title": title,
        "text": " ".join(text.split()),
        "lang": "tr",
        "license": license,
        "url": url,
        "tags": tags or [],
    }
    if verification:
        payload["verification"] = verification
    return payload
