#include "common/simulation_control.hpp"

#include <cmath>
#include <functional>
#include <stdexcept>
#include <string>

namespace {
void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void requireThrows(const std::string& name, const std::function<void()>& fn) {
    try {
        fn();
    } catch (const std::exception&) {
        return;
    }
    throw std::runtime_error(name + " did not fail");
}
}

int main() {
    scl::common::ErrorMetrics metrics;
    scl::common::LatencyStats latency;
    latency.encodeTimeNsSum = 1000;
    latency.channelTimeNsSum = 2000;
    latency.decodeTimeNsSum = 3000;
    latency.recoveryTimeNsSum = 4000;
    latency.totalTimeNsSum = 10000;
    latency.maxDecodeTimeNs = 3000;
    latency.maxTotalTimeNs = 10000;
    scl::common::addFrameResult(metrics, {0U, 1U, 0U, 1U}, {0U, 1U, 1U, 1U}, latency);
    scl::common::addFrameResult(metrics, {0U, 0U, 0U, 0U}, {0U, 0U, 0U, 0U}, latency);
    const auto summary = scl::common::summarizeMetrics(metrics);
    require(metrics.bitErrors == 1U && metrics.frameErrors == 1U && metrics.successfulFrames == 1U, "error counters mismatch");
    require(std::fabs(summary.ber - 0.125) < 1e-15, "BER mismatch");
    require(std::fabs(summary.fer - 0.5) < 1e-15, "FER mismatch");
    require(std::fabs(summary.successRate - 0.5) < 1e-15, "successRate mismatch");
    require(summary.avgEncodeTimeUs == 1.0 && summary.maxDecodeTimeUs == 3.0, "latency mismatch");
    requireThrows("empty summary", [] { (void)scl::common::summarizeMetrics({}); });
    requireThrows("length mismatch", [&] { scl::common::addFrameResult(metrics, {0U}, {0U, 1U}); });

    const scl::common::StopConfig formal = scl::common::formalStopConfig();
    require(formal.minFrames == 5000U && formal.maxFrames == 50000U && formal.targetFrameErrors == 200U, "formal stop config mismatch");
    scl::common::ErrorMetrics stopMetrics;
    stopMetrics.processedFrames = 4999;
    stopMetrics.frameErrors = 200;
    require(!scl::common::evaluateStop(formal, stopMetrics).shouldStop, "stopped before minFrames");
    stopMetrics.processedFrames = 5000;
    require(scl::common::evaluateStop(formal, stopMetrics).reason == "TARGET_FRAME_ERRORS", "target stop mismatch");
    stopMetrics.frameErrors = 0;
    stopMetrics.processedFrames = 50000;
    require(scl::common::evaluateStop(formal, stopMetrics).reason == "MAX_FRAMES", "max stop mismatch");
    return 0;
}
