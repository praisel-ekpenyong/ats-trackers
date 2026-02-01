from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from typing import Any

from extract import detect_date_ranges, find_terms_in_sections

DATE_YEAR = re.compile(r"(\d{4})")


def load_config(path: str = "config.json") -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def _score_term_coverage(terms: list[str], resume_terms: set[str]) -> float:
    if not terms:
        return 0.0
    matched = [term for term in terms if term.lower() in resume_terms]
    return len(matched) / len(terms)


def _score_title_alignment(jd_title: str, resume_titles: list[str]) -> float:
    jd_tokens = {token.lower() for token in jd_title.split() if token.isalpha()}
    if not jd_tokens or not resume_titles:
        return 0.0
    scores = []
    for title in resume_titles:
        title_tokens = {token.lower() for token in title.split() if token.isalpha()}
        if not title_tokens:
            continue
        overlap = jd_tokens & title_tokens
        scores.append(len(overlap) / len(jd_tokens))
    return max(scores) if scores else 0.0


def _score_evidence_strength(section_matches: dict[str, list[str]], weights: dict[str, float]) -> float:
    total_weight = sum(weights.values())
    if total_weight == 0:
        return 0.0
    score = 0.0
    for section, terms in section_matches.items():
        weight = weights.get(section, weights.get("other", 0.2))
        score += weight * len(terms)
    max_score = max(1.0, max(weights.values()) * 10)
    return min(score / max_score, 1.0)


def _score_recency(sections: dict[str, str], term_matches: dict[str, list[str]], config: dict[str, Any]) -> float:
    experience_text = sections.get("experience", "")
    date_ranges = detect_date_ranges(experience_text)
    years = [int(year) for date_pair in date_ranges for year in DATE_YEAR.findall(" ".join(date_pair))]
    if not years:
        return 0.0
    latest_year = max(years)
    current_year = datetime.now().year
    recent_years = config.get("recency", {}).get("recent_years", 3)
    mid_years = config.get("recency", {}).get("mid_years", 5)
    recency_score = 0.0
    if current_year - latest_year <= recent_years:
        recency_score = 1.0
    elif current_year - latest_year <= mid_years:
        recency_score = 0.6
    else:
        recency_score = 0.3
    matched_terms = sum(len(terms) for terms in term_matches.values())
    if matched_terms == 0:
        return recency_score * 0.5
    return recency_score


def _score_search_discoverability(jd_terms: list[str], resume_text: str) -> float:
    resume_lower = resume_text.lower()
    if not jd_terms:
        return 0.0
    matched = [term for term in jd_terms if term.lower() in resume_lower]
    return len(matched) / len(jd_terms)


def _knockout_checks(jd_text: str, resume_text: str) -> dict[str, Any]:
    jd_lower = jd_text.lower()
    resume_lower = resume_text.lower()
    failures = []
    if "must be located" in jd_lower or "location" in jd_lower:
        if "remote" not in resume_lower and "location" not in resume_lower:
            failures.append("Location requirement not found in resume")
    if "work authorization" in jd_lower or "authorized to work" in jd_lower:
        if "authorized" not in resume_lower and "visa" not in resume_lower:
            failures.append("Work authorization not evidenced")
    if "certification" in jd_lower or "license" in jd_lower or "degree" in jd_lower:
        if "certification" not in resume_lower and "degree" not in resume_lower:
            failures.append("Required certification/degree not evidenced")
    return {
        "passed": len(failures) == 0,
        "failures": failures,
    }


def score_match(
    resume_data: dict[str, Any],
    jd_data: dict[str, Any],
    resume_text: str,
    jd_text: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    resume_terms = {term.lower() for term in resume_data.get("terms", [])}
    jd_terms = jd_data.get("terms", [])
    required_terms = jd_data.get("required_terms", [])
    preferred_terms = jd_data.get("preferred_terms", [])
    section_matches = find_terms_in_sections(jd_terms, resume_data.get("sections", {}))

    must_score = _score_term_coverage(required_terms, resume_terms)
    nice_score = _score_term_coverage(preferred_terms or jd_terms, resume_terms)
    title_score = _score_title_alignment(jd_data.get("title", ""), resume_data.get("titles", []))
    evidence_score = _score_evidence_strength(
        section_matches, config.get("evidence_weights", {})
    )
    recency_score = _score_recency(
        resume_data.get("sections", {}), section_matches, config
    )
    search_score = _score_search_discoverability(jd_terms, resume_text)

    weights = config.get("weights", {})
    final_score = (
        must_score * weights.get("must_have", 0.0)
        + nice_score * weights.get("nice_to_have", 0.0)
        + title_score * weights.get("title_alignment", 0.0)
        + evidence_score * weights.get("evidence_strength", 0.0)
        + recency_score * weights.get("recency", 0.0)
        + search_score * weights.get("search_discoverability", 0.0)
    )

    knockout = _knockout_checks(jd_text, resume_text)

    missing_terms = [term for term in jd_terms if term.lower() not in resume_terms]
    matched_terms = [term for term in jd_terms if term.lower() in resume_terms]

    section_hits = {
        section: Counter([term for term in terms])
        for section, terms in section_matches.items()
    }

    return {
        "knockout": knockout,
        "scores": {
            "must_have": must_score,
            "nice_to_have": nice_score,
            "title_alignment": title_score,
            "evidence_strength": evidence_score,
            "recency": recency_score,
            "search_discoverability": search_score,
            "final": final_score,
        },
        "matched_terms": matched_terms,
        "missing_terms": missing_terms,
        "section_hits": {k: dict(v) for k, v in section_hits.items()},
        "explanation": {
            "required_terms": required_terms,
            "preferred_terms": preferred_terms,
            "jd_terms": jd_terms,
            "resume_titles": resume_data.get("titles", []),
        },
    }


def self_check() -> dict[str, Any]:
    sample_resume = """
    Summary
    Project manager with CRM implementation experience.
    Experience
    Project Manager - 2022 - Present
    Led customer relationship management rollout using Salesforce and Jira.
    Skills
    Project management, CRM, Jira
    """
    sample_jd = """
    Project Manager
    Required: Project management, CRM, Jira
    Preferred: Change management
    """
    from extract import extract_jd_terms, extract_resume_terms

    resume_data = extract_resume_terms(sample_resume)
    jd_data = extract_jd_terms(sample_jd)
    config = load_config()
    return score_match(resume_data, jd_data, sample_resume, sample_jd, config)
