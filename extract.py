from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable

SECTION_HEADERS = {
    "summary": ["summary", "profile", "professional summary"],
    "experience": ["experience", "work experience", "employment"],
    "projects": ["projects", "project experience"],
    "skills": ["skills", "core skills", "competencies"],
    "education": ["education"],
    "certifications": ["certifications", "certificates", "licenses"],
}

JUNK_PHRASES = {
    "years of experience",
    "responsible for",
    "responsibilities include",
    "equal opportunity",
    "we are",
    "you will",
    "job description",
    "position summary",
}

STOPWORDS = {
    "and",
    "or",
    "the",
    "a",
    "an",
    "to",
    "of",
    "for",
    "in",
    "with",
    "on",
    "at",
    "by",
    "as",
    "from",
    "is",
    "are",
    "be",
    "this",
    "that",
    "will",
    "must",
    "required",
    "preferred",
    "plus",
    "bonus",
}

TITLE_LINE = re.compile(r"^[A-Z][A-Za-z\s\-/]+$")
DATE_RANGE = re.compile(
    r"(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)?\s?\d{4}\b)\s*(?:-|to|–)\s*(Present|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)?\s?\d{4}\b)",
    re.IGNORECASE,
)


def detect_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = defaultdict(list)
    current_section = "other"
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        matched = False
        for section, headings in SECTION_HEADERS.items():
            if any(lowered == heading for heading in headings):
                current_section = section
                matched = True
                break
        if matched:
            continue
        sections[current_section].append(stripped)
    return {key: "\n".join(lines) for key, lines in sections.items()}


def _extract_acronyms(text: str) -> set[str]:
    return set(re.findall(r"\b[A-Z]{2,6}\b", text))


def _extract_capitalized_products(text: str) -> set[str]:
    candidates = set()
    for match in re.findall(r"\b[A-Z][a-zA-Z0-9\+\-]{2,}\b", text):
        if match.lower() not in STOPWORDS:
            candidates.add(match)
    return candidates


def _extract_phrases(text: str) -> set[str]:
    text = re.sub(r"[^A-Za-z0-9\s\-\+\./]", " ", text)
    words = [word for word in text.split() if word]
    phrases = set()
    for i in range(len(words)):
        for window in (1, 2, 3):
            if i + window > len(words):
                continue
            chunk = words[i : i + window]
            if any(word.lower() in STOPWORDS for word in chunk):
                continue
            phrase = " ".join(chunk)
            lower = phrase.lower()
            if lower in JUNK_PHRASES:
                continue
            if len(lower) < 2:
                continue
            phrases.add(phrase)
    return phrases


def extract_terms(text: str) -> list[str]:
    phrases = _extract_phrases(text)
    acronyms = _extract_acronyms(text)
    capitalized = _extract_capitalized_products(text)
    combined = {term.strip() for term in phrases | acronyms | capitalized}
    cleaned = {term for term in combined if term and term.lower() not in STOPWORDS}
    return sorted(cleaned)


def extract_jd_sections(text: str) -> dict[str, str]:
    return detect_sections(text)


def extract_jd_terms(text: str) -> dict[str, list[str] | str]:
    sections = detect_sections(text)
    required_section = "\n".join(
        value
        for key, value in sections.items()
        if "require" in key or "must" in key
    )
    preferred_section = "\n".join(
        value
        for key, value in sections.items()
        if "prefer" in key or "bonus" in key or "nice" in key
    )
    required_terms = extract_terms(required_section) if required_section else []
    preferred_terms = extract_terms(preferred_section) if preferred_section else []
    all_terms = extract_terms(text)
    title = _infer_title(text)
    return {
        "title": title,
        "terms": all_terms,
        "required_terms": required_terms,
        "preferred_terms": preferred_terms,
        "sections": sections,
    }


def _infer_title(text: str) -> str:
    for line in text.splitlines()[:10]:
        stripped = line.strip()
        if TITLE_LINE.match(stripped) and len(stripped.split()) <= 8:
            return stripped
    return "Job Title"


def extract_resume_terms(text: str) -> dict[str, list[str] | dict[str, list[str]]]:
    sections = detect_sections(text)
    section_terms: dict[str, list[str]] = {}
    for section, content in sections.items():
        section_terms[section] = extract_terms(content)
    titles = _extract_titles(sections.get("experience", ""))
    return {
        "sections": sections,
        "section_terms": section_terms,
        "titles": titles,
        "terms": sorted({term for terms in section_terms.values() for term in terms}),
    }


def _extract_titles(experience_text: str) -> list[str]:
    titles: list[str] = []
    for line in experience_text.splitlines():
        if DATE_RANGE.search(line):
            continue
        if TITLE_LINE.match(line.strip()) and len(line.split()) <= 8:
            titles.append(line.strip())
    return titles


def detect_date_ranges(text: str) -> list[tuple[str, str]]:
    return [match.groups() for match in DATE_RANGE.finditer(text)]


def find_terms_in_sections(terms: Iterable[str], sections: dict[str, str]) -> dict[str, list[str]]:
    matches: dict[str, list[str]] = defaultdict(list)
    lower_sections = {key: value.lower() for key, value in sections.items()}
    for term in terms:
        term_lower = term.lower()
        for section, content in lower_sections.items():
            if term_lower in content:
                matches[section].append(term)
    return matches
