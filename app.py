"""
Smart Momentum - Public Portfolio Dashboard
Displays live picks, NAV performance, and historical simulation.
NO proprietary methodology is exposed.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────────────────────
# Page Configuration
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Smart Momentum Portfolio",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📈 Smart Momentum Portfolio")
st.markdown("Live picks, transparent performance, institutional-grade risk management.")
st.markdown("---")

# ─────────────────────────────────────────────────────────────
# Data Loading
# ─────────────────────────────────────────────────────────────
DATA_DIR = Path("data")

@st.cache_data
def load_nav_history():
    path = DATA_DIR / "nav_history.csv"
    if path.exists():
        df = pd.read_csv(path, parse_dates=["date"])
        return df
    return pd.DataFrame()

@st.cache_data
def load_live_picks():
    path = DATA_DIR / "live_picks.json"
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return []

@st.cache_data
def load_ytd_performance():
    path = DATA_DIR / "ytd_performance.json"
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return []

@st.cache_data
def load_recent_trades():
    path = DATA_DIR / "recent_trades.json"
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return []

# Load all data
nav_df = load_nav_history()
live_picks = load_live_picks()
ytd_perf = load_ytd_performance()
recent_trades = load_recent_trades()

if nav_df.empty:
    st.error("⚠️ No data available yet. The pipeline is currently running.")
    st.stop()

# ─────────────────────────────────────────────────────────────
# Section 1: Current Portfolio Performance
# ─────────────────────────────────────────────────────────────
st.subheader("💼 Current Portfolio Performance")

col1, col2, col3, col4 = st.columns(4)

# Calculate aggregate metrics
if ytd_perf:
    total_port_return = sum(p["portfolio_return"] for p in ytd_perf) / len(ytd_perf)
    total_bench_return = sum(p["benchmark_return"] for p in ytd_perf) / len(ytd_perf)
    total_active_return = sum(p["active_return"] for p in ytd_perf) / len(ytd_perf)
    
    col1.metric(
        label="Portfolio Return (YTD)",
        value=f"{total_port_return*100:+.1f}%",
        delta=f"vs {total_bench_return*100:+.1f}% Benchmark"
    )
    col2.metric(
        label="Active Return",
        value=f"{total_active_return*100:+.1f}%",
        delta="Outperformance" if total_active_return > 0 else "Underperformance"
    )
    col3.metric(
        label="Active Positions",
        value=len(live_picks),
        delta="Currently held"
    )
    col4.metric(
        label="Data Freshness",
        value="Updated",
        delta=f"{datetime.now().strftime('%H:%M')} today"
    )
else:
    st.warning("Performance data not yet available.")

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# Section 2: Live Picks Table
# ─────────────────────────────────────────────────────────────
st.subheader("🎯 Current Holdings")

if live_picks:
    picks_df = pd.DataFrame(live_picks)
    
    # Portfolio filter
    portfolios = ["All"] + sorted(picks_df["portfolio_id"].unique().tolist())
    selected_port = st.selectbox("Filter by Portfolio", portfolios)
    
    if selected_port != "All":
        picks_df = picks_df[picks_df["portfolio_id"] == selected_port]
    
    # Format for display
    display_df = picks_df.copy()
    display_df["entry_date"] = pd.to_datetime(display_df["entry_date"]).dt.date
    display_df["entry_price"] = display_df["entry_price"].apply(lambda x: f"${x:.2f}")
    display_df["current_price"] = display_df["current_price"].apply(lambda x: f"${x:.2f}")
    display_df["unrealized_pnl"] = display_df["unrealized_pnl"].apply(lambda x: f"{x*100:+.2f}%")
    
    # Rename columns for public display
    display_df = display_df.rename(columns={
        "portfolio_id": "Portfolio",
        "ticker": "Ticker",
        "entry_date": "Entry Date",
        "entry_price": "Entry Price",
        "current_price": "Current Price",
        "unrealized_pnl": "P&L"
    })
    
    # Drop internal columns
    if "shares" in display_df.columns:
        display_df = display_df.drop(columns=["shares"])
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("No active positions at this time.")

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# Section 3: NAV Performance Chart
# ─────────────────────────────────────────────────────────────
st.subheader("📊 Portfolio NAV vs Benchmark")

if not nav_df.empty:
    # Portfolio selector
    port_options = nav_df["portfolio_id"].unique().tolist()
    selected_nav_port = st.selectbox("Select Portfolio for NAV Chart", port_options)
    
    nav_filtered = nav_df[nav_df["portfolio_id"] == selected_nav_port].sort_values("date")
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=nav_filtered["date"],
        y=nav_filtered["portfolio_nav"],
        name="Portfolio NAV",
        mode="lines",
        line=dict(color="#00cc96", width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=nav_filtered["date"],
        y=nav_filtered["benchmark_nav"],
        name="Benchmark NAV",
        mode="lines",
        line=dict(color="#636efa", width=2, dash="dash")
    ))
    
    fig.update_layout(
        title=f"NAV Performance: {selected_nav_port}",
        xaxis_title="Date",
        yaxis_title="NAV ($)",
        height=450,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# Section 4: Recent Trade Activity
# ─────────────────────────────────────────────────────────────
st.subheader("🔄 Recent Trade Activity")

if recent_trades:
    trades_df = pd.DataFrame(recent_trades)
    
    # Format for display (NO exit reasons shown - methodology protection)
    display_trades = trades_df[["portfolio_id", "ticker", "entry_date", "exit_date", "trade_return"]].copy()
    display_trades["trade_return"] = display_trades["trade_return"].apply(lambda x: f"{x*100:+.2f}%")
    
    display_trades = display_trades.rename(columns={
        "portfolio_id": "Portfolio",
        "ticker": "Ticker",
        "entry_date": "Entry",
        "exit_date": "Exit",
        "trade_return": "Return"
    })
    
    st.dataframe(display_trades, use_container_width=True, hide_index=True)
else:
    st.info("No recent trades to display.")

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# Section 5: Historical Performance (Sanitized)
# ─────────────────────────────────────────────────────────────
st.subheader("📈 Historical Performance")

if not nav_df.empty:
    # Calculate year-by-year returns
    nav_df["year"] = nav_df["date"].dt.year
    
    annual_returns = nav_df.groupby(["portfolio_id", "year"]).agg(
        start_nav=("portfolio_nav", "first"),
        end_nav=("portfolio_nav", "last"),
        start_bench=("benchmark_nav", "first"),
        end_bench=("benchmark_nav", "last")
    ).reset_index()
    
    annual_returns["port_return"] = (annual_returns["end_nav"] / annual_returns["start_nav"]) - 1
    annual_returns["bench_return"] = (annual_returns["end_bench"] / annual_returns["start_bench"]) - 1
    annual_returns["active_return"] = annual_returns["port_return"] - annual_returns["bench_return"]
    
    # Create heatmap
    heatmap_data = annual_returns.pivot(index="year", columns="portfolio_id", values="active_return")
    
    fig_heat = px.imshow(
        heatmap_data,
        text_auto=".1%",
        color_continuous_scale="RdYlGn",
        title="Active Return vs Benchmark by Year",
        labels=dict(x="Portfolio", y="Year", color="Active Return")
    )
    fig_heat.update_layout(height=400)
    st.plotly_chart(fig_heat, use_container_width=True)

# ─────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "Smart Momentum Portfolio | Institutional-grade active management | "
    "Data updated every 2 hours during market hours | "
    "Past performance does not guarantee future results."
)
