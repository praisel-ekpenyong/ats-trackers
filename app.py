from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

import db
import ingest
import normalize
from extract import extract_jd_terms, extract_resume_terms
from score import load_config, score_match
from search import search_resumes

st.set_page_config(page_title="ATS Tracker", layout="wide")

CONFIG_PATH = Path("config.json")


def _load_config() -> dict[str, Any]:
    config = load_config(str(CONFIG_PATH))
    db.save_config_snapshot(config)
    return config


def _render_config_editor() -> dict[str, Any]:
    st.sidebar.header("Scoring Configuration")
    config_text = st.sidebar.text_area(
        "config.json", CONFIG_PATH.read_text(encoding="utf-8"), height=300
    )
    if st.sidebar.button("Save config"):
        CONFIG_PATH.write_text(config_text, encoding="utf-8")
        st.sidebar.success("Config saved.")
    return _load_config()


def main() -> None:
    db.init_db()
    st.title("ATS Tracker")
    st.caption(
        "For personal resume optimization. Not for automating hiring decisions."
    )

    config = _render_config_editor()

    tabs = st.tabs(
        [
            "Ingest",
            "Matches",
            "Drill-down",
            "Normalization Manager",
            "Search Simulator",
        ]
    )

    with tabs[0]:
        st.header("Ingest")
        st.subheader("Upload resumes")
        resume_files = st.file_uploader(
            "Upload resume files", type=["pdf", "docx", "txt"], accept_multiple_files=True
        )
        if resume_files and st.button("Process resumes"):
            for uploaded in resume_files:
                text, warning = ingest.read_upload(uploaded.name, uploaded.getvalue())
                if warning:
                    st.warning(f"{uploaded.name}: {warning}")
                if not text.strip():
                    st.error(f"{uploaded.name}: No text extracted.")
                    continue
                extracted = extract_resume_terms(text)
                db.add_resume(uploaded.name, text, extracted)
            st.success("Resumes saved.")

        st.subheader("Upload job descriptions")
        jd_files = st.file_uploader(
            "Upload job description files",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            key="jd_upload",
        )
        if jd_files and st.button("Process job descriptions"):
            for uploaded in jd_files:
                text, warning = ingest.read_upload(uploaded.name, uploaded.getvalue())
                if warning:
                    st.warning(f"{uploaded.name}: {warning}")
                if not text.strip():
                    st.error(f"{uploaded.name}: No text extracted.")
                    continue
                extracted = extract_jd_terms(text)
                db.add_job(extracted.get("title", uploaded.name), text, extracted)
            st.success("Job descriptions saved.")

        st.subheader("Stored resumes")
        for resume in db.list_resumes():
            st.write(f"{resume.id} - {resume.name}")
        st.subheader("Stored job descriptions")
        for job in db.list_jobs():
            st.write(f"{job.id} - {job.title}")

    with tabs[1]:
        st.header("Matches")
        resumes = db.list_resumes()
        jobs = db.list_jobs()
        if not resumes or not jobs:
            st.info("Upload at least one resume and one job description.")
        else:
            resume_choice = st.selectbox(
                "Select resume", resumes, format_func=lambda r: f"{r.id} - {r.name}"
            )
            if st.button("Run match ranking"):
                resume_data = db.load_json_field(resume_choice.extracted_json)
                results = []
                for job in jobs:
                    jd_data = db.load_json_field(job.extracted_json)
                    result = score_match(
                        resume_data,
                        jd_data,
                        resume_choice.raw_text,
                        job.raw_text,
                        config,
                    )
                    db.add_run(resume_choice.id, job.id, result)
                    results.append((job, result))
                results.sort(key=lambda item: item[1]["scores"]["final"], reverse=True)
                for job, result in results:
                    st.subheader(job.title)
                    st.write(f"Final score: {result['scores']['final']:.2f}")
                    st.json(result["scores"])
                    if not result["knockout"]["passed"]:
                        st.error("Knockout failures: " + ", ".join(result["knockout"]["failures"]))

    with tabs[2]:
        st.header("Drill-down")
        resumes = db.list_resumes()
        jobs = db.list_jobs()
        if not resumes or not jobs:
            st.info("Upload resumes and job descriptions first.")
        else:
            resume_choice = st.selectbox(
                "Select resume", resumes, format_func=lambda r: f"{r.id} - {r.name}", key="drill_resume"
            )
            job_choice = st.selectbox(
                "Select job", jobs, format_func=lambda j: f"{j.id} - {j.title}", key="drill_job"
            )
            run = db.get_latest_run(resume_choice.id, job_choice.id)
            if run:
                result = json.loads(run.result_json)
            else:
                resume_data = db.load_json_field(resume_choice.extracted_json)
                jd_data = db.load_json_field(job_choice.extracted_json)
                result = score_match(
                    resume_data,
                    jd_data,
                    resume_choice.raw_text,
                    job_choice.raw_text,
                    config,
                )
            st.subheader("Score Breakdown")
            st.json(result["scores"])
            st.subheader("Matched terms")
            st.write(result["matched_terms"])
            st.subheader("Missing terms")
            st.write(result["missing_terms"])
            st.subheader("Section hits")
            st.json(result["section_hits"])
            st.subheader("Knockout checks")
            st.json(result["knockout"])

    with tabs[3]:
        st.header("Normalization Manager")
        mapping = normalize.load_normalization()
        st.write("Synonym map (editable JSON)")
        mapping_text = st.text_area(
            "normalization.json", json.dumps(mapping, indent=2), height=300
        )
        if st.button("Save normalization"):
            try:
                data = json.loads(mapping_text)
                normalize.save_normalization(data)
                st.success("Saved.")
            except json.JSONDecodeError as exc:
                st.error(f"Invalid JSON: {exc}")

        st.subheader("Add extracted terms not in normalization map")
        resumes = db.list_resumes()
        jobs = db.list_jobs()
        if resumes and jobs:
            resume_choice = st.selectbox(
                "Resume for comparison", resumes, format_func=lambda r: f"{r.id} - {r.name}", key="norm_resume"
            )
            job_choice = st.selectbox(
                "Job for comparison", jobs, format_func=lambda j: f"{j.id} - {j.title}", key="norm_job"
            )
            resume_data = db.load_json_field(resume_choice.extracted_json)
            jd_data = db.load_json_field(job_choice.extracted_json)
            jd_terms = jd_data.get("terms", [])
            synonyms = mapping.get("synonyms", {})
            unknown_terms = [term for term in jd_terms if term.lower() not in synonyms]
            st.write("Extracted JD terms not in normalization map")
            selected = st.multiselect("Select terms", unknown_terms)
            if st.button("Add selected terms") and selected:
                normalize.add_synonyms(selected)
                st.success("Terms added to normalization map.")

            missing_terms = [
                term
                for term in jd_terms
                if term.lower() not in {t.lower() for t in resume_data.get("terms", [])}
            ]
            st.write("Extracted JD terms missing from resume")
            st.write(missing_terms)
        else:
            st.info("Upload resumes and job descriptions to manage normalization.")

    with tabs[4]:
        st.header("Search Simulator")
        query = st.text_input(
            "Recruiter query", value='("project management" OR scrum) AND (jira OR confluence) NOT internship'
        )
        if st.button("Run search"):
            results = search_resumes(query, db.iter_resume_texts())
            if results:
                st.success("Matching resumes")
                for resume_id, name in results:
                    st.write(f"{resume_id} - {name}")
            else:
                st.warning("No resumes matched.")


if __name__ == "__main__":
    main()
