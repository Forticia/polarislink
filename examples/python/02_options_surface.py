#!/usr/bin/env python3
"""
Example: querying an options surface dataset through a PolarisLink gateway.
"""

import os
from polarislink import PolarisLinkClient

def main():
    api_key = os.environ.get("FORTICIA_API_KEY", "fca_demo_key")
    client = PolarisLinkClient(api_key=api_key)

    print("Querying SPX 8D Options Microstructure Surface...")
    try:
        surface = client.get_options_surface("SPX", limit=20)
        contracts = surface.get("contracts", [])
        print(f"Retrieved {len(contracts)} contracts across strike/expiry slices.")
    except Exception as e:
        print("Note: In offline/demo mode:", e)

if __name__ == "__main__":
    main()
