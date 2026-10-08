import streamlit as st
import pandas as pd
import json
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="Smart Momentum Demo", layout="wide", page_icon="📈")

# ─────────────────────────────────────────────────────────
# 1. LOAD DATA
# ─────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    try:
        nav = pd.read_csv("data/nav_history.csv")
        nav['date'] = pd.to_datetime(nav['date'])
    except FileNotFoundError:
        st.error("Data not available yet. The pipeline is currently running.")
        st.stop()
        
    with open("data/live_picks.json", "r") as f: 
        picks = json.load(f)
    with open("data/recent_trades.json", "r") as f: 
        trades = json.load(f)
        
    return nav, picks, trades

nav_df, live_picks, recent_trades = load_data()

# ─────────────────────────────────────────────────────────
# 2. FEATURE 1: DYNAMIC TIME WINDOW (T6M vs YTD)
# ─────────────────────────────────────────────────────────
max_date = nav_df['date'].max()

if max_date.month <= 6:
    start_date = max_date - relativedelta(months=6)
    window_label = "Trailing 6 Months"
else:
    start_date = pd.Timestamp(year=max_date.year, month=1, day=1)
    window_label = "Year-to-Date"

window_nav = nav_df[nav_df['date'] >= start_date].copy()

st.title(f"💼 Smart Momentum Portfolio ({window_label})")
st.caption(f"Data as of {max_date.strftime('%B %d, %Y')}")

portfolios = window_nav['portfolio_id'].unique()
cols = st.columns(len(portfolios))

for i, port_id in enumerate(portfolios):
    port_data = window_nav[window_nav['portfolio_id'] == port_id]
    if port_data.empty: continue
    
    port_start = port_data['portfolio_nav'].iloc[0]
    port_end = port_data['portfolio_nav'].iloc[-1]
    bench_start = port_data['benchmark_nav'].iloc[0]
    bench_end = port_data['benchmark_nav'].iloc[-1]
    
    port_ret = ((port_end / port_start) - 1) * 100
    bench_ret = ((bench_end / bench_start) - 1) * 100
    active_ret = port_ret - bench_ret
    
    with cols[i]:
        st.subheader(port_id.replace('_', ' ').title())
        st.metric("Portfolio Return", f"{port_ret:.2f}%", f"{active_ret:+.2f}% vs Bench")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=port_data['date'], y=port_data['portfolio_nav'], name='Portfolio', line=dict(color='#00A67E', width=3)))
        fig.add_trace(go.Scatter(x=port_data['date'], y=port_data['benchmark_nav'], name='Benchmark', line=dict(color='gray', width=2, dash='dash')))
        fig.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), showlegend=False, yaxis=dict(showticklabels=False))
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ─────────────────────────────────────────────────────────
# 3. FEATURE 2: INDIVIDUAL STOCK TRADE ATTRIBUTION CHART
# ─────────────────────────────────────────────────────────
st.header("🔍 Trade Attribution & Price Action")
st.write(f"Visualizing exact entry and exit points for trades executed within the **{window_label}** window.")

all_tickers = set([p['ticker'] for p in live_picks] + [t['ticker'] for t in recent_trades])

col1, col2 = st.columns(2)
with col1:
    selected_port = st.selectbox("Select Portfolio", portfolios)
with col2:
    selected_ticker = st.selectbox("Select Ticker", sorted(list(all_tickers)))

if selected_ticker:
    with st.spinner(f"Fetching price history for {selected_ticker}..."):
        fetch_start = start_date - relativedelta(months=1)
        ticker_obj = yf.Ticker(selected_ticker)
        hist = ticker_obj.history(start=fetch_start, end=max_date + pd.Timedelta(days=1))
        
        # FIX: Strip timezone info from yfinance data to match tz-naive dates from JSON
        hist.index = hist.index.tz_localize(None)
        
        if hist.empty:
            st.warning(f"Could not fetch price data for {selected_ticker}.")
        else:
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=hist.index, y=hist['Close'], mode='lines', name='Daily Close', 
                line=dict(color='#1f77b4', width=2)
            ))
            
            fig.add_vrect(x0=start_date, x1=max_date, fillcolor="green", opacity=0.05, line_width=0, annotation_text=f"   {window_label} Window", annotation_position="top left")

            def get_price_on_date(target_date, hist_df):
                if target_date in hist_df.index:
                    return hist_df.loc[target_date, 'Close']
                mask = hist_df.index <= target_date
                if mask.any():
                    return hist_df.loc[mask, 'Close'].iloc[-1]
                return None

            entries = [t for t in recent_trades if t['ticker'] == selected_ticker and pd.to_datetime(t['entry_date']) >= start_date]
            entries += [p for p in live_picks if p['ticker'] == selected_ticker and pd.to_datetime(p['entry_date']) >= start_date]
            
            entry_dates = []
            entry_prices = []
            for e in entries:
                ed = pd.to_datetime(e['entry_date'])
                price = get_price_on_date(ed, hist)
                if price is not None:
                    entry_dates.append(ed)
                    entry_prices.append(price)

            if entry_dates:
                fig.add_trace(go.Scatter(
                    x=entry_dates, y=entry_prices, mode='markers+text', name='Entry',
                    marker=dict(symbol='triangle-up', size=15, color='green', line=dict(width=2, color='black')),
                    text=[f"${p:.2f}" for p in entry_prices], textposition="top center", textfont=dict(color="green", size=12)
                ))

            exits = [t for t in recent_trades if t['ticker'] == selected_ticker and pd.to_datetime(t['exit_date']) >= start_date]
            
            exit_dates = []
            exit_prices = []
            for e in exits:
                ed = pd.to_datetime(e['exit_date'])
                price = get_price_on_date(ed, hist)
                if price is not None:
                    exit_dates.append(ed)
                    exit_prices.append(price)

            if exit_dates:
                fig.add_trace(go.Scatter(
                    x=exit_dates, y=exit_prices, mode='markers+text', name='Exit',
                    marker=dict(symbol='triangle-down', size=15, color='red', line=dict(width=2, color='black')),
                    text=[f"${p:.2f}" for p in exit_prices], textposition="bottom center", textfont=dict(color="red", size=12)
                ))

            opens = [p for p in live_picks if p['ticker'] == selected_ticker and pd.to_datetime(p['entry_date']) >= start_date]
            if opens:
                current_dates = []
                current_prices = []
                for p in opens:
                    price = get_price_on_date(max_date, hist)
                    if price is not None:
                        current_dates.append(max_date)
                        current_prices.append(price)
                
                if current_dates:
                    fig.add_trace(go.Scatter(
                        x=current_dates, y=current_prices, mode='markers+text', name='Current Price',
                        marker=dict(symbol='circle', size=12, color='blue', line=dict(width=2, color='black')),
                        text=[f"${p:.2f}" for p in current_prices], textposition="top right", textfont=dict(color="blue", size=12)
                    ))

            fig.update_layout(
                title=f"{selected_ticker} Price Action ({window_label})",
                xaxis_title="Date",
                yaxis_title="Price ($)",
                height=500,
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption("Data generated automatically by the Smart Momentum Core Pipeline.")
