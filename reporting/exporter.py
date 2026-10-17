"""
Reporting & Export module (+ data access for the dashboard).

Everything here reads straight from SQLite via get_db() and returns
Pandas DataFrames / plain dicts, so the dashboard and the exports always
show exactly the same data.
"""

import io
import json
import zipfile
from datetime import datetime

import pandas as pd

from database import get_db
from analytics.dashboard_analytics import load_clustered_dataset


# ------------------------------------------------------------
# small helpers
# ------------------------------------------------------------
def _query(sql, params=()):
    connection = get_db()
    try:
        return pd.read_sql_query(sql, connection, params=params)
    finally:
        connection.close()


def _csv_safe(df):
    """
    Stop spreadsheet formula injection: a text cell starting with = + - @
    would be executed by Excel. Prefix such cells with a quote.
    """
    df = df.copy()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].apply(
            lambda v: "'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@") else v
        )
    return df


def df_to_csv_bytes(df):
    return _csv_safe(df).to_csv(index=False).encode("utf-8")


def to_json_bytes(obj):
    return json.dumps(obj, indent=2, default=str, ensure_ascii=False).encode("utf-8")


def _records(df):
    return json.loads(df.to_json(orient="records", date_format="iso"))


# ------------------------------------------------------------
# dashboard data access
# ------------------------------------------------------------
def load_active_sessions():
    """Sessions currently running or paused, with live counters."""
    return _query("""
        SELECT
            es.session_id,
            es.candidate_id,
            c.name AS candidate,
            es.status,
            es.started_at,
            (SELECT COUNT(*) FROM browser_events b
               WHERE b.session_id = es.session_id) AS events,
            (SELECT MAX(event_time) FROM browser_events b
               WHERE b.session_id = es.session_id) AS last_event,
            (SELECT COUNT(*) FROM suspicious_events s
               WHERE s.session_id = es.session_id) AS flags,
            (SELECT COUNT(*) FROM face_events f
               WHERE f.session_id = es.session_id
                 AND f.ended_at IS NULL) AS face_absent_now,
            (SELECT COUNT(*) FROM alerts a
               WHERE a.session_id = es.session_id AND a.status = 'open') AS open_alerts
        FROM exam_sessions es
        JOIN candidates c ON c.id = es.candidate_id
        WHERE es.status != 'submitted'
        ORDER BY es.started_at DESC
    """)


def load_sessions_overview():
    """One row per session with score, risk and counters."""
    return _query("""
        SELECT
            es.session_id,
            es.candidate_id,
            c.name AS candidate,
            es.status,
            es.started_at,
            es.submitted_at,
            s.integrity_score,
            s.risk_level,
            s.face_presence_ratio,
            s.event_penalty,
            (SELECT COUNT(*) FROM alerts a
               WHERE a.session_id = es.session_id AND a.status = 'open') AS open_alerts,
            (SELECT COUNT(*) FROM evidence e
               WHERE e.session_id = es.session_id) AS evidence_count
        FROM exam_sessions es
        JOIN candidates c ON c.id = es.candidate_id
        LEFT JOIN integrity_scores s ON s.session_id = es.session_id
        ORDER BY es.started_at DESC
    """)


def load_alerts(status=None):
    sql = """
        SELECT a.id, a.session_id, a.candidate_id, c.name AS candidate,
               a.alert_type, a.message, a.severity, a.status, a.created_at
        FROM alerts a
        JOIN candidates c ON c.id = a.candidate_id
    """
    params = ()
    if status:
        sql += " WHERE a.status = ?"
        params = (status,)
    return _query(sql + " ORDER BY a.created_at DESC", params)


def set_alert_status(alert_id, status):
    if status not in ("open", "reviewed", "dismissed"):
        raise ValueError("invalid status")
    connection = get_db()
    try:
        connection.execute("UPDATE alerts SET status = ? WHERE id = ?", (status, alert_id))
        connection.commit()
    finally:
        connection.close()


def load_ai_report(session_id):
    df = _query(
        "SELECT * FROM ai_reports WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
        (session_id,),
    )
    return df.iloc[0].to_dict() if not df.empty else None


def load_evidence_meta(session_id):
    """Evidence metadata only (no image bytes)."""
    return _query("""
        SELECT id, evidence_type, filename, mime_type, sha256_hash, created_at
        FROM evidence WHERE session_id = ? ORDER BY created_at DESC
    """, (session_id,))


def load_evidence_bytes(evidence_id):
    connection = get_db()
    try:
        row = connection.execute(
            "SELECT file_data FROM evidence WHERE id = ?", (evidence_id,)
        ).fetchone()
        return bytes(row["file_data"]) if row else None
    finally:
        connection.close()


# ------------------------------------------------------------
# export datasets
# ------------------------------------------------------------
def get_session_logs_df(session_id=None):
    """Browser, face and rule-engine events in one chronological table."""
    where = "WHERE session_id = ?" if session_id else ""
    params = (session_id,) if session_id else ()

    browser = _query(f"""
        SELECT session_id, candidate_id, 'browser' AS source, event_type,
               event_time AS start_time, NULL AS end_time,
               NULL AS duration_seconds, NULL AS severity, details
        FROM browser_events {where}""", params)

    face = _query(f"""
        SELECT session_id, candidate_id, 'face' AS source, event_type,
               started_at AS start_time, ended_at AS end_time,
               duration_seconds, NULL AS severity, NULL AS details
        FROM face_events {where}""", params)

    flags = _query(f"""
        SELECT session_id, candidate_id, 'rule_engine' AS source, event_type,
               event_time AS start_time, NULL AS end_time,
               NULL AS duration_seconds, severity, reason AS details
        FROM suspicious_events {where}""", params)

    frames = [f for f in (browser, face, flags) if not f.empty]
    if not frames:
        return pd.DataFrame(columns=[
            "session_id", "candidate_id", "source", "event_type", "start_time",
            "end_time", "duration_seconds", "severity", "details"])

    return (pd.concat(frames, ignore_index=True)
              .sort_values(["session_id", "start_time"])
              .reset_index(drop=True))


def get_scores_df(session_id=None):
    where = "WHERE s.session_id = ?" if session_id else ""
    params = (session_id,) if session_id else ()
    return _query(f"""
        SELECT s.session_id, s.candidate_id, c.name AS candidate,
               s.integrity_score, s.risk_level, s.event_penalty,
               s.face_presence_ratio, s.computed_at
        FROM integrity_scores s
        JOIN candidates c ON c.id = s.candidate_id
        {where}
        ORDER BY s.computed_at DESC""", params)


def get_clusters_df(session_id=None):
    df = load_clustered_dataset()
    if df.empty:
        return df
    return df[df["session_id"] == session_id] if session_id else df


def get_ai_reports_df(session_id=None):
    where = "WHERE session_id = ?" if session_id else ""
    params = (session_id,) if session_id else ()
    return _query(f"SELECT * FROM ai_reports {where} ORDER BY created_at DESC", params)


def get_alerts_df(session_id=None):
    where = "WHERE session_id = ?" if session_id else ""
    params = (session_id,) if session_id else ()
    return _query(f"SELECT * FROM alerts {where} ORDER BY created_at DESC", params)


def get_evidence_meta_df(session_id=None):
    where = "WHERE session_id = ?" if session_id else ""
    params = (session_id,) if session_id else ()
    return _query(f"""
        SELECT id, candidate_id, session_id, evidence_type, filename,
               mime_type, sha256_hash, created_at
        FROM evidence {where} ORDER BY created_at DESC""", params)


# ------------------------------------------------------------
# JSON bundles + ZIP
# ------------------------------------------------------------
def build_session_bundle(session_id):
    """Everything about ONE session as a single JSON-able dict."""
    return {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "session_id": session_id,
        "integrity_score": _records(get_scores_df(session_id)),
        "cluster_assignment": _records(get_clusters_df(session_id)),
        "ai_reports": _records(get_ai_reports_df(session_id)),
        "alerts": _records(get_alerts_df(session_id)),
        "evidence_metadata": _records(get_evidence_meta_df(session_id)),
        "event_log": _records(get_session_logs_df(session_id)),
    }


def build_cohort_bundle():
    """Cohort-level JSON: scores, clusters, AI reports, alerts, evidence list."""
    return {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "integrity_scores": _records(get_scores_df()),
        "cluster_assignments": _records(get_clusters_df()),
        "ai_reports": _records(get_ai_reports_df()),
        "alerts": _records(get_alerts_df()),
        "evidence_metadata": _records(get_evidence_meta_df()),
    }


def build_zip_bytes():
    """One ZIP with a CSV per dataset plus the full cohort JSON."""
    files = {
        "session_logs.csv": df_to_csv_bytes(get_session_logs_df()),
        "integrity_scores.csv": df_to_csv_bytes(get_scores_df()),
        "cluster_assignments.csv": df_to_csv_bytes(get_clusters_df()),
        "ai_reports.csv": df_to_csv_bytes(get_ai_reports_df()),
        "alerts.csv": df_to_csv_bytes(get_alerts_df()),
        "evidence_metadata.csv": df_to_csv_bytes(get_evidence_meta_df()),
        "cohort_export.json": to_json_bytes(build_cohort_bundle()),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()