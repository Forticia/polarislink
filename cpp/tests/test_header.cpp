#include <polarislink/polarislink.hpp>
#include <iostream>
#include <cassert>

int main() {
    // 1. Guardrail tests
    polarislink::enforce_institutional_guardrails("ibkr");
    polarislink::enforce_institutional_guardrails("cme");

    bool caught = false;
    try {
        polarislink::enforce_institutional_guardrails("yfinance");
    } catch (const std::runtime_error&) {
        caught = true;
    }
    assert(caught && "Expected retail provider guardrail to throw runtime_error");

    // 2. Struct tests
    polarislink::BacktestRunMetrics run;
    run.strategy_name = "Sample_Volatility_Model";
    run.sharpe = 1.0;
    run.cagr = 0.42;
    run.max_drawdown = 0.065;
    run.trades_count = 520;

    assert(run.sharpe > 0.5);
    assert(run.strategy_name == "Sample_Volatility_Model");

    std::cout << "[PASS] PolarisLink C++20 Header verification succeeded.\n";
    return 0;
}
