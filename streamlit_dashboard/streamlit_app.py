"""
ExamGuard - Invigilator Dashboard (Streamlit)

Run (Flask app can run at the same time, they share the SQLite file):
    streamlit run dashboard.py
"""

import hmac
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from database import init_db
from analytics import dashboard_analytics as charts
from analytics.exam_analytics import get_integrity_dataframe, get_browser_dataframe
from reporting import exporter as ex

load_dotenv()
init_db()

PASSWORD = os.environ.get("REVIEWER_PASSWORD", "examguard123")
ROUTINE = {"mouse_activity", "keyboard_activity", "answer_selected", "answer_saved"}
RISK_ICON = {"Low": "🟢", "Medium": "🟠", "High": "🔴"}

st.set_page_config(page_title="ExamGuard Dashboard", page_icon="🛡️", layout="wide")


# ------------------------------------------------------------
# helpers
# ------------------------------------------------------------
def show_fig(fig):
    st.pyplot(fig)
    plt.close(fig)


@st.cache_data(ttl=30)
def cached_analytics():
    integrity = get_integrity_dataframe()
    browser = get_browser_dataframe()
    clustered = charts.load_clustered_dataset()
    return integrity, browser, clustered


def download_row(label, csv_df, json_obj, file_stem):
    """A CSV + JSON download button pair."""
    c1, c2 = st.columns(2)
    c1.download_button(f"{label} (CSV)", ex.df_to_csv_bytes(csv_df),
                       f"{file_stem}.csv", "text/csv", key=f"csv_{file_stem}",
                       disabled=csv_df.empty)
    c2.download_button(f"{label} (JSON)", ex.to_json_bytes(json_obj),
                       f"{file_stem}.json", "application/json", key=f"json_{file_stem}",
                       disabled=csv_df.empty)


# ------------------------------------------------------------
# login gate
# ------------------------------------------------------------
if not st.session_state.get("auth"):
    st.title("🛡️ ExamGuard")
    st.subheader("Invigilator sign in")
    pw = st.text_input("Password", type="password")
    if st.button("Sign in", type="primary"):
        if hmac.compare_digest(pw, PASSWORD):
            st.session_state["auth"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

with st.sidebar:
    st.title("🛡️ ExamGuard")
    st.caption("Invigilator dashboard")
    if st.button("Refresh data"):
        st.cache_data.clear()
        st.rerun()
    if st.button("Log out"):
        st.session_state.clear()
        st.rerun()

st.title("Examination Monitoring Dashboard")

tab_live, tab_sessions, tab_analytics, tab_export = st.tabs(
    ["📡 Live monitoring", "🔎 Session review", "📊 Analytics", "📦 Export"]
)


# ------------------------------------------------------------
# 1. LIVE MONITORING + REAL-TIME ALERTS  (auto-refreshes every 5 s)
# ------------------------------------------------------------
with tab_live:

    @st.fragment(run_every=5)
    def live_panel():
        active = ex.load_active_sessions()
        open_alerts = ex.load_alerts(status="open")

        m1, m2, m3 = st.columns(3)
        m1.metric("Active sessions", len(active))
        m2.metric("Open alerts", len(open_alerts))
        m3.metric("Candidates with face absent now",
                  int((active["face_absent_now"] > 0).sum()) if not active.empty else 0)

        st.subheader("Sessions in progress")
        if active.empty:
            st.info("No exam sessions are running right now.")
        else:
            st.dataframe(
                active.drop(columns=["session_id", "candidate_id"]),
                width="stretch", hide_index=True,
            )

        st.subheader("Open alerts")
        if open_alerts.empty:
            st.success("No open alerts.")
        else:
            for _, a in open_alerts.head(25).iterrows():
                c1, c2 = st.columns([6, 1])
                c1.warning(
                    f"**{a['severity']}** · {a['candidate']} · {a['alert_type']}  \n"
                    f"{a['message']}  \n:gray[{str(a['created_at'])[:19]}]"
                )
                # on_click runs before the fragment re-renders, so the alert
                # disappears from the list without any manual rerun
                c2.button("Mark reviewed", key=f"ack_{a['id']}",
                          on_click=ex.set_alert_status,
                          args=(int(a["id"]), "reviewed"))

    live_panel()


# ------------------------------------------------------------
# 2. SESSION REVIEW  (score, AI summary, events, evidence)
# ------------------------------------------------------------
def sessions_tab():
    overview = ex.load_sessions_overview()

    if overview.empty:
        st.info("No sessions recorded yet.")
    else:
        f1, f2 = st.columns(2)
        risk_filter = f1.multiselect("Risk level", ["Low", "Medium", "High"])
        only_alerts = f2.checkbox("Only sessions with open alerts")

        view = overview
        if risk_filter:
            view = view[view["risk_level"].isin(risk_filter)]
        if only_alerts:
            view = view[view["open_alerts"] > 0]

        st.dataframe(view.drop(columns=["session_id", "candidate_id"]),
                     width="stretch", hide_index=True)

        if view.empty:
            st.info("No sessions match these filters.")
            return

        # label -> session_id (label includes the start time, so it is unique)
        label_to_sid = {
            f"{r.candidate} · {str(r.started_at)[:16]} · "
            f"{r.status if pd.isna(r.risk_level) else r.risk_level} · {r.session_id[:6]}":
            r.session_id
            for r in view.itertuples()
        }
        chosen = st.selectbox("Open a session", list(label_to_sid))
        sid = label_to_sid[chosen]
        row = view[view["session_id"] == sid].iloc[0]

        st.divider()
        st.subheader(f"{row['candidate']}")

        if pd.isna(row["integrity_score"]):
            st.info(f"Session is **{row['status']}** - no integrity score yet "
                    "(it is computed when the candidate submits).")
        else:
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Integrity score", f"{row['integrity_score']:.0f}")
            k2.metric("Risk", f"{RISK_ICON.get(row['risk_level'], '')} {row['risk_level']}")
            k3.metric("Face presence", f"{row['face_presence_ratio']:.1f}%")
            k4.metric("Event penalty", f"{row['event_penalty']:.0f}")

        # ---- AI summary
        st.markdown("#### AI integrity summary")
        report = ex.load_ai_report(sid)
        if report:
            st.write(report["report"])
            source = report.get("source")
            note = "rule-based fallback" if source == "fallback" else "LLM-generated"
            st.caption(f"{note} · {str(report['created_at'])[:19]}")
        elif not pd.isna(row["integrity_score"]):
            st.caption("No report saved for this session yet.")
            if st.button("Generate AI report", key=f"gen_{sid}"):
                from ai.integrity_agent import generate_real_integrity_report
                from monitoring.ai_repor_manager import save_ai_report
                with st.spinner("Generating report..."):
                    try:
                        text = generate_real_integrity_report(int(row["candidate_id"]), sid)
                        save_ai_report(candidate_id=int(row["candidate_id"]),
                                       session_id=sid, report=text)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not generate report: {e}")

        # ---- flags + events
        logs = ex.get_session_logs_df(sid)

        st.markdown("#### Rule-engine flags")
        flags = logs[logs["source"] == "rule_engine"]
        if flags.empty:
            st.caption("No flags raised.")
        else:
            st.dataframe(flags[["start_time", "event_type", "severity", "details"]],
                         width="stretch", hide_index=True)

        e1, e2 = st.columns(2)
        with e1:
            st.markdown("#### Event counts")
            browser = logs[(logs["source"] == "browser")]
            counts = browser["event_type"].value_counts()
            if counts.empty:
                st.caption("No browser events.")
            else:
                st.bar_chart(counts)
        with e2:
            st.markdown("#### Face-absent intervals")
            face = logs[logs["source"] == "face"][
                ["start_time", "end_time", "duration_seconds"]]
            if face.empty:
                st.caption("No face-absent intervals.")
            else:
                st.dataframe(face, width="stretch", hide_index=True)
                st.caption(f"Total absent: {face['duration_seconds'].sum():.0f} s")

        with st.expander("Full event timeline (without routine mouse/keyboard events)"):
            timeline = logs[~logs["event_type"].isin(ROUTINE)]
            st.dataframe(timeline, width="stretch", hide_index=True)

        # ---- evidence
        st.markdown("#### Evidence")
        evidence = ex.load_evidence_meta(sid)
        if evidence.empty:
            st.caption("No screenshots stored for this session.")
        else:
            cols = st.columns(3)
            for i, e in enumerate(evidence.itertuples()):
                data = ex.load_evidence_bytes(e.id)
                with cols[i % 3]:
                    if data:
                        st.image(data, caption=f"{str(e.created_at)[:19]}")
                    st.caption(f"SHA-256: `{e.sha256_hash[:16]}…`")

        # ---- per-session export
        st.markdown("#### Export this session")
        st.download_button(
            "Full session bundle (JSON)", ex.to_json_bytes(ex.build_session_bundle(sid)),
            f"session_{sid[:8]}.json", "application/json", key=f"bundle_{sid}")


with tab_sessions:
    sessions_tab()


# ------------------------------------------------------------
# 3. ANALYTICS (cohort level)
# ------------------------------------------------------------
with tab_analytics:
    integrity_df, browser_df, clustered = cached_analytics()

    if integrity_df.empty:
        st.info("No scored sessions yet. Generate data with "
                "`python synthetic_data_generator.py 60` or submit an exam.")
    else:
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Sessions scored", len(integrity_df))
        s2.metric("Average score", f"{integrity_df['integrity_score'].mean():.1f}")
        s3.metric("High-risk sessions", int((integrity_df["risk_level"] == "High").sum()))
        s4.metric("Avg face presence", f"{integrity_df['face_presence_ratio'].mean():.1f}%")

        a1, a2 = st.columns(2)
        with a1:
            show_fig(charts.plot_integrity_distribution(integrity_df))
        with a2:
            show_fig(charts.plot_risk_distribution(integrity_df))

        if not browser_df.empty:
            b1, b2 = st.columns(2)
            with b1:
                show_fig(charts.plot_event_frequency(browser_df))
            with b2:
                show_fig(charts.plot_event_heatmap(browser_df))

        st.subheader("Session behaviour clusters (K-Means)")
        if clustered.empty:
            st.info("Not enough data for clustering.")
        else:
            c1, c2 = st.columns([3, 2])
            with c1:
                show_fig(charts.plot_clusters(clustered))
            with c2:
                summary = (clustered.groupby("cluster_label")
                           .agg(sessions=("session_id", "count"),
                                avg_score=("integrity_score", "mean"),
                                avg_face_presence=("face_presence_ratio", "mean"))
                           .round(1).reset_index())
                st.dataframe(summary, hide_index=True, width="stretch")

        st.subheader("Cohort risk profile")
        st.dataframe(charts.cohort_risk_profile(integrity_df),
                     hide_index=True, width="stretch")


# ------------------------------------------------------------
# 4. EXPORT (JSON / CSV)
# ------------------------------------------------------------
with tab_export:
    st.write("Download structured exports of every session output. "
             "Screenshots are exported as metadata (hash, time) only.")

    st.download_button(
        "⬇️ Download everything (ZIP: CSVs + JSON)", ex.build_zip_bytes(),
        "examguard_export.zip", "application/zip", type="primary")

    st.divider()

    datasets = {
        "Session logs": ("session_logs", ex.get_session_logs_df()),
        "Integrity scores": ("integrity_scores", ex.get_scores_df()),
        "Cluster assignments": ("cluster_assignments", ex.get_clusters_df()),
        "AI reports": ("ai_reports", ex.get_ai_reports_df()),
        "Alerts": ("alerts", ex.get_alerts_df()),
    }
    for label, (stem, df) in datasets.items():
        st.markdown(f"**{label}** · {len(df)} rows")
        download_row(label, df, ex._records(df), stem)

    st.markdown("**Full cohort bundle**")
    st.download_button("Cohort bundle (JSON)", ex.to_json_bytes(ex.build_cohort_bundle()),
                       "cohort_export.json", "application/json", key="cohort_json")