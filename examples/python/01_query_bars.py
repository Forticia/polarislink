#!/usr/bin/env python3
"""
Example: Querying 25-Year Daily Bars from Forticia Market Data Vault.
"""

import os
from polarislink import PolarisLinkClient

def main():
    api_key = os.environ.get("FORTICIA_API_KEY", "fca_demo_key")
    client = PolarisLinkClient(api_key=api_key)

    print("Querying AAPL daily bars from 2020-01-01...")
    try:
        bars = client.get_bars("AAPL", universe="us_equities_daily", start="2020-01-01", limit=10)
        print(f"Retrieved {len(bars)} records:")
        for bar in bars[:5]:
            print(" ", bar)
    except Exception as e:
        print("Note: In offline/demo mode:", e)

if __name__ == "__main__":
    main()
