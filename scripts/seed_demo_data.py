"""Regenerate the bundled demo SQLite database and CSV samples.

Usage: python scripts/seed_demo_data.py [--root data]
The output is deterministic so the committed files can be rebuilt byte-for-byte
in content (SQLite page layout may differ between SQLite versions).
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path

COMPANIES = [
    # ticker, name, exchange, country, sector, currency, market_cap_billion
    ("AAPL", "Apple Inc.", "NASDAQ", "US", "Technology", "USD", 3400.0),
    ("MSFT", "Microsoft Corporation", "NASDAQ", "US", "Technology", "USD", 3100.0),
    ("NVDA", "NVIDIA Corporation", "NASDAQ", "US", "Semiconductors", "USD", 3300.0),
    ("AMZN", "Amazon.com, Inc.", "NASDAQ", "US", "Consumer", "USD", 1900.0),
    ("JPM", "JPMorgan Chase & Co.", "NYSE", "US", "Financials", "USD", 600.0),
    ("RELIANCE.NS", "Reliance Industries Limited", "NSE", "IN", "Energy", "INR", 19500.0),
    ("TCS.NS", "Tata Consultancy Services", "NSE", "IN", "Technology", "INR", 14000.0),
    ("INFY.NS", "Infosys Limited", "NSE", "IN", "Technology", "INR", 7600.0),
    ("HDFCBANK.NS", "HDFC Bank Limited", "NSE", "IN", "Financials", "INR", 13000.0),
    ("TATAMOTORS.NS", "Tata Motors Limited", "NSE", "IN", "Automobile", "INR", 2600.0),
]

# ticker, fiscal_year, revenue_billion, net_income_billion (illustrative demo values)
FINANCIALS = [
    ("AAPL", 2024, 391.0, 93.7),
    ("AAPL", 2025, 410.0, 101.0),
    ("MSFT", 2024, 245.1, 88.1),
    ("MSFT", 2025, 281.7, 101.8),
    ("NVDA", 2024, 60.9, 29.8),
    ("NVDA", 2025, 130.5, 72.9),
    ("AMZN", 2024, 638.0, 59.2),
    ("AMZN", 2025, 690.0, 70.0),
    ("JPM", 2024, 177.6, 58.5),
    ("JPM", 2025, 182.0, 57.0),
    ("RELIANCE.NS", 2024, 9010.0, 696.0),
    ("RELIANCE.NS", 2025, 9650.0, 700.0),
    ("TCS.NS", 2024, 2409.0, 459.0),
    ("TCS.NS", 2025, 2552.0, 485.0),
    ("INFY.NS", 2024, 1536.0, 262.0),
    ("INFY.NS", 2025, 1629.0, 267.0),
    ("HDFCBANK.NS", 2024, 2830.0, 608.0),
    ("HDFCBANK.NS", 2025, 3070.0, 673.0),
    ("TATAMOTORS.NS", 2024, 4380.0, 314.0),
    ("TATAMOTORS.NS", 2025, 4400.0, 280.0),
]

SALES_HEADER = ["order_id", "order_date", "region", "product", "units", "unit_price", "returned"]
REGIONS = ["North", "South", "East", "West"]
PRODUCTS = [("Laptop", 899.0), ("Monitor", 199.0), ("Keyboard", 49.5), ("Headset", 79.0)]

PRICES_HEADER = ["date", "ticker", "open", "high", "low", "close", "volume"]


def build_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE companies (
                ticker TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                exchange TEXT NOT NULL,
                country TEXT NOT NULL,
                sector TEXT NOT NULL,
                currency TEXT NOT NULL,
                market_cap_billion REAL NOT NULL
            );
            CREATE TABLE financials (
                ticker TEXT NOT NULL REFERENCES companies(ticker),
                fiscal_year INTEGER NOT NULL,
                revenue_billion REAL NOT NULL,
                net_income_billion REAL NOT NULL,
                PRIMARY KEY (ticker, fiscal_year)
            );
            """
        )
        connection.executemany("INSERT INTO companies VALUES (?, ?, ?, ?, ?, ?, ?)", COMPANIES)
        connection.executemany("INSERT INTO financials VALUES (?, ?, ?, ?)", FINANCIALS)
        connection.commit()
        connection.execute("VACUUM")
    finally:
        connection.close()


def build_sales_csv(path: Path) -> None:
    rows = []
    for index in range(1, 61):
        product, price = PRODUCTS[index % len(PRODUCTS)]
        rows.append(
            [
                f"ORD-{index:04d}",
                f"2026-{(index % 9) + 1:02d}-{(index % 27) + 1:02d}",
                REGIONS[index % len(REGIONS)],
                product,
                str((index * 7) % 15 + 1),
                f"{price:.2f}",
                "true" if index % 11 == 0 else "false",
            ]
        )
    rows[4][4] = ""  # one missing value so the analyzer shows missing_count
    _write_csv(path, SALES_HEADER, rows)


def build_prices_csv(path: Path) -> None:
    base = {"AAPL": 230.0, "RELIANCE.NS": 1250.0, "NVDA": 120.0}
    rows = []
    for day in range(1, 21):
        for ticker, start in base.items():
            close = round(start * (1 + 0.004 * ((day * 3) % 7 - 3)), 2)
            rows.append(
                [
                    f"2026-09-{day:02d}",
                    ticker,
                    f"{close * 0.995:.2f}",
                    f"{close * 1.01:.2f}",
                    f"{close * 0.985:.2f}",
                    f"{close:.2f}",
                    str(1_000_000 + day * 12_345),
                ]
            )
    _write_csv(path, PRICES_HEADER, rows)


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="data", type=Path)
    arguments = parser.parse_args()
    root: Path = arguments.root
    build_database(root / "demo.db")
    build_sales_csv(root / "csv" / "sample_sales.csv")
    build_prices_csv(root / "csv" / "sample_stock_prices.csv")
    print(f"Demo data written under {root.resolve()}")


if __name__ == "__main__":
    main()
