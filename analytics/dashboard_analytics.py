import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from analytics.exam_analytics import (
    get_integrity_dataframe,
    get_browser_dataframe,
    create_session_features,
    create_ml_dataset,
)

EVENT_COLUMNS = ["tab_switch", "focus_lost", "copy_attempt",
                 "paste_attempt", "cut_attempt", "right_click"]
RISK_COLORS = {"Low": "#4caf50", "Medium": "#ffb300", "High": "#e53935"}


def plot_integrity_distribution(df):
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(df["integrity_score"], bins=10, edgecolor="black")
    ax.set_xlabel("Integrity score"); ax.set_ylabel("Sessions")
    ax.set_title("Integrity score distribution")
    fig.tight_layout()
    return fig


def plot_risk_distribution(df):
    order = [r for r in RISK_COLORS if r in set(df["risk_level"])]
    counts = df["risk_level"].value_counts().reindex(order)
    fig, ax = plt.subplots(figsize=(5, 4))
    counts.plot(kind="bar", ax=ax, color=[RISK_COLORS[r] for r in order])
    ax.set_ylabel("Sessions"); ax.set_title("Risk level distribution")
    ax.tick_params(axis="x", rotation=0)
    fig.tight_layout()
    return fig


def plot_event_frequency(browser_df):
    fig, ax = plt.subplots(figsize=(8, 4))
    browser_df["event_type"].value_counts().plot(kind="bar", ax=ax)
    ax.set_ylabel("Count"); ax.set_title("Browser event frequency")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    return fig


def time_heatmap_matrix(browser_df, bucket_minutes=5,
                        ignore=("mouse_activity", "keyboard_activity")):
    df = browser_df[~browser_df["event_type"].isin(ignore)].copy()
    if df.empty:
        return pd.DataFrame()
    df["event_time"] = pd.to_datetime(df["event_time"])
    start = df.groupby("session_id")["event_time"].transform("min")
    secs = (df["event_time"] - start).dt.total_seconds()
    df["bucket"] = (secs // (bucket_minutes * 60) * bucket_minutes).astype(int)
    return df.pivot_table(index="event_type", columns="bucket",
                          values="session_id", aggfunc="count", fill_value=0)


def plot_event_heatmap(browser_df):
    matrix = time_heatmap_matrix(browser_df)
    fig, ax = plt.subplots(figsize=(10, 4))
    if matrix.empty:
        ax.text(0.5, 0.5, "No data", ha="center")
        return fig
    sns.heatmap(matrix, annot=True, fmt="d", cmap="YlOrRd", ax=ax)
    ax.set_xlabel("Minutes since exam start"); ax.set_ylabel("")
    ax.set_title("Event frequency over time (all sessions)")
    fig.tight_layout()
    return fig


def cluster_sessions(dataset):
    """K-Means on behaviour only (integrity_score is derived from these)."""
    cols = [c for c in EVENT_COLUMNS + ["face_presence_ratio"] if c in dataset.columns]
    if dataset.empty or len(dataset) < 4 or not cols:
        return dataset.assign(cluster=0, cluster_label="n/a (too few sessions)")

    scaled = StandardScaler().fit_transform(dataset[cols])

    best_k, best = 2, -1.0
    for k in range(2, min(5, len(dataset) - 1) + 1):
        labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(scaled)
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(scaled, labels)
        if score > best:
            best_k, best = k, score

    result = dataset.copy()
    result["cluster"] = KMeans(n_clusters=best_k, random_state=42,
                               n_init=10).fit_predict(scaled)
    rank = (result.groupby("cluster")["integrity_score"].mean()
                  .sort_values(ascending=False))
    names = ["Well-behaved", "Moderate", "High-activity", "Outlier", "Outlier 2"]
    result["cluster_label"] = result["cluster"].map(
        {c: names[i] for i, c in enumerate(rank.index)})
    return result


def load_clustered_dataset():
    integrity_df = get_integrity_dataframe()
    browser_df = get_browser_dataframe()
    if integrity_df.empty or browser_df.empty:
        return pd.DataFrame()
    dataset = create_ml_dataset(integrity_df, create_session_features(browser_df))
    return cluster_sessions(dataset)


def plot_clusters(clustered):
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.scatterplot(data=clustered, x="face_presence_ratio", y="integrity_score",
                    hue="cluster_label", s=90, ax=ax)
    ax.set_title("K-Means session clusters")
    fig.tight_layout()
    return fig


def cohort_risk_profile(df):
    return (df.groupby("risk_level")
              .agg(sessions=("session_id", "count"),
                   avg_score=("integrity_score", "mean"),
                   avg_face_presence=("face_presence_ratio", "mean"),
                   avg_event_penalty=("event_penalty", "mean"))
              .round(2).reset_index())