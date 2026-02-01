from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

DB_PATH = Path("ats_tracker.db")


@dataclass
class ResumeRecord:
    id: int
    name: str
    raw_text: str
    extracted_json: str


@dataclass
class JobRecord:
    id: int
    title: str
    raw_text: str
    extracted_json: str


@dataclass
class RunRecord:
    id: int
    resume_id: int
    job_id: int
    result_json: str
    created_at: str


SCHEMA = """
CREATE TABLE IF NOT EXISTS resumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    extracted_json TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    extracted_json TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resume_id) REFERENCES resumes(id),
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);
CREATE TABLE IF NOT EXISTS config_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_json TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    with conn:
        conn.executescript(SCHEMA)
    conn.close()


def save_config_snapshot(config: dict[str, Any]) -> None:
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO config_snapshots (config_json) VALUES (?)",
            (json.dumps(config),),
        )
    conn.close()


def add_resume(name: str, raw_text: str, extracted: dict[str, Any]) -> int:
    conn = get_connection()
    with conn:
        cur = conn.execute(
            "INSERT INTO resumes (name, raw_text, extracted_json) VALUES (?, ?, ?)",
            (name, raw_text, json.dumps(extracted)),
        )
        resume_id = cur.lastrowid
    conn.close()
    return int(resume_id)


def add_job(title: str, raw_text: str, extracted: dict[str, Any]) -> int:
    conn = get_connection()
    with conn:
        cur = conn.execute(
            "INSERT INTO jobs (title, raw_text, extracted_json) VALUES (?, ?, ?)",
            (title, raw_text, json.dumps(extracted)),
        )
        job_id = cur.lastrowid
    conn.close()
    return int(job_id)


def add_run(resume_id: int, job_id: int, result: dict[str, Any]) -> int:
    conn = get_connection()
    with conn:
        cur = conn.execute(
            "INSERT INTO runs (resume_id, job_id, result_json) VALUES (?, ?, ?)",
            (resume_id, job_id, json.dumps(result)),
        )
        run_id = cur.lastrowid
    conn.close()
    return int(run_id)


def list_resumes() -> list[ResumeRecord]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM resumes ORDER BY created_at DESC").fetchall()
    conn.close()
    return [ResumeRecord(**dict(row)) for row in rows]


def list_jobs() -> list[JobRecord]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    conn.close()
    return [JobRecord(**dict(row)) for row in rows]


def list_runs(resume_id: int | None = None) -> list[RunRecord]:
    conn = get_connection()
    if resume_id:
        rows = conn.execute(
            "SELECT * FROM runs WHERE resume_id = ? ORDER BY created_at DESC",
            (resume_id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM runs ORDER BY created_at DESC").fetchall()
    conn.close()
    return [RunRecord(**dict(row)) for row in rows]


def get_resume(resume_id: int) -> ResumeRecord | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return ResumeRecord(**dict(row))


def get_job(job_id: int) -> JobRecord | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return JobRecord(**dict(row))


def get_latest_run(resume_id: int, job_id: int) -> RunRecord | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM runs WHERE resume_id = ? AND job_id = ? ORDER BY created_at DESC LIMIT 1",
        (resume_id, job_id),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return RunRecord(**dict(row))


def delete_resume(resume_id: int) -> None:
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM resumes WHERE id = ?", (resume_id,))
    conn.close()


def delete_job(job_id: int) -> None:
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.close()


def load_json_field(data: str) -> dict[str, Any]:
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return {}


def iter_resume_texts() -> Iterable[tuple[int, str, str]]:
    conn = get_connection()
    rows = conn.execute("SELECT id, name, raw_text FROM resumes").fetchall()
    conn.close()
    for row in rows:
        yield int(row[0]), str(row[1]), str(row[2])
