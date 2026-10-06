#include <polarislink/polarislink.hpp>
#include <iostream>

int main() {
    std::cout << "PolarisLink C++20 Client Example\n";

    polarislink::Client client("fca_demo_key");

    polarislink::BacktestRunMetrics run;
    run.strategy_name = "Sample_Volatility_Model";
    run.sharpe = 2.45;
    run.cagr = 0.38;
    run.max_drawdown = 0.075;
    run.trades_count = 450;

    std::cout << "Initialized run metrics for: " << run.strategy_name << "\n";
    std::cout << "Sharpe: " << run.sharpe << ", CAGR: " << run.cagr << "\n";

    return 0;
}
