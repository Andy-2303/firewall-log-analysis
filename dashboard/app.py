"""Firewall traffic dashboard. Reads the analytics tables from PostgreSQL (read-only user).

Run from the project folder:  python -m streamlit run dashboard/app.py
"""
import os
from decimal import Decimal

import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

DB_URL = os.environ.get(
    "FIREWALL_DB_URL",
    "postgresql+psycopg2://assistant_ro:assistant_pw@localhost:5432/firewall",
)

ALLOWED_COLOR = "#4C78A8"
BLOCKED_COLOR = "#E45756"

st.set_page_config(page_title="Firewall Traffic Dashboard", layout="wide")


@st.cache_resource
def get_engine():
    return create_engine(DB_URL)


def _floatify(df: pd.DataFrame) -> pd.DataFrame:
    """Postgres numeric columns arrive as Decimal; convert them so charts work."""
    for col in df.columns:
        if df[col].dtype == object and df[col].map(lambda v: isinstance(v, Decimal)).any():
            df[col] = df[col].astype(float)
    return df


@st.cache_data(ttl=60)
def load_table(table: str) -> pd.DataFrame:
    # table names come from the fixed list below, never from user input
    with get_engine().connect() as conn:
        df = pd.read_sql(text(f"SELECT * FROM analytics.{table} LIMIT 5000"), conn)
    return _floatify(df)


def port_label(port: int, service: str) -> str:
    return f"{port} {service}" if service != "Other" else str(port)


# ---------- load data ----------
try:
    actions = load_table("action_summary")
    ports = load_table("block_rate_by_port")
    outliers = load_table("outlier_sessions")
except Exception as e:  # database down, tables missing, wrong password...
    st.title("Firewall Traffic Dashboard")
    st.error("Could not read the analytics tables. Is the database running, and has the pipeline been run?")
    st.code("docker compose up -d\npython pipeline/transform.py")
    st.caption(str(e).splitlines()[0])
    st.stop()

# ---------- sidebar filters ----------
st.sidebar.header("Filters")
min_sessions = st.sidebar.slider("Minimum sessions per port", 50, 1000, 50, step=50)
top_n = st.sidebar.slider("Number of ports to show", 5, 30, 15)

shown = (
    ports[ports["sessions"] >= min_sessions]
    .sort_values("sessions", ascending=False)
    .head(top_n)
    .copy()
)
shown["port"] = [port_label(p, s) for p, s in zip(shown["destination_port"], shown["service_name"])]

# ---------- headline numbers ----------
total_sessions = int(actions["sessions"].sum())
blocked_sessions = int(actions.loc[actions["action"] != "allow", "sessions"].sum())
blocked_pct = round(100 * blocked_sessions / total_sessions, 1) if total_sessions else 0.0
top_blocked = ports.sort_values("blocked_sessions", ascending=False).iloc[0]
top_blocked_share = round(100 * int(top_blocked["blocked_sessions"]) / blocked_sessions, 1) if blocked_sessions else 0.0

st.title("Firewall Traffic Dashboard")
st.caption("Source: UCI Internet Firewall Data. Built from the analytics tables of the PostgreSQL pipeline.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total sessions", f"{total_sessions:,}")
c2.metric("Blocked", f"{blocked_pct}%")
c3.metric(
    "Top blocked destination",
    port_label(int(top_blocked["destination_port"]), top_blocked["service_name"]),
    f"{top_blocked_share}% of all blocked sessions",
    delta_color="off",
    delta_arrow="off",
)
c4.metric("Unusual sessions flagged", f"{len(outliers):,}")

# ---------- charts ----------
left, right = st.columns(2)

with left:
    st.subheader("Sessions by firewall action")
    action_chart = (
        alt.Chart(actions)
        .mark_bar()
        .encode(
            x=alt.X("action:N", sort="-y", title=None),
            y=alt.Y("sessions:Q", title="Sessions"),
            color=alt.condition(alt.datum.action == "allow", alt.value(ALLOWED_COLOR), alt.value(BLOCKED_COLOR)),
            tooltip=["action", "sessions", alt.Tooltip("pct_of_sessions:Q", title="% of sessions")],
        )
        .properties(height=360)
    )
    st.altair_chart(action_chart)

with right:
    st.subheader(f"Block rate for the {len(shown)} busiest ports")
    rate_chart = (
        alt.Chart(shown)
        .mark_bar(color=BLOCKED_COLOR)
        .encode(
            x=alt.X("block_rate_pct:Q", title="Block rate (%)", scale=alt.Scale(domain=[0, 100])),
            y=alt.Y("port:N", sort=list(shown["port"]), title=None),
            tooltip=["port", "sessions", "blocked_sessions", "block_rate_pct"],
        )
        .properties(height=360)
    )
    st.altair_chart(rate_chart)

st.subheader("Allowed vs blocked sessions per port")
split = shown.assign(allowed=shown["sessions"] - shown["blocked_sessions"])[["port", "allowed", "blocked_sessions"]]
split = split.rename(columns={"allowed": "Allowed", "blocked_sessions": "Blocked"})
long = split.melt(id_vars="port", var_name="outcome", value_name="sessions")
stack_chart = (
    alt.Chart(long)
    .mark_bar()
    .encode(
        x=alt.X("sessions:Q", title="Sessions"),
        y=alt.Y("port:N", sort=list(shown["port"]), title=None),
        color=alt.Color(
            "outcome:N",
            scale=alt.Scale(domain=["Allowed", "Blocked"], range=[ALLOWED_COLOR, BLOCKED_COLOR]),
            title=None,
        ),
        tooltip=["port", "outcome", "sessions"],
    )
    .properties(height=420)
)
st.altair_chart(stack_chart)

# ---------- tables ----------
st.subheader("Port details")
st.dataframe(
    shown[["port", "sessions", "blocked_sessions", "block_rate_pct"]],
    hide_index=True,
    column_config={
        "port": "Destination port",
        "sessions": "Sessions",
        "blocked_sessions": "Blocked",
        "block_rate_pct": st.column_config.ProgressColumn("Block rate (%)", min_value=0, max_value=100, format="%.1f"),
    },
)

st.subheader("Unusual sessions")
reasons = ["All"] + sorted(outliers["reason"].unique())
choice = st.selectbox("Reason flagged", reasons)
view = outliers if choice == "All" else outliers[outliers["reason"] == choice]
st.write(f"{len(view):,} sessions. Showing the 200 largest by bytes.")
st.dataframe(
    view.sort_values("bytes", ascending=False)
    .head(200)[["session_id", "destination_port", "service_name", "action", "bytes", "packets", "elapsed_seconds", "reason"]],
    hide_index=True,
)

st.caption(
    "Note: the dataset has no IP addresses or timestamps, so source-based and time-of-day analysis is not possible."
)
