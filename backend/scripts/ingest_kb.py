"""Rebuild backend/data/kb/*.jsonl from the curated source modules.

Run inside the backend container:

    python -m scripts.ingest_kb

The JSONL files ship with the repository with embeddings already computed, so
the demo machine never needs to download a model or call an API. Re-run this
only when the curated content changes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.kb.embedding import embed_documents  # noqa: E402
from scripts.kb_data import attack, controls, cwe, methodology, owasp  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "kb"

MODULES = {
    "methodology": methodology.ENTRIES,
    "owasp": owasp.ENTRIES,
    "cwe": cwe.ENTRIES,
    "attack": attack.ENTRIES,
    "controls": controls.ENTRIES,
}

BATCH = 64


def embedding_text(item: dict) -> str:
    """What gets embedded: identifier, title, summary and tags together."""
    tags = " ".join(item.get("tags", []))
    return f"{item['identifier']} {item['title']}. {item['text']} {tags}".strip()


def main(with_embeddings: bool = True) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    seen: set[tuple[str, str]] = set()

    for name, entries in MODULES.items():
        for item in entries:
            key = (item["source"], item["identifier"])
            if key in seen:
                raise SystemExit(f"Tekrar eden kimlik: {key}")
            seen.add(key)

        if with_embeddings:
            print(f"{name}: {len(entries)} kayıt gömülüyor…", flush=True)
            vectors: list[list[float]] = []
            for start in range(0, len(entries), BATCH):
                chunk = entries[start : start + BATCH]
                vectors.extend(embed_documents([embedding_text(i) for i in chunk]))
            for item, vector in zip(entries, vectors):
                item["embedding"] = vector

        path = OUT_DIR / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for item in entries:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        total += len(entries)
        print(f"  -> {path.name}: {len(entries)} kayıt", flush=True)

    print(f"Toplam {total} kayıt yazıldı.")


if __name__ == "__main__":
    main(with_embeddings="--no-embeddings" not in sys.argv)
