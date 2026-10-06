#pragma once
/**
 * Forticia PolarisLink™ — C++20 Institutional Client Library (v2.6.1)
 * Single-header, dual-transport C++20 client for the PolarisLink wire protocol.
 *
 * Provides:
 * 1. High-speed programmatic backtest telemetry logging (POST /api/v1/polaris/runs).
 * 2. Institutional knowledge & governance sync (GET /api/v1/polaris/knowledge).
 * 3. Market data bar ingestion into native C++ structures.
 * 4. Autonomous issue reporting & harvester reconciliation.
 *
 * Transport Modes:
 * - Native libcurl (Default when available): In-memory execution, zero subprocesses, zero argv leakage.
 * - Ephemeral Config Fallback: Zero-dependency stdin/mode-0600 config isolation preventing credential exposure in ps/argv.
 *
 * Usage:
 *   #include <polarislink/polarislink.hpp>
 *
 *   polarislink::Client client("fca_live_...");
 *   auto knowledge = client.get_knowledge();
 *
 *   polarislink::BacktestRunMetrics run;
 *   run.strategy_name = "Sample_Volatility_Model";
 *   run.sharpe = 1.0;
 *   run.cagr = 0.38;
 *   run.max_drawdown = 0.075;
 *   run.trades_count = 450;
 *   std::string run_id = client.log_run(run);
 */

#include <string>
#include <vector>
#include <sstream>
#include <iostream>
#include <optional>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include <algorithm>
#include <array>
#include <memory>
#include <unistd.h>
#include <sys/stat.h>

#if __has_include(<curl/curl.h>) && !defined(POLARISLINK_NO_LIBCURL)
#define POLARISLINK_HAS_LIBCURL 1
#include <curl/curl.h>
#endif

namespace polarislink {

inline const std::vector<std::string> RETAIL_PROHIBITED_PROVIDERS = {
    "yfinance", "yahoo", "alphavantage", "finnhub", "polygon_free"
};

inline void enforce_institutional_guardrails(const std::string& provider) {
    std::string lower = provider;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    for (const auto& prohibited : RETAIL_PROHIBITED_PROVIDERS) {
        if (lower.find(prohibited) != std::string::npos) {
            throw std::runtime_error(
                "Forticia Quantitative Governance Violation: Retail provider '" + provider +
                "' is strictly prohibited. Zero Bad Data Mandate requires verified primary vault feeds."
            );
        }
    }
}

struct DailyBar {
    std::string date;
    double open = 0.0;
    double high = 0.0;
    double low = 0.0;
    double close = 0.0;
    double volume = 0.0;
};

struct OptionQuote {
    std::string contract;
    std::string underlying;
    std::string expiration;
    double strike = 0.0;
    std::string right;
    std::string date;
    std::optional<double> bid;
    std::optional<double> ask;
    std::optional<double> mid;
    std::optional<double> spread;
    double volume = 0.0;
    std::optional<double> iv;
    std::optional<double> delta;
    std::optional<double> gamma;
    std::optional<double> theta;
    std::optional<double> vega;
    std::optional<double> underlying_price;
};

struct MarketDepthTick {
    uint64_t ts = 0;
    std::string timestamp_iso;
    std::string venue;
    std::string symbol;
    char side = 'A';
    char action = 'n';
    std::string action_desc;
    double price = 0.0;
    double size = 0.0;
};

struct MarketDepthSummary {
    std::string symbol;
    std::string date;
    std::string venue = "CME";
    int total_ticks = 0;
    std::optional<double> best_bid;
    std::optional<double> best_ask;
    std::optional<double> spread;
    std::optional<double> spread_bps;
    std::vector<MarketDepthTick> ticks;
};

struct CorporateBuybackHistoricalStats {
    int evaluated_events = 0;
    double average_alpha_bps = 0.0;
    double excess_over_placebo_bps = 0.0;
    double win_rate_pct = 0.0;
    double profit_factor = 0.0;
};

struct CorporateBuybackProgram {
    std::string symbol;
    std::string company_name;
    double authorized_billions = 0.0;
    double repurchase_yield_pct = 0.0;
    std::string last_earnings_date;
    std::string blackout_lift_date;
    std::string execution_window_end;
    std::string status;
    int days_until_lift = 0;
    int days_remaining_in_window = 0;
    CorporateBuybackHistoricalStats historical_stats;
};

struct CorporateBuybackResponse {
    std::string as_of_date;
    int active_programs_count = 0;
    int current_window_active_count = 0;
    std::string rule_of_law;
    std::string universe;
    std::string data_quality;
    bool quotes_verified = true;
    std::vector<CorporateBuybackProgram> programs;
};

struct BacktestRunMetrics {
    std::string strategy_name;
    std::string workspace_id = "default";
    std::string universe = "us_equities_daily";
    std::string start_date;
    std::string end_date;
    std::optional<double> sharpe;
    std::optional<double> cagr;
    std::optional<double> max_drawdown;
    int trades_count = 0;
    std::optional<double> win_rate;
    std::string git_commit;
    std::string provenance_hash;
    std::string metrics_json = "{}";
};

struct TelemetryStatus {
    std::string status;
    std::string gateway;
    std::string node;
    std::string protocol_version;
    int uptime_seconds = 0;
    int runs_recorded = 0;
};

struct GovernanceKnowledge {
    bool zero_bad_data_enforced = true;
    std::vector<std::string> prohibited_vendors;
    std::vector<std::string> available_universes;
};

class Client {
public:
    explicit Client(std::string api_key = "", std::string base_url = "") {
        if (api_key.empty()) {
            const char* env_key = std::getenv("FORTICIA_API_KEY");
            m_api_key = env_key ? env_key : "";
        } else {
            m_api_key = std::move(api_key);
        }

        if (base_url.empty()) {
            const char* env_url = std::getenv("FORTICIA_API_URL");
            m_base_url = env_url ? env_url : "https://forticia.uk";
        } else {
            m_base_url = std::move(base_url);
        }

        // Trim trailing slash
        while (!m_base_url.empty() && m_base_url.back() == '/') {
            m_base_url.pop_back();
        }
    }

    TelemetryStatus get_telemetry() {
        std::string raw = http_request("GET", "/api/polarislink/telemetry");
        TelemetryStatus t;
        t.status = extract_json_string(raw, "status");
        t.gateway = extract_json_string(raw, "gateway");
        t.node = extract_json_string(raw, "node");
        t.protocol_version = extract_json_string(raw, "protocolVersion");
        return t;
    }

    GovernanceKnowledge get_knowledge() {
        std::string raw = http_request("GET", "/api/polarislink/knowledge");
        GovernanceKnowledge k;
        k.zero_bad_data_enforced = (raw.find("\"zeroBadDataMandate\"") != std::string::npos);
        k.prohibited_vendors = RETAIL_PROHIBITED_PROVIDERS;
        return k;
    }

    std::string log_run(const BacktestRunMetrics& r) {
        if (r.strategy_name.empty()) {
            throw std::invalid_argument("Strategy name is required to log backtest run.");
        }

        std::ostringstream json;
        json << "{"
             << "\"strategyName\":\"" << escape_json(r.strategy_name) << "\","
             << "\"workspaceId\":\"" << escape_json(r.workspace_id) << "\","
             << "\"universe\":\"" << escape_json(r.universe) << "\","
             << "\"gitCommit\":\"" << escape_json(r.git_commit) << "\","
             << "\"provenanceHash\":\"" << escape_json(r.provenance_hash) << "\","
             << "\"tradesCount\":" << r.trades_count;

        if (!r.start_date.empty()) json << ",\"startDate\":\"" << escape_json(r.start_date) << "\"";
        if (!r.end_date.empty()) json << ",\"endDate\":\"" << escape_json(r.end_date) << "\"";
        if (r.sharpe.has_value()) json << ",\"sharpe\":" << *r.sharpe;
        if (r.cagr.has_value()) json << ",\"cagr\":" << *r.cagr;
        if (r.max_drawdown.has_value()) json << ",\"maxDrawdown\":" << *r.max_drawdown;
        if (r.win_rate.has_value()) json << ",\"winRate\":" << *r.win_rate;

        json << "}";

        std::string response = http_request("POST", "/api/polarislink/runs", json.str());
        return extract_json_string(response, "id");
    }

    bool report_issue(const std::string& title, const std::string& description, const std::string& category = "Data Gap", const std::string& priority = "Normal", const std::string& workspace = "default") {
        std::ostringstream json;
        json << "{"
             << "\"title\":\"" << escape_json(title) << "\","
             << "\"description\":\"" << escape_json(description) << "\","
             << "\"category\":\"" << escape_json(category) << "\","
             << "\"priority\":\"" << escape_json(priority) << "\","
             << "\"workspace\":\"" << escape_json(workspace) << "\""
             << "}";

        std::string response = http_request("POST", "/api/polarislink/issues", json.str());
        return response.find("\"success\":true") != std::string::npos;
    }

    std::vector<DailyBar> get_bars(const std::string& symbol, const std::string& universe = "us_equities_daily", const std::string& start = "", const std::string& end = "", int limit = 10000) {
        std::string path = "/api/polarislink/quant/bars?symbol=" + symbol + "&universe=" + universe + "&format=csv&limit=" + std::to_string(limit);
        if (!start.empty()) path += "&start=" + start;
        if (!end.empty()) path += "&end=" + end;

        std::string raw = http_request("GET", path);
        std::vector<DailyBar> bars;
        std::istringstream stream(raw);
        std::string line;
        bool is_header = true;

        while (std::getline(stream, line)) {
            while (!line.empty() && (line.back() == '\r' || line.back() == ' ')) line.pop_back();
            if (line.empty()) continue;
            if (is_header) {
                is_header = false;
                continue;
            }
            auto cols = split_csv_line(line);
            if (cols.size() >= 6) {
                DailyBar b;
                b.date = cols[0];
                b.open = safe_stod(cols[1]);
                b.high = safe_stod(cols[2]);
                b.low = safe_stod(cols[3]);
                b.close = safe_stod(cols[4]);
                b.volume = safe_stod(cols[5]);
                bars.push_back(b);
            }
        }
        return bars;
    }

    std::vector<OptionQuote> get_options_surface(const std::string& symbol = "SPX") {
        std::string path = "/api/polarislink/quant/options/surface?symbol=" + symbol + "&format=csv";
        std::string raw = http_request("GET", path);
        std::vector<OptionQuote> quotes;
        std::istringstream stream(raw);
        std::string line;
        bool is_header = true;

        while (std::getline(stream, line)) {
            while (!line.empty() && (line.back() == '\r' || line.back() == ' ')) line.pop_back();
            if (line.empty()) continue;
            if (is_header) {
                is_header = false;
                continue;
            }
            auto cols = split_csv_line(line);
            if (cols.size() >= 10) {
                OptionQuote q;
                q.contract = cols[0];
                q.underlying = cols[1];
                q.expiration = cols[2];
                q.strike = safe_stod(cols[3]);
                q.right = cols[4];
                if (!cols[5].empty()) q.bid = safe_stod(cols[5]);
                if (!cols[6].empty()) q.ask = safe_stod(cols[6]);
                if (!cols[7].empty()) q.mid = safe_stod(cols[7]);
                if (!cols[8].empty()) q.spread = safe_stod(cols[8]);
                if (cols.size() > 10 && !cols[10].empty()) q.iv = safe_stod(cols[10]);
                if (cols.size() > 11 && !cols[11].empty()) q.delta = safe_stod(cols[11]);
                if (cols.size() > 12 && !cols[12].empty()) q.gamma = safe_stod(cols[12]);
                if (cols.size() > 13 && !cols[13].empty()) q.vega = safe_stod(cols[13]);
                if (cols.size() > 14 && !cols[14].empty()) q.theta = safe_stod(cols[14]);
                if (cols.size() > 15 && !cols[15].empty()) q.volume = safe_stod(cols[15]);
                quotes.push_back(q);
            }
        }
        return quotes;
    }

    std::vector<OptionQuote> get_options_history(const std::string& symbol = "SPX", const std::string& contract = "", const std::string& expiration = "", const std::string& start = "", const std::string& end = "", int limit = 10000) {
        std::string path = "/api/polarislink/quant/options/history?symbol=" + symbol + "&format=csv&limit=" + std::to_string(limit);
        if (!contract.empty()) path += "&contract=" + contract;
        if (!expiration.empty()) path += "&expiration=" + expiration;
        if (!start.empty()) path += "&start=" + start;
        if (!end.empty()) path += "&end=" + end;

        std::string raw = http_request("GET", path);
        std::vector<OptionQuote> quotes;
        std::istringstream stream(raw);
        std::string line;
        bool is_header = true;

        while (std::getline(stream, line)) {
            while (!line.empty() && (line.back() == '\r' || line.back() == ' ')) line.pop_back();
            if (line.empty()) continue;
            if (is_header) {
                is_header = false;
                continue;
            }
            auto cols = split_csv_line(line);
            if (cols.size() >= 10) {
                OptionQuote q;
                q.contract = cols[0];
                q.date = cols[1];
                q.underlying = cols[2];
                q.expiration = cols[3];
                q.strike = safe_stod(cols[4]);
                q.right = cols[5];
                if (!cols[6].empty()) q.bid = safe_stod(cols[6]);
                if (!cols[7].empty()) q.ask = safe_stod(cols[7]);
                if (!cols[8].empty()) q.mid = safe_stod(cols[8]);
                if (!cols[9].empty()) q.spread = safe_stod(cols[9]);
                if (cols.size() > 10 && !cols[10].empty()) q.volume = safe_stod(cols[10]);
                if (cols.size() > 11 && !cols[11].empty()) q.iv = safe_stod(cols[11]);
                if (cols.size() > 12 && !cols[12].empty()) q.delta = safe_stod(cols[12]);
                if (cols.size() > 13 && !cols[13].empty()) q.gamma = safe_stod(cols[13]);
                if (cols.size() > 14 && !cols[14].empty()) q.vega = safe_stod(cols[14]);
                if (cols.size() > 15 && !cols[15].empty()) q.theta = safe_stod(cols[15]);
                if (cols.size() > 16 && !cols[16].empty()) q.underlying_price = safe_stod(cols[16]);
                quotes.push_back(q);
            }
        }
        return quotes;
    }

    std::vector<MarketDepthTick> get_market_depth(const std::string& symbol, const std::string& date = "", int limit = 500) {
        std::string path = "/api/polarislink/quant/depth?symbol=" + symbol + "&format=csv&limit=" + std::to_string(limit);
        if (!date.empty()) path += "&date=" + date;

        std::string raw = http_request("GET", path);
        std::vector<MarketDepthTick> ticks;
        std::istringstream stream(raw);
        std::string line;
        bool is_header = true;

        while (std::getline(stream, line)) {
            while (!line.empty() && (line.back() == '\r' || line.back() == ' ')) line.pop_back();
            if (line.empty()) continue;
            if (is_header) {
                is_header = false;
                continue;
            }
            auto cols = split_csv_line(line);
            if (cols.size() >= 9) {
                MarketDepthTick t;
                try { t.ts = std::stoull(cols[0]); } catch (...) {}
                t.timestamp_iso = cols[1];
                t.venue = cols[2];
                t.symbol = cols[3];
                t.side = cols[4].empty() ? 'A' : cols[4][0];
                t.action = cols[5].empty() ? 'n' : cols[5][0];
                t.action_desc = cols[6];
                t.price = safe_stod(cols[7]);
                t.size = safe_stod(cols[8]);
                ticks.push_back(t);
            }
        }
        return ticks;
    }

    /**
     * @brief Fetch SEC Rule 10b-18 post-blackout corporate share repurchase schedule and empirical alpha.
     */
    CorporateBuybackResponse get_buybacks(const std::string& symbol = "", const std::string& status = "") {
        std::string path = "/api/polarislink/quant/buybacks?format=csv";
        if (!symbol.empty()) path += "&symbol=" + symbol;
        if (!status.empty()) path += "&status=" + status;

        std::string csv_data = http_request("GET", path);
        std::istringstream stream(csv_data);
        std::string line;
        CorporateBuybackResponse response;
        response.rule_of_law = "SEC Rule 10b-18 Safe Harbor (17 CFR § 240.10b-18)";
        response.universe = "sp100_buyback_leaders";
        response.data_quality = "institutional_catalog_verified";
        response.quotes_verified = true;

        bool header = true;
        while (std::getline(stream, line)) {
            if (line.empty()) continue;
            if (header) {
                header = false;
                continue;
            }
            auto cols = split_csv_line(line);
            if (cols.size() >= 15) {
                CorporateBuybackProgram prog;
                prog.symbol = cols[0];
                prog.company_name = cols[1];
                if (prog.company_name.size() >= 2 && prog.company_name.front() == '"' && prog.company_name.back() == '"') {
                    prog.company_name = prog.company_name.substr(1, prog.company_name.size() - 2);
                }
                prog.authorized_billions = safe_stod(cols[2]);
                prog.repurchase_yield_pct = safe_stod(cols[3]);
                prog.last_earnings_date = cols[4];
                prog.blackout_lift_date = cols[5];
                prog.execution_window_end = cols[6];
                prog.status = cols[7];
                try { prog.days_until_lift = std::stoi(cols[8]); } catch (...) {}
                try { prog.days_remaining_in_window = std::stoi(cols[9]); } catch (...) {}
                try { prog.historical_stats.evaluated_events = std::stoi(cols[10]); } catch (...) {}
                prog.historical_stats.average_alpha_bps = safe_stod(cols[11]);
                prog.historical_stats.excess_over_placebo_bps = safe_stod(cols[12]);
                prog.historical_stats.win_rate_pct = safe_stod(cols[13]);
                prog.historical_stats.profit_factor = safe_stod(cols[14]);

                if (prog.status == "active_window") response.current_window_active_count++;
                response.programs.push_back(prog);
            }
        }
        response.active_programs_count = static_cast<int>(response.programs.size());
        return response;
    }

    // =========================================================================
    // POLARISSWARM™: MULTI-CLUSTER QUANT RESEARCH SWARM CONTROL PLANE
    // =========================================================================

    struct SwarmLeaseResult {
        std::string status;
        std::string frontier_id;
        std::string node_id;
        std::string expires_at;
        int ttl_seconds = 0;
        bool is_conflict = false;
        std::string held_by;
        int remaining_seconds = 0;
    };

    SwarmLeaseResult claim_lease(
        const std::string& node_id,
        const std::string& frontier_id,
        int ttl_seconds = 7200,
        const std::string& swarm_id = "default"
    ) {
        std::ostringstream json;
        json << "{"
             << "\"nodeId\":\"" << escape_json(node_id) << "\","
             << "\"frontierId\":\"" << escape_json(frontier_id) << "\","
             << "\"ttlSeconds\":" << ttl_seconds
             << "}";

        std::string response = http_request("POST", "/api/polarislink/swarm/" + swarm_id + "/leases/claim", json.str());
        SwarmLeaseResult res;
        res.status = extract_json_string(response, "status");
        res.frontier_id = extract_json_string(response, "frontierId");
        res.node_id = extract_json_string(response, "nodeId");
        res.expires_at = extract_json_string(response, "expiresAt");
        if (response.find("409") != std::string::npos || res.status.empty()) {
            res.is_conflict = true;
            res.held_by = extract_json_string(response, "heldBy");
        }
        return res;
    }

    bool release_lease(
        const std::string& node_id,
        const std::string& frontier_id,
        bool completed = false,
        const std::string& summary = "",
        const std::string& swarm_id = "default"
    ) {
        std::ostringstream json;
        json << "{"
             << "\"nodeId\":\"" << escape_json(node_id) << "\","
             << "\"frontierId\":\"" << escape_json(frontier_id) << "\","
             << "\"completed\":" << (completed ? "true" : "false");
        if (!summary.empty()) {
            json << ",\"summary\":\"" << escape_json(summary) << "\"";
        }
        json << "}";

        std::string response = http_request("POST", "/api/polarislink/swarm/" + swarm_id + "/leases/release", json.str());
        return (response.find("\"status\":\"released\"") != std::string::npos);
    }

    bool send_heartbeat(
        const std::string& node_id,
        const std::string& swarm_id = "default",
        const std::string& status = "",
        const std::string& workload_summary = "",
        const std::string& cpu_load = "",
        const std::string& active_hypothesis = ""
    ) {
        std::ostringstream json;
        json << "{\"nodeId\":\"" << escape_json(node_id) << "\"";
        if (!status.empty()) json << ",\"status\":\"" << escape_json(status) << "\"";
        if (!workload_summary.empty()) json << ",\"workloadSummary\":\"" << escape_json(workload_summary) << "\"";
        if (!cpu_load.empty()) json << ",\"cpuLoad\":\"" << escape_json(cpu_load) << "\"";
        if (!active_hypothesis.empty()) json << ",\"activeHypothesis\":\"" << escape_json(active_hypothesis) << "\"";
        json << "}";
        std::string response = http_request("POST", "/api/polarislink/swarm/" + swarm_id + "/heartbeat", json.str());
        return (response.find("\"acknowledged\":true") != std::string::npos || response.find("\"status\":") != std::string::npos);
    }

    bool broadcast_scar(
        const std::string& scar_id,
        const std::string& title,
        const std::string& mechanism,
        const std::string& root_cause,
        const std::string& rule,
        const std::string& source_node = "",
        const std::string& swarm_id = "default"
    ) {
        std::ostringstream json;
        json << "{"
             << "\"scarId\":\"" << escape_json(scar_id) << "\","
             << "\"title\":\"" << escape_json(title) << "\","
             << "\"mechanism\":\"" << escape_json(mechanism) << "\","
             << "\"rootCause\":\"" << escape_json(root_cause) << "\","
             << "\"rule\":\"" << escape_json(rule) << "\"";
        if (!source_node.empty()) {
            json << ",\"sourceNode\":\"" << escape_json(source_node) << "\"";
        }
        json << "}";

        std::string response = http_request("POST", "/api/polarislink/swarm/" + swarm_id + "/scars", json.str());
        return (response.find("\"status\":\"broadcasted\"") != std::string::npos);
    }

    std::string get_swarm_status(const std::string& swarm_id = "default") {
        return http_request("GET", "/api/polarislink/swarm/" + swarm_id + "/status");
    }

    std::string replenish_frontier_wave(
        const std::string& wave_name = "Wave 2 — Cross-Asset & Volatility Surface Frontiers",
        const std::string& target_universe = "US_EQUITIES_SP500_OPTIONS_CBOE_CME",
        int min_frontiers = 50,
        bool pre_screen_against_scars = true,
        const std::string& swarm_id = "default"
    ) {
        std::ostringstream json;
        json << "{"
             << "\"waveName\":\"" << escape_json(wave_name) << "\","
             << "\"targetUniverse\":\"" << escape_json(target_universe) << "\","
             << "\"minFrontiers\":" << min_frontiers << ","
             << "\"preScreenAgainstScars\":" << (pre_screen_against_scars ? "true" : "false")
             << "}";
        return http_request("POST", "/api/polarislink/swarm/" + swarm_id + "/frontiers/replenish", json.str());
    }

    std::string batch_register_frontiers(
        const std::string& frontiers_json_array,
        bool pre_screen_against_scars = true,
        const std::string& swarm_id = "default"
    ) {
        std::ostringstream json;
        json << "{"
             << "\"frontiers\":" << frontiers_json_array << ","
             << "\"preScreenAgainstScars\":" << (pre_screen_against_scars ? "true" : "false")
             << "}";
        return http_request("POST", "/api/polarislink/swarm/" + swarm_id + "/frontiers/batch", json.str());
    }

    std::string get_frontier_catalog_stats(const std::string& swarm_id = "default") {
        return http_request("GET", "/api/polarislink/swarm/" + swarm_id + "/frontiers/catalog-stats");
    }

    std::string list_frontier_waves(const std::string& swarm_id = "default") {
        return http_request("GET", "/api/polarislink/swarm/" + swarm_id + "/waves");
    }

    std::string get_swarm_leases(const std::string& swarm_id = "default") {
        return http_request("GET", "/api/polarislink/swarm/" + swarm_id + "/leases");
    }

    std::string list_swarm_discoveries(const std::string& status = "", const std::string& domain = "", int limit = 50, const std::string& swarm_id = "default") {
        std::string path = "/api/polarislink/swarm/" + swarm_id + "/discoveries?limit=" + std::to_string(limit);
        if (!status.empty()) path += "&status=" + status;
        if (!domain.empty()) path += "&domain=" + domain;
        return http_request("GET", path);
    }

    std::string get_spec(const std::string& format = "json") {
        std::string path = "/api/spec";
        if (format == "markdown" || format == "md") {
            path += "?format=markdown";
        }
        return http_request("GET", path);
    }

    std::string get_changelog(const std::string& format = "json") {
        std::string path = "/api/changelog";
        if (format == "markdown" || format == "md") {
            path += "?format=markdown";
        }
        return http_request("GET", path);
    }

    std::string get_reports(const std::string& report_type = "") {
        std::string path = "/api/polarislink/reports";
        if (!report_type.empty()) {
            path += "?type=" + report_type;
        }
        return http_request("GET", path);
    }

    std::string get_notifications() {
        return http_request("GET", "/api/polarislink/notifications");
    }

    std::string update_notifications(const std::string& json_payload) {
        return http_request("PUT", "/api/polarislink/notifications", json_payload);
    }

    std::string get_cross_audit_queue(const std::string& domain = "", const std::string& exclude_node_id = "", int limit = 50, const std::string& swarm_id = "default") {
        std::string path = "/api/polarislink/swarm/" + swarm_id + "/cross-audit/queue?limit=" + std::to_string(limit);
        if (!domain.empty()) path += "&domain=" + domain;
        if (!exclude_node_id.empty()) path += "&excludeNodeId=" + exclude_node_id;
        return http_request("GET", path);
    }

    std::string get_audits_queue(const std::string& domain = "", const std::string& exclude_node_id = "", int limit = 50, const std::string& swarm_id = "default") {
        std::string path = "/api/polarislink/swarm/" + swarm_id + "/audits?limit=" + std::to_string(limit);
        if (!domain.empty()) path += "&domain=" + domain;
        if (!exclude_node_id.empty()) path += "&excludeNodeId=" + exclude_node_id;
        return http_request("GET", path);
    }

    // Quantitative Portfolio Manifest & Summary (v2.2.4 & v2.3.0)
    std::string get_portfolio_manifest(const std::string& swarm_id = "default") {
        return http_request("GET", "/quant/manifest?swarm=" + swarm_id);
    }

    std::string sync_portfolio_manifest(const std::string& manifest_json, const std::string& mode = "replace", const std::string& swarm_id = "default") {
        return http_request("POST", "/quant/manifest/sync?swarm=" + swarm_id + "&mode=" + mode, manifest_json);
    }

    std::string get_quant_summary(const std::string& swarm_id = "default") {
        return http_request("GET", "/quant/summary?swarm=" + swarm_id);
    }

    std::string get_borrow_curves(const std::string& symbol = "") {
        std::string path = "/quant/borrow";
        if (!symbol.empty()) path += "?symbol=" + symbol;
        return http_request("GET", path);
    }

    std::string submit_cross_audit_verdict(const std::string& disposition_id, const std::string& verdict_json) {
        return http_request("POST", "/api/dispositions/" + disposition_id + "/audit", verdict_json);
    }

    std::string replenish_frontier_waves(int count = 50, const std::string& wave_id = "", const std::string& swarm_id = "default") {
        std::string payload = "{\"minFrontiers\":" + std::to_string(count) + ",\"preScreenAgainstScars\":true";
        if (!wave_id.empty()) {
            payload += ",\"waveName\":\"" + wave_id + "\"";
        }
        payload += "}";
        return http_request("POST", "/api/polarislink/swarm/" + swarm_id + "/frontiers/replenish", payload);
    }

    std::string batch_register_frontiers(const std::string& frontiers_json, const std::string& swarm_id = "default") {
        std::string payload = "{\"frontiers\":" + frontiers_json + ",\"preScreenAgainstScars\":true}";
        return http_request("POST", "/api/polarislink/swarm/" + swarm_id + "/frontiers/batch", payload);
    }

    std::string orthogonalize_alpha(const std::string& payload_json, const std::string& swarm_id = "default") {
        return http_request("POST", "/api/polarislink/swarm/" + swarm_id + "/orthogonalize", payload_json);
    }

    std::string claim_cross_audit(
        const std::string& frontier_id,
        const std::string& auditor_node_id,
        const std::string& auditor_researcher = "",
        int ttl_minutes = 60,
        const std::string& swarm_id = "default"
    ) {
        std::ostringstream json;
        json << "{"
             << "\"frontierId\":\"" << escape_json(frontier_id) << "\","
             << "\"auditorNodeId\":\"" << escape_json(auditor_node_id) << "\","
             << "\"ttlMinutes\":" << ttl_minutes;
        if (!auditor_researcher.empty()) {
            json << ",\"auditorResearcher\":\"" << escape_json(auditor_researcher) << "\"";
        }
        json << "}";
        return http_request("POST", "/api/polarislink/swarm/" + swarm_id + "/cross-audit/claim", json.str());
    }

    std::string submit_cross_audit_verdict(
        const std::string& audit_id,
        const std::string& frontier_id,
        const std::string& auditor_node_id,
        const std::string& verdict,
        double is_sharpe = 0.0,
        double oos_sharpe = 0.0,
        int trades = 0,
        double mae_bps = 0.0,
        const std::string& notes = "",
        const std::string& swarm_id = "default"
    ) {
        std::ostringstream json;
        json << "{"
             << "\"auditId\":\"" << escape_json(audit_id) << "\","
             << "\"frontierId\":\"" << escape_json(frontier_id) << "\","
             << "\"auditorNodeId\":\"" << escape_json(auditor_node_id) << "\","
             << "\"verdict\":\"" << escape_json(verdict) << "\","
             << "\"replicationIsSharpe\":" << is_sharpe << ","
             << "\"replicationOosSharpe\":" << oos_sharpe << ","
             << "\"replicationTrades\":" << trades << ","
             << "\"replicationMaeBps\":" << mae_bps;
        if (!notes.empty()) {
            json << ",\"notes\":\"" << escape_json(notes) << "\"";
        }
        json << "}";
        return http_request("POST", "/api/polarislink/swarm/" + swarm_id + "/cross-audit/verdict", json.str());
    }

    // =========================================================================
    // INSTITUTIONAL ALPHA DESK & THE DARK ENGINE (v2.0 C++ Methods)
    // =========================================================================

    std::string submit_execution_intent(const std::string& json_payload) {
        return http_request("POST", "/api/polarislink/execution/intents", json_payload);
    }

    std::string get_crossing_book() {
        return http_request("GET", "/api/polarislink/execution/crossing");
    }

    std::string get_fills(const std::string& symbol = "", int limit = 100) {
        std::string path = "/api/polarislink/execution/fills?limit=" + std::to_string(limit);
        if (!symbol.empty()) {
            path += "&symbol=" + symbol;
        }
        return http_request("GET", path);
    }

    std::string get_tca(const std::string& fill_id) {
        return http_request("GET", "/api/polarislink/execution/tca/" + fill_id);
    }

    std::string get_locates(const std::string& symbol = "") {
        std::string path = "/api/polarislink/risk/locates";
        if (!symbol.empty()) {
            path += "?symbol=" + symbol;
        }
        return http_request("GET", path);
    }

    std::string get_risk_limits() {
        return http_request("GET", "/api/polarislink/risk/limits");
    }

    std::string get_features_catalog(const std::string& domain = "") {
        std::string path = "/api/polarislink/features/catalog";
        if (!domain.empty()) {
            path += "?category=" + domain;
        }
        return http_request("GET", path);
    }

    std::string get_feature_series(const std::string& feature_id, const std::string& symbol = "SPY", int limit = 1000) {
        std::string path = "/api/polarislink/features/series?featureId=" + feature_id + "&symbol=" + symbol + "&limit=" + std::to_string(limit);
        return http_request("GET", path);
    }

    std::string orthogonalize_alpha(
        const std::string& challenger_id,
        const std::vector<double>& challenger_vector,
        const std::string& incumbent_id,
        const std::vector<double>& incumbent_vector,
        double threshold_ir = 1.0,
        const std::string& swarm_id = "default"
    ) {
        std::ostringstream json;
        json << "{"
             << "\"challengerStrategyId\":\"" << escape_json(challenger_id) << "\","
             << "\"challengerVector\":[";
        for (size_t i = 0; i < challenger_vector.size(); ++i) {
            if (i > 0) json << ",";
            json << challenger_vector[i];
        }
        json << "],"
             << "\"incumbentStrategyId\":\"" << escape_json(incumbent_id) << "\","
             << "\"incumbentVector\":[";
        for (size_t i = 0; i < incumbent_vector.size(); ++i) {
            if (i > 0) json << ",";
            json << incumbent_vector[i];
        }
        json << "],"
             << "\"thresholdIr\":" << threshold_ir
             << "}";
        return http_request("POST", "/api/polarislink/swarm/" + swarm_id + "/orthogonalize", json.str());
    }

    std::string get_impact_surface(const std::string& universe = "") {
        std::string path = "/api/polarislink/quant/impact-surface";
        if (!universe.empty()) {
            path += "?universe=" + universe;
        }
        return http_request("GET", path);
    }

    std::string get_macro_events(const std::string& event_name = "", const std::string& category = "", int64_t as_of_knowledge = -1) {
        std::string path = "/api/polarislink/quant/macro/events?";
        if (!event_name.empty()) path += "eventName=" + event_name + "&";
        if (!category.empty()) path += "category=" + category + "&";
        if (as_of_knowledge >= 0) path += "asOfKnowledge=" + std::to_string(as_of_knowledge) + "&";
        if (path.back() == '?' || path.back() == '&') path.pop_back();
        return http_request("GET", path);
    }

    std::string get_cftc_positioning(const std::string& contract = "", int64_t as_of_knowledge = -1) {
        std::string path = "/api/polarislink/quant/positioning/cot?";
        if (!contract.empty()) path += "contract=" + contract + "&";
        if (as_of_knowledge >= 0) path += "asOfKnowledge=" + std::to_string(as_of_knowledge) + "&";
        if (path.back() == '?' || path.back() == '&') path.pop_back();
        return http_request("GET", path);
    }

    std::string get_options_gex(const std::string& symbol = "SPX", const std::string& as_of_date = "", int64_t as_of_knowledge = -1) {
        std::string path = "/api/polarislink/quant/options/gex?symbol=" + symbol;
        if (!as_of_date.empty()) path += "&asOfDate=" + as_of_date;
        if (as_of_knowledge >= 0) path += "&asOfKnowledge=" + std::to_string(as_of_knowledge);
        return http_request("GET", path);
    }

    std::string resolve_symbology(const std::string& ticker = "", const std::string& canonical_id = "") {
        std::string path = "/api/polarislink/quant/symbology/resolve?";
        if (!ticker.empty()) path += "ticker=" + ticker + "&";
        if (!canonical_id.empty()) path += "canonicalId=" + canonical_id + "&";
        if (path.back() == '?' || path.back() == '&') path.pop_back();
        return http_request("GET", path);
    }

    std::string get_continuous_futures(const std::string& contract_root = "") {
        std::string path = "/api/polarislink/quant/futures/continuous";
        if (!contract_root.empty()) path += "?root=" + contract_root;
        return http_request("GET", path);
    }

    std::string get_discrete_futures_contracts(const std::string& contracts = "", const std::string& tenor = "") {
        std::string path = "/api/polarislink/futures/contracts?";
        if (!contracts.empty()) path += "contracts=" + contracts + "&";
        if (!tenor.empty()) path += "tenor=" + tenor + "&";
        if (path.back() == '?' || path.back() == '&') path.pop_back();
        return http_request("GET", path);
    }

    std::string get_futures_bars(const std::string& symbol = "", const std::string& tenor = "", const std::string& start = "", const std::string& end = "", int limit = 1000, const std::string& format = "json") {
        std::string path = "/api/polarislink/quant/futures/bars?";
        if (!symbol.empty()) path += "symbol=" + symbol + "&";
        if (!tenor.empty()) path += "tenor=" + tenor + "&";
        if (!start.empty()) path += "start=" + start + "&";
        if (!end.empty()) path += "end=" + end + "&";
        path += "limit=" + std::to_string(limit) + "&format=" + format;
        return http_request("GET", path);
    }

    std::string get_borrow_fee_curves(const std::string& symbol = "", const std::string& as_of_date = "") {
        std::string path = "/api/polarislink/quant/borrow-curves?";
        if (!symbol.empty()) path += "symbol=" + symbol + "&";
        if (!as_of_date.empty()) path += "asOfDate=" + as_of_date + "&";
        if (path.back() == '?' || path.back() == '&') path.pop_back();
        return http_request("GET", path);
    }

private:
    std::string m_api_key;
    std::string m_base_url;

    static std::vector<std::string> split_csv_line(const std::string& line) {
        std::vector<std::string> fields;
        std::stringstream ss(line);
        std::string item;
        while (std::getline(ss, item, ',')) {
            fields.push_back(item);
        }
        return fields;
    }

    static double safe_stod(const std::string& s, double fallback = 0.0) {
        if (s.empty()) return fallback;
        try {
            return std::stod(s);
        } catch (...) {
            return fallback;
        }
    }

    static std::string escape_json(const std::string& s) {
        std::ostringstream o;
        for (char c : s) {
            if (c == '"') o << "\\\"";
            else if (c == '\\') o << "\\\\";
            else if (c == '\b') o << "\\b";
            else if (c == '\f') o << "\\f";
            else if (c == '\n') o << "\\n";
            else if (c == '\r') o << "\\r";
            else if (c == '\t') o << "\\t";
            else o << c;
        }
        return o.str();
    }

    static std::string extract_json_string(const std::string& json, const std::string& key) {
        std::string search = "\"" + key + "\":\"";
        auto pos = json.find(search);
        if (pos == std::string::npos) return "";
        pos += search.length();
        auto end_pos = json.find('"', pos);
        if (end_pos == std::string::npos) return "";
        return json.substr(pos, end_pos - pos);
    }

#if defined(POLARISLINK_HAS_LIBCURL)
    static size_t curl_write_callback(void* contents, size_t size, size_t nmemb, void* userp) {
        size_t total_size = size * nmemb;
        std::string* str = static_cast<std::string*>(userp);
        str->append(static_cast<char*>(contents), total_size);
        return total_size;
    }
#endif

    static std::string escape_curl_config_value(const std::string& val) {
        std::ostringstream o;
        for (char c : val) {
            if (c == '"') o << "\\\"";
            else if (c == '\\') o << "\\\\";
            else if (c == '\n') o << "\\n";
            else if (c == '\r') o << "\\r";
            else if (c == '\t') o << "\\t";
            else o << c;
        }
        return o.str();
    }

    std::string http_request(const std::string& method, const std::string& path, const std::string& body = "") {
        std::string url = m_base_url + path;

#if defined(POLARISLINK_HAS_LIBCURL)
        CURL* curl = curl_easy_init();
        if (!curl) {
            throw std::runtime_error("PolarisLink™ C++ Client: Failed to initialize libcurl.");
        }

        std::string response_buffer;
        struct curl_slist* headers = nullptr;
        headers = curl_slist_append(headers, "User-Agent: Forticia-PolarisLink-CPP/2.6.1 (Native)");
        headers = curl_slist_append(headers, "Accept: application/json");

        if (!m_api_key.empty()) {
            std::string auth_header = "Authorization: Bearer " + m_api_key;
            headers = curl_slist_append(headers, auth_header.c_str());
        }

        if (!body.empty()) {
            headers = curl_slist_append(headers, "Content-Type: application/json");
            curl_easy_setopt(curl, CURLOPT_POSTFIELDS, body.c_str());
        }

        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST, method.c_str());
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, curl_write_callback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response_buffer);
        curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L);

        CURLcode res = curl_easy_perform(curl);
        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);

        if (res != CURLE_OK) {
            throw std::runtime_error(std::string("PolarisLink™ C++ Client: libcurl request failed: ") + curl_easy_strerror(res));
        }
        return response_buffer;

#else
        // Zero-dependency secure fallback: Passes credentials via strict mode-0600 ephemeral config
        // preventing API key leakage to process table / argv (/proc/<pid>/cmdline).
        char config_path[] = "/tmp/polarislink_cfg_XXXXXX";
        int fd = mkstemp(config_path);
        if (fd < 0) {
            throw std::runtime_error("PolarisLink™ C++ Client: Failed to allocate secure ephemeral config buffer.");
        }
        fchmod(fd, 0600);

        std::ostringstream cfg;
        cfg << "url = \"" << escape_curl_config_value(url) << "\"\n";
        cfg << "header = \"User-Agent: Forticia-PolarisLink-CPP/2.6.1 (Native)\"\n";
        cfg << "header = \"Accept: application/json\"\n";
        if (!m_api_key.empty()) {
            cfg << "header = \"Authorization: Bearer " << escape_curl_config_value(m_api_key) << "\"\n";
        }
        if (!body.empty()) {
            cfg << "header = \"Content-Type: application/json\"\n";
            cfg << "data = \"" << escape_curl_config_value(body) << "\"\n";
        }

        std::string cfg_data = cfg.str();
        ssize_t written = write(fd, cfg_data.data(), cfg_data.size());
        close(fd);

        if (written < static_cast<ssize_t>(cfg_data.size())) {
            unlink(config_path);
            throw std::runtime_error("PolarisLink™ C++ Client: Failed to write ephemeral config payload.");
        }

        std::ostringstream cmd;
        cmd << "curl -s -X " << method << " -K " << config_path;

        std::array<char, 512> buffer;
        std::string result;
        FILE* pipe = popen(cmd.str().c_str(), "r");
        if (!pipe) {
            unlink(config_path);
            throw std::runtime_error("PolarisLink™ C++ Client: Failed to execute fallback HTTP command.");
        }
        while (fgets(buffer.data(), buffer.size(), pipe) != nullptr) {
            result += buffer.data();
        }
        pclose(pipe);
        unlink(config_path);
        return result;
#endif
    }
};

} // namespace polarislink
