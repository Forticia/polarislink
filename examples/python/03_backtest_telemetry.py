#!/usr/bin/env python3
"""
Example: Logging Backtest Telemetry Run to Forticia Research Sink.
"""

import os
from polarislink import PolarisLinkClient

def main():
    api_key = os.environ.get("FORTICIA_API_KEY", "fca_demo_key")
    client = PolarisLinkClient(api_key=api_key)

    run_payload = {
        "strategy": "Sample_Macro_Strategy",
        "parameters": {
            "target_vol": 0.12,
            "lookback_days": 60,
            "rebalance_freq": "weekly"
        },
        "metrics": {
            "sharpe": 1.0,
            "cagr": 0.34,
            "max_drawdown": 0.082,
            "trades_count": 312
        },
        "provenance": {
            "commit_hash": "a1b2c3d4e5f6",
            "branch": "main",
            "engine": "Engine_v2.6"
        }
    }

    print("Registering backtest telemetry run...")
    try:
        resp = client.log_run(run_payload)
        print("Logged run response:", resp)
    except Exception as e:
        print("Note: In offline/demo mode:", e)

if __name__ == "__main__":
    main()
