"""
Export sanitized data for the public Streamlit demo.
Strips all proprietary signal logic, exit reasons, and parameters.
"""
import pandas as pd
from pathlib import Path
import json

DATA_ROOT = Path("data")
OUTPUT_DIR = DATA_ROOT / "public_demo"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def export_public_data():
    print("🚀 Exporting sanitized public demo data...")

    # 1. Export NAV History (Portfolio vs Benchmark)
    print("  [1/4] Exporting NAV history...")
    nav_history = []
    for summary_file in (DATA_ROOT / "portfolio/summary/v1").glob("*.parquet"):
        df = pd.read_parquet(summary_file)
        port_id = summary_file.stem.replace("portfolio=", "")
        
        # Only keep date, NAV, and Benchmark return (Strip cash, positions_value, etc.)
        for _, row in df.iterrows():
            nav_history.append({
                "date": row["date"].strftime("%Y-%m-%d"),
                "portfolio_id": port_id,
                "portfolio_nav": row["nav"],
                "benchmark_nav": 1_000_000 * (1 + row["benchmark_cum_return"])
            })
            
    nav_df = pd.DataFrame(nav_history)
    nav_df.to_csv(OUTPUT_DIR / "nav_history.csv", index=False)

    # 2. Export Live Picks (Open Positions)
    print("  [2/4] Exporting live picks...")
    all_picks = []
    open_pos_dir = DATA_ROOT / "portfolio/open_positions"
    if open_pos_dir.exists():
        for pos_file in open_pos_dir.glob("*.parquet"):
            port_id = pos_file.stem.replace("portfolio=", "")
            df = pd.read_parquet(pos_file)
            if not df.empty:
                df["portfolio_id"] = port_id
                # Strip shares and internal tracking data
                df = df[["portfolio_id", "ticker", "entry_date", "entry_price", "current_price", "unrealized_pnl"]]
                df["entry_date"] = df["entry_date"].astype(str)
                all_picks.append(df)
                
    if all_picks:
        picks_df = pd.concat(all_picks, ignore_index=True)
        picks_df.to_json(OUTPUT_DIR / "live_picks.json", orient="records", indent=2)
    else:
        Path(OUTPUT_DIR / "live_picks.json").write_text("[]")

    # 3. Export Year-to-Date Performance Summary
    print("  [3/4] Exporting YTD performance summary...")
    ytd_summary = []
    for summary_file in (DATA_ROOT / "portfolio/summary/v1").glob("*.parquet"):
        df = pd.read_parquet(summary_file).sort_values("date")
        port_id = summary_file.stem.replace("portfolio=", "")
        
        if not df.empty:
            final_nav = df["nav"].iloc[-1]
            bench_cum_ret = df["benchmark_cum_return"].iloc[-1]
            port_cum_ret = (final_nav / 1_000_000) - 1
            
            ytd_summary.append({
                "portfolio_id": port_id,
                "benchmark_ticker": df["benchmark_ticker"].iloc[0],
                "portfolio_return": port_cum_ret,
                "benchmark_return": bench_cum_ret,
                "active_return": port_cum_ret - bench_cum_ret
            })
            
    ytd_df = pd.DataFrame(ytd_summary)
    ytd_df.to_json(OUTPUT_DIR / "ytd_performance.json", orient="records", indent=2)

    # 4. Export Recent Completed Trades (Last 30 days of activity, no exit reasons)
    print("  [4/4] Exporting recent trade activity...")
    recent_trades = []
    for trades_file in (DATA_ROOT / "portfolio/trades/v1").glob("*.parquet"):
        df = pd.read_parquet(trades_file)
        port_id = trades_file.stem.replace("portfolio=", "")
        if not df.empty:
            df["portfolio_id"] = port_id
            # STRICTLY REMOVE EXIT REASONS AND INTERNAL METRICS
            df = df[["portfolio_id", "ticker", "entry_date", "exit_date", "trade_return"]]
            df["entry_date"] = pd.to_datetime(df["entry_date"]).dt.strftime("%Y-%m-%d")
            df["exit_date"] = pd.to_datetime(df["exit_date"]).dt.strftime("%Y-%m-%d")
            recent_trades.append(df)
            
    if recent_trades:
        trades_df = pd.concat(recent_trades, ignore_index=True)
        # Only show the last 50 trades to the public
        trades_df = trades_df.sort_values("exit_date", ascending=False).head(50)
        trades_df.to_json(OUTPUT_DIR / "recent_trades.json", orient="records", indent=2)
    else:
        Path(OUTPUT_DIR / "recent_trades.json").write_text("[]")

    print(f"✅ Public demo data exported to {OUTPUT_DIR.absolute()}")
    print("   Files: nav_history.csv, live_picks.json, ytd_performance.json, recent_trades.json")

if __name__ == "__main__":
    export_public_data()