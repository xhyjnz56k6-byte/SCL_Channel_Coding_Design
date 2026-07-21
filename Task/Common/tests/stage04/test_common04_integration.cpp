#include "common/simulation_pipeline.hpp"

#include <functional>
#include <stdexcept>
#include <string>

namespace {
void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}
}

int main() {
    scl::common::IdentitySimulationConfig k200;
    k200.payloadLength = 200;
    k200.encodedLength = 248;
    k200.frameCount = 100;
    k200.stopConfig = {0, 100, 0, false};
    const auto hard200 = scl::common::runIdentitySimulation(k200);
    k200.decisionMode = scl::common::DecisionMode::LlrSign;
    const auto llr200 = scl::common::runIdentitySimulation(k200);
    require(hard200.metrics.processedFrames == 100U && llr200.metrics.processedFrames == 100U, "K200 processed mismatch");
    require(hard200.metrics.bitErrors == llr200.metrics.bitErrors, "hard/LLR K200 mismatch");

    scl::common::IdentitySimulationConfig k300;
    k300.payloadLength = 300;
    k300.encodedLength = 390;
    k300.frameCount = 100;
    k300.stopConfig = {0, 100, 0, false};
    const auto low = scl::common::runIdentitySimulation(k300);
    k300.ebN0_dB = 4.0;
    const auto high = scl::common::runIdentitySimulation(k300);
    require(high.metrics.bitErrors <= low.metrics.bitErrors + 20U, "gross SNR trend failed");

    k300.frameCount = 50;
    const auto first = scl::common::runIdentitySimulation(k300);
    k300.frameStart = 50;
    const auto second = scl::common::runIdentitySimulation(k300);
    const auto merged = scl::common::mergeShardMetrics({first.metrics, second.metrics});
    k300.frameStart = 0;
    k300.frameCount = 100;
    const auto continuous = scl::common::runIdentitySimulation(k300);
    require(merged.processedFrames == continuous.metrics.processedFrames, "merged frame count mismatch");
    require(merged.bitErrors == continuous.metrics.bitErrors, "merged bit errors mismatch");
    require(scl::common::summaryRowToCsv(continuous).find("IDENTITY") != std::string::npos, "identity CSV missing");
    return 0;
}
