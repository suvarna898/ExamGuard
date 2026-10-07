import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from database import get_db


# ============================================================
# 1. LOAD INTEGRITY SCORE DATA
# ============================================================

def load_integrity_scores():
    """
    Fetch completed integrity-score records
    from the SQLite database.
    """

    connection = get_db()

    try:

        rows = connection.execute("""
            SELECT
                session_id,
                candidate_id,
                event_penalty,
                face_presence_ratio,
                integrity_score,
                risk_level,
                computed_at

            FROM integrity_scores

            ORDER BY computed_at
        """).fetchall()

        return [dict(row) for row in rows]

    finally:

        connection.close()


# ============================================================
# 2. CONVERT INTEGRITY DATA TO PANDAS DATAFRAME
# ============================================================

def get_integrity_dataframe():
    """
    Convert SQLite integrity-score data
    into a Pandas DataFrame.
    """

    rows = load_integrity_scores()

    df = pd.DataFrame(rows)

    return df


# ============================================================
# 3. BASIC STATISTICS
# ============================================================

def calculate_basic_statistics(df):
    """
    Calculate basic statistics from
    integrity-score data.
    """

    if df.empty:
        return {}

    statistics = {

        "total_sessions":
            len(df),

        "average_score":
            round(
                df["integrity_score"].mean(),
                2
            ),

        "minimum_score":
            df["integrity_score"].min(),

        "maximum_score":
            df["integrity_score"].max(),

        "average_face_presence":
            round(
                df["face_presence_ratio"].mean(),
                2
            ),

        "average_event_penalty":
            round(
                df["event_penalty"].mean(),
                2
            )
    }

    return statistics


# ============================================================
# 4. RISK LEVEL DISTRIBUTION
# ============================================================

def get_risk_distribution(df):
    """
    Count the number of sessions
    for each risk level.
    """

    if df.empty:
        return pd.Series(dtype="int64")

    return (
        df["risk_level"]
        .value_counts()
    )


# ============================================================
# 5. LOAD BROWSER EVENTS
# ============================================================

def load_browser_events():
    """
    Fetch browser events from SQLite.
    """

    connection = get_db()

    try:

        rows = connection.execute("""
            SELECT
                session_id,
                candidate_id,
                event_type,
                event_time,
                details

            FROM browser_events

            ORDER BY event_time
        """).fetchall()

        return [dict(row) for row in rows]

    finally:

        connection.close()


# ============================================================
# 6. CONVERT BROWSER EVENTS TO DATAFRAME
# ============================================================

def get_browser_dataframe():
    """
    Convert browser events into
    a Pandas DataFrame.
    """

    rows = load_browser_events()

    df = pd.DataFrame(rows)

    return df


# ============================================================
# 7. EVENT FREQUENCY
# ============================================================

def get_event_frequency(browser_df):
    """
    Count how many times each browser event occurred.
    """

    if browser_df.empty:
        return pd.Series(dtype="int64")

    return (
        browser_df["event_type"]
        .value_counts()
    )


# ============================================================
# 8. CREATE EVENT MATRIX
# ============================================================

def create_event_matrix(browser_df):
    """
    Create a session × event matrix.

    Rows    = exam sessions
    Columns = browser event types
    Values  = number of events
    """

    if browser_df.empty:
        return pd.DataFrame()

    matrix = pd.crosstab(
        browser_df["session_id"],
        browser_df["event_type"]
    )

    return matrix


# ============================================================
# 9. CREATE SESSION FEATURES
# ============================================================

def create_session_features(browser_df):
    """
    Convert raw browser events into
    numerical features for each session.
    """

    if browser_df.empty:
        return pd.DataFrame()

    features = pd.crosstab(
        browser_df["session_id"],
        browser_df["event_type"]
    )

    features = features.reset_index()

    return features


# ============================================================
# 10. CREATE MACHINE LEARNING DATASET
# ============================================================

def create_ml_dataset(
    integrity_df,
    session_features
):
    """
    Combine integrity-score information
    and browser-event features.

    One row represents one exam session.
    """

    if integrity_df.empty:
        return pd.DataFrame()

    if session_features.empty:

        return integrity_df.copy()

    dataset = integrity_df.merge(
        session_features,
        on="session_id",
        how="left"
    )

    # Browser events that did not occur
    # should have count = 0.
    dataset = dataset.fillna(0)

    return dataset


# ============================================================
# 11. PLOT INTEGRITY SCORE DISTRIBUTION
# ============================================================

def plot_integrity_distribution(df):
    """
    Display histogram of integrity scores.
    """

    if df.empty:

        print(
            "No integrity-score data available."
        )

        return

    plt.figure(
        figsize=(8, 5)
    )

    plt.hist(
        df["integrity_score"],
        bins=10
    )

    plt.xlabel(
        "Integrity Score"
    )

    plt.ylabel(
        "Number of Sessions"
    )

    plt.title(
        "Integrity Score Distribution"
    )

    plt.tight_layout()

    plt.show()


# ============================================================
# 12. PLOT RISK DISTRIBUTION
# ============================================================

def plot_risk_distribution(df):
    """
    Display the number of sessions
    in each risk level.
    """

    if df.empty:

        print(
            "No risk-level data available."
        )

        return

    counts = (
        df["risk_level"]
        .value_counts()
    )

    plt.figure(
        figsize=(7, 5)
    )

    counts.plot(
        kind="line"
    )

    plt.xlabel(
        "Risk Level"
    )

    plt.ylabel(
        "Number of Sessions"
    )

    plt.title(
        "Risk Level Distribution"
    )

    plt.xticks(
        rotation=0
    )

    plt.tight_layout()

    plt.show()


# ============================================================
# 13. PLOT BROWSER EVENT FREQUENCY
# ============================================================

def plot_event_frequency(browser_df):
    """
    Display browser event frequency.
    """

    if browser_df.empty:

        print(
            "No browser event data available."
        )

        return

    counts = (
        browser_df["event_type"]
        .value_counts()
    )

    plt.figure(
        figsize=(10, 6)
    )

    counts.plot(
        kind="pie"
    )

    plt.xlabel(
        "Event Type"
    )

    plt.ylabel(
        "Frequency"
    )

    plt.title(
        "Browser Event Frequency"
    )

    plt.xticks(
        rotation=45,
        ha="right"
    )

    plt.tight_layout()

    plt.show()


# ============================================================
# 14. PLOT EVENT HEATMAP
# ============================================================

def plot_event_heatmap(browser_df):
    """
    Display a heatmap showing
    browser event frequency per session.
    """

    matrix = create_event_matrix(
        browser_df
    )

    if matrix.empty:

        print(
            "No browser-event data available."
        )

        return

    plt.figure(
        figsize=(12, 7)
    )

    sns.heatmap(
        matrix,
        annot=True,
        fmt="d"
    )

    plt.title(
        "Browser Event Heatmap"
    )

    plt.xlabel(
        "Event Type"
    )

    plt.ylabel(
        "Exam Session"
    )

    plt.tight_layout()

    plt.show()


# ============================================================
# 15. SELECT FEATURES FOR K-MEANS
# ============================================================

def prepare_ml_features(dataset):
    """
    Select numerical session features
    that will be used by K-Means.
    """

    possible_features = [

        "integrity_score",

        "face_presence_ratio",

        "tab_switch",

        "focus_lost",

        "copy_attempt",

        "paste_attempt",

        "cut_attempt",

        "right_click"
    ]

    selected_features = []

    for column in possible_features:

        if column in dataset.columns:

            selected_features.append(
                column
            )

    if not selected_features:

        return pd.DataFrame()

    features = dataset[
        selected_features
    ].copy()

    return features


# ============================================================
# 16. STANDARDIZE FEATURES
# ============================================================

def scale_features(features):
    """
    Standardize numerical features
    before K-Means clustering.
    """

    scaler = StandardScaler()

    scaled_data = scaler.fit_transform(
        features
    )

    return scaled_data


# ============================================================
# 17. APPLY K-MEANS CLUSTERING
# ============================================================

def apply_kmeans(
    dataset,
    n_clusters=3
):
    """
    Apply K-Means clustering
    to exam sessions.
    """

    features = prepare_ml_features(
        dataset
    )

    if features.empty:

        print(
            "Not enough features for K-Means."
        )

        return dataset

    # Number of sessions must be greater
    # than or equal to number of clusters.
    if len(features) < n_clusters:

        print(
            "Not enough sessions for K-Means."
        )

        return dataset

    scaled_data = scale_features(
        features
    )

    model = KMeans(
        n_clusters=n_clusters,
        random_state=42,
        n_init=10
    )

    clusters = model.fit_predict(
        scaled_data
    )

    result = dataset.copy()

    result["cluster"] = clusters

    return result


# ============================================================
# 18. DISPLAY CLUSTER SUMMARY
# ============================================================

def display_cluster_summary(dataset):
    """
    Display basic characteristics
    of each K-Means cluster.
    """

    if "cluster" not in dataset.columns:

        print(
            "No cluster information available."
        )

        return

    print(
        "\n===== CLUSTER SUMMARY ====="
    )

    summary = (
        dataset
        .groupby("cluster")
        [
            [
                "integrity_score",
                "face_presence_ratio"
            ]
        ]
        .mean()
        .round(2)
    )

    print(summary)


# ============================================================
# 19. VISUALIZE K-MEANS CLUSTERS
# ============================================================

def plot_kmeans_clusters(dataset):
    """
    Display K-Means clusters using
    face presence and integrity score.
    """

    if "cluster" not in dataset.columns:

        print(
            "No cluster information available."
        )

        return

    plt.figure(
        figsize=(8, 6)
    )

    plt.scatter(
        dataset["face_presence_ratio"],
        dataset["integrity_score"],
        c=dataset["cluster"]
    )

    plt.xlabel(
        "Face Presence (%)"
    )

    plt.ylabel(
        "Integrity Score"
    )

    plt.title(
        "K-Means Exam Session Clusters"
    )

    plt.tight_layout()

    plt.show()


# ============================================================
# 20. MAIN ANALYTICS PROGRAM
# ============================================================

def main():

    print(
        "\n===================================="
    )

    print(
        "       EXAMGUARD DATA ANALYTICS"
    )

    print(
        "===================================="
    )


    # --------------------------------------------------------
    # LOAD INTEGRITY DATA
    # --------------------------------------------------------

    integrity_df = (
        get_integrity_dataframe()
    )

    print(
        "\n===== INTEGRITY DATA ====="
    )

    if integrity_df.empty:

        print(
            "No integrity-score records found."
        )

    else:

        print(
            integrity_df
        )


    # --------------------------------------------------------
    # BASIC DATAFRAME INFORMATION
    # --------------------------------------------------------

    if not integrity_df.empty:

        print(
            "\n===== DATAFRAME SHAPE ====="
        )

        print(
            integrity_df.shape
        )

        print(
            "\n===== DATAFRAME COLUMNS ====="
        )

        print(
            integrity_df.columns
        )

        print(
            "\n===== DATA TYPES ====="
        )

        print(
            integrity_df.dtypes
        )


    # --------------------------------------------------------
    # BASIC STATISTICS
    # --------------------------------------------------------

    statistics = (
        calculate_basic_statistics(
            integrity_df
        )
    )

    print(
        "\n===== BASIC STATISTICS ====="
    )

    for key, value in statistics.items():

        print(
            f"{key}: {value}"
        )


    # --------------------------------------------------------
    # RISK DISTRIBUTION
    # --------------------------------------------------------

    risk_distribution = (
        get_risk_distribution(
            integrity_df
        )
    )

    print(
        "\n===== RISK DISTRIBUTION ====="
    )

    print(
        risk_distribution
    )


    # --------------------------------------------------------
    # LOAD BROWSER EVENTS
    # --------------------------------------------------------

    browser_df = (
        get_browser_dataframe()
    )

    print(
        "\n===== BROWSER EVENTS ====="
    )

    if browser_df.empty:

        print(
            "No browser events found."
        )

    else:

        print(
            browser_df.head()
        )


    # --------------------------------------------------------
    # EVENT FREQUENCY
    # --------------------------------------------------------

    event_frequency = (
        get_event_frequency(
            browser_df
        )
    )

    print(
        "\n===== EVENT FREQUENCY ====="
    )

    print(
        event_frequency
    )


    # --------------------------------------------------------
    # EVENT MATRIX
    # --------------------------------------------------------

    event_matrix = (
        create_event_matrix(
            browser_df
        )
    )

    print(
        "\n===== EVENT MATRIX ====="
    )

    print(
        event_matrix
    )


    # --------------------------------------------------------
    # CREATE SESSION FEATURES
    # --------------------------------------------------------

    session_features = (
        create_session_features(
            browser_df
        )
    )

    print(
        "\n===== SESSION FEATURES ====="
    )

    print(
        session_features
    )


    # --------------------------------------------------------
    # CREATE ML DATASET
    # --------------------------------------------------------

    ml_dataset = (
        create_ml_dataset(
            integrity_df,
            session_features
        )
    )

    print(
        "\n===== ML DATASET ====="
    )

    print(
        ml_dataset
    )


    # --------------------------------------------------------
    # VISUALIZATIONS
    # --------------------------------------------------------

    if not integrity_df.empty:

        plot_integrity_distribution(
            integrity_df
        )

        plot_risk_distribution(
            integrity_df
        )


    if not browser_df.empty:

        plot_event_frequency(
            browser_df
        )

        plot_event_heatmap(
            browser_df
        )


    # --------------------------------------------------------
    # K-MEANS
    # --------------------------------------------------------

    if not ml_dataset.empty:

        clustered_dataset = (
            apply_kmeans(
                ml_dataset,
                n_clusters=3
            )
        )

        print(
            "\n===== K-MEANS RESULT ====="
        )

        print(
            clustered_dataset
        )


        # ----------------------------------------------------
        # CLUSTER SUMMARY
        # ----------------------------------------------------

        display_cluster_summary(
            clustered_dataset
        )


        # ----------------------------------------------------
        # CLUSTER VISUALIZATION
        # ----------------------------------------------------

        if "cluster" in clustered_dataset.columns:

            plot_kmeans_clusters(
                clustered_dataset
            )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()