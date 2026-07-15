#!/usr/bin/env python3
"""
NR TIMES — Portfolio Data Fetcher
Fetches live prices, computes correlation matrix, outputs portfolio_data.json + market_data.json
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(REPO_ROOT, "data")
OUTPUT_DIR = DATA_DIR
CONFIG_FILE = os.path.join(DATA_DIR, "portfolio_config.json")

def main():
    print("📊 NR TIMES — Fetching portfolio data...")

    try:
        import yfinance as yf
        import numpy as np
    except ImportError:
        print("ERROR: Required packages not installed. Run: pip install yfinance numpy")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load config
    if not os.path.exists(CONFIG_FILE):
        print(f"ERROR: Config file not found: {CONFIG_FILE}")
        sys.exit(1)

    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

    # ── Fetch Holdings Data ─────────────────────────────────────────────────

    holdings_data = []
    tickers_for_corr = []
    price_history = {}

    print("\n📈 Fetching holding prices...")
    for holding in config.get("holdings", []):
        ticker_sym = holding["ticker"]
        try:
            tk = yf.Ticker(ticker_sym)
            hist = tk.history(period="6mo")
            if hist.empty:
                print(f"  ⚠ No data for {ticker_sym}")
                continue

            current_price = float(hist["Close"].iloc[-1])
            prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current_price
            day_change_pct = ((current_price - prev_close) / prev_close) * 100

            avg_cost = holding.get("avgCost", current_price)
            quantity = holding.get("quantity", 0)
            total_value = current_price * quantity
            total_cost = avg_cost * quantity
            pnl_pct = ((current_price - avg_cost) / avg_cost) * 100 if avg_cost > 0 else 0

            holdings_data.append({
                "ticker": ticker_sym,
                "name": holding.get("name", ticker_sym),
                "quantity": quantity,
                "avgCost": round(avg_cost, 2),
                "currentPrice": round(current_price, 2),
                "dayChange": round(day_change_pct, 2),
                "totalValue": round(total_value, 2),
                "totalCost": round(total_cost, 2),
                "pnl": round(total_value - total_cost, 2),
                "pnlPct": round(pnl_pct, 2),
            })

            # Store close prices for correlation
            tickers_for_corr.append(ticker_sym)
            price_history[ticker_sym] = hist["Close"].pct_change().dropna().values.tolist()

            print(f"  ✓ {holding['name']}: ₹{current_price:.2f} ({day_change_pct:+.2f}%)")

        except Exception as e:
            print(f"  ✗ Error fetching {ticker_sym}: {e}")

    # ── Compute Portfolio Weights ────────────────────────────────────────────

    total_portfolio_value = sum(h["totalValue"] for h in holdings_data)
    for h in holdings_data:
        h["weight"] = round((h["totalValue"] / total_portfolio_value) * 100, 2) if total_portfolio_value > 0 else 0

    # ── Compute Correlation Matrix ───────────────────────────────────────────

    print("\n📐 Computing correlation matrix...")
    corr_matrix = []
    corr_labels = []

    if len(tickers_for_corr) >= 2:
        # Align lengths
        min_len = min(len(price_history[t]) for t in tickers_for_corr)
        aligned = {}
        for t in tickers_for_corr:
            aligned[t] = price_history[t][-min_len:]

        # Build matrix
        returns_matrix = np.array([aligned[t] for t in tickers_for_corr])
        corr = np.corrcoef(returns_matrix)

        # Find names
        name_map = {}
        for h in config.get("holdings", []):
            name_map[h["ticker"]] = h.get("name", h["ticker"]).split(" ")[0]  # short name

        corr_labels = [name_map.get(t, t) for t in tickers_for_corr]
        corr_matrix = [[round(float(corr[i][j]), 3) for j in range(len(tickers_for_corr))]
                       for i in range(len(tickers_for_corr))]

        print(f"  ✓ {len(tickers_for_corr)}x{len(tickers_for_corr)} correlation matrix computed")

    # ── Fetch Sidebar Market Data ────────────────────────────────────────────

    print("\n📊 Fetching sidebar instruments...")
    sidebar_data = []
    for instr in config.get("sidebar_instruments", []):
        ticker_sym = instr["ticker"]
        try:
            tk = yf.Ticker(ticker_sym)
            hist = tk.history(period="5d")
            if hist.empty:
                continue
            current = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
            change_pct = ((current - prev) / prev) * 100

            sidebar_data.append({
                "name": instr.get("name", ticker_sym),
                "ticker": ticker_sym,
                "price": round(current, 2),
                "change": round(change_pct, 2),
            })
            print(f"  ✓ {instr['name']}: {current:.2f} ({change_pct:+.2f}%)")
        except Exception as e:
            print(f"  ✗ Error fetching {ticker_sym}: {e}")

    # ── Write Outputs ────────────────────────────────────────────────────────

    portfolio_output = {
        "lastUpdated": datetime.now(IST).isoformat(),
        "totalValue": round(total_portfolio_value, 2),
        "holdings": holdings_data,
        "correlationLabels": corr_labels,
        "correlationMatrix": corr_matrix,
    }

    market_output = {
        "lastUpdated": datetime.now(IST).isoformat(),
        "instruments": sidebar_data,
    }

    portfolio_file = os.path.join(OUTPUT_DIR, "portfolio_data.json")
    market_file = os.path.join(OUTPUT_DIR, "market_data.json")

    with open(portfolio_file, "w", encoding="utf-8") as f:
        json.dump(portfolio_output, f, ensure_ascii=False, indent=2)

    with open(market_file, "w", encoding="utf-8") as f:
        json.dump(market_output, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Portfolio data: {portfolio_file}")
    print(f"💾 Market data: {market_file}")
    print(json.dumps({"status": "ok", "holdings": len(holdings_data), "sidebar": len(sidebar_data)}))


if __name__ == "__main__":
    main()
