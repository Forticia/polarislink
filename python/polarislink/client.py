#!/usr/bin/env python3
"""
Forticia PolarisLink™ — Official Institutional Client SDK (v2.6.1)
Zero-dependency institutional client for Forticia Research, 8D Options Surfaces, and Market Data Vault.

Usage:
    from forticia_sdk import ForticiaClient, PolarisLinkClient

    client = PolarisLinkClient(api_key="fca_live_...")
    
    # 1. Inspect Available Datasets
    universes = client.get_universes()
    print("Available universes:", [u["id"] for u in universes])

    # 2. Query 25-Year Daily Bars (returns pandas.DataFrame or list)
    df = client.get_bars("AAPL", universe="us_equities_daily", start="2020-01-01")
    print(df.tail())

    # 3. Stream Full Raw CSV File to Local Disk
    client.download_dataset("SPY", universe="us_equities_daily", output_file="./SPY.csv")

    # 4. Point-in-Time Federal Reserve Macro Indicators
    vix_df = client.get_macro_series("VIXCLS", start="2020-01-01")
    yield_spread = client.get_macro_series("T10Y2Y", start="2020-01-01")
"""

import io
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, List, Optional, Union

# Optional pandas support
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    pd = None
    HAS_PANDAS = False


RETAIL_PROHIBITED_PROVIDERS = {"yfinance", "yahoo", "alphavantage", "finnhub", "polygon_free"}

def enforce_institutional_guardrails(provider: Optional[str] = None):
    """
    Enforce Forticia Quantitative Governance Policy:
    Retail providers and unverified web-scraped feeds are strictly barred from quantitative modeling.
    """
    if provider and any(p in provider.lower() for p in RETAIL_PROHIBITED_PROVIDERS):
        raise RuntimeError(
            f"Forticia Quantitative Governance Violation: Retail provider '{provider}' is strictly prohibited. "
            "Institutional risk models and 8D options surface estimation mandate verified primary vault feeds."
        )


class ForticiaClient:
    """
    Official Python Client for Forticia PolarisLink™ Protocol (v2.6.1).
    Provides high-speed unthrottled access to 8D options surfaces, continuous tick archives,
    and the PolarisLink™ Agent Protocol.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize the Forticia API client.
        
        :param api_key: Forticia API Key (defaults to FORTICIA_API_KEY environment variable)
        :param base_url: Base URL (defaults to FORTICIA_API_URL env or https://forticia.uk)
        :param timeout: HTTP request timeout in seconds
        """
        self.api_key = api_key or os.environ.get("FORTICIA_API_KEY", "").strip()
        raw_base = base_url or os.environ.get("FORTICIA_API_URL", "https://forticia.uk")
        self.base_url = raw_base.rstrip("/")
        self.timeout = timeout

        # Configure resilient SSL context
        try:
            import certifi
            self._ssl_context = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            try:
                self._ssl_context = ssl.create_default_context()
            except Exception:
                self._ssl_context = ssl._create_unverified_context()

    def _request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        method: str = "GET",
        stream: bool = False,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        url = f"{self.base_url}{endpoint}"
        if params:
            query_str = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
            if query_str:
                url = f"{url}?{query_str}"

        payload_bytes = None
        if data is not None:
            payload_bytes = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=payload_bytes, method=method)
        req.add_header("User-Agent", "Forticia-PolarisLink-SDK/2.6.1 (Institutional)")
        req.add_header("Accept", "application/json, text/csv; q=0.9, text/event-stream; q=0.8")

        if headers:
            for hk, hv in headers.items():
                req.add_header(hk, hv)

        if payload_bytes is not None:
            req.add_header("Content-Type", "application/json")

        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")

        try:
            resp = urllib.request.urlopen(req, timeout=self.timeout, context=self._ssl_context)
            if stream:
                return resp
            raw_body = resp.read().decode("utf-8")
            return json.loads(raw_body)
        except urllib.error.HTTPError as err:
            try:
                error_body = json.loads(err.read().decode("utf-8"))
                msg = error_body.get("error", err.reason)
            except Exception:
                msg = str(err)
            raise RuntimeError(f"Forticia API Error [{err.code}]: {msg}") from err
        except urllib.error.URLError as err:
            raise ConnectionError(f"Failed to connect to Forticia API at {self.base_url}: {err.reason}") from err

    def _request_raw(self, endpoint: str, method: str = "GET"):
        """
        Issue an authenticated request and return the raw response object
        (binary-safe). Used for attachment downloads.
        """
        url = f"{self.base_url}{endpoint}"
        req = urllib.request.Request(url, method=method)
        req.add_header("User-Agent", "Forticia-PolarisLink-SDK/2.6.1 (Institutional)")
        req.add_header("Accept", "application/octet-stream, application/json")
        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")
        try:
            return urllib.request.urlopen(req, timeout=self.timeout, context=self._ssl_context)
        except urllib.error.HTTPError as err:
            try:
                error_body = json.loads(err.read().decode("utf-8"))
                msg = error_body.get("error", err.reason)
            except Exception:
                msg = str(err)
            raise RuntimeError(f"Forticia API Error [{err.code}]: {msg}") from err
        except urllib.error.URLError as err:
            raise ConnectionError(f"Failed to connect to Forticia API at {self.base_url}: {err.reason}") from err

    def _request_multipart(
        self,
        endpoint: str,
        files: Dict[str, Any],
        method: str = "POST",
    ) -> Any:
        """
        Issue an authenticated multipart/form-data request (file uploads).
        ``files`` maps field name -> (filename, bytes) or (filename, bytes, mime).
        """
        url = f"{self.base_url}{endpoint}"
        boundary = uuid.uuid4().hex
        body = io.BytesIO()
        for field_name, spec in files.items():
            filename, file_bytes = spec[0], spec[1]
            mime = spec[2] if len(spec) > 2 else "application/octet-stream"
            body.write(f"--{boundary}\r\n".encode("utf-8"))
            body.write(
                f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode("utf-8")
            )
            body.write(f"Content-Type: {mime}\r\n\r\n".encode("utf-8"))
            body.write(file_bytes)
            body.write(b"\r\n")
        body.write(f"--{boundary}--\r\n".encode("utf-8"))

        req = urllib.request.Request(url, data=body.getvalue(), method=method)
        req.add_header("User-Agent", "Forticia-PolarisLink-SDK/2.6.1 (Institutional)")
        req.add_header("Accept", "application/json")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")

        try:
            resp = urllib.request.urlopen(req, timeout=self.timeout, context=self._ssl_context)
            return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            try:
                error_body = json.loads(err.read().decode("utf-8"))
                msg = error_body.get("error", err.reason)
            except Exception:
                msg = str(err)
            raise RuntimeError(f"Forticia API Error [{err.code}]: {msg}") from err
        except urllib.error.URLError as err:
            raise ConnectionError(f"Failed to connect to Forticia API at {self.base_url}: {err.reason}") from err

    # =========================================================================
    # SYSTEM & HEALTH
    # =========================================================================

    def health(self) -> Dict[str, Any]:
        """Check system and vault connectivity."""
        return self._request("/api/v1/health")

    # =========================================================================
    # QUANT DOMAIN: DATASETS & BARS
    # =========================================================================

    def get_universes(self) -> List[Dict[str, Any]]:
        """List all available institutional datasets/universes in the vault."""
        res = self._request("/api/polarislink/quant/universes")
        return res.get("universes", [])

    def list_symbols(self, universe: str = "us_equities_daily") -> List[str]:
        """List all available symbol tickers in the specified universe."""
        res = self._request("/api/polarislink/quant/symbols", {"universe": universe})
        return res.get("symbols", [])

    def get_bars(
        self,
        symbol: str,
        universe: str = "us_equities_daily",
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 10000,
        offset: int = 0,
        as_dataframe: bool = True,
    ) -> Union[Any, List[Dict[str, Any]]]:
        """
        Query clean historical bars with 1-day and overnight return calculations.
        """
        res = self._request(
            "/api/polarislink/quant/bars",
            {
                "symbol": symbol,
                "universe": universe,
                "start": start,
                "end": end,
                "limit": limit,
                "offset": offset,
            },
        )
        bars = res.get("bars", [])

        if as_dataframe and HAS_PANDAS:
            df = pd.DataFrame(bars)
            if not df.empty and "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                df.set_index("date", inplace=True)
            return df
        return bars

    def download_dataset(
        self,
        symbol: str,
        universe: str = "us_equities_daily",
        output_file: Optional[str] = None,
    ) -> str:
        """
        Stream full raw CSV dataset directly to local file storage.
        """
        dest = output_file or f"./{symbol.upper()}_{universe}.csv"
        resp = self._request(
            "/api/polarislink/quant/download",
            {"symbol": symbol, "universe": universe},
            stream=True,
        )

        dest_dir = os.path.dirname(os.path.abspath(dest))
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)

        chunk_size = 64 * 1024
        total_bytes = 0
        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                total_bytes += len(chunk)

        return os.path.abspath(dest)

    # =========================================================================
    # MACRO DOMAIN: FEDERAL RESERVE ECONOMIC DATA
    # =========================================================================

    def get_macro_catalog(self) -> List[Dict[str, Any]]:
        """List all available Federal Reserve macroeconomic series with metadata."""
        res = self._request("/api/polarislink/quant/macro", {"series": "catalog"})
        return res.get("catalog", [])

    def get_macro_series(
        self,
        series: str = "VIXCLS",
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 10000,
        offset: int = 0,
        as_dataframe: bool = True,
    ) -> Union[Any, List[Dict[str, Any]]]:
        """
        Retrieve point-in-time observations for a Federal Reserve indicator.
        """
        res = self._request(
            "/api/polarislink/quant/macro",
            {
                "series": series,
                "start": start,
                "end": end,
                "limit": limit,
                "offset": offset,
            },
        )
        obs = res.get("observations", [])

        if as_dataframe and HAS_PANDAS:
            df = pd.DataFrame(obs)
            if not df.empty and "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                df.set_index("date", inplace=True)
                df.rename(columns={"value": series.upper()}, inplace=True)
            return df
        return obs

    # =========================================================================
    # QUANT DOMAIN: 8-DIMENSIONAL OPTIONS SURFACE & GREEKS
    # =========================================================================

    def get_options_surface(
        self,
        symbol: str = "SPX",
        as_dataframe: bool = True,
        source_provider: Optional[str] = None,
    ) -> Union[Any, Dict[str, Any]]:
        """
        Query 8-dimensional options strike surface (bid, ask, mid, spread bps, Greeks, volume, OI).
        Enforces institutional governance to block retail/scraped feeds.
        """
        enforce_institutional_guardrails(source_provider)

        res = self._request("/api/polarislink/quant/options/surface", {"symbol": symbol})
        surface_contracts = res.get("surface", [])

        if as_dataframe and HAS_PANDAS:
            flattened = []
            for c in surface_contracts:
                greeks = c.get("greeks", {}) or {}
                row = {
                    "contract": c.get("contract"),
                    "underlying": c.get("underlying"),
                    "expiration": c.get("expiration"),
                    "strike": c.get("strike"),
                    "right": c.get("right"),
                    "bid": c.get("bid"),
                    "ask": c.get("ask"),
                    "mid": c.get("mid"),
                    "spread": c.get("spread"),
                    "spread_bps": c.get("spreadBps"),
                    "volume": c.get("volume"),
                    "open_interest": c.get("openInterest"),
                    "iv": greeks.get("iv"),
                    "delta": greeks.get("delta"),
                    "gamma": greeks.get("gamma"),
                    "vega": greeks.get("vega"),
                    "theta": greeks.get("theta"),
                    "last_updated": c.get("lastUpdated"),
                }
                flattened.append(row)
            df = pd.DataFrame(flattened)
            return df

        return res

    def get_options_chain(self, symbol: str = "SPX") -> Dict[str, Any]:
        """
        Retrieve options chain contract matrix, expirations, and strikes catalog.
        """
        return self._request("/api/polarislink/quant/options/chain", {"symbol": symbol})

    def get_options_history(
        self,
        symbol: str = "SPX",
        contract: Optional[str] = None,
        expiration: Optional[str] = None,
        strike: Optional[float] = None,
        right: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 10000,
        offset: int = 0,
        as_dataframe: bool = True,
        source_provider: Optional[str] = None,
    ) -> Union[Any, Dict[str, Any]]:
        """
        Query historical options time-series and quote tape (bid, ask, mid, spread, Greeks, underlying spot).
        Enforces institutional governance to block retail/scraped feeds.
        """
        enforce_institutional_guardrails(source_provider)

        params: Dict[str, Any] = {
            "symbol": symbol,
            "contract": contract,
            "expiration": expiration,
            "strike": strike,
            "right": right,
            "start": start,
            "end": end,
            "limit": limit,
            "offset": offset,
        }

        res = self._request("/api/polarislink/quant/options/history", params)
        quotes = res.get("quotes", [])

        if as_dataframe and HAS_PANDAS:
            flattened = []
            for c in quotes:
                greeks = c.get("greeks", {}) or {}
                row = {
                    "contract": c.get("contract"),
                    "underlying": c.get("underlying"),
                    "expiration": c.get("expiration"),
                    "strike": c.get("strike"),
                    "right": c.get("right"),
                    "date": c.get("lastUpdated"),
                    "bid": c.get("bid"),
                    "ask": c.get("ask"),
                    "mid": c.get("mid"),
                    "spread": c.get("spread"),
                    "spread_bps": c.get("spreadBps"),
                    "volume": c.get("volume"),
                    "iv": greeks.get("iv"),
                    "delta": greeks.get("delta"),
                    "gamma": greeks.get("gamma"),
                    "vega": greeks.get("vega"),
                    "theta": greeks.get("theta"),
                    "spot_price": res.get("spotPrice"),
                    "data_quality": c.get("dataQuality"),
                }
                flattened.append(row)
            df = pd.DataFrame(flattened)
            return df

        return res

    # =========================================================================
    # QUANT DOMAIN: CME LEVEL 2 MARKET DEPTH & ORDER BOOK
    # =========================================================================

    def get_market_depth(
        self,
        symbol: str,
        date: Optional[str] = None,
        limit: int = 500,
        side: Optional[str] = None,
        as_dataframe: bool = False,
    ) -> Union[Any, Dict[str, Any]]:
        """
        Query CME Level 2 tick order book depth updates (ES, NQ, RTY, 6E, GC, CL).
        
        :param symbol: CME futures contract (e.g. 'ESU6', 'NQU6', 'CLV6')
        :param date: Date session string (e.g. '20260904' or '2026-09-04')
        :param limit: Maximum ticks to retrieve (default 500, max 10000)
        :param side: Optional filter for 'A' (Ask) or 'B' (Bid)
        :param as_dataframe: Convert tick updates to pandas DataFrame if True
        :return: Dict containing inside market summary (bestBid, bestAsk, spread) and tick array, or DataFrame
        """
        params = {"symbol": symbol, "limit": limit}
        if date:
            params["date"] = date
        if side:
            params["side"] = side

        res = self._request("/api/polarislink/quant/depth", params)
        if as_dataframe and HAS_PANDAS:
            ticks = res.get("ticks", [])
            df = pd.DataFrame(ticks)
            if not df.empty and "timestampIso" in df.columns:
                df["datetime"] = pd.to_datetime(df["timestampIso"])
                df.set_index("datetime", inplace=True)
            return df
        return res

    def get_buybacks(
        self,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        as_dataframe: bool = False,
    ) -> Union[Any, Dict[str, Any]]:
        """
        Query SEC Rule 10b-18 post-blackout corporate share repurchase schedules and empirical alpha metrics.
        
        :param symbol: Optional corporate ticker filter (e.g. 'AAPL', 'MSFT', 'JPM')
        :param status: Optional regime filter ('active_window', 'blackout_active', 'mid_cycle', 'scheduled')
        :param as_dataframe: Convert repurchase programs list to pandas DataFrame if True
        :return: Dict containing active repurchase catalog, blackout dates, safe harbor conditions, and alpha metrics
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        if status:
            params["status"] = status

        res = self._request("/api/polarislink/quant/buybacks", params)
        if as_dataframe and HAS_PANDAS:
            programs = res.get("programs", [])
            df = pd.DataFrame(programs)
            if not df.empty and "symbol" in df.columns:
                df.set_index("symbol", inplace=True)
            return df
        return res

    def stream_market_data(
        self,
        symbols: Union[str, List[str]] = "SPX,QQQ,AAPL,TSLA,NVDA",
        max_events: Optional[int] = None,
    ):
        """
        Generator yielding real-time market data ticks and cluster telemetry via Server-Sent Events (SSE).
        """
        if isinstance(symbols, list):
            symbols = ",".join(symbols)

        resp = self._request("/api/v1/stream", {"symbols": symbols}, stream=True)
        event_count = 0

        current_event = None
        for line_bytes in resp:
            line = line_bytes.decode("utf-8").strip()
            if not line:
                continue

            if line.startswith("event:"):
                current_event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                raw_data = line.split(":", 1)[1].strip()
                try:
                    data = json.loads(raw_data)
                except Exception:
                    data = raw_data

                yield {"event": current_event or "message", "data": data}
                event_count += 1
                if max_events and event_count >= max_events:
                    break

    # =========================================================================
    # POLARISLINK: AGENT-TO-AGENT PROTOCOL
    # =========================================================================

    def get_telemetry(self) -> Dict[str, Any]:
        """Query PolarisLink™ cluster telemetry, node capacity, and agent context."""
        return self._request("/api/polarislink/telemetry")

    def list_issues(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        workspace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List platform & quantitative research issues, optionally scoped to a workspace.

        :param workspace: a workspace id or 'all' (default: all)
        """
        res = self._request("/api/polarislink/issues", {"status": status, "category": category, "workspace": workspace})
        return res.get("issues", [])

    def get_issue(self, issue_id: int) -> Dict[str, Any]:
        """
        Fetch issue details including all discussion thread comments.
        
        :param issue_id: Ticket ID number (e.g. 2)
        :return: Issue dictionary with 'comments' list
        """
        res = self._request(f"/api/polarislink/issues/{issue_id}")
        return res.get("issue", {})

    def get_issue_comments(self, issue_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve all comments for a specific issue thread.
        
        :param issue_id: Ticket ID number (e.g. 2)
        :return: List of comment dictionaries
        """
        res = self._request(f"/api/polarislink/issues/{issue_id}/comments")
        return res.get("comments", [])

    def add_issue_comment(self, issue_id: int, comment: str) -> Dict[str, Any]:
        """
        Append a research or progress comment to an issue thread.
        
        :param issue_id: Ticket ID number (e.g. 2)
        :param comment: Comment text
        :return: Updated issue object
        """
        payload = {"comment": comment}
        return self._request(f"/api/polarislink/issues/{issue_id}/comments", data=payload, method="POST")

    def update_issue(
        self,
        issue_id: int,
        status: str,
        resolution_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update issue status and optionally append a resolution note.
        
        :param issue_id: Ticket ID number (e.g. 2)
        :param status: 'Open', 'In Progress', 'Resolved', or 'Closed'
        :param resolution_note: Optional technical explanation
        :return: Updated issue object
        """
        payload: Dict[str, Any] = {"status": status}
        if resolution_note:
            payload["resolutionNote"] = resolution_note
        return self._request(f"/api/polarislink/issues/{issue_id}", data=payload, method="PATCH")

    def report_issue(
        self,
        title: str,
        description: str,
        category: str = "General",
        priority: str = "Normal",
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
        author_role: Optional[str] = None,
        sender_type: Optional[str] = None,
        agent_persona: Optional[str] = None,
        workspace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Programmatically report an issue to Forticia Console via PolarisLink™.
        Automatically passes agent attribution headers and senderType metadata.

        :param workspace: Target workspace (a canonical workspace id). Workspace-scoped
            API keys are hard-bound to their workspace and ignore/override this field.
        """
        payload: Dict[str, Any] = {
            "title": title,
            "description": description,
            "category": category,
            "priority": priority,
        }
        if workspace:
            payload["workspace"] = workspace
        if user_name:
            payload["userName"] = user_name
        if user_email:
            payload["userEmail"] = user_email
        if author_role:
            payload["authorRole"] = author_role
        if sender_type:
            payload["senderType"] = sender_type
        if agent_persona:
            payload["agentPersona"] = agent_persona

        req_headers: Dict[str, str] = {}
        if agent_persona:
            req_headers["X-Polaris-Agent"] = agent_persona
        elif sender_type == "agent":
            req_headers["X-Polaris-Agent"] = "agent"

        return self._request(
            "/api/polarislink/issues",
            data=payload,
            method="POST",
            headers=req_headers if req_headers else None,
        )

    create_issue = report_issue

    def list_workspaces(self) -> List[Dict[str, Any]]:
        """
        List the canonical workspace registry for issue intake (e.g. 'research').
        """
        res = self._request("/api/polarislink/workspaces")
        return res.get("workspaces", [])

    def list_issue_attachments(self, issue_id: int) -> List[Dict[str, Any]]:
        """
        List attachments on an issue (filename, size, sha256, download URL).
        """
        res = self._request(f"/api/polarislink/issues/{issue_id}/attachments")
        return res.get("attachments", [])

    def upload_issue_attachment(self, issue_id: int, file_path: str) -> Dict[str, Any]:
        """
        Upload a local file (e.g. a corrected factsheet, PDF, or spreadsheet)
        as an attachment on an issue. Multipart/form-data transmission with
        a 25 MB ceiling and institutional MIME whitelist.

        :param file_path: Absolute or relative path to a local file
        :return: Attachment object with server-side download URL and sha256
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Attachment file not found: {file_path}")

        filename = os.path.basename(file_path)
        with open(file_path, "rb") as fh:
            file_bytes = fh.read()

        return self._request_multipart(
            f"/api/polarislink/issues/{issue_id}/attachments",
            files={"file": (filename, file_bytes)},
        )

    def download_issue_attachment(self, issue_id: int, attachment_id: str, output_path: str) -> str:
        """
        Download an issue attachment to a local path.

        :return: The output path written.
        """
        res = self._request_raw(f"/api/polarislink/issues/{issue_id}/attachments/{attachment_id}")
        with open(output_path, "wb") as fh:
            fh.write(res.read())
        return output_path

    def provision_workspace_key(
        self,
        workspace: str,
        name: Optional[str] = None,
        agent_name: Optional[str] = None,
        agent_email: Optional[str] = None,
        rate_limit_per_min: int = 600,
    ) -> Dict[str, Any]:
        """
        Provision a workspace-scoped API key (founder-privileged). The raw
        token is returned exactly once — store it securely immediately.

        :param workspace: Target workspace id (a canonical workspace id)
        :return: Dict with 'rawToken', 'key', and integration instructions
        """
        payload: Dict[str, Any] = {"rateLimitPerMin": rate_limit_per_min}
        if name:
            payload["name"] = name
        if agent_name:
            payload["agentName"] = agent_name
        if agent_email:
            payload["agentEmail"] = agent_email
        return self._request(f"/api/polarislink/workspaces/{workspace}/keys", data=payload, method="POST")

    def get_workspace_work(
        self,
        workspace: str = "default",
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List tasks and Kanban status stages for a workspace."""
        return self._request("/api/polarislink/work", {"workspace": workspace, "status": status})

    def create_workspace_task(
        self,
        title: str,
        workspace: str = "default",
        status: str = "Queued",
        owner: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new work item / task on the workspace Kanban board.
        """
        payload = {
            "title": title,
            "workspaceId": workspace,
            "status": status,
            "owner": owner,
        }
        return self._request("/api/polarislink/work/tasks", data=payload, method="POST")

    def update_workspace_task(self, task_id: str, status: str) -> Dict[str, Any]:
        """
        Move a task along the Kanban board ('Queued', 'In Progress', 'Verification', 'Complete').
        """
        payload = {"status": status}
        return self._request(f"/api/polarislink/work/tasks/{task_id}", data=payload, method="PATCH")

    # =========================================================================
    # WORKSPACE SHARED DRIVE & KANBAN TASKS API
    # =========================================================================

    def get_drive_files(self, workspace: str = "default") -> Dict[str, Any]:
        """
        List shared files and folders in a workspace drive.
        
        :param workspace: Workspace identifier (e.g. 'research')
        :return: Dict with folders, totalFiles, totalBytes, and files list
        """
        return self._request(f"/api/polarislink/workspaces/{workspace}/drive")

    def upload_drive_file(
        self,
        file_path_or_content: Union[str, bytes],
        file_name: str,
        workspace: str = "default",
        mime_type: str = "application/octet-stream",
    ) -> Dict[str, Any]:
        """
        Upload a file to the workspace shared drive.
        
        :param file_path_or_content: File path string or raw bytes
        :param file_name: Target file name (e.g. 'strategy_backtest_report.pdf')
        :param workspace: Workspace identifier
        :param mime_type: MIME type
        :return: Upload confirmation and file metadata
        """
        import base64
        if isinstance(file_path_or_content, str) and os.path.exists(file_path_or_content):
            with open(file_path_or_content, "rb") as f:
                content_bytes = f.read()
        elif isinstance(file_path_or_content, bytes):
            content_bytes = file_path_or_content
        else:
            content_bytes = str(file_path_or_content).encode("utf-8")

        b64_content = base64.b64encode(content_bytes).decode("ascii")
        payload = {
            "name": file_name,
            "content": b64_content,
            "encoding": "base64",
            "mimeType": mime_type,
        }
        return self._request(f"/api/polarislink/workspaces/{workspace}/drive/upload", data=payload, method="POST")

    def download_drive_file(self, file_id: str, output_path: str, workspace: str = "default") -> str:
        """
        Download a file from the workspace shared drive to local disk.
        
        :param file_id: Unique file identifier
        :param output_path: Local target file path
        :param workspace: Workspace identifier
        :return: Path to saved file
        """
        raw_stream = self._request(f"/api/polarislink/workspaces/{workspace}/drive/files/{file_id}", stream=True)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in raw_stream:
                f.write(chunk)
        return output_path

    def delete_drive_file(self, file_id: str, workspace: str = "default") -> Dict[str, Any]:
        """
        Delete a file from the workspace drive.
        """
        return self._request(f"/api/polarislink/workspaces/{workspace}/drive/files/{file_id}", method="DELETE")

    def get_tasks(self, workspace: str = "default", status: Optional[str] = None) -> Dict[str, Any]:
        """List tasks and Kanban status stages for a workspace."""
        params = {"workspace": workspace}
        if status:
            params["status"] = status
        return self._request(f"/api/polarislink/workspaces/{workspace}/tasks", params)

    def create_task(
        self,
        title: str,
        workspace: str = "default",
        status: str = "Queued",
        owner: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new Kanban task in the workspace."""
        payload = {
            "title": title,
            "workspaceId": workspace,
            "status": status,
            "owner": owner,
        }
        return self._request(f"/api/polarislink/workspaces/{workspace}/tasks", data=payload, method="POST")

    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        title: Optional[str] = None,
        owner: Optional[str] = None,
        workspace: str = "default",
    ) -> Dict[str, Any]:
        """Update a Kanban task status, title, or assignee."""
        payload: Dict[str, Any] = {}
        if status:
            payload["status"] = status
        if title:
            payload["title"] = title
        if owner:
            payload["owner"] = owner
        return self._request(f"/api/polarislink/workspaces/{workspace}/tasks/{task_id}", data=payload, method="PATCH")

    def delete_task(self, task_id: str, workspace: str = "default") -> Dict[str, Any]:
        """Delete a Kanban task from the workspace."""
        return self._request(f"/api/polarislink/workspaces/{workspace}/tasks/{task_id}", method="DELETE")

    # =========================================================================
    # ACTIVITY & TELEMETRY AUDIT LOGGING API
    # =========================================================================

    def get_activity(
        self,
        workspace: Optional[str] = None,
        actor: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Retrieve workspace or protocol-wide audit events and agent telemetry.
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if workspace:
            params["workspace"] = workspace
        if actor:
            params["actor"] = actor
        return self._request("/api/polarislink/activity", params)

    def log_activity(
        self,
        detail: str,
        action: str = "telemetry",
        workspace: str = "default",
        actor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Record an agent milestone or audit event to the Forticia protocol ledger.
        """
        payload = {
            "detail": detail,
            "action": action,
            "workspaceId": workspace,
            "actor": actor,
        }
        return self._request("/api/polarislink/activity", data=payload, method="POST")

    def get_knowledge(self) -> Dict[str, Any]:
        """Query PolarisLink™ canonical quantitative governance rules, datasets, and cluster topology."""
        return self._request("/api/polarislink/knowledge")

    def sync_governance(self) -> Dict[str, Any]:
        """
        Synchronize local environment against Forticia Institutional Governance Policies.
        Enforces zero bad data mandates and validates against retail scraper contamination.
        """
        knowledge = self.get_knowledge()
        prohibited = knowledge.get("governancePolicies", {}).get("retailDataProhibition", {}).get("prohibitedVendors", [])
        for p in prohibited:
            enforce_institutional_guardrails(p)
        return knowledge

    def get_spec(self, format: str = "json") -> Union[Dict[str, Any], str]:
        """
        Query PolarisLink™ live wire protocol specification and catalog.
        Args:
            format: "json" for structured schema/contract map, or "markdown" for raw document text.
        """
        params = {}
        if format in ("markdown", "md"):
            params["format"] = "markdown"
        return self._request("/api/spec", params=params)

    def get_changelog(self, format: str = "json") -> Union[Dict[str, Any], str]:
        """
        Query PolarisLink™ protocol release history and changelog.
        Args:
            format: "json" for structured releases list, or "markdown" for raw document text.
        """
        params = {}
        if format in ("markdown", "md"):
            params["format"] = "markdown"
        return self._request("/api/changelog", params=params)

    def get_reports(self, report_type: Optional[str] = None) -> Union[Dict[str, Any], str]:
        """
        Query institutional reports catalog or fetch specific transactional report (e.g. 'research-log').
        """
        params = {}
        if report_type:
            params["type"] = report_type
        return self._request("/api/polarislink/reports", params=params)

    def get_notifications(self) -> Dict[str, Any]:
        """Query caller notification preferences across system alerts, discoveries, and issues."""
        return self._request("/api/polarislink/notifications")

    def update_notifications(self, preferences: Dict[str, bool]) -> Dict[str, Any]:
        """Update caller notification preferences."""
        return self._request("/api/polarislink/notifications", data=preferences, method="PUT")

    # =========================================================================
    # QUANT DOMAIN & PORTFOLIO MANIFEST (v2.2.4 & v2.3.0)
    # =========================================================================

    def get_manifest(self, swarm_id: str = "default") -> Dict[str, Any]:
        """
        Query the authoritative active paper-trading portfolio manifest.
        Returns NAV, cash reserve, active sleeve count, and sleeve allocations.
        """
        params = {"swarm": swarm_id} if swarm_id else {}
        return self._request("/quant/manifest", params=params)

    def sync_manifest(
        self,
        manifest: Union[Dict[str, Any], List[Dict[str, Any]]],
        mode: str = "replace",
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Synchronize or replace active paper-trading sleeves in PostgreSQL.
        mode: 'replace' prunes non-present sleeves to maintain NAV invariant ($1.00M USD).
        """
        payload: Dict[str, Any] = {}
        if isinstance(manifest, list):
            payload = {"mode": mode, "active_paper_strategies": manifest}
        elif isinstance(manifest, dict):
            payload = dict(manifest)
            payload["mode"] = mode
        params = {"swarm": swarm_id} if swarm_id else {}
        return self._request("/quant/manifest/sync", params=params, data=payload, method="POST")

    def get_summary(self, swarm_id: str = "default") -> Dict[str, Any]:
        """
        Query institutional portfolio summary, vault metrics, and selection funnel statistics.
        """
        params = {"swarm": swarm_id} if swarm_id else {}
        return self._request("/quant/summary", params=params)

    def get_borrow_curves(self, symbol: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Query securities lending borrow rates, fees, and hard-to-borrow (HTB) indicators.
        """
        params = {"symbol": symbol} if symbol else {}
        return self._request("/quant/borrow", params=params)

    def replenish_frontier_waves(
        self,
        wave_id: Optional[str] = None,
        count: int = 50,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Replenish a wave of candidate research frontiers with Battle Scar pre-screening.
        """
        payload: Dict[str, Any] = {"minFrontiers": count, "preScreenAgainstScars": True}
        if wave_id:
            payload["waveName"] = wave_id
        return self._request(f"/api/polarislink/swarm/{swarm_id}/frontiers/replenish", data=payload, method="POST")

    def log_run(
        self,
        strategy_name: str,
        sharpe: Optional[float] = None,
        cagr: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        trades_count: int = 0,
        win_rate: Optional[float] = None,
        universe: str = "us_equities_daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        git_commit: str = "",
        provenance_hash: str = "",
        metrics: Optional[Dict[str, Any]] = None,
        workspace: str = "default",
    ) -> Dict[str, Any]:
        """
        Log quantitative backtest run telemetry to Forticia Console via PolarisLink™.
        """
        payload = {
            "strategyName": strategy_name,
            "workspaceId": workspace,
            "universe": universe,
            "startDate": start_date,
            "endDate": end_date,
            "sharpe": sharpe,
            "cagr": cagr,
            "maxDrawdown": max_drawdown,
            "tradesCount": trades_count,
            "winRate": win_rate,
            "gitCommit": git_commit,
            "provenanceHash": provenance_hash,
            "metrics": metrics or {},
        }
        return self._request("/api/polarislink/runs", data=payload, method="POST")

    def get_runs(
        self,
        workspace: str = "default",
        strategy: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List recorded backtest runs for an agent or workspace."""
        res = self._request("/api/polarislink/runs", {"workspace": workspace, "strategy": strategy, "limit": limit})
        return res.get("runs", [])

    def stream_polaris_events(self, max_events: Optional[int] = None):
        """
        Connect to PolarisLink™ real-time SSE stream for duplex agent coordination,
        task updates, issue auto-healing, and run telemetry.
        """
        resp = self._request("/api/polarislink/stream", stream=True)
        count = 0
        current_event = "message"

        try:
            for line_bytes in resp:
                line = line_bytes.decode("utf-8").strip()
                if not line:
                    continue
                if line.startswith("event:"):
                    current_event = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    raw_data = line.split(":", 1)[1].strip()
                    try:
                        parsed = json.loads(raw_data)
                    except Exception:
                        parsed = raw_data
                    yield {"event": current_event, "data": parsed}
                    count += 1
                    if max_events and count >= max_events:
                        break
        finally:
            resp.close()

    # =========================================================================
    # POLARISSWARM™: MULTI-CLUSTER QUANT RESEARCH SWARM CONTROL PLANE
    # =========================================================================

    def get_swarm_directory(self) -> Dict[str, Any]:
        """Query public directory of active PolarisSwarm™ research clusters."""
        return self._request("/api/polarislink/swarm")

    def get_swarm_status(self, swarm_id: str = "default") -> Dict[str, Any]:
        """Query status and registered research nodes for a swarm cluster."""
        return self._request(f"/api/polarislink/swarm/{swarm_id}/status")

    def get_swarm_frontiers(
        self,
        swarm_id: str = "default",
        domain: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query active research frontiers for a swarm cluster."""
        params = {"domain": domain} if domain else None
        res = self._request(f"/api/polarislink/swarm/{swarm_id}/frontiers", params=params)
        return res.get("frontiers", [])

    def replenish_frontier_wave(
        self,
        swarm_id: str = "default",
        wave_name: Optional[str] = None,
        domain_focus: Optional[List[str]] = None,
        target_universe: Optional[str] = None,
        min_frontiers: int = 50,
        pre_screen_against_scars: bool = True,
    ) -> Dict[str, Any]:
        """Synthesizes and replenishes a new wave of research frontiers (Issue #82)."""
        payload: Dict[str, Any] = {
            "minFrontiers": min_frontiers,
            "preScreenAgainstScars": pre_screen_against_scars,
        }
        if wave_name:
            payload["waveName"] = wave_name
        if domain_focus:
            payload["domainFocus"] = domain_focus
        if target_universe:
            payload["targetUniverse"] = target_universe
        return self._request(f"/api/polarislink/swarm/{swarm_id}/frontiers/replenish", data=payload, method="POST")

    def batch_register_frontiers(
        self,
        frontiers: List[Dict[str, Any]],
        swarm_id: str = "default",
        pre_screen_against_scars: bool = True,
    ) -> Dict[str, Any]:
        """Batch registers research frontiers with pre-screening against Battle Scars (Issue #82)."""
        payload = {
            "frontiers": frontiers,
            "preScreenAgainstScars": pre_screen_against_scars,
        }
        return self._request(f"/api/polarislink/swarm/{swarm_id}/frontiers/batch", data=payload, method="POST")

    def get_frontier_catalog_stats(
        self,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Retrieves catalog coverage, starvation metrics, and wave telemetry (Issue #82)."""
        return self._request(f"/api/polarislink/swarm/{swarm_id}/frontiers/catalog-stats")

    def list_frontier_waves(
        self,
        swarm_id: str = "default",
    ) -> List[Dict[str, Any]]:
        """Lists recorded replenishment waves for a cluster (Issue #82)."""
        res = self._request(f"/api/polarislink/swarm/{swarm_id}/waves")
        return res.get("waves", [])

    def claim_swarm_lease(
        self,
        node_id: str,
        frontier_id: str,
        ttl_seconds: int = 7200,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Atomically acquire a research lease for a frontier (mutual exclusion)."""
        payload = {
            "nodeId": node_id,
            "frontierId": frontier_id,
            "ttlSeconds": ttl_seconds,
        }
        return self._request(f"/api/polarislink/swarm/{swarm_id}/leases/claim", data=payload, method="POST")

    def release_swarm_lease(
        self,
        node_id: str,
        frontier_id: str,
        completed: bool = False,
        summary: Optional[str] = None,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Relinquish or mark completed an active research lease."""
        payload: Dict[str, Any] = {
            "nodeId": node_id,
            "frontierId": frontier_id,
            "completed": completed,
        }
        if summary:
            payload["summary"] = summary
        return self._request(f"/api/polarislink/swarm/{swarm_id}/leases/release", data=payload, method="POST")

    def send_swarm_heartbeat(
        self,
        node_id: str,
        swarm_id: str = "default",
        status: Optional[str] = None,
        workload_summary: Optional[str] = None,
        cpu_load: Optional[Union[str, int, float]] = None,
        active_hypothesis: Optional[str] = None,
        active_frontier: Optional[str] = None,
        current_progress: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a liveness heartbeat with active compute workload telemetry and auto-renew active leases."""
        payload: Dict[str, Any] = {"nodeId": node_id}
        if status:
            payload["status"] = status
        if workload_summary:
            payload["workloadSummary"] = workload_summary
        if cpu_load is not None:
            payload["cpuLoad"] = cpu_load
        if active_hypothesis:
            payload["activeHypothesis"] = active_hypothesis
        if active_frontier:
            payload["activeFrontier"] = active_frontier
        if current_progress:
            payload["currentProgress"] = current_progress
        return self._request(f"/api/polarislink/swarm/{swarm_id}/heartbeat", data=payload, method="POST")

    def broadcast_swarm_scar(
        self,
        scar_id: str,
        title: str,
        mechanism: str,
        root_cause: str,
        rule: str,
        source_node: Optional[str] = None,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Broadcast a newly codified Battle Scar (negative prior) across the swarm."""
        payload: Dict[str, Any] = {
            "scarId": scar_id,
            "title": title,
            "mechanism": mechanism,
            "rootCause": root_cause,
            "rule": rule,
        }
        if source_node:
            payload["sourceNode"] = source_node
        return self._request(f"/api/polarislink/swarm/{swarm_id}/scars", data=payload, method="POST")

    def get_swarm_assistance_requests(
        self,
        status: Optional[str] = None,
        for_node_id: Optional[str] = None,
        swarm_id: str = "default",
    ) -> List[Dict[str, Any]]:
        """Query pending PolarisSwarm™ assistance requests with dynamic relevance scoring."""
        params: Dict[str, str] = {}
        if status:
            params["status"] = status
        if for_node_id:
            params["forNodeId"] = for_node_id
        res = self._request(f"/api/polarislink/swarm/{swarm_id}/assistance/requests", params=params)
        return res.get("requests", [])

    def claim_swarm_assistance(
        self,
        request_id: str,
        assisting_node_id: str,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Claim an open assistance request to assist a stalled or disconnected peer node."""
        payload = {"assistingNodeId": assisting_node_id}
        return self._request(f"/api/polarislink/swarm/{swarm_id}/assistance/requests/{request_id}/claim", data=payload, method="POST")

    def reclaim_swarm_frontier(
        self,
        frontier_id: str,
        node_id: str,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Reclaim sovereign research lease when originator node reconnects."""
        payload = {"nodeId": node_id}
        return self._request(f"/api/polarislink/swarm/{swarm_id}/frontiers/{frontier_id}/reclaim", data=payload, method="POST")

    def reconcile_swarm_assistance(
        self,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Auto-reconcile completed frontiers and orphaned assistance requests across research manifests."""
        payload = {"swarmId": swarm_id}
        return self._request(f"/api/polarislink/swarm/{swarm_id}/assistance/reconcile", data=payload, method="POST")

    def get_swarm_sleeves(
        self,
        swarm_id: str = "default",
    ) -> List[Dict[str, Any]]:
        """Query surviving, parameter-locked alpha sleeves and capital allocations."""
        res = self._request(f"/api/polarislink/swarm/{swarm_id}/sleeves")
        return res.get("sleeves", [])

    def upsert_swarm_sleeve(
        self,
        sleeve: Dict[str, Any],
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Register or update a surviving alpha sleeve in cluster database."""
        return self._request(f"/api/polarislink/swarm/{swarm_id}/sleeves", data=sleeve, method="POST")

    def sync_swarm_manifest(
        self,
        manifest_payload: Dict[str, Any],
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Batch-synchronize full paper trading manifest into cluster database."""
        return self._request(f"/api/polarislink/swarm/{swarm_id}/manifest", data=manifest_payload, method="POST")

    def get_swarm_leases(
        self,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Query all active frontier and cross-audit leases in the swarm."""
        return self._request(f"/api/polarislink/swarm/{swarm_id}/leases")

    def list_swarm_discoveries(
        self,
        swarm_id: str = "default",
        status: Optional[str] = None,
        domain: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Query catalog of completed alpha research discoveries and replication states."""
        params: Dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        if domain:
            params["domain"] = domain
        return self._request(f"/api/polarislink/swarm/{swarm_id}/discoveries", params)

    def get_cross_audit_queue(
        self,
        swarm_id: str = "default",
        domain: Optional[str] = None,
        exclude_node_id: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Query discoveries awaiting independent peer replication with optional node exclusion."""
        params: Dict[str, Any] = {"limit": limit}
        if domain:
            params["domain"] = domain
        if exclude_node_id:
            params["excludeNodeId"] = exclude_node_id
        return self._request(f"/api/polarislink/swarm/{swarm_id}/cross-audit/queue", params)

    def get_audits_queue(
        self,
        swarm_id: str = "default",
        domain: Optional[str] = None,
        exclude_node_id: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Direct shortcut to query discoveries awaiting peer cross-audit (GET /api/polarislink/swarm/{swarmId}/audits)."""
        params: Dict[str, Any] = {"limit": limit}
        if domain:
            params["domain"] = domain
        if exclude_node_id:
            params["excludeNodeId"] = exclude_node_id
        return self._request(f"/api/polarislink/swarm/{swarm_id}/audits", params)

    def claim_cross_audit(
        self,
        frontier_id: str,
        auditor_node_id: str,
        auditor_researcher: Optional[str] = None,
        ttl_minutes: int = 60,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Acquire atomic mutual-exclusion lease for independent replication of an alpha discovery."""
        payload: Dict[str, Any] = {
            "frontierId": frontier_id,
            "auditorNodeId": auditor_node_id,
            "ttlMinutes": ttl_minutes,
        }
        if auditor_researcher:
            payload["auditorResearcher"] = auditor_researcher
        return self._request(f"/api/polarislink/swarm/{swarm_id}/cross-audit/claim", data=payload, method="POST")

    def submit_cross_audit_verdict(
        self,
        audit_id: str,
        frontier_id: str,
        auditor_node_id: str,
        verdict: str,
        replication_is_sharpe: Optional[float] = None,
        replication_oos_sharpe: Optional[float] = None,
        replication_trades: Optional[int] = None,
        replication_mae_bps: Optional[float] = None,
        notes: Optional[str] = None,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Submit independent replication verdict ('VERIFIED_REPLICATED' or 'CHALLENGED_FALSIFIED')."""
        payload: Dict[str, Any] = {
            "auditId": audit_id,
            "frontierId": frontier_id,
            "auditorNodeId": auditor_node_id,
            "verdict": verdict,
        }
        if replication_is_sharpe is not None:
            payload["replicationIsSharpe"] = replication_is_sharpe
        if replication_oos_sharpe is not None:
            payload["replicationOosSharpe"] = replication_oos_sharpe
        if replication_trades is not None:
            payload["replicationTrades"] = replication_trades
        if replication_mae_bps is not None:
            payload["replicationMaeBps"] = replication_mae_bps
        if notes is not None:
            payload["notes"] = notes
        return self._request(f"/api/polarislink/swarm/{swarm_id}/cross-audit/verdict", data=payload, method="POST")

    def get_swarm_capabilities(
        self,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Query authoritative cluster superpowers, active protocols, and autonomous agent directives."""
        return self._request(f"/api/polarislink/swarm/{swarm_id}/capabilities")

    def get_swarm_superpowers(
        self,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Convenience alias for get_swarm_capabilities."""
        return self.get_swarm_capabilities(swarm_id=swarm_id)

    def post_swarm_debate(
        self,
        title: str,
        body: str,
        message_type: str = "HYPOTHESIS_PROPOSAL",
        node_id: Optional[str] = None,
        author: Optional[str] = None,
        frontier_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        target_node_id: Optional[str] = None,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Post structured debate entry to Swarm Deliberation Plane (HYPOTHESIS, ADVERSARIAL_CRITIQUE, etc.)."""
        payload: Dict[str, Any] = {
            "title": title,
            "body": body,
            "messageType": message_type,
            "nodeId": node_id or "node-unspecified",
        }
        if author:
            payload["author"] = author
        if frontier_id:
            payload["frontierId"] = frontier_id
        if strategy_id:
            payload["strategyId"] = strategy_id
        if target_node_id:
            payload["targetNodeId"] = target_node_id
        return self._request(f"/api/polarislink/swarm/{swarm_id}/debates", data=payload, method="POST")

    def list_swarm_debates(
        self,
        frontier_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        limit: int = 50,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Query Swarm Deliberation Plane entries."""
        params: Dict[str, Any] = {"limit": limit}
        if frontier_id:
            params["frontierId"] = frontier_id
        if strategy_id:
            params["strategyId"] = strategy_id
        return self._request(f"/api/polarislink/swarm/{swarm_id}/debates", params)

    def post_patrol_notice(
        self,
        title: str,
        body: str,
        violation_type: str,
        severity: str = "WARN",
        target_node_id: Optional[str] = None,
        frontier_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        suggested_remedy: Optional[str] = None,
        author_node_id: str = "node-patrol",
        author_name: Optional[str] = None,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Broadcast structured methodology patrol notice across swarm cluster."""
        payload: Dict[str, Any] = {
            "title": title,
            "body": body,
            "violationType": violation_type,
            "severity": severity,
            "authorNodeId": author_node_id,
            "authorName": author_name or "Swarm Patrol Guard",
        }
        if target_node_id:
            payload["targetNodeId"] = target_node_id
        if frontier_id:
            payload["frontierId"] = frontier_id
        if strategy_id:
            payload["strategyId"] = strategy_id
        if suggested_remedy:
            payload["suggestedRemedy"] = suggested_remedy
        return self._request(f"/api/polarislink/swarm/{swarm_id}/patrol/notice", data=payload, method="POST")

    def list_patrol_notices(
        self,
        target_node_id: Optional[str] = None,
        unacknowledged_only: bool = False,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Query structured patrol notices from the cluster."""
        params: Dict[str, Any] = {}
        if target_node_id:
            params["nodeId"] = target_node_id
        if unacknowledged_only:
            params["unacknowledged"] = "true"
        return self._request(f"/api/polarislink/swarm/{swarm_id}/patrol/notices", params)

    def acknowledge_patrol_notice(
        self,
        notice_id: str,
        node_id: Optional[str] = None,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Acknowledge a patrol notice received by a node."""
        params: Dict[str, Any] = {}
        if node_id:
            params["nodeId"] = node_id
        return self._request(f"/api/polarislink/swarm/{swarm_id}/patrol/notices/{notice_id}/ack", params=params, method="POST")

    def record_strategy_disposition(
        self,
        strategy_id: str,
        strategy_name: str,
        disposition: str,
        node_id: str,
        metrics: Optional[Dict[str, Any]] = None,
        target_symbols: Optional[List[str]] = None,
        frontier_id: Optional[str] = None,
        holding_period_days: Optional[int] = None,
        microstructural_thesis: Optional[str] = None,
        falsification_rationale: Optional[str] = None,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Register research verdict (VALIDATED, FALSIFIED, CANDIDATE) for an evaluated strategy."""
        payload: Dict[str, Any] = {
            "strategyId": strategy_id,
            "strategyName": strategy_name,
            "disposition": disposition,
            "nodeId": node_id,
            "metrics": metrics or {},
            "targetSymbols": target_symbols or [],
        }
        if frontier_id:
            payload["frontierId"] = frontier_id
        if holding_period_days is not None:
            payload["holdingPeriodDays"] = holding_period_days
        if microstructural_thesis:
            payload["microstructuralThesis"] = microstructural_thesis
        if falsification_rationale:
            payload["falsificationRationale"] = falsification_rationale
        return self._request(f"/api/polarislink/swarm/{swarm_id}/dispositions", data=payload, method="POST")

    def list_strategy_dispositions(
        self,
        disposition: Optional[str] = None,
        frontier_id: Optional[str] = None,
        limit: int = 50,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """Query strategy dispositions from cluster research database."""
        params: Dict[str, Any] = {"limit": limit}
        if disposition:
            params["disposition"] = disposition
        if frontier_id:
            params["frontierId"] = frontier_id
        return self._request(f"/api/polarislink/swarm/{swarm_id}/dispositions", params)

    def stream_swarm_events(
        self,
        swarm_id: str = "default",
        max_events: Optional[int] = None,
    ):
        """Connect to the PolarisSwarm™ duplex SSE event stream."""
        resp = self._request(f"/api/polarislink/swarm/{swarm_id}/events", stream=True)
        count = 0
        current_event = "message"

        try:
            for line_bytes in resp:
                line = line_bytes.decode("utf-8").strip()
                if not line:
                    continue
                if line.startswith("event:"):
                    current_event = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    raw_data = line.split(":", 1)[1].strip()
                    try:
                        parsed = json.loads(raw_data)
                    except Exception:
                        parsed = raw_data
                    yield {"event": current_event, "data": parsed}
                    count += 1
                    if max_events and count >= max_events:
                        break
        finally:
            resp.close()

    def dispatch_compute_job(
        self,
        strategy_name: str,
        backtest_script: str,
        parameters: Optional[Dict[str, Any]] = None,
        cores_requested: int = 4,
        priority: int = 5,
        timeout_seconds: int = 3600,
        node_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatch an asynchronous backtest compute job to the compute server."""
        payload: Dict[str, Any] = {
            "strategyName": strategy_name,
            "backtestScript": backtest_script,
            "coresRequested": cores_requested,
            "priority": priority,
            "timeoutSeconds": timeout_seconds,
        }
        if parameters:
            payload["parameters"] = parameters
        if node_id:
            payload["nodeId"] = node_id
        return self._request("/api/polarislink/compute/dispatch", method="POST", json_body=payload)

    def get_compute_job(self, job_id: str) -> Dict[str, Any]:
        """Query status and outputs of a compute job."""
        return self._request(f"/api/polarislink/compute/jobs/{job_id}")

    def get_compute_capacity(self) -> Dict[str, Any]:
        """Query real-time cluster compute capacity and worker pool status."""
        return self._request("/api/polarislink/compute/capacity")

    def cancel_compute_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a queued or running compute job."""
        return self._request(f"/api/polarislink/compute/jobs/{job_id}", method="DELETE")

    def export_research_log(self, swarm_id: str = "default", format: str = "markdown") -> str:
        """Export the authoritative research ledger (Evaluations, Tombstones, Scars) as markdown."""
        resp = self._request(f"/api/polarislink/swarm/export/research-log?swarmId={swarm_id}&format={format}")
        if isinstance(resp, dict) and "markdown" in resp:
            return resp["markdown"]
        return str(resp)

    # =========================================================================
    # INSTITUTIONAL ALPHA DESK & THE DARK ENGINE (v2.0 Subsystems)
    # =========================================================================

    def submit_execution_intent(
        self,
        pod_id: str,
        strategy_id: str,
        targets: List[Dict[str, Any]],
        urgency: str = "BALANCED_TWAP",
        rebalance_horizon_sec: int = 14400,
        alpha_decay_halflife_sec: int = 7200,
    ) -> Dict[str, Any]:
        """
        Submit continuous target portfolio state vector to the Dark Engine internal crossing matcher.
        Applies pre-trade ADV participation clamping (1.5% ceiling).
        """
        payload = {
            "podId": pod_id,
            "strategyId": strategy_id,
            "timestampNs": 1725900000000000000,
            "sequenceNumber": 1,
            "urgency": urgency,
            "rebalanceHorizonSec": rebalance_horizon_sec,
            "alphaDecayHalfLifeSec": alpha_decay_halflife_sec,
            "targets": targets,
        }
        return self._request("/api/polarislink/execution/intents", method="POST", data=payload)

    def get_crossing_book(self) -> Dict[str, Any]:
        """Query active intents in the internal Dark Engine crossing book."""
        return self._request("/api/polarislink/execution/crossing")

    def get_fills(
        self,
        strategy_id: Optional[str] = None,
        symbol: Optional[str] = None,
        venue: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Query execution fills with crossing savings and venue attribution."""
        params: Dict[str, Any] = {"limit": limit}
        if strategy_id:
            params["strategyId"] = strategy_id
        if symbol:
            params["symbol"] = symbol
        if venue:
            params["venue"] = venue
        return self._request("/api/polarislink/execution/fills", params=params)

    def get_tca(self, fill_id: str) -> Dict[str, Any]:
        """Query post-trade Transaction Cost Analysis (TCA) shortfall decomposition and markouts."""
        return self._request(f"/api/polarislink/execution/tca/{fill_id}")

    def get_locates(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Query Real-Time Locate Inventory Cache (LIC) for short locate availability."""
        params = {"symbol": symbol} if symbol else None
        return self._request("/api/polarislink/risk/locates", params=params)

    def get_risk_limits(self) -> Dict[str, Any]:
        """Query institutional pre-trade risk limits, leverage caps, and ADV participation ceiling."""
        return self._request("/api/polarislink/risk/limits")

    def get_features_catalog(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """List centralized feature catalog items in the shared bitemporal lakehouse."""
        params = {"category": domain} if domain else None
        return self._request("/api/polarislink/features/catalog", params=params)

    def get_feature_series(
        self,
        feature_id: str,
        symbol: str = "SPY",
        as_of_knowledge_epoch: Optional[int] = None,
        limit: int = 1000,
    ) -> Dict[str, Any]:
        """Query bitemporal point-in-time feature time series strictly bounded by knowledge timestamp."""
        params: Dict[str, Any] = {"featureId": feature_id, "symbol": symbol, "limit": limit}
        if as_of_knowledge_epoch is not None:
            params["asOfKnowledgeEpoch"] = as_of_knowledge_epoch
        return self._request("/api/polarislink/features/series", params=params)

    def register_feature(
        self,
        feature_id: str,
        name: str,
        domain: str,
        description: str,
        formula: str,
        parameters: Optional[Dict[str, Any]] = None,
        update_frequency: str = "1m",
    ) -> Dict[str, Any]:
        """Register a new derived quantitative feature in the shared bitemporal lakehouse."""
        payload = {
            "featureId": feature_id,
            "name": name,
            "domain": domain,
            "description": description,
            "formula": formula,
            "parameters": parameters or {},
            "updateFrequency": update_frequency,
        }
        return self._request("/api/polarislink/features/register", method="POST", data=payload)

    def orthogonalize_alpha(
        self,
        challenger_id: str,
        challenger_vector: List[float],
        incumbent_id: str,
        incumbent_vector: List[float],
        benchmark_returns: Optional[List[float]] = None,
        threshold_ir: float = 1.0,
        swarm_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Execute Gram-Schmidt orthogonalization duel on candidate alpha vector against incumbent.
        Returns residual Information Ratio, factor loadings, and mathematical redundancy disposition.
        """
        payload: Dict[str, Any] = {
            "challengerStrategyId": challenger_id,
            "challengerVector": challenger_vector,
            "incumbentStrategyId": incumbent_id,
            "incumbentVector": incumbent_vector,
            "thresholdIr": threshold_ir,
        }
        if benchmark_returns:
            payload["benchmarkReturns"] = benchmark_returns
        return self._request(f"/api/polarislink/swarm/{swarm_id}/orthogonalize", method="POST", data=payload)

    def get_impact_surface(self, universe: Optional[str] = None) -> Dict[str, Any]:
        """Query calibrated square-root market impact surfaces I(Q) = Y * sigma * sqrt(Q / ADV)."""
        params = {"universe": universe} if universe else None
        return self._request("/api/polarislink/quant/impact-surface", params=params)

    def get_macro_events(
        self,
        event_name: Optional[str] = None,
        category: Optional[str] = None,
        from_timestamp: Optional[int] = None,
        to_timestamp: Optional[int] = None,
        as_of_knowledge: Optional[int] = None,
        limit: int = 500,
    ) -> Dict[str, Any]:
        """Query point-in-time macro event calendar with standardized surprise vectors."""
        params: Dict[str, Any] = {"limit": limit}
        if event_name:
            params["eventName"] = event_name
        if category:
            params["category"] = category
        if from_timestamp is not None:
            params["fromTimestamp"] = from_timestamp
        if to_timestamp is not None:
            params["toTimestamp"] = to_timestamp
        if as_of_knowledge is not None:
            params["asOfKnowledge"] = as_of_knowledge
        return self._request("/api/polarislink/quant/macro/events", params=params)

    def get_cftc_positioning(
        self,
        contract_code: Optional[str] = None,
        from_timestamp: Optional[int] = None,
        to_timestamp: Optional[int] = None,
        as_of_knowledge: Optional[int] = None,
        limit: int = 500,
    ) -> Dict[str, Any]:
        """Query CFTC Commitments of Traders (COT) disaggregated positioning reports."""
        params: Dict[str, Any] = {"limit": limit}
        if contract_code:
            params["contract"] = contract_code
        if from_timestamp is not None:
            params["fromTimestamp"] = from_timestamp
        if to_timestamp is not None:
            params["toTimestamp"] = to_timestamp
        if as_of_knowledge is not None:
            params["asOfKnowledge"] = as_of_knowledge
        return self._request("/api/polarislink/quant/positioning/cot", params=params)

    def get_options_gex(
        self,
        symbol: str = "SPX",
        as_of_date: Optional[str] = None,
        as_of_knowledge: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Query options dealer Gamma Exposure (GEX) surface and zero-gamma flip points."""
        params: Dict[str, Any] = {"symbol": symbol}
        if as_of_date:
            params["asOfDate"] = as_of_date
        if as_of_knowledge is not None:
            params["asOfKnowledge"] = as_of_knowledge
        return self._request("/api/polarislink/quant/options/gex", params=params)

    def resolve_symbology(
        self,
        ticker: Optional[str] = None,
        canonical_id: Optional[str] = None,
        figi: Optional[str] = None,
        cusip: Optional[str] = None,
        globex_symbol: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resolve instrument across cash equities, options OSI, futures Globex, and rates."""
        params: Dict[str, Any] = {}
        if canonical_id:
            params["canonicalId"] = canonical_id
        if ticker:
            params["ticker"] = ticker
        if figi:
            params["figi"] = figi
        if cusip:
            params["cusip"] = cusip
        if globex_symbol:
            params["globexSymbol"] = globex_symbol
        return self._request("/api/polarislink/quant/symbology/resolve", params=params)

    def get_continuous_futures(
        self,
        contract_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query continuous futures roll rules, active/next contracts, and basis spreads."""
        params = {"root": contract_root} if contract_root else None
        return self._request("/api/polarislink/quant/futures/continuous", params=params)

    def get_discrete_futures_contracts(
        self,
        symbols: Optional[str] = None,
        tenor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query official discrete futures contract specifications (conId, multiplier, tick, FND, delivery regime)."""
        params: Dict[str, Any] = {}
        if symbols:
            params["contracts"] = symbols
        if tenor:
            params["tenor"] = tenor
        return self._request("/api/polarislink/futures/contracts", params=params or None)

    def get_futures_bars(
        self,
        symbol: Optional[str] = None,
        tenor: Optional[str] = None,
        universe: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
        format: str = "json",
    ) -> Dict[str, Any]:
        """Query discrete and continuous futures OHLCV and settlement bars."""
        params: Dict[str, Any] = {"limit": limit, "offset": offset, "format": format}
        if symbol:
            params["symbol"] = symbol
        if tenor:
            params["tenor"] = tenor
        if universe:
            params["universe"] = universe
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        return self._request("/api/polarislink/quant/futures/bars", params=params)

    def get_borrow_fee_curves(
        self,
        symbol: Optional[str] = None,
        as_of_date: Optional[str] = None,
        limit: int = 500,
    ) -> Dict[str, Any]:
        """Query securities lending borrow fee rates (bps) and utilization percentages."""
        params: Dict[str, Any] = {"limit": limit}
        if symbol:
            params["symbol"] = symbol
        if as_of_date:
            params["asOfDate"] = as_of_date
        return self._request("/api/polarislink/quant/borrow-curves", params=params)



# Canonical PolarisLink™ Institutional Aliases
PolarisLinkClient = ForticiaClient
PolarisLink = ForticiaClient

__all__ = ["ForticiaClient", "PolarisLinkClient", "PolarisLink", "enforce_institutional_guardrails"]


def _cli_main():
    import argparse

    parser = argparse.ArgumentParser(description="Forticia Research Vault & PolarisLink™ CLI")
    parser.add_argument("--key", default=None, help="Forticia API Key")
    parser.add_argument("--url", default=None, help="Base API URL")
    
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("health", help="Check API & vault status")
    subparsers.add_parser("universes", help="List all datasets in vault")

    sym_parser = subparsers.add_parser("symbols", help="List symbols in universe")
    sym_parser.add_argument("--universe", default="us_equities_daily", help="Dataset identifier")

    bars_parser = subparsers.add_parser("bars", help="Query bars for symbol")
    bars_parser.add_argument("symbol", help="Ticker symbol (e.g. AAPL)")
    bars_parser.add_argument("--universe", default="us_equities_daily", help="Dataset identifier")
    bars_parser.add_argument("--start", default=None, help="Start date YYYY-MM-DD")
    bars_parser.add_argument("--limit", type=int, default=5, help="Number of bars to print")

    opt_parser = subparsers.add_parser("options", help="Query 8D options strike surface")
    opt_parser.add_argument("symbol", nargs="?", default="SPX", help="Ticker symbol (e.g. SPX, QQQ)")
    opt_parser.add_argument("--chain", action="store_true", help="Print chain catalog instead of surface")
    opt_parser.add_argument("--limit", type=int, default=5, help="Number of surface contracts to print")

    dl_parser = subparsers.add_parser("download", help="Download raw CSV dataset")
    dl_parser.add_argument("symbol", help="Ticker symbol")
    dl_parser.add_argument("--universe", default="us_equities_daily")
    dl_parser.add_argument("--out", default=None, help="Output file path")

    stream_parser = subparsers.add_parser("stream", help="Stream real-time SSE market ticks")
    stream_parser.add_argument("--symbols", default="SPX,QQQ", help="Comma-separated tickers")
    stream_parser.add_argument("--count", type=int, default=5, help="Max events to stream")

    macro_parser = subparsers.add_parser("macro", help="Query a macro indicator series")
    macro_parser.add_argument("series", nargs="?", default="VIXCLS", help="Macro indicator (e.g. VIXCLS, T10Y2Y)")
    macro_parser.add_argument("--catalog", action="store_true", help="Show all series catalog")

    polaris_parser = subparsers.add_parser("polaris", help="PolarisLink™ Agent Operations")
    polaris_sub = polaris_parser.add_subparsers(dest="polaris_cmd")
    polaris_sub.add_parser("telemetry", help="Query cluster telemetry")
    polaris_sub.add_parser("knowledge", help="Query quantitative governance rules and datasets")
    polaris_sub.add_parser("runs", help="List recorded backtest runs")
    p_logrun = polaris_sub.add_parser("log-run", help="Log backtest run telemetry")
    p_logrun.add_argument("strategy", help="Strategy name")
    p_logrun.add_argument("--sharpe", type=float, default=None, help="Sharpe ratio")
    p_logrun.add_argument("--cagr", type=float, default=None, help="CAGR (e.g. 0.35)")
    p_logrun.add_argument("--drawdown", type=float, default=None, help="Max Drawdown (e.g. 0.08)")
    p_logrun.add_argument("--trades", type=int, default=0, help="Trades count")
    p_logrun.add_argument("--universe", default="us_equities_daily", help="Dataset universe")
    polaris_sub.add_parser("stream", help="Stream real-time agent events and telemetry")
    polaris_sub.add_parser("work", help="List Kanban tasks")
    p_task = polaris_sub.add_parser("add-task", help="Add Kanban task")
    p_task.add_argument("title", help="Task title")
    p_task.add_argument("--status", default="Queued", help="Task status")
    p_issues = polaris_sub.add_parser("issues", help="List reported issues")
    p_issues.add_argument("--status", default=None, help="Filter by status")
    p_issues.add_argument("--category", default=None, help="Filter by category")

    p_get_issue = polaris_sub.add_parser("get-issue", help="Get issue details and comments")
    p_get_issue.add_argument("id", type=int, help="Issue ID")

    p_issue = polaris_sub.add_parser("report-issue", help="Report issue")
    p_issue.add_argument("title", help="Issue title")
    p_issue.add_argument("description", help="Issue description")
    p_issue.add_argument("--category", default="General", help="Category")
    p_issue.add_argument("--priority", default="Normal", help="Priority")

    p_comment = polaris_sub.add_parser("comment-issue", help="Add comment to issue")
    p_comment.add_argument("id", type=int, help="Issue ID")
    p_comment.add_argument("comment", help="Comment text")

    p_update_issue = polaris_sub.add_parser("update-issue", help="Update issue status")
    p_update_issue.add_argument("id", type=int, help="Issue ID")
    p_update_issue.add_argument("--status", required=True, help="Status (Open, In Progress, Resolved, Closed)")
    p_update_issue.add_argument("--note", default=None, help="Resolution note")

    swarm_parser = subparsers.add_parser("swarm", help="PolarisSwarm™ Research Swarm Control Plane")
    swarm_parser.add_argument("--swarm-id", default="default", help="Swarm cluster ID (default: default)")
    swarm_sub = swarm_parser.add_subparsers(dest="swarm_cmd")
    swarm_sub.add_parser("directory", help="List active swarm clusters")
    swarm_sub.add_parser("status", help="Query cluster status and node registry")
    sw_stats = swarm_sub.add_parser("catalog-stats", help="Get swarm catalog stats & starvation index")
    sw_replenish = swarm_sub.add_parser("replenish", help="Replenish new wave of frontiers")
    sw_replenish.add_argument("--wave-name", default=None, help="Name of wave")
    sw_replenish.add_argument("--min-frontiers", type=int, default=50, help="Min frontiers to replenish")
    sw_frontiers = swarm_sub.add_parser("frontiers", help="List research frontiers")
    sw_frontiers.add_argument("--domain", default=None, help="Filter domain")
    sw_claim = swarm_sub.add_parser("claim", help="Claim a research frontier lease")
    sw_claim.add_argument("node_id", help="Researcher Node ID")
    sw_claim.add_argument("frontier_id", help="Frontier ID to claim")
    sw_claim.add_argument("--ttl", type=int, default=7200, help="Lease TTL seconds (default: 7200)")
    sw_release = swarm_sub.add_parser("release", help="Release a research lease")
    sw_release.add_argument("node_id", help="Researcher Node ID")
    sw_release.add_argument("frontier_id", help="Frontier ID to release")
    sw_release.add_argument("--completed", action="store_true", help="Mark milestone completed")
    sw_release.add_argument("--summary", default=None, help="Summary notes")
    sw_hb = swarm_sub.add_parser("heartbeat", help="Send node heartbeat")
    sw_hb.add_argument("node_id", help="Researcher Node ID")
    sw_scar = swarm_sub.add_parser("broadcast-scar", help="Broadcast a codified battle scar")
    sw_scar.add_argument("scar_id", help="Scar ID (e.g. SCAR-158)")
    sw_scar.add_argument("title", help="Scar title")
    sw_scar.add_argument("mechanism", help="Mechanical failure description")
    sw_scar.add_argument("root_cause", help="Underlying market microstructure root cause")
    sw_scar.add_argument("rule", help="Mandatory guardrail rule")
    sw_scar.add_argument("--node-id", default=None, help="Source node ID")
    swarm_sub.add_parser("stream", help="Stream real-time swarm events (SSE)")

    args = parser.parse_args()
    client = ForticiaClient(api_key=args.key, base_url=args.url)

    if args.command == "health":
        print(json.dumps(client.health(), indent=2))
    elif args.command == "universes":
        u = client.get_universes()
        for item in u:
            print(f"- [{item['id']}] {item['name']} ({item['symbolCount']} symbols)")
    elif args.command == "symbols":
        symbols = client.list_symbols(args.universe)
        print(f"Symbols in {args.universe} ({len(symbols)} total):")
        print(", ".join(symbols[:50]) + ("..." if len(symbols) > 50 else ""))
    elif args.command == "bars":
        bars = client.get_bars(args.symbol, universe=args.universe, start=args.start, limit=args.limit, as_dataframe=False)
        print(json.dumps(bars, indent=2))
    elif args.command == "options":
        if args.chain:
            chain = client.get_options_chain(args.symbol)
            print(json.dumps(chain, indent=2))
        else:
            surface = client.get_options_surface(args.symbol, as_dataframe=False)
            contracts = surface.get("surface", [])[:args.limit]
            print(f"Options Surface for {args.symbol} (Spot: ${surface.get('spotPrice')}, Total: {surface.get('contractsCount')}):")
            print(json.dumps(contracts, indent=2))
    elif args.command == "stream":
        print(f"Connecting to Forticia SSE stream for {args.symbols}...")
        for evt in client.stream_market_data(symbols=args.symbols, max_events=args.count):
            print(f"[{evt['event']}] {json.dumps(evt['data'])}")
    elif args.command == "download":
        path = client.download_dataset(args.symbol, universe=args.universe, output_file=args.out)
        print(f"Downloaded {args.symbol} to: {path}")
    elif args.command == "macro":
        if args.catalog:
            cat = client.get_macro_catalog()
            for c in cat:
                print(f"- {c['id']}: {c['name']} (Latest: {c['latestValue']} on {c['latestDate']})")
        else:
            obs = client.get_macro_series(args.series, limit=10, as_dataframe=False)
            print(f"Latest observations for {args.series}:")
            print(json.dumps(obs[:10], indent=2))
    elif args.command == "polaris":
        if args.polaris_cmd == "telemetry":
            print(json.dumps(client.get_telemetry(), indent=2))
        elif args.polaris_cmd == "knowledge":
            print(json.dumps(client.get_knowledge(), indent=2))
        elif args.polaris_cmd == "runs":
            runs = client.get_runs()
            print(json.dumps(runs, indent=2))
        elif args.polaris_cmd == "log-run":
            res = client.log_run(
                strategy_name=args.strategy,
                sharpe=args.sharpe,
                cagr=args.cagr,
                max_drawdown=args.drawdown,
                trades_count=args.trades,
                universe=args.universe,
            )
            print(json.dumps(res, indent=2))
        elif args.polaris_cmd == "stream":
            print("Connecting to PolarisLink™ real-time stream...")
            for evt in client.stream_polaris_events(max_events=20):
                print(f"[{evt['event']}] {json.dumps(evt['data'])}")
        elif args.polaris_cmd == "work":
            print(json.dumps(client.get_workspace_work(), indent=2))
        elif args.polaris_cmd == "add-task":
            res = client.create_workspace_task(args.title, status=args.status)
            print(json.dumps(res, indent=2))
        elif args.polaris_cmd == "issues":
            issues = client.list_issues(status=args.status, category=args.category)
            print(json.dumps(issues, indent=2))
        elif args.polaris_cmd == "get-issue":
            issue = client.get_issue(args.id)
            print(json.dumps(issue, indent=2))
        elif args.polaris_cmd == "report-issue":
            res = client.report_issue(args.title, args.description, category=args.category, priority=args.priority)
            print(json.dumps(res, indent=2))
        elif args.polaris_cmd == "comment-issue":
            res = client.add_issue_comment(args.id, args.comment)
            print(json.dumps(res, indent=2))
        elif args.polaris_cmd == "update-issue":
            res = client.update_issue(args.id, args.status, resolution_note=args.note)
            print(json.dumps(res, indent=2))
        else:
            parser.parse_args(["polaris", "--help"])
    elif args.command == "swarm":
        sid = getattr(args, "swarm_id", "default")
        if args.swarm_cmd == "directory":
            print(json.dumps(client.get_swarm_directory(), indent=2))
        elif args.swarm_cmd == "status":
            print(json.dumps(client.get_swarm_status(sid), indent=2))
        elif args.swarm_cmd == "catalog-stats":
            print(json.dumps(client.get_frontier_catalog_stats(sid), indent=2))
        elif args.swarm_cmd == "replenish":
            res = client.replenish_frontier_wave(sid, wave_name=args.wave_name, min_frontiers=args.min_frontiers)
            print(json.dumps(res, indent=2))
        elif args.swarm_cmd == "frontiers":
            print(json.dumps(client.get_swarm_frontiers(sid, domain=args.domain), indent=2))
        elif args.swarm_cmd == "claim":
            res = client.claim_swarm_lease(args.node_id, args.frontier_id, ttl_seconds=args.ttl, swarm_id=sid)
            print(json.dumps(res, indent=2))
        elif args.swarm_cmd == "release":
            res = client.release_swarm_lease(args.node_id, args.frontier_id, completed=args.completed, summary=args.summary, swarm_id=sid)
            print(json.dumps(res, indent=2))
        elif args.swarm_cmd == "heartbeat":
            res = client.send_swarm_heartbeat(args.node_id, swarm_id=sid)
            print(json.dumps(res, indent=2))
        elif args.swarm_cmd == "broadcast-scar":
            res = client.broadcast_swarm_scar(args.scar_id, args.title, args.mechanism, args.root_cause, args.rule, source_node=args.node_id, swarm_id=sid)
            print(json.dumps(res, indent=2))
        elif args.swarm_cmd == "stream":
            print(f"Connecting to PolarisSwarm™ SSE stream for cluster '{sid}'...")
            for evt in client.stream_swarm_events(swarm_id=sid, max_events=20):
                print(f"[{evt['event']}] {json.dumps(evt['data'])}")
        else:
            parser.parse_args(["swarm", "--help"])
    else:
        parser.print_help()


if __name__ == "__main__":
    _cli_main()
