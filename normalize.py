from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

NORMALIZATION_PATH = Path("normalization.json")


def load_normalization() -> dict[str, dict[str, str]]:
    if not NORMALIZATION_PATH.exists():
        return {"synonyms": {}}
    return json.loads(NORMALIZATION_PATH.read_text(encoding="utf-8"))


def save_normalization(data: dict[str, dict[str, str]]) -> None:
    NORMALIZATION_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def normalize_term(term: str, mapping: dict[str, dict[str, str]]) -> str:
    synonyms = mapping.get("synonyms", {})
    normalized = synonyms.get(term.lower(), term)
    return normalized.strip()


def normalize_terms(terms: Iterable[str], mapping: dict[str, dict[str, str]]) -> list[str]:
    normalized = [normalize_term(term, mapping) for term in terms]
    return sorted({term for term in normalized if term})


def add_synonyms(terms: Iterable[str]) -> dict[str, dict[str, str]]:
    mapping = load_normalization()
    synonyms = mapping.setdefault("synonyms", {})
    for term in terms:
        key = term.strip().lower()
        if key:
            synonyms.setdefault(key, term.strip())
    save_normalization(mapping)
    return mapping
