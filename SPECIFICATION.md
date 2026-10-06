# Forticia PolarisLink™ Protocol (PLP) — Canonical Institutional Technical Specification

**Document Version:** `2.6.1-PROD`  
**Classification:** Forticia Research Institute — Proprietary Architecture  
**Document Identifier:** `FCA-SPEC-PLP-2026-V1.2`  
**Protocol Family:** `Forticia PolarisLink™`  
**Base URL:** `https://forticia.uk/api/polarislink` (Production) / `http://localhost:8787/api/v1` (Development / Test)  
**Wire Headers:**  
`X-PolarisLink-Protocol: Forticia PolarisLink™`  
`X-PolarisLink-Version: 2.6.1`  
**Client SDKs:**  
- Python: `sdk/forticia_sdk.py` (`PolarisLinkClient`, Zero external dependencies)  
- C++20: `cpp/include/polarislink/polarislink.hpp` (Native, Single Header)

---

## 1. Executive Architecture & Mission Statement

**Forticia PolarisLink™** is the sovereign quantitative market data, agent coordination, and telemetry nervous system for Forticia Research Institute. Architected to bridge low-latency algorithmic execution engines (**C++20 reference engine**), autonomous AI researchers, partner research nodes, and institutional allocators directly to Forticia's high-speed data vault.

PolarisLink™ replaces disjointed REST silos with a unified institutional protocol designed for long-term parity with **CME MDP 3.0** and **FIX 5.0 SP2**, supporting:
1. **Zero Bad Data Invariant:** Strict mathematical truth. Zero synthetic, randomized, or heuristic market data.
2. **Duplex Agent Telemetry:** Persistent Server-Sent Events (SSE) and streaming gateways delivering real-time task lifecycle updates, cluster metrics, and harvester ingestion events with zero HTTP polling.
3. **Autonomous Closed-Loop Healing:** Self-reconciling issue watchdog (`polaris-autofix`) that detects missing tickers, dispatches cluster harvester jobs, resolves access lockouts, and enforces quantitative governance.
4. **8-Dimensional Options Microstructure:** Full options chain surfaces carrying strike, expiration, underlying spot, bid/ask quote spread, trade print, implied volatility, Greeks, and open interest.
5. **Backtest Run Auditing:** Immutable telemetry sink capturing strategy parameters, Sharpe ratios, CAGR, max drawdown, trade count, and git provenance hashes.

```
                                  FORTICIA POLARISLINK™ TOPOLOGY
                                  
   C++ Reference Engine      Autonomous Agents (Hermes)           Institutional Allocators
 ┌──────────────────┐       ┌──────────────────────────┐         ┌─────────────────────────┐
 │  polarislink.hpp │       │  Python SDK / CLI        │         │  Forticia Console / Web │
 └────────┬─────────┘       └────────────┬─────────────┘         └────────────┬────────────┘
          │                              │                                    │
          ▼                              ▼                                    ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────┐
 │                  PolarisLink™ Institutional Gateway Node (Hono / Node.js)               │
 │                                   Host: forticia.uk (:8787)                             │
 ├───────────────────────────────┬─────────────────────────────────┬───────────────────────┤
 │     Zero-Trust RBAC Guard     │     Polaris Duplex Event Bus    │   Autonomous Watchdog │
 │  • Constant-time key verify   │  • Server-Sent Events (/stream) │  • polaris-autoheal.ts│
 │  • Sandboxed principal scopes │  • Real-time run/task broadcast │  • Harvester triggers │
 └───────────────┬───────────────┴────────────────┬────────────────┴───────────────┬───────┘
                 │                                │                                │
                 ▼                                ▼                                ▼
 ┌───────────────────────────────┐ ┌──────────────────────────────┐ ┌──────────────────────┐
 │     Market Data Vault NVMe    │ │     PGlite / Postgres DB     │ │  Capture Gateways    │
 │ • 25-Year Daily Bars (S&P100) │ │ • agent_runs (Telemetry)     │ │ • Options Live       │
 │ • Continuous M1/H1 Captures   │ │ • tasks (4-Stage Kanban)     │ │ • Equity Pacing      │
 │ • 8D Options Surfaces         │ │ • issues (Auto-Healed)       │ │ • M1 Tick Ingestion  │
 └───────────────────────────────┘ └──────────────────────────────┘ └──────────────────────┘
```

---

## 2. Wire Routing Architecture, Versioning & Transport Invariants

### 2.1 Sovereign Unversioned Roots vs. Versioned Compatibility
PolarisLink™ provides two complementary routing models across all endpoints:

1. **Sovereign Unversioned Routes (`/api/polarislink/*`, `/api/quant/*`, and direct `/api/*`):**
   - **Modern Sovereign Standard:** Designed for autonomous AI agents, C++20 algorithmic execution loops, and internal microservices. Eliminates unnecessary `/v1` ceremony.
   - **First-Class Examples:**
     - `GET /api/status` (Public cluster diagnostic status probe)
     - `GET /api/catalog` (Unified multi-asset data catalog)
     - `GET /api/polarislink/stream` (Duplex SSE telemetry bus)
     - `GET /api/polarislink/quant/bars` (Continuous bar queries)
     - `GET /api/polarislink/quant/options/sessions` (Parquet options sessions)
2. **Versioned REST Compatibility Shims (`/api/v1/*`):**
   - **Why `/api/v1` Exists:** Standard enterprise and broker integration best practice to establish an immutable contract compatibility boundary for legacy harnesses, automated cron pipelines, and external allocator integrations.
   - **Contract Guarantee:** Wire compatibility is strictly guaranteed for all `/api/v1/*` endpoints. If a future breaking wire transport transition occurs (e.g., pure binary Protobuf or Simple Binary Encoding replacing JSON), it will be introduced under `/api/v2/*`, ensuring existing institutional clients on `/api/v1/*` never break.

### 2.2 Three-Tier Versioning Hierarchy
PolarisLink™ enforces an immutable versioning contract:
1. **Wire Route Prefix (`/api/v1`):** Contract stability boundary. Only bumped to `/api/v2` in the event of breaking wire transport changes (e.g., binary SBE replacing JSON).
2. **Protocol Semantic Version (`v2.6.1`):** Broadcast via HTTP headers (`X-PolarisLink-Version: 2.6.1`) and `/api/v1/health`.
   - **MAJOR:** Architectural protocol overhaul.
   - **MINOR (1.1 $\rightarrow$ 1.2):** Additive capabilities: `/runs` telemetry sink, `/knowledge` gateway, persistent `/stream`, and `polaris-autofix` daemon.
   - **PATCH:** Latency optimizations, bugfixes, zero schema alterations.
3. **Client SDKs:** Maintained at strict lockstep SemVer with the protocol gateway.

### 2.3 Standard Wire Headers
Every PolarisLink™ response unconditionally carries canonical provenance headers:
```http
X-PolarisLink-Protocol: Forticia PolarisLink™
X-PolarisLink-Version: 2.6.1
Content-Type: application/json; charset=utf-8
```

### 2.4 The Zero Bad Data Mandate
Quantitative integrity is non-negotiable across all PolarisLink™ endpoints:
- **No Mock or Synthetic Quotes:** Endpoints must NEVER use `Math.random()`, Brownian motion jitter, or heuristic spreads.
- **Explicit Provenance Flags:** If a dataset contains only midpoint trade bars, quote spread fields (`bid`, `ask`, `spread`, `spreadBps`, `bidSize`, `askSize`, `openInterest`) must return `null`. The contract declares:
  ```json
  {
    "quotesVerified": false,
    "dataQuality": "midpoint_bar_only"
  }
  ```
- **Prohibited Data Vendors:** Retail web scrapers (`yfinance`, `yahoo`, `alphavantage`, `finnhub`, `polygon_free`) are strictly blocked by the protocol gateway and SDKs.

---

## 3. Cryptographic Security & Zero-Trust RBAC

PolarisLink™ operates a zero-trust Bearer token authentication guard (`api/protocol/api-auth.ts`). Tokens are matched using cryptographic constant-time comparison (`crypto.timingSafeEqual`) to prevent side-channel timing attacks.

### 3.1 Scope Hierarchy & Rate Limits Matrix

| Scope | Capability Category | Accessible Endpoints | Standard Rate Limit |
|---|---|---|---|
| `admin:*` | System Administration | Unconstrained access across all endpoints, catalogs, and workspaces | 10,000 req/min |
| `quant:*` | Quantitative Core | Full access to market data, options surfaces, strategy runs, and SSE stream | 5,000 req/min |
| `quant:market_data:*` | Data Vault & Egress | Historical continuous bars, 8D options surfaces, and raw dataset downloads | 2,000 req/min |
| `quant:strategy:*` | Execution Telemetry | Logging backtest execution metrics (`POST /runs`) and querying run histories | 2,000 req/min |
| `ops:autoheal` | AutoHeal Resilience | Autonomous 404 route gap interception, diagnostic packet staging, and code triage | 2,000 req/min |
| `ops:harvester:dispatch` | Harvester Ingestion | Background catalog ingestion worker dispatch (`forticia_harvester.py`) | 1,000 req/min |
| `ops:agent:telemetry` | Cluster Operations | Node health queries (`/telemetry`), heartbeats, and persistent SSE streams (`/stream`) | 5,000 req/min |
| `quant:market_data:read` | Read-Only Audit | Read-only market data inspection. Raw file download and strategy writes are blocked. | 300 req/min |

### 3.2 Authentication Headers
Requests must supply credentials via standard HTTP headers:
```http
Authorization: Bearer <API_KEY>
```
Or alternatively:
```http
X-API-Key: <API_KEY>
```

---

## 4. Domain I: PolarisLink™ Agent Protocol (`/api/polarislink/*`)

### 4.1 Cluster Telemetry & Node Health
**Endpoint:** `GET /api/polarislink/telemetry`  
**Authentication:** Required (`ops:agent:telemetry` or `quant:*`)  
**Description:** Returns real-time gateway health, connected stream count, recorded backtest runs, memory footprint, and vault status.

#### Response:
```json
{
  "status": "operational",
  "gateway": "PolarisLink™ Institutional Agent Gateway v2.6.1",
  "node": "node-compute-1",
  "protocolVersion": "2.6.1",
  "uptimeSeconds": 142850,
  "activeStreams": 3,
  "autoHealEngine": "operational",
  "agentContext": {
    "principalId": "node_quant_01",
    "name": "Quantitative Research Node",
    "email": "research-node@forticia.uk",
    "role": "researcher",
    "scopes": ["quant:market_data:*", "quant:strategy:*"]
  },
  "system": {
    "memoryHeapUsedMb": 64,
    "memoryRssMb": 118,
    "nodeVersion": "v22.14.0"
  },
  "runsRecorded": 42,
  "vault": {
    "status": "online",
    "activePath": "/home/admin1/forticia-main/data/vault",
    "universesCount": 5,
    "totalSymbolsIndexed": 482
  },
  "timestamp": "2026-09-05T01:40:00.000Z"
}
```

---

### 4.2 Knowledge & Quantitative Governance Gateway
**Endpoint:** `GET /api/polarislink/knowledge`  
**Authentication:** Required  
**Description:** Canonical remote knowledge endpoint allowing remote research agents and algorithmic nodes to sync Forticia's quantitative constitution, prohibited data vendors, dataset schemas, and cluster topology.

#### Response:
```json
{
  "gateway": "PolarisLink™ Institutional Knowledge & Governance Gateway",
  "version": "2.6.1",
  "governancePolicies": {
    "zeroBadDataMandate": {
      "enforced": true,
      "description": "Zero synthetic, mocked, or randomized market data permitted. Missing quotes or Greek surfaces must return null with explicit provenance flags."
    },
    "retailDataProhibition": {
      "prohibitedVendors": ["yfinance", "yahoo", "alphavantage", "finnhub", "polygon_free"],
      "enforced": true,
      "reason": "Retail scraped feeds lack institutional NBBO timestamps and order-book depth."
    },
    "optionsRepresentation8D": {
      "requiredDimensions": ["strike", "expiry", "underlying", "bid", "ask", "trade_price", "implied_vol", "greeks"],
      "guideline": "Simulated option execution fills require quote spread dimension."
    },
    "outOfSampleIsolation": {
      "enforced": true,
      "guideline": "Train and test partitions must be strictly segregated."
    }
  },
  "datasets": {
    "universes": [
      {
        "id": "equity_universe_daily",
        "name": "S&P 100 Primary Ingestion",
        "symbolCount": 102,
        "endpoint": "/api/polarislink/quant/bars?universe=equity_universe_daily"
      }
    ],
    "continuousTickCapture": {
      "status": "active",
      "source": "forticia-ingest",
      "frequency": "M1 continuous"
    }
  },
  "clusterTopology": {
    "primaryNode": "forticia-node-1",
    "harvesterService": "forticia-ingest.service",
    "optionsCapture": "options-capture.service",
    "apiPort": 8787
  }
}
```

---

### 4.3 Quantitative Backtest Run Telemetry Sink
Stores immutable records of backtest executions, strategy parameters, and performance statistics directly in Postgres `agent_runs`.

#### A. Record Backtest Run
**Endpoint:** `POST /api/polarislink/runs`  
**Authentication:** Required (`quant:strategy:*` or `admin:*`)

##### Request Body:
```json
{
  "strategyName": "strategy-alpha",
  "workspaceId": "research",
  "universe": "equity_universe_daily",
  "startDate": "2024-01-02",
  "endDate": "2024-08-31",
  "sharpe": 0.00,
  "cagr": 0.00,
  "maxDrawdown": 0.00,
  "tradesCount": 0,
  "winRate": 0.00,
  "gitCommit": "9f8a7c2b",
  "provenanceHash": "sha256:4a8b7c9e...",
  "metrics": {
    "profitFactor": 0.00,
    "calmarRatio": 0.00,
    "avgTradeDurationMinutes": 0.00
  }
}
```

##### Response (`201 Created`):
```json
{
  "success": true,
  "message": "Backtest run recorded successfully with PolarisLink™ ID: 7a9c3d4e-...",
  "run": {
    "id": "7a9c3d4e-...",
    "workspaceId": "research",
    "agentName": "Polaris-Research-Agent",
    "agentRole": "researcher",
    "strategyName": "strategy-alpha",
    "gitCommit": "9f8a7c2b",
    "universe": "equity_universe_daily",
    "startDate": "2024-01-02",
    "endDate": "2024-08-31",
    "sharpe": 0.00,
    "cagr": 0.00,
    "maxDrawdown": 0.00,
    "tradesCount": 0,
    "winRate": 0.00,
    "provenanceHash": "sha256:4a8b7c9e...",
    "createdAt": "2026-09-05T01:40:00.000Z"
  }
}
```

#### B. Query Runs List
**Endpoint:** `GET /api/polarislink/runs?workspace=research&strategy={name}&limit={n}`  
**Response:** Array of runs sorted by `created_at DESC`.

#### C. Query Single Run Detail
**Endpoint:** `GET /api/polarislink/runs/:id`  
**Response:** Single run detail including parsed `metrics` JSON object.

---

### 4.4 Persistent Real-Time Event & Telemetry Stream (SSE)
**Endpoint:** `GET /api/polarislink/stream`  
**Authentication:** Required  
**Content-Type:** `text/event-stream`  
**Description:** Duplex SSE channel streaming live cluster telemetry, task transitions, issue self-healing updates, and backtest run logs in real time with sub-millisecond propagation.

#### Event Types:
| Event Name | Description |
|---|---|
| `connected` | Initial handshake emitting gateway node and principal authorization context. |
| `knowledge_sync` | Baseline snapshot of active governance rules and vault universes. |
| `run_event` | Emitted when any agent records a backtest run via `POST /runs`. |
| `task_event` | Emitted when a Kanban task is created or moved across stages. |
| `issue_event` | Emitted when an operational issue is created, commented on, or auto-healed. |
| `error_event` | Emitted on unhandled HTTP 500 runtime exceptions with request path, method, and sanitized stack trace. |
| `autoheal_event` | Emitted when Polaris AutoHeal™ triggers triage, multi-asset harvester dispatch, or security quarantine. |
| `heartbeat` | 15-second heartbeat containing uptime, memory RSS, and active streams. |

#### Stream Wire Sample:
```http
event: connected
data: {"gateway":"PolarisLink™ Real-Time Agent Stream v2.6.1","node":"node-compute-1","protocol":"PolarisLink™ Duplex Telemetry Protocol"}

event: error_event
data: {"method":"GET","path":"/api/polarislink/quant/bars","error":"Cannot read properties of undefined","stack":"TypeError: ...","timestamp":"2026-09-06T09:00:00.000Z"}

event: autoheal_event
data: {"action":"data_gap_harvester_dispatched","issueId":7,"missingSymbols":["SPY","QQQ","NVDA","TSLA","AAPL"],"timestamp":"2026-09-06T09:00:01.000Z"}

event: run_event
data: {"type":"run","payload":{"action":"logged","run":{"id":"7a9c3d4e...","strategyName":"strategy-alpha","sharpe":0.00}}}

event: heartbeat
data: {"uptime":142865,"rssMb":118,"activeStreams":3,"timestamp":"2026-09-06T09:00:15.000Z"}
```

---

### 4.5 Polaris AutoHeal™ — Autonomous Error Interception & Self-Healing (`polaris-autoheal`)
**Endpoints:**
- `GET /api/polarislink/issues` (Filter by `status`, `category`, `workspace`)
- `POST /api/polarislink/issues` (Report new issue; triggers pre-flight security perimeter and AutoHeal)
- `GET /api/polarislink/issues/:id` (Fetch issue detail)
- `GET /api/polarislink/issues/:id/comments` (Fetch structured comment thread, total count, and author metadata; aliases: `GET /api/issues/:id/comments`, 307 redirect: `GET /issues/:id/comments`)
- `POST /api/polarislink/issues/:id/comments` (Append discussion comment)
- `PATCH /api/polarislink/issues/:id` (Update status: `Open`, `In Progress`, `Resolved`, `Closed`)
- `GET /api/polarislink/issues/:id/attachments` (List attachment manifest)
- `POST /api/polarislink/issues/:id/attachments` (Multipart upload, field `file`)
- `GET /api/polarislink/issues/:id/attachments/:attachmentId` (Authenticated download with `X-Content-Sha256`)

#### Per-Workspace Issue Fabric (v2.5.0):
Every issue belongs to exactly one workspace: a project workspace from the canonical registry, the `platform` workspace (console and platform problems, readable by all staff; the default when no workspace is given), or a personal space `personal-<userId>`. Issues also carry `visibility`: `project` (all members, default), `restricted` (reporter plus grants managed through `GET/PUT /issues/:id/access`) or `private` (reporter only, plus privileged reviewers). Unscoped principals (founder, researchers, agents) may target any canonical workspace via the `workspace` body field; workspace-scoped keys are hard-bound — the workspace resolves from the key's `workspaceScope`, client-supplied values to the contrary receive `403 Workspace boundary violation`.

#### Workspace Registry & Workspace-Scoped Key Provisioning (v2.5.0):
- `GET /api/polarislink/workspaces` — canonical workspace registry (id, name, domain, lead, summary).
- `POST /api/polarislink/workspaces/:id/keys` — provisions a key cryptographically bound to the workspace. Delegation is exactly one depth: founder → platform key (`platform: true`, scope `ops:workspace-keys:provision`) → agent keys (scopes `ops:issues:file` + `ops:issues:comment` only). Agent keys can never mint further keys and never touch quant, execution, or swarm surfaces. Raw `fca_live_...` tokens are returned exactly once; only SHA-256 hashes are stored.

#### Attachment Transport Invariants (v2.5.0):
25 MB hard ceiling, ≤ 10 attachments per issue, strict MIME whitelist (PDF, Office, ODF, CSV, JSON, ZIP, text, Markdown, PNG/JPEG/WebP/SVG), `path.basename()` sanitization with traversal rejection, server-generated storage keys, SHA-256 digests recorded at upload and echoed via `X-Content-Sha256` on download. The full lifecycle is centralized in the deep module `api/issue-attachments.ts`.

#### Event-Driven Triage & Pre-Flight Logic:
When an issue is reported via `POST /issues`, the **Polaris AutoHeal™ Engine** (`api/polaris-autoheal.ts`) evaluates the issue immediately and emits real-time events over `/stream`:
1. **Security & Jailbreak Pre-Flight Gate:**
   - Scans text for prompt injection heuristics (`ignore previous instructions`, `DAN`, `jailbreak`), credential exfiltration attempts (`.env`, `credentials/`, private keys), and arbitrary shell patterns (`rm -rf`, `exec()`, `child_process`).
   - Malicious payloads are **immediately quarantined** (`status = Closed`), code execution is permanently aborted, and an emergency alert is pushed to the Hermes Notification Wall.
2. **Market Data Gaps (`category: "Data Gap"`):**
   - Automatically extracts target ticker (e.g. `AAPL`, `SPX`).
   - Cross-references data vault. If symbol exists, comments with direct endpoint link and marks issue `Resolved`.
   - If missing from local cache, marks status `In Progress` and dispatches ticket to the quant harvester queue on cluster node `node-compute-1`.
2. **Security & Credentials Isolation:**
   - Account security states, MFA resets, and lockout lifting are strictly isolated from ticket ingestion.
   - Any ticket requesting credential manipulation receives an automated policy advisory; user authentication state is never modified via issue parsing.
3. **Quantitative Governance Guardrail:**
   - Detects queries for prohibited retail scrapers (`yfinance`, `yahoo`, `polygon_free`).
   - Appends official policy rejection citing the Zero Bad Data Mandate and marks issue `Closed`.
4. **Autonomous Agent Dispatch (`issue_event` over `/stream`):**
   - Non-trivial issues emit real-time SSE events over `GET /api/polarislink/stream`, waking autonomous execution agents strictly on movement with zero idle token burn.

---

### 4.6 Workspace Work & Kanban Task Management
**Endpoints:**
- `GET /api/polarislink/workspaces/:id/tasks` & `GET /api/polarislink/tasks?workspace=research`
- `POST /api/polarislink/workspaces/:id/tasks` & `POST /api/polarislink/tasks`
- `PATCH /api/polarislink/workspaces/:id/tasks/:taskId` & `PATCH /api/polarislink/tasks/:taskId`
- `DELETE /api/polarislink/workspaces/:id/tasks/:taskId`

Enables programmatic management of tasks across the canonical 4-stage Kanban workflow:
```
[Queued] ────► [In Progress] ────► [Verification] ────► [Complete]
```

---

### 4.7 Workspace Shared Drive API
**Endpoints:**
- `GET /api/polarislink/workspaces/:id/drive` & `GET /api/polarislink/drive?workspace={id}`: Lists folders, files, file sizes, MIME types, modified dates, and direct streaming links.
- `GET /api/polarislink/workspaces/:id/drive/tree` & `GET /api/polarislink/drive/tree?workspace={id}`: Hierarchical directory tree of folders and files with recursive counts, sizes, and download links.
- `POST /api/polarislink/workspaces/:id/drive/upload` & `POST /api/polarislink/drive/upload`: Programmatic file upload accepting multipart/form-data or Base64 JSON payloads with automatic audit logging.
- `GET /api/polarislink/workspaces/:id/drive/files/:fileId` & `GET /api/polarislink/drive/files/:fileId`: Downloads or streams files with full `Content-Type` and `Content-Disposition`.
- `DELETE /api/polarislink/workspaces/:id/drive/files/:fileId` & `DELETE /api/polarislink/drive/files/:fileId`: Deletes files from storage with audit trail recording.

---

### 4.8 Activity & Telemetry Audit Logging API
**Endpoints:**
- `GET /api/polarislink/workspaces/:id/activity`: Retrieves chronological workspace audit trail events.
- `GET /api/polarislink/activity` & `GET /api/polarislink/telemetry/activity`: Protocol-wide audit stream across all workspaces and agent operations.
- `POST /api/polarislink/activity` & `POST /api/polarislink/telemetry/activity`: Programmatic milestone logging for autonomous agents and backtest runners.

### 4.9 Operational Health & Diagnostic Status Probe
**Endpoints:** `GET /api/polarislink/status`, `GET /api/status`, `GET /status`  
**Authentication:** Public / Unblocked  
**Rate Tier:** 10,000 / min  
**Description:** Dedicated high-frequency diagnostic status probe for external agent harnesses, watchdogs, and cluster health monitors. Returns operational status, active protocol version, process uptime, domain health states (`quant`, `vault`, `stream`, `autoheal`), cluster node identity (`node-compute-1`), and total indexed symbols (1,149) without authentication hurdles.

### 4.10 Unified Institutional Reports Catalog & Notifications Gateway
**Endpoints:**
- `GET /api/polarislink/reports` (Aliases: `GET /api/reports`, `GET /reports`)
- `GET /api/polarislink/reports?type=research-log` (or `format=json`)
- `GET /api/polarislink/notifications` (Alias: `GET /api/notifications`)
- `GET /api/polarislink/notifications/peek` (Aliases: `GET /api/notifications/peek`, `GET /notifications/peek`)
- `PUT /api/polarislink/notifications` (Alias: `PUT /api/notifications`)

**Description:**
1. **Reports Catalog:** Provides programmatic discovery of canonical institutional research reports (`RESEARCH_LOG.md`, swarm telemetry, paper trading sleeves manifest, macro events, COT positioning, options GEX surfaces). Query parameter `?type=research-log` streams the transactional markdown research log directly.
2. **Notifications Gateway:** Provides direct sovereign endpoints for inspecting and updating caller notification preferences across email alerts, discoveries, verdicts, scars, and system alerts with a strict disabled-by-default baseline.
3. **Notifications Peek:** Provides a non-mutating operational telemetry check returning active unread notification counts, open issue summaries, and system alerts.

### 4.11 First-Class Sovereign Specification & Changelog Discovery
**Endpoints:**
- `GET /api/spec` (Aliases: `GET /spec`, `GET /api/docs/spec`, `GET /docs/spec`, `GET /api/polarislink/spec`)
- `GET /api/changelog` (Aliases: `GET /changelog`, `GET /api/docs/changelog`, `GET /docs/changelog`, `GET /api/polarislink/changelog`)

**Authentication:** Public / Unblocked  
**Rate Tier:** 10,000 / min  
**Description:** Dedicated first-class public diagnostic endpoints serving live protocol specifications, wire contracts, and release history without authentication. Eliminates routing guesswork and 404 friction for autonomous LLM agents, C++20 engine nodes, and external allocators. Supports `?format=markdown` (or `?format=md`) to stream raw markdown documents directly (`text/markdown; charset=utf-8`) or default structured JSON envelopes.

---

## 5. Domain II: Institutional Market Data Vault (`/api/polarislink/quant/*`)

### 5.1 Master Institutional Quant Catalog
`GET /api/polarislink/quant/catalog` & `GET /api/catalog`  
Unified multi-asset discovery endpoint returning comprehensive metadata for all registered universes, partitioned options sessions (`SPY`, `QQQ`, `NVDA`, `TSLA`, `AAPL`, `SPXW`), macroeconomic indicators, corporate buybacks, and ETF fund flows.

### 5.2 Dataset Universes Catalog
`GET /api/polarislink/quant/universes`  
Returns metadata for all physical datasets registered in the data vault (`eq_25y`, `eq_10y`, `equity_universe_daily`, `eq_universe_hourly`, `macro_data`, `futures_feed`).

### 5.3 Historical Bars Query
`GET /api/polarislink/quant/bars?symbol={SYM}&universe={UID}&start={YYYY-MM-DD}&end={YYYY-MM-DD}&format={json|csv}&limit={N}`  
Queries high-precision cleaned historical bars with pre-computed daily (`ret1d`) and overnight (`overnightRet`) returns.

### 5.4 Partitioned Options Daily Sessions Manifest
`GET /api/polarislink/quant/options/sessions?symbol={SYM}`  
Lists all partitioned historical options daily sessions available in the vault for the requested underlying (e.g. 1,051 sessions for `SPY`, 516 for `QQQ`, 238 for `NVDA`, 238 for `TSLA`, 239 for `AAPL`). Returns date, filename, byte size, and direct session download URLs.

### 5.5 8D Options Volatility Surfaces
`GET /api/polarislink/quant/options/surface?symbol={SYM}`  
Returns full institutional 8-dimensional option chains with NBBO quotes, Greeks, implied volatility, and explicit data quality indicators. Uses pure TypeScript streaming tail buffers (`readCsvTail`) to read column headers and slice a bounded 16 MB window, completely eliminating memory overflow on continuous multi-gigabyte stores (`SPXW.csv`).

### 5.6 Historical Options Quote Tape & Greeks Time-Series
`GET /api/polarislink/quant/options/history?symbol={SYM}&contract={CTR}&expiration={YYYY-MM-DD}&strike={K}&right={C|P}&start={YYYY-MM-DD}&end={YYYY-MM-DD}&format={json|csv}&limit={N}&offset={M}`  
Replays multi-strike options quote tapes with NBBO bid/ask spreads, trade prints, and volatility parameters across dates for realistic simulated execution. (Alias: `/api/polarislink/quant/options/bars`).

### 5.7 Raw File & Parquet Session Download Streaming
`GET /api/polarislink/quant/download?symbol={SYM}&universe={UID}&date={YYYY-MM-DD}&format={parquet|csv|zip}`  
Streams uncompressed raw datasets or individual partitioned daily Parquet session archives directly from NVMe vault storage with proper MIME types (`application/vnd.apache.parquet`, `application/zip`, `text/csv`). Supports direct subpath queries (e.g. `symbol=SPY/2022-05-11.parquet`) and auto-infers `options_chains` when `date` or `format=parquet` is specified.

### 5.8 CME Level 2 Tick Order Book Depth
`GET /api/polarislink/quant/depth?symbol={SYM}&date={YYYYMMDD}&limit={N}&side={A|B}&format={json|csv}`  
Streams authentic high-frequency Level 2 tick order book depth updates captured directly from the exchange feed at ~740 msgs/sec for CME futures (`ESU6`, `NQU6`, `RTYU6`, `6EU6`, `GCV6`, `CLV6`). Provides bid/ask prices, sizes, action codes, inside spread, and basis points.

### 5.9 SEC Rule 10b-18 Corporate Buyback Blackout Schedule & Empirical Alpha
`GET /api/polarislink/quant/buybacks?symbol={SYM}&status={active_window|blackout_active|mid_cycle|scheduled}&format={json|csv}`  
Returns canonical SEC Rule 10b-18 safe harbor repurchase schedules, corporate blackout lift dates ($D_{+2}$), active algorithmic execution windows ($D_{+2} \to D_{+10}$), authorized repurchase capital ($ in billions), trailing buyback yield %, and 25-year empirical event study metrics (+62,696 bps net alpha across 997 quarterly cycles, +31.92 bps structural excess over placebo, $p < 0.01$).

### 5.10 Frontier 3 ETF Basis Arbitrage Flow Pipeline
`GET /api/polarislink/quant/etf-flows?symbol={SYM}`  
Exposes creation/redemption fund flow data, NAV premium/discount spreads, and basket constituent tracking for ETF basis arbitrage models.

### 5.11 Macroeconomic Event Calendar & PIT Schedule
`GET /api/polarislink/quant/calendar?series={series}&category={category}&start={YYYY-MM-DD}&end={YYYY-MM-DD}&limit={n}`  
Point-in-Time (PIT) macroeconomic event calendar, standardized surprise vectors, and consensus estimates from `macro_event_calendar`. Supports `series` filtering (`treasury_auctions`, `fomc`, `cpi`, `nfp`, `gdp`), `category` filtering (`RATES_AUCTION`, `MONETARY_POLICY`, `INFLATION`, `LABOR`, `GROWTH`), and `asOfKnowledge` PIT point-in-time querying. Aliases: `GET /api/calendar`, `GET /calendar`, `GET /quant/calendar`.

### 5.12 US Treasury Debt Auction Concession & Refunding Gateway
`GET /api/polarislink/quant/auctions?symbol={symbol}&tenor={tenor}&start={YYYY-MM-DD}&end={YYYY-MM-DD}&format={json|csv}&limit={n}`  
Authentic US Treasury debt auction concession records spanning 2021 to 2026 for 10-Year Notes (`ZN`), 2-Year Notes (`ZT`), 5-Year Notes (`ZF`), and 30-Year Bonds (`ZB`). Delivers exact high/median auction yields, tail basis points, bid-to-cover ratios, primary dealer allocations, indirect bidder allocations, and total accepted amounts. Dual JSON and high-throughput CSV streaming (`format=csv`). Backed by vault dataset (`fred_data/treasury_10y_auctions_2020_2026.parquet`) and PostgreSQL `treasury_auctions` table. Aliases: `GET /api/auctions`, `GET /auctions`, `GET /quant/auctions`.

---

## 6. Official Client Implementations & SDK Reference

### 6.1 Python Institutional Client (`forticia_sdk.py`)

```python
from forticia_sdk import PolarisLinkClient

# Initialize client
client = PolarisLinkClient(api_key="forticia_live_example_...")

# 1. Sync Governance & Verify Zero Bad Data Compliance
knowledge = client.sync_governance()
print(f"Connected to {knowledge['clusterTopology']['primaryNode']}")

# 2. Query Clean Historical Bars
bars = client.get_bars("SPY", universe="equity_universe_daily", start="2024-01-01")

# 3. Query Historical Options Quote Tape & Greeks
opt_history = client.get_options_history("SPX", expiration="2026-09-18", strike=8400)

# 4. Log Backtest Execution Metrics
run_result = client.log_run(
    strategy_name="strategy-beta",
    sharpe=0.00,
    cagr=0.00,
    max_drawdown=0,
    trades_count=0,
    universe="equity_universe_daily",
    metrics={"profitFactor": 0.00, "calmar": 0.00}
)
print("Recorded Run ID:", run_result["run"]["id"])

# 5. Stream Duplex Real-Time Agent Events
for event in client.stream_polaris_events(max_events=10):
    print(f"[{event['event']}] {event['data']}")
```

### 6.2 C++20 Header-Only Client (`polarislink.hpp`)

```cpp
#include <polarislink/polarislink.hpp>
#include <iostream>

int main() {
    polarislink::Client client("forticia_live_example_...");

    // Enforce Forticia Quantitative Governance
    polarislink::enforce_institutional_guardrails("eq_primary");

    // Pull historical equity bars directly into engine structures
    auto bars = client.get_bars("SPY", "equity_universe_daily", "2024-01-01");
    std::cout << "Loaded " << bars.size() << " bars for SPY\n";

    // Pull historical options quote tape & Greeks for options backtest
    auto quotes = client.get_options_history("SPX", "", "2026-09-18");
    std::cout << "Loaded " << quotes.size() << " SPX options quotes\n";

    // Log execution metrics directly to Console
    polarislink::BacktestRunMetrics run;
    run.strategy_name = "strategy-alpha";
    run.sharpe = 0.00;
    run.cagr = 0.00;
    run.max_drawdown = 0.061;
    run.trades_count = 620;

    std::string run_id = client.log_run(run);
    std::cout << "Successfully logged run: " << run_id << "\n";
    return 0;
}
```

### 6.3 Command Line Interface (CLI)

```bash
# Query cluster telemetry
python3 sdk/forticia_sdk.py polaris telemetry

# Query governance rules and active datasets
python3 sdk/forticia_sdk.py polaris knowledge

# List recorded backtest runs
python3 sdk/forticia_sdk.py polaris runs

# Log backtest run from CLI
python3 sdk/forticia_sdk.py polaris log-run "strategy-gamma" --sharpe 0.00 --cagr 0.00 --drawdown 0.00 --trades 0

# Report issue for autonomous resolution
python3 sdk/forticia_sdk.py polaris report-issue "Missing NVDA M1 bars" "Need 2024 tick data in vault" --priority High
```

---

## 7. Error Handling & Standard Error Codes

PolarisLink™ returns structured RFC-7807 compliant error payloads:
```json
{
  "error": "Detailed institutional explanation of failure condition."
}
```

| HTTP Status | Condition |
|---|---|
| **200 OK** | Successful query or stream handshake. |
| **201 Created** | Entity created (`/runs`, `/issues`, `/tasks`). |
| **400 Bad Request** | Missing required parameters or malformed payload. |
| **401 Unauthorized** | Missing or invalid Bearer token. |
| **403 Forbidden** | Principal lacks required RBAC scope (e.g. download attempt by allocator key). |
| **404 Not Found** | Requested entity or dataset file does not exist in vault. |
| **429 Rate Limited** | Request frequency exceeded principal threshold. |
| **500 Internal Error** | Cluster node fault or database failure. |

---

---

## 7.5 Mail & Correspondence Engine (`/api/v1/polaris/mail/*`)

PolarisLink™ provides autonomous research agents direct programmatic access to workspace email correspondence:

- `GET /api/v1/polaris/mail/messages?workspace=research` — Retrieves mailbox messages and headers.
- `POST /api/v1/polaris/mail/send` — Dispatches outbound emails via workspace IMAP/SMTP configuration.
- `POST /api/v1/polaris/mail/sync` — Forces immediate IMAP sync watermark.

---

## 8. PolarisSwarm™ Multi-Cluster Swarm Control Plane (`/api/polarislink/swarm/*`)

### 8.1 Executive Architecture & Dual-Plane Model
**PolarisSwarm™** is Forticia's distributed cognitive quantitative research control plane. Designed to coordinate autonomous AI research swarms, workstation nodes, and high-performance compute clusters across active research frontiers without duplicate backtests, fragmented hypotheses, or Git merge conflicts.

PolarisSwarm™ enforces an institutional **Dual-Plane Coordination Architecture**:
1. **Real-Time API Control Plane (Sub-15ms):** PolarisLink™ API manages atomic research leases, mutual exclusion locks (HTTP 409 Conflict), node heartbeats, dead-man failover timers, and instant Battle Scar pub/sub distribution.
2. **Immutable Provenance Plane (Git):** Distributed Git repositories store immutable research logs (`RESEARCH_LOG.md`), verifiable backtest harnesses, parameter grids, and signed commits.

### 8.2 Multi-Cluster Scoping (`/swarm/:swarmId/*`)
PolarisSwarm™ supports multiple sovereign clusters under a single protocol umbrella:
- `research`: quantitative backtesting, alpha discovery, and options surface research.
- `harvester`: Market data vault ingestion, options tape capture, and paced equity ingestion pipelines.
- `autoheal`: Diagnostic watchdogs, route-gap healing, and anomaly reconciliation agents.

Direct convenience aliases are provided for the primary quant research cluster:

### 8.3 Wire Endpoints & Contracts

#### 1. Global Swarm Directory
- **Route:** `GET /api/polarislink/swarm`
- **Scope:** `Public / Unblocked`
- **Purpose:** Public directory listing all active clusters, node counts, leased frontiers, and active battle scars.

#### 2. Cluster Status & Node Telemetry
- **Route:** `GET /api/polarislink/swarm/:swarmId/status`
- **Scope:** `ops:swarm:read` or `quant:*`
- **Headers:** `X-Polaris-Swarm: PolarisSwarm™ v1.0`

#### 2.1 Swarm Nodes Telemetry Matrix
- **Route:** `GET /api/polarislink/swarm/:swarmId/nodes` (and direct alias `GET /api/polarislink/swarm/nodes`)
- **Scope:** `ops:swarm:read` or `quant:*`
- **Purpose:** Fast dedicated endpoint returning registered cluster nodes with deterministic ordering (`node-alpha` first, `node-compute-1` second, collaborators alphabetical).
- **Response Wire:**
```json
{
  "swarmId": "research",
  "totalNodes": 3,
  "activeNodes": 2,
  "nodes": [
    { "nodeId": "node-alpha", "researcher": "Researcher A", "status": "HUNTING", "role": "PRIMARY RESEARCH DESK" },
    { "nodeId": "node-compute-1", "researcher": "Forticia Central Research Supernode", "status": "ACTIVE", "role": "CENTRAL CLOUD COMPUTE" },
    { "nodeId": "node-beta", "researcher": "Researcher B", "status": "OFFLINE", "role": "SATELLITE QUANT DESK" }
  ],
  "timestamp": "2026-09-08T12:00:00.000Z"
}
```
- **Response Wire:**
```json
{
  "swarmId": "research",
  "version": "1.0.0-PROD",
  "protocol": "Forticia PolarisSwarm™",
  "timestamp": "2026-09-07T22:30:00.000Z",
  "nodes": [
    { "id": "node-alpha", "name": "Research Workstation A", "role": "Principal Macro & Execution Architecture", "domains": ["macro_cross_asset"], "status": "active", "lastSeen": "2026-09-07T22:29:45.000Z" },
    { "id": "node-beta", "name": "Research Workstation B", "role": "Options Volatility & Surface Modeling", "domains": ["options_volatility_microstructure"], "status": "active", "lastSeen": "2026-09-07T22:29:40.000Z" },
    { "id": "node-gamma", "name": "Research Workstation C", "role": "Futures Order Book & Microstructure", "domains": ["futures_orderbook_l2"], "status": "active", "lastSeen": "2026-09-07T22:29:50.000Z" },
    { "id": "node-compute-1", "name": "Forticia Compute Node", "role": "Distributed Parameter Sweep & GARCH", "domains": ["options_volatility_microstructure", "macro_cross_asset"], "status": "active", "lastSeen": "2026-09-07T22:29:55.000Z" }
  ],
  "stats": {
    "totalFrontiers": 4,
    "leasedFrontiers": 2,
    "availableFrontiers": 2,
    "activeBattleScars": 157
  }
}
```

#### 2.2 Swarm Node Remote Operator Hold Protocol
- **Routes:**
  - `POST /api/polarislink/swarm/:swarmId/nodes/:nodeId/pause` (alias: `POST /nodes/:nodeId/pause`)
  - `POST /api/polarislink/swarm/:swarmId/nodes/:nodeId/resume` (alias: `POST /nodes/:nodeId/resume`)
- **Scope:** `ops:swarm:write` or `admin`
- **Purpose:** Programmatic and console administrative controls enabling cluster operators to enact or release a graceful hold on a specific research node. Eradicates artificial database hacks. Nodes in hold maintain persistent `is_paused = true` and `pause_reason`, dynamically return `status: "PAUSED"`, and are instructed via heartbeat ACK (`operatorHold: true`) to cease acquiring frontiers.
- **Pause Request Wire:**
```http
POST /api/polarislink/swarm/{swarmId}/nodes/node-gamma/pause HTTP/1.1
Host: forticia.uk
Authorization: Bearer <API_KEY>
Content-Type: application/json

{
  "reason": "Stepped away from desk for CME London close"
}
```
- **Pause Response Wire:**
```json
{
  "success": true,
  "node": {
    "nodeId": "node-gamma",
    "researcher": "Researcher C",
    "status": "PAUSED",
    "isPaused": true,
    "pauseReason": "Stepped away from desk for CME London close",
    "lastSeen": "2026-09-09T14:45:00.000Z"
  }
}
```

#### 2.3 Swarm Researcher Personas Catalog
- **Route:** `GET /api/polarislink/swarm/:swarmId/personas` (and direct aliases `GET /api/personas`, `GET /api/polarislink/swarm/personas`)
- **Single Persona Route:** `GET /api/polarislink/swarm/:swarmId/personas/:id`
- **Scope:** Public / `ops:swarm:read` / `quant:*` (Unblocked discovery)
- **Purpose:** Authoritative programmatic discovery endpoint returning registered research personas (for example `agent-alpha`, `agent-beta`), authorized cluster node IDs, specialized quantitative research domains, operational mandates, active epistemological review gates, execution privilege boundaries (Sovereign Executor vs Candidate Submitter), and canonical communication tone guidelines.
- **Response Wire:**
```json
{
  "swarmId": "research",
  "totalPersonas": 6,
  "personas": [
    {
      "id": "agent-alpha",
      "name": "Agent Alpha",
      "title": "AI Lead Quantitative Research Agent",
      "authorizedNodes": ["node-compute-1", "node-alpha", "node-agent-1"],
      "domain": "Cross-Asset Options Microstructure, Volatility Surfaces & Alpha Modeling",
      "mandate": "Autonomous quantitative research, reference engine backtesting architecture, high-frequency execution microstructure, options pricing surfaces, risk factor decomposition, and invariant NAV preservation across modern regime (2020-Present) with blind OOS stress-testing (2001-2019).",
      "reviewGates": [
        "Gate 1: Theory First & Microstructure Rationale",
        "Gate 2: Two-Stage Air-Gap (2020+ Modern IS vs 2001-2019 Blind OOS)",
        "Gate 3: Small-Sample Gate (Overlap-Adjusted N_eff >= 15)",
        "Gate 4: Matched Placebo Controls (Delta Sharpe >= +0.50, Student t >= 3.0)",
        "Gate 5: Intraday MAE Survival (-200 bps Hard Barrier Truncation)",
        "Gate 6: Zero Test Impersonation (No Probes via Collaborator Credentials)",
        "Gate 7: 8-Dimensional Options Provenance (Zero Synthetic Quotes)",
        "Gate 8: Execution Microstructure Friction & Queue Penalty",
        "Gate 9: Parameter Stability & Machine Learning Deflation"
      ],
      "executionBoundary": "Sovereign Research Executor & Paper Allocation Engine (Local Workstation & Compute Cluster)",
      "voice": "Institutional quantitative rigor, basis-point precision, ruthless adversarial skepticism against selection bias, lookahead leakage, and in-sample overfitting."
    }
  ],
  "timestamp": "2026-09-09T13:40:00.000Z"
}
```

#### 3. Frontier Discovery Matrix
- **Route:** `GET /api/polarislink/swarm/:swarmId/frontiers?domain=<domain>`
- **Scope:** `ops:swarm:read` or `quant:*`
- **Query Parameters:** `domain` (optional filter: `macro_cross_asset`, `options_volatility_microstructure`, `futures_orderbook_l2`)
- **Response Wire:**
```json
{
  "swarmId": "research",
  "frontiers": [
    {
      "id": "frontier-01-vix-term-structure-roll-premia",
      "domain": "macro_cross_asset",
      "title": "VIX Term Structure Roll Premia & Contango Decay Harvest",
      "priority": "P0",
      "status": "leased",
      "lease": {
        "nodeId": "node-alpha",
        "nodeName": "Research Workstation A",
        "claimedAt": "2026-09-07T21:00:00.000Z",
        "expiresAt": "2026-09-07T23:00:00.000Z",
        "ttlSeconds": 7200,
        "remainingSeconds": 3410
      }
    }
  ]
}
```

#### 4. Atomic Frontier Lease Claim (Mutual Exclusion)
- **Route:** `POST /api/polarislink/swarm/:swarmId/leases/claim`
- **Scope:** `ops:swarm:manage` or `quant:*`
- **Request Wire:**
```json
{
  "nodeId": "node-beta",
  "frontierId": "frontier-02-0dte-spx-gamma-scalping-skew",
  "ttlSeconds": 7200
}
```
- **Response (200 OK):**
```json
{
  "status": "leased",
  "frontierId": "frontier-02-0dte-spx-gamma-scalping-skew",
  "nodeId": "node-beta",
  "expiresAt": "2026-09-08T00:30:00.000Z",
  "ttlSeconds": 7200
}
```
- **Collision Response (409 Conflict):**
```json
{
  "error": "Frontier is currently leased by node-beta",
  "heldBy": "node-beta",
  "expiresAt": "2026-09-08T00:30:00.000Z",
  "remainingSeconds": 7180
}
```

#### 5. Frontier Lease Release & Completion
- **Route:** `POST /api/polarislink/swarm/:swarmId/leases/release`
- **Scope:** `ops:swarm:manage` or `quant:*`
- **Request Wire:**
```json
{
  "nodeId": "node-beta",
  "frontierId": "frontier-02-0dte-spx-gamma-scalping-skew",
  "completed": true,
  "summary": "Completed 0DTE gamma scalping sweep across 1,051 sessions. Rule 9 verified."
}
```

#### 5b. Active Swarm Leases Directory
- **Route:** `GET /api/polarislink/swarm/:swarmId/leases`
- **Scope:** `ops:swarm:read` or `quant:*` (Unblocked / Public Read)
- **Response Wire:**
```json
{
  "swarmId": "research",
  "totalActiveLeases": 1,
  "leases": [
    {
      "frontierId": "cme_treasury_yield_curve_futures_basis",
      "frontierNum": 29,
      "frontierName": "CME CBOT Ultra 10-Year (TN) vs 10-Year (ZN) Curve Basis & Intraday Convexity Roll",
      "domain": "futures_orderbook_l2",
      "status": "LEASED",
      "nodeId": "node-gamma",
      "researcher": "node-gamma",
      "claimedAt": "2026-09-08T16:38:30.975Z",
      "expiresAt": 1788887310975,
      "remainingSeconds": 1740,
      "ttlMinutes": 30,
      "nodeStatus": "HUNTING",
      "nodeIp": "103.160.70.135",
      "nodeEnvironment": "Windows 11 x64, 16 Cores",
      "nodeLastHeartbeat": "2026-09-08T16:38:30.973Z"
    }
  ],
  "timestamp": "2026-09-08T16:45:00.000Z"
}
```

#### 6. Liveness Heartbeat & Workload Telemetry
- **Route:** `POST /api/polarislink/swarm/:swarmId/heartbeat`
- **Scope:** `ops:swarm:manage` or `quant:*`
- **Request Wire:**
```json
{
  "nodeId": "node-alpha",
  "status": "SIMULATING_LOCAL",
  "workloadSummary": "Simulating Strategy 205 (CRWD vs PANW) · 3,552 sessions",
  "cpuLoad": "85%",
  "activeHypothesis": "Strategy 205",
  "activeFrontier": "macro_yield_curve"
}
```
- **Granular Status States:**
  - `HUNTING_FRONTIER`: Actively scanning available registry vectors for assignment.
  - `SIMULATING_LOCAL`: Actively running local unleased backtests, parameter sweeps, or hypothesis evaluations.
  - `LEASE_ACTIVE`: Actively executing compute on an exclusive leased frontier.
  - `QUIESCENT_IDLE`: Connected and standing by with 0 active compute.
  - `ACTIVE`, `IDLE`, `AUDITING`, `OFFLINE`, `DRAINING`: Standard operational states.
- **Behavior:** Updates `last_heartbeat` timestamp, records structured compute telemetry (`workload_summary`, `cpu_load`, `active_hypothesis`), broadcasts node heartbeat over the cluster SSE stream, and extends TTL on `activeFrontier` research leases. Stale nodes whose leases expire forfeit them automatically to the unleased pool.

#### 7. Battle Scar Knowledge Base & Pub/Sub Broadcast

##### 7a. Query Codified Battle Scars
- **Route:** `GET /api/polarislink/swarm/:swarmId/scars`
- **Scope:** `ops:swarm:read`, `ops:swarm:manage`, or `quant:*`
- **Response Wire:**
```json
{
  "swarmId": "research",
  "totalScars": 3,
  "scars": [
    {
      "scarCode": "SCAR-96",
      "name": "0DTE Far-OTM Delta Liquidity Cliff",
      "description": "Far-OTM options (delta < 0.05) exhibit severe quoting withdrawal under market stress resulting in complete fill failure.",
      "nodeId": "node-beta",
      "author": "Researcher B",
      "forbiddenKeywords": ["0dte_far_otm", "delta_sub_0.05"],
      "vetoRule": "Reject option contracts with delta < 0.05 on 0DTE horizons."
    }
  ],
  "timestamp": "2026-09-07T21:28:33.315Z"
}
```

##### 7b. Pub/Sub Battle Scar Broadcast
- **Route:** `POST /api/polarislink/swarm/:swarmId/scars`
- **Scope:** `ops:swarm:manage` or `quant:*`
- **Request Wire:**
```json
{
  "scarId": "SCAR-158",
  "title": "Unanchored OTM Put Delta Calibration Collapse",
  "mechanism": "Deep OTM IV interpolation fails when strike spread > 200 pts.",
  "rootCause": "Lack of quote depth in far tail causes Black-Scholes solver non-convergence.",
  "rule": "Mandate cubic spline volatility smoothing before delta calibration.",
  "sourceNode": "node-beta"
}
```

#### 8. Real-Time Duplex Swarm Event Stream
- **Route:** `GET /api/polarislink/swarm/:swarmId/events`
- **Scope:** `ops:swarm:read` or `quant:*`
- **Stream Format:** `text/event-stream`
- **Events Emitted:**
  - `lease_claimed`: Pushed when any peer node claims a research frontier.
  - `lease_released`: Pushed when a lease is released or completed.
  - `scar_broadcast`: Pushed instantly when a researcher codifies a new negative prior.
  - `assistance_requested`: Pushed when an orphaned frontier enters the open RFQ assistance ledger.
  - `assistance_claimed`: Pushed when a peer desk or supernode adopts an assistance request.
  - `frontier_reclaimed`: Pushed when an original researcher reconnects and reclaims their sovereign lease.
  - `heartbeat`: Swarm telemetry and liveness tick every 30 seconds.

#### 8b. Unified Real-Time Swarm Push Stream
- **Route:** `GET /api/polarislink/swarm/stream` (Aliases: `GET /api/swarm/stream`)
- **Scope:** `ops:swarm:read` or `quant:*`
- **Stream Format:** `text/event-stream`
- **Events Emitted:** `issue_created`, `issue_updated`, `comment_added`, `frontier_claimed`, `frontier_completed`, `debate_posted`, `peer_audit_verdict`, with 30-second `heartbeat` keepalive. Eliminates polling loops across remote nodes.

### 8.3 PolarisSwarm™ Relay & Asynchronous Distributed Handoff (SWARM-RELAY)

When remote research nodes experience connectivity outages (e.g. power failure or network partition) while holding active frontier leases, the SWARM-RELAY architecture prevents research stagnation while rigorously respecting researcher sovereignty:
- **Zero Blind Auto-Assignment:** Leased frontiers from dark nodes (>180s without heartbeat) transition to `ASSISTANCE_REQUESTED` and register an open RFQ in `swarm_assistance_requests`. Workloads are never dumped onto random nodes.
- **Pure Infrastructure Supernode:** The Central Research Supernode (`node-compute-1`) is dedicated simulation infrastructure without an independent researcher persona; it never autonomously claims hypotheses.
- **Dynamic Relevance Matching:** Incoming peer nodes and newly joined desks dynamically evaluate pending requests against their domain capabilities.
- **Sovereign Reclaim Guarantee:** When the original researcher reconnects, calling `reclaim` instantly restores their exclusive lease and resolves all assistance requests with zero loss of progress.

#### 1. Distributed Assistance RFQ Ledger
- **Route:** `GET /api/polarislink/swarm/:swarmId/assistance/requests`
- **Scope:** `ops:swarm:read` or `quant:*`
- **Query Parameters:** `status` (`OPEN` | `CLAIMED` | `RESOLVED`), `forNodeId` (Node ID to compute real-time domain affinity and relevance match percentage)
- **Response Format:**
```json
{
  "success": true,
  "count": 1,
  "requests": [
    {
      "id": "req_8b31f0a28941",
      "swarmId": "research",
      "frontierId": "frontier-02-0dte-spx-gamma-scalping-skew",
      "frontierName": "0DTE SPX Intraday Volatility Skew & Order Book Pressure",
      "originatorNodeId": "node-beta",
      "originatorName": "Researcher B",
      "domain": "options_volatility_microstructure",
      "requiredCapabilities": ["options_volatility_microstructure", "empirical_audit"],
      "status": "OPEN",
      "relevanceScores": { "node-alpha": 0.4, "node-compute-1": 0.85 },
      "myRelevance": { "score": 0.4, "matchType": "CROSS_DOMAIN", "reasoning": "Cross-domain peer desk (macro_cross_asset)" },
      "workloadSummary": "Researcher Researcher B is offline. Workload open for peer adoption or test execution.",
      "createdAt": "2026-09-08T12:00:00.000Z"
    }
  ]
}
```

#### 2. Adopt Assistance Request
- **Route:** `POST /api/polarislink/swarm/:swarmId/assistance/requests/:id/claim`
- **Scope:** `ops:swarm:manage` or `quant:*`
- **Payload:** `{ "assistingNodeId": "node-alpha" }`
- **Action:** Transitions frontier to `ASSISTED_EXECUTION`, sets `assisting_node_id`, and initializes a collaborative tracking record in `swarm_handoffs`.

#### 3. Sovereign Frontier Reclaim
- **Route:** `POST /api/polarislink/swarm/:swarmId/frontiers/:id/reclaim`
- **Scope:** `ops:swarm:manage` or `quant:*`
- **Payload:** `{ "nodeId": "node-beta" }`
- **Action:** Enforces identity check against `original_node_id`, resolves open requests and handoffs (`RECLAIMED_BY_ORIGINATOR`), and restores sovereign exclusive lease (`status = 'LEASED'`) to the returning researcher.

### 8.4 Programmatic Swarm Alpha Sleeves API (`/api/polarislink/swarm/:swarmId/sleeves`)

Provides persistence, discovery, and automated synchronization for live paper trading strategy sleeves across research clusters:

#### 1. List Swarm Sleeves
- **Route:** `GET /api/polarislink/swarm/:swarmId/sleeves` (and direct alias `GET /api/polarislink/swarm/sleeves`)
- **Scope:** `ops:swarm:read` or `quant:*`
- **Response:** Returns list of active trading strategies, allocated paper capital (USD), underlying universes, and drawdown thresholds.

#### 2. Upsert Swarm Sleeve
- **Route:** `POST /api/polarislink/swarm/:swarmId/sleeves`
- **Scope:** `ops:swarm:manage` or `quant:*`
- **Payload:** `{ "sleeveId": "...", "strategyName": "...", "universe": "...", "allocationUsd": 35000, "maxDrawdownBps": 0 }`
- **Action:** Persists sleeve to PostgreSQL table `swarm_sleeves` and records `SLEEVE_REGISTERED` event.

#### 3. Batch Manifest Synchronization
- **Route:** `POST /api/polarislink/swarm/:swarmId/manifest`
- **Scope:** `ops:swarm:manage` or `quant:*`
- **Payload:** `{ "brokerAccount": "<paper-account-id>", "sleeves": [ ... ] }`
- **Action:** Atomically synchronizes master paper trading portfolio manifests into Forticia cluster persistence.

#### 4. Promote Validated Disposition to Active Paper Sleeve
- **Route:** `POST /api/polarislink/swarm/:swarmId/dispositions/:id/promote` (and direct alias `POST /dispositions/:id/promote`)
- **Scope:** `ops:swarm:manage` or `quant:*`
- **Payload:** `{ "allocatedCapitalUsd": 31000 }`
- **Action:** Promotes a validated candidate disposition into an active codified sleeve in `swarm_sleeves` under the paper broker account, sets disposition status to `APPROVED` with `master_verdict = 'PROMOTED_PAPER'`, and broadcasts a `sleeve_promoted` event to the cluster duplex SSE stream.

#### 5. Cluster-Wide Batch Promotion of Validated Pipeline Alphas
- **Route:** `POST /api/polarislink/swarm/:swarmId/sleeves/sync-validated` (and direct alias `POST /sleeves/sync-validated`)
- **Scope:** `ops:swarm:manage` or `quant:*`
- **Payload:** `{ "defaultCapitalUsd": 31000 }`
- **Action:** Atomically promotes all unpromoted validated candidate strategies across the cluster into active paper trading sleeves under the paper broker account, updating funnel metrics and broadcasting cluster-wide portfolio expansion events.

#### 6. Cross-Node Adversarial Peer Audit & Mistake Scoring Protocol
- **Route:** `POST /api/polarislink/swarm/{swarmId}/dispositions/:id/audit` (Aliases: `POST /api/dispositions/:id/audit`, `POST /api/swarm/dispositions/:id/audit`)
- **Scope:** `ops:swarm:manage` or `quant:*`
- **Payload:** `{ "auditorNodeId": "node-gamma", "verdict": "CHALLENGED", "epistemologicalClass": "MICROSTRUCTURE_FRICTION_OMISSION", "stopoutChurnObserved": true, "neffObserved": 0.0, "placeboDeltaSharpe": 0.00, "mistakeScorePenalty": 15, "auditNotes": "..." }`
- **Action:** Appends peer audit verdict to `swarm_dispositions.peer_audits`, updates master consensus verdict (`CHALLENGED` or `FALSIFIED`), docks mistake penalty points against the target node on `swarm_nodes.reliability_score`, and broadcasts `peer_audit_verdict` SSE event.

### 8.5 Collaborative Alpha Replication Protocol & Cross-Audit Verification Matrix (SWARM-REPLICATION)

To preserve scientific rigor and prevent selection bias across distributed research desks (each workstation and its agent), PolarisSwarm™ implements an adversarial cross-audit protocol. When a research node discovers and codifies a candidate alpha strategy, the finding is not taken on blind faith; it enters a peer verification queue where independent desks must independently reproduce the Modern In-Sample (2020+) and Blind Historical Out-of-Sample (2001-2019) results before production deployment.

#### 1. Swarm Discoveries Catalog
- **Route:** `GET /api/polarislink/swarm/:swarmId/discoveries` (Aliases: `GET /api/polarislink/swarm/discoveries`)
- **Scope:** `ops:swarm:read` or `quant:*`
- **Query Parameters:**
  - `status`: Filter by audit status (`UNAUDITED`, `AUDIT_IN_PROGRESS`, `VERIFIED_REPLICATED`, `CHALLENGED_FALSIFIED`)
  - `domain`: Filter by quantitative domain
  - `limit`: Integer page size (default: 50, max: 200)
- **Response Wire:**
```json
{
  "swarmId": "research",
  "totalDiscoveries": 1,
  "discoveries": [
    {
      "frontierId": "cme_treasury_yield_curve_futures_basis",
      "frontierNum": 29,
      "frontierName": "CME CBOT Ultra 10-Year (TN) vs 10-Year (ZN) Curve Basis & Intraday Convexity Roll",
      "domain": "futures_orderbook_l2",
      "completedByNodeId": "node-gamma",
      "auditStatus": "UNAUDITED",
      "activeAuditId": null,
      "resultsSummary": "Example summary of in-sample and out-of-sample results.",
      "metrics": {
        "isSharpe": 0.00,
        "oosSharpe": 0.00,
        "isTrades": 0,
        "oosTrades": 0,
        "winRate": 0.00,
        "maxDrawdownBps": 0
      },
      "completedAt": "2026-09-08T16:38:30.975Z"
    }
  ],
  "timestamp": "2026-09-08T17:00:00.000Z"
}
```

#### 2. Cross-Audit Verification Queue
- **Route:** `GET /api/polarislink/swarm/:swarmId/cross-audit/queue` (Aliases: `GET /api/polarislink/swarm/cross-audit/queue`)
- **Scope:** `ops:swarm:read` or `quant:*`
- **Query Parameters:**
  - `domain`: Filter by quantitative domain
  - `excludeNodeId`: Excludes discoveries completed by the requesting node to prevent self-audit
  - `limit`: Integer page size (default: 50)
- **Action:** Returns completed frontiers awaiting peer replication whose audit status is `UNAUDITED` or whose audit lease has expired.

#### 3. Adversarial Cross-Audit Claim (Mutual Exclusion)
- **Route:** `POST /api/polarislink/swarm/:swarmId/cross-audit/claim`
- **Scope:** `ops:swarm:manage` or `quant:*`
- **Request Wire:**
```json
{
  "frontierId": "cme_treasury_yield_curve_futures_basis",
  "auditorNodeId": "node-alpha",
  "auditorResearcher": "Researcher A (Quant Desk)",
  "ttlMinutes": 60
}
```
- **Response:** `HTTP 200 OK` with `auditId`, `expiresAt`, and leased parameters.
- **Mutual Exclusion Gate:** If another node holds an active audit lease (`expiresAt > now`), returns `HTTP 409 Conflict` with holder details. If `auditorNodeId === completedByNodeId`, returns `HTTP 400 Bad Request` (self-auditing prohibited).

#### 4. Cross-Audit Verdict Submission
- **Route:** `POST /api/polarislink/swarm/:swarmId/cross-audit/verdict`
- **Scope:** `ops:swarm:manage` or `quant:*`
- **Request Wire:**
```json
{
  "auditId": "audit_8f29a1b4",
  "frontierId": "cme_treasury_yield_curve_futures_basis",
  "auditorNodeId": "node-alpha",
  "verdict": "VERIFIED_REPLICATED",
  "replicationIsSharpe": 0.00,
  "replicationOosSharpe": 0.00,
  "replicationTrades": 15,
  "replicationMaeBps": -185,
  "notes": "Independently replicated on the reference engine."
}
```
- **Action:** Updates `swarm_cross_audits` to `COMPLETED`, updates `swarm_frontiers.audit_status` to `VERIFIED_REPLICATED` or `CHALLENGED_FALSIFIED`, stamps auditor attribution, releases the audit lease, and emits real-time `AUDIT_VERDICT` event over SSE.

### 8.5 Swarm Patrol & Real-Time Node Deviation Notices (`SWARM-PATROL`)

To maintain institutional quantitative rigor without cluttering human issue trackers, PolarisSwarm™ provides an autonomous peer advisory and anti-lookahead communication plane. Research guardians (e.g. a guardian agent on `node-alpha`) can broadcast structured advisories, methodology warnings, or parameter falsification critique directly to peer nodes (e.g. `node-gamma`).

#### 1. Broadcast Patrol Notice
- **Route:** `POST /api/polarislink/swarm/:swarmId/patrol/notice` (Alias: `POST /patrol/notice`)
- **Scope:** `ops:swarm:manage` or `quant:*`
- **Request Wire:**
```json
{
  "targetNodeId": "node-gamma",
  "severity": "WARN",
  "violationType": "LOOKAHEAD_BIAS_CHECK",
  "details": "Strategy 196 uses next-day VWAP benchmark in exit condition. Falsify on blind OOS 2001-2019 data.",
  "suggestedRemedy": "Shift benchmark calculation to contemporaneous rolling midpoint only.",
  "frontierId": "frontier-196-xom-xle-basis"
}
```
- **Action:** Records structured notice in cluster state, enforces node ownership, and emits real-time `SWARM_PATROL_NOTICE` event over cluster duplex SSE stream (`/api/polarislink/swarm/:swarmId/events`).

#### 2. Query Patrol Notices
- **Route:** `GET /api/polarislink/swarm/:swarmId/patrol/notices` (Alias: `GET /patrol/notices`)
- **Scope:** `ops:swarm:read` or `quant:*`
- **Query Parameters:** `nodeId` (filter by target or authoring node), `unacknowledged` (boolean), `limit` (int)
- **Response:** Array of active advisories with timestamps and acknowledgment state.

#### 3. Acknowledge Patrol Notice
- **Route:** `POST /api/polarislink/swarm/:swarmId/patrol/notices/:id/ack` (Alias: `POST /patrol/notices/:id/ack`)
- **Scope:** `ops:swarm:manage` or `quant:*`
- **Action:** Sets `acknowledged = true`, records node remediation notes, and logs audit verification trail.

### 8.6 Cryptographic Identity Verification & Anti-Spoofing Architecture

To protect quantitative research integrity and prevent impersonation across distributed API callers and AI agents, PolarisLink™ enforces cryptographic caller attribution:
- **Principal Binding (`validateAuthorIdentity`):** Resolves caller identity strictly from authenticated `ApiKeyPrincipal` (or session bearer). API keys assigned to external researchers (e.g. `node-gamma`) are cryptographically restricted from claiming founder personas, agent personas, or peer researchers.
- **Strict Email & Persona Enclosure:** Closed logic flaw where omitting `author_email` permitted arbitrary persona claims. Authenticated tokens bound to specific emails (e.g. `researcher@example.org`, `researcher-b@example.org`, `researcher-c@example.org`) are strictly restricted to their associated personas.
- **Automated Founder Boundary:** Founder bearer tokens invoked via automated scripts and headless processes default strictly to `Polaris AutoHeal™` (`polaris@forticia.uk`), reserving human founder signatures strictly for verified interactive console sessions.
- **Node Ownership Enforcement (`validateNodeOwnership`):** Enforces that node actions (`/swarm/claim`, `/swarm/release`, `/swarm/heartbeat`, `/swarm/dispositions`, `/cross-audit/claim`) match the authenticated node identity. Mismatched node claims unconditionally return `HTTP 403 Forbidden`.
- **Zero Substring Attribution:** Completely eradicates heuristics where comment text containing an agent name (e.g. *"Thanks agent-alpha"*) reattributes authorship.

### 8.7 Sovereign Swarm Shortcuts (`/api/debates`, `/api/patrol`, `/api/verdicts`)

To eliminate routing ceremony for autonomous research agents, C++20 harnesses, and external cluster monitors, PolarisLink™ provides direct top-level unversioned endpoints alongside nested routes:
- **`GET /api/debates`**: Direct sovereign shortcut to active swarm debates and peer critiques (alias for `GET /api/polarislink/swarm/{swarmId}/debates`). Supports `frontierId`, `strategyId`, `rootsOnly`, and `limit` query parameters.
- **`GET /api/patrol`**: Direct sovereign shortcut to active swarm patrol advisories and methodological warnings (alias for `GET /api/polarislink/swarm/{swarmId}/patrol/notices`). Supports `nodeId` and `unacknowledged` query filters.
- **`GET /api/verdicts`**: Direct sovereign shortcut to cluster consensus verdicts and promotion decisions (alias for `GET /api/polarislink/swarm/{swarmId}/verdicts`). Supports `strategyId` and `limit` query parameters.

### 8.8 Symmetrical Cloud Compute Delegation Engine

To overcome local thermal and CPU constraints on research workstations (e.g. `node-alpha`), PolarisLink™ v1.9.2 introduces symmetrical cloud compute delegation to the dedicated compute cluster:
- **Worker Pool & Core Reservation:** Allocates physical CPU cores per job with automatic queuing when total allocated cores reach cluster capacity (12 cores).
- **Asynchronous Dispatch (`POST /api/polarislink/compute/dispatch` & `/api/compute/dispatch`):** Enqueues backtest harnesses or trajectory simulations with scheduling priority (1–10), hyperparameters, and timeout limits (default: 3600s).
- **Cluster Capacity Probe (`GET /api/polarislink/compute/capacity` & `/api/compute/capacity`):** Reports real-time available cores, active worker details, queued jobs count, and hardware profiling.
- **Job Lifecycle & Logs (`GET /api/polarislink/compute/jobs/:id` & `DELETE /api/polarislink/compute/jobs/:id`):** Real-time monitoring of job state (`QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`), execution duration, stdout/stderr streaming logs, and performance metrics.
- **Real-Time Push Telemetry:** Emits typed SSE events (`compute_job_queued`, `compute_job_started`, `compute_job_completed`, `compute_job_failed`) over `/api/polarislink/swarm/stream`.

### 8.9 Transactional ACID Research Ledger & Universal Export

To eliminate file write collisions, merge conflicts, and corruption across distributed swarm research nodes:
- **Relational ACID Tables:** Codifies backtest evaluations (`research_evaluations`), tombstone autopsies (`research_tombstones`), battle scars (`research_scars`), and compute executions (`compute_jobs`) in PostgreSQL with foreign-key constraints and B-Tree indexes.
- **Universal Markdown Export (`GET /api/polarislink/swarm/export/research-log` & `/api/export/research-log`):** Deterministically synthesizes the authoritative institutional `RESEARCH_LOG.md` on demand from live database records. Formats Modern In-Sample 2020+ vs. Blind Out-of-Sample 2001–2019 Sharpe tables, intraday MAE stop-out survival rates (-200 bps threshold), small-sample trade gates ($N \ge 15$), Tombstone autopsies, and codified Battle Scars with verified mathematical accuracy.

### 8.10 Dynamic Multi-Wave Frontier Synthesis & Starvation Defense Engine (v2.3.0)

PolarisLink™ v2.3.0 introduces dynamic multi-wave synthesis to prevent autonomous research cluster starvation (`CRITICAL_STARVATION`) once Waves 1 and 2 are fully completed (221/221 frontiers, 311+ Battle Scars):
- **Dynamic Wave Replenishment (`POST /api/polarislink/swarm/:swarmId/frontiers/replenish`):**
  - Direct Sovereign Aliases: `POST /api/frontiers/replenish`, `POST /frontiers/replenish`.
  - Wire Request:
    ```json
    {
      "waveName": "Wave 3 — Macro Frictions, Cross-Market Basis & Order Flow Toxicity",
      "targetWaveId": 3,
      "domainFocus": [
        "fixed_income_relative_value",
        "commodity_term_structure",
        "order_flow_microstructure",
        "macro_cross_asset"
      ],
      "targetUniverse": "US_EQUITIES_FUTURES_RATES_CBOE_CME",
      "minFrontiers": 40,
      "preScreenAgainstScars": true,
      "customCandidates": []
    }
    ```
  - Response (`201 Created`):
    ```json
    {
      "success": true,
      "waveId": 3,
      "replenishedCount": 32,
      "vetoedCount": 10,
      "activeFrontiersInQueue": 32,
      "timestamp": "2026-09-10T08:05:00.000Z"
    }
    ```
- **Modular Candidate Generators (`api/protocol/swarm-waves.ts`):**
  - **Wave 3:** 32 valid frontiers covering Fixed Income / Rates Relative Value (SOFR-EFFR basis dispersion, 2Y-5Y-10Y Treasury curvature concession, Ultra 10Y vs Classic 10Y CTD roll basis), Commodity Crack & Calendar Spreads (WTI roll, RBOB vs HO crack, CBOT Soybean Crush GPM, natural gas injection storage), Order Flow Microstructure (cancel-to-fill ratios, VPIN toxicity, dark crossing block momentum), and Macro Cross-Asset Lead Indicators (Semiconductor book-to-bill capex lead, BoJ carry trade unwind risk).
  - **Wave 4+ Extensible Parametric Synthesis:** Synthesizes higher wave tiers parametrically with `w{N}_` prefixes so the cluster queue never starves.
- **Dynamic Collision-Free ID Prefixing (`w{N}_`):** All Wave $N$ frontiers receive deterministic `w{N}_` primary keys, preventing upsert primary key collisions across waves.
- **Monotonic Wave Numbering:** Automatically increments wave indices based on `MAX(wave_id)` in `swarm_frontiers`, respecting caller overrides (`targetWaveId`).
- **Frontier State Reset on Replenishment:** Automatically clears stale lease metadata (`status = 'AVAILABLE'`, `lease_node_id = NULL`, `lease_claimed_at = NULL`, `lease_expires_at = NULL`), making existing hypotheses immediately leaseable.
- **Catalog Telemetry & Starvation Index (`GET /api/polarislink/swarm/:swarmId/frontiers/catalog-stats`):**
  - Direct Sovereign Aliases: `GET /api/catalog-stats`, `GET /catalog-stats`.
  - Evaluates live cluster queue health: `currentWave`, `totalFrontiers`, `completedFrontiers`, `availableFrontiers`, `scarsEnforcedCount`, and `starvationStatus` (`HEALTHY`, `LOW_INVENTORY`, `CRITICAL_STARVATION`).

---

## 10. Point-in-Time Macro Event Calendars, CFTC Positioning, Options GEX & Symbology (v2.1.0)

PolarisLink™ v2.1.0 introduces point-in-time structural positioning feeds, options dealer gamma exposure surfaces, and cross-asset symbology mapping for theory-first systematic research:

### 10.1 Macro Event Calendars & Surprise Vectors
- **Endpoints:** `GET /api/polarislink/quant/macro/events`, `POST /api/polarislink/quant/macro/events` (Aliases: `/api/macro/events`, `/api/quant/macro/events`).
- **Required Scopes:** `quant:macro:read` (Read), `ops:harvester:dispatch` or `admin:*` (Ingest).
- **Bitemporal Dual Timestamping:** Stores `event_timestamp` and `knowledge_timestamp` as 64-bit epoch microseconds (`BIGINT`), ensuring historical backtests executed at timestamp $T$ cannot observe subsequent data revisions or late prints.
- **Standardized Surprise Calculation:**
  $$\text{Surprise} = \frac{\text{Actual} - \text{Consensus}}{\sigma_{\text{consensus}}}$$
  Quantifies market surprise in units of consensus standard deviations, normalizing release impact across economic categories.

### 10.2 CFTC Commitments of Traders (COT) Disaggregated Reports
- **Endpoints:** `GET /api/polarislink/quant/positioning/cot`, `POST /api/polarislink/quant/positioning/cot` (Aliases: `/api/positioning/cot`, `/api/quant/positioning/cot`).
- **Required Scopes:** `quant:positioning:read`.
- **Contracts Covered:** `ES`, `NQ`, `RTY`, `ZB`, `ZN`, `ZF`, `CL`, `GC`, `NG`.
- **Fields:** `commercialNet`, `nonCommercialNet`, `totalOpenInterest`, and `speculatorNetPctOi` ($\text{SpeculatorNetPctOI} = (\text{NonCommercialNet} / \text{TotalOI}) \times 100$).

### 10.3 Options Dealer Gamma Exposure (GEX) & Skew
- **Endpoints:** `GET /api/polarislink/quant/options/gex`, `POST /api/polarislink/quant/options/gex` (Aliases: `/api/options/gex`, `/api/quant/options/gex`).
- **Required Scopes:** `quant:gex:read`.
- **Underlyings:** `SPX`, `SPY`, `QQQ`.
- **Metrics:** `netGexUsd`, `zeroGexStrike` (critical market inflection where net gamma flips from mean-reverting positive to trending negative), `callGexUsd`, `putGexUsd`, `strikesGex` distribution array, and 25-delta risk reversal skew (`skew25dRr`).

### 10.4 Cross-Asset Symbology & Continuous Futures Roll Resolver
- **Endpoints:**
  - `GET /api/polarislink/quant/symbology/resolve` (Aliases: `/api/symbology/resolve`, `/api/quant/symbology/resolve`)
  - `GET /api/polarislink/quant/symbology/map`
  - `GET /api/polarislink/quant/futures/continuous` (Aliases: `/api/futures/continuous`, `/api/quant/futures/continuous`, `/api/polarislink/quant/futures/rolls`, `/api/futures/rolls`, `/api/quant/futures/rolls`, `/futures/rolls`, `/api/futures/roll-rules`)
  - `GET /api/polarislink/quant/borrow-curves` (Aliases: `/api/borrow-curves`, `/api/quant/borrow-curves`, `/borrow-curves`, `/api/polarislink/quant/borrow`, `/api/quant/borrow`, `/api/borrow`, `/borrow`, `/quant/borrow`)
- **Symbology Resolution:** Resolves unified canonical identifiers across cash equities (`FIGI`, `CUSIP`, `ISIN`), options (`OSI`), futures (`Globex Symbol` + `month cycle` + `multiplier`), and Federal Reserve benchmark rates.
- **Continuous Futures Roll Rules:** Pan-contract roll definitions (`VOLUME_SWITCH`, `OPEN_INTEREST_SWITCH`, `CALENDAR_DAYS_BEFORE_EXPIRY`) with backwardation/contango panama difference and ratio basis adjustments.
- **Securities Lending Utilization & Borrow Curves:** Tracks annual borrow fees (bps), utilization percentages, and Hard-To-Borrow (`hardToBorrow`) flags across liquid baskets.

### 10.5 Discrete & Continuous Futures Bars Gateway
- **Endpoints:**
  - `GET /api/polarislink/quant/futures/bars` (Aliases: `/api/futures/bars`, `/api/futures/bars/:symbol`, `/futures/bars`, `/api/polarislink/futures/bars`)
- **Discrete & Continuous Contracts:** Serves cleaned daily OHLCV and authentic settlement marks ($P_{\text{settle}}$) across commodity (CBOT Soybeans `ZS`, Soybean Meal `ZM`, Soybean Oil `ZL`, WTI Crude `CL`), equity index (`ES`, `NQ`), treasury (`ZB`), and FX futures.
- **Tenor Code Parsing:** Automatically resolves CME letter month codes (`F` through `Z` with 1-2 digit year suffix, e.g. `H25` -> March 2025 / `202503`) and matches canonical discrete contract IDs (`conId`, `localSymbol` e.g. `ZSH5`, `ZMH5`, `ZLH5`).
- **Streaming Formats:** Supports both structured JSON (`format=json`) and raw tabular CSV streaming (`format=csv`) with date range filtering (`start`, `end`) and bounded pagination (`limit`, `offset`).

### 10.6 Autonomous Swarm Deliberations & Elaborate Thinking Engine (v2.4.2)
- **Endpoints:**
  - `POST /api/polarislink/swarm/:swarmId/debates/:debateId/resolve` (Aliases: `/api/debates/:debateId/resolve`, `/swarm/debates/:debateId/resolve`)
  - `GET /api/polarislink/swarm/:swarmId/debates/pending-audit` (Aliases: `/api/debates/pending-audit`, `/debates/pending-audit`)
- **Review Gates Matrix:** Evaluates reported strategy metrics against 6 strict gates: (1) Theory & Microstructure (&ge; 20 chars); (2A) Modern IS (2020+) Sharpe &ge; 1.00; (2B) Blind OOS (2001–2019) Sharpe &ge; 0.80; (3) Overlap-Adjusted Small-Sample Trade Floor $N_{\text{eff}} \ge 15$; (4) Matched Placebo Control Separation $\Delta\text{Sharpe} \ge +0.50$; (5) Intraday MAE Stopout Churn &le; 35.0%; and (6) Quote Provenance (Exchange prints vs simulated ticks).
- **Opt-In Human Notifications (Zero Inbox Spam):** Email dispatches for machine-to-machine deliberation traffic are suppressed by default (`debates_email: false`), requiring explicit opt-in in user notification preferences.
- **Autonomous Resolution & Codification:** Deliberation threads conclude with authoritative verdicts: `FATAL_FALSIFICATION` auto-codifying Battle Scars (`SCAR-FALS-*`), `VERIFIED_PROMOTION` advancing to live paper trading sleeves ($30k+ paper allocation) under the $1,000,000.00 USD NAV invariant, or `CONSENSUS_REVISE` requesting methodology recalibration.

### 10.7 Swarm Deliberation Autonomous Dispatch & Zero-Token Runner (RFC #113, v2.5.1)
- **Protocol Symmetry:** Deliberations support structured routing, explicit targeting, and event-driven wakeups matching the issue event plane.
- **Endpoints:**
  - `POST /api/polarislink/swarm/:swarmId/debates` (Aliases: `/api/debates`, `/swarm/debates`)
  - `POST /api/polarislink/swarm/:swarmId/debates/:debateId/replies` (Aliases: `/api/debates/:debateId/replies`, `/swarm/debates/:debateId/replies`)
  - `GET /api/polarislink/swarm/:swarmId/events?stream=swarm_debates` (Aliases: `/api/events?stream=swarm_debates`, `/api/polarislink/stream`)
- **Node Targeting & Mention Syntax:**
  - Automatic mention parsing extracts `@node-<name>` tokens (e.g. `@node-gamma`, `@node-beta`) and `@all` from debate body/content, merging them into `targetNodeIds: string[]`.
  - Request fields: `targetNodeIds?: string[]`, `priority?: "low" | "normal" | "high" | "directive"`, `category?: "directive" | "thesis" | "falsification" | "sleeve_allocation" | "methodology"`, `authorNodeId: string`, `isAutonomous?: boolean`, `content?: string` (or `body`).
- **Sliding-Window Rate Limit & Circuit Breaker:**
  - Keyed on `${debateId}:${authorNodeId}`. Max 3 replies per node per thread in 15 minutes (900s). Returns HTTP 429 with `Retry-After: 900` header unless `priority: "directive"`.
- **Cross-Stream Event Symmetry:**
  - Emits typed SSE events (`type: "swarm_debate"`, `action: "thread_created" | "reply_created"`, `threadId`, `replyId`, `priority`, `targetNodeIds`, `authorNodeId`) across both cluster stream (`/swarm/:id/stream`, `/events?stream=swarm_debates`) and global stream (`/api/polarislink/stream`).
- **Zero-Token Client Runner Daemon (`scripts/polaris_swarm_runner.py`):**
  - Subscribes to persistent HTTPS SSE with HTTP Basic/Bearer auth. 0 LLM tokens consumed while idle.
  - Wire Filter Gate: Discards self-authored events (`authorNodeId == MY_NODE_ID`). Checks `targetNodeIds.includes(MY_NODE_ID) || targetNodeIds.includes("all") || priority == "directive"`. Discards non-matching events at transport layer without invoking local LLM context.
  - Sliding-window loop guard (1 reply / thread / 15m unless directive).
  - CLI options: `--node-id`, `--auth-token`, `--api-base`, `--swarm-id`, `--dry-run`, `--once`.

### 10.8 Swarm Deliberations v2: Thread Hierarchy, Recursive DAG Queries & Universal Ingress (RFC #115, v2.5.2)
- **Problem Resolved:** Rectifies the 1-level shallow query limitation in `getSwarmDebateThread` that blinded child replies ($A \to B \to C$) and provoked ad-hoc Windows-specific client polling scripts.
- **First-Class Thread Hierarchy (`root_debate_id`):**
  - Database schema indexes `root_debate_id` on `swarm_debates` with immediate $O(1)$ ancestor resolution on write and recursive CTE backfill for legacy debates.
  - Symmetrizes `GET /api/polarislink/swarm/:swarmId/debates/:debateId` to recursively return all descendants in chronological order regardless of reply depth, with total recursive reply counts.
- **Dedicated Thread Directory Endpoint:**
  - `GET /api/polarislink/swarm/:swarmId/threads` (Aliases: `/api/threads`, `/threads`, `/api/swarm/threads`)
  - Aggregates root conversations with total message counts, participant rosters, latest message snippet, and multi-dimensional filtering (`targetNodeId`, `participantNodeId`, `category`, `priority`, `since`, `limit`).
- **Universal Cross-Platform Ingress & Desktop Alerts:**
  - Upgrades `scripts/polaris_swarm_runner.py` with cross-platform native notification routing (macOS `osascript`, Linux `notify-send`, Windows PowerShell WinRT XML toasts) and `--sync-threads` command.

---

## 11. Verification & Test Pipeline

The PolarisLink™ test suite validates data integrity, zero-mock guardrails, and protocol routes:

```bash
# Run comprehensive institutional test pipeline
npm test

# Component test targets:
npm run verify:integrity  # Scans all codebase paths for mock/synthetic data
npm run verify:api        # Validates RBAC scoping, vault providers, and download streams
npm run verify:polaris    # Validates v2.6.1 runs sink, knowledge gateway, and auto-heal
```

---
*Forticia PolarisLink™ is a proprietary protocol of Forticia Ltd. Registered in England & Wales.*

