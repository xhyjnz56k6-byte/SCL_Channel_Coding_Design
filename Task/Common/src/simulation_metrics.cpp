#include "common/simulation_metrics.hpp"

#include <algorithm>
#include <limits>
#include <stdexcept>

namespace scl::common {

namespace {
void checkedAdd(std::uint64_t& target, std::uint64_t value, const char* name) {
    if (value > std::numeric_limits<std::uint64_t>::max() - target) {
        throw std::overflow_error(std::string(name) + " overflow");
    }
    target += value;
}

double averageUs(std::uint64_t sumNs, std::uint64_t count) {
    return static_cast<double>(sumNs) / static_cast<double>(count) / 1000.0;
}
}

std::uint64_t countBitErrors(const BitVector& originalPayload, const BitVector& recoveredPayload) {
    if (originalPayload.size() != recoveredPayload.size()) {
        throw std::invalid_argument("payload length mismatch");
    }
    validateBits(originalPayload, "originalPayload");
    validateBits(recoveredPayload, "recoveredPayload");
    std::uint64_t errors = 0;
    for (std::size_t i = 0; i < originalPayload.size(); ++i) {
        if (originalPayload[i] != recoveredPayload[i]) {
            ++errors;
        }
    }
    return errors;
}

void addFrameResult(ErrorMetrics& metrics,
                    const BitVector& originalPayload,
                    const BitVector& recoveredPayload,
                    const LatencyStats& frameLatency) {
    const std::uint64_t errors = countBitErrors(originalPayload, recoveredPayload);
    checkedAdd(metrics.processedFrames, 1U, "processedFrames");
    checkedAdd(metrics.totalPayloadBits, static_cast<std::uint64_t>(originalPayload.size()), "totalPayloadBits");
    checkedAdd(metrics.bitErrors, errors, "bitErrors");
    if (errors != 0U) {
        checkedAdd(metrics.frameErrors, 1U, "frameErrors");
    } else {
        checkedAdd(metrics.successfulFrames, 1U, "successfulFrames");
    }
    checkedAdd(metrics.latency.encodeTimeNsSum, frameLatency.encodeTimeNsSum, "encodeTimeNsSum");
    checkedAdd(metrics.latency.channelTimeNsSum, frameLatency.channelTimeNsSum, "channelTimeNsSum");
    checkedAdd(metrics.latency.decodeTimeNsSum, frameLatency.decodeTimeNsSum, "decodeTimeNsSum");
    checkedAdd(metrics.latency.recoveryTimeNsSum, frameLatency.recoveryTimeNsSum, "recoveryTimeNsSum");
    checkedAdd(metrics.latency.totalTimeNsSum, frameLatency.totalTimeNsSum, "totalTimeNsSum");
    metrics.latency.maxDecodeTimeNs = std::max(metrics.latency.maxDecodeTimeNs, frameLatency.maxDecodeTimeNs);
    metrics.latency.maxTotalTimeNs = std::max(metrics.latency.maxTotalTimeNs, frameLatency.maxTotalTimeNs);
}

MetricsSummary summarizeMetrics(const ErrorMetrics& metrics) {
    if (metrics.processedFrames == 0U || metrics.totalPayloadBits == 0U) {
        throw std::invalid_argument("processedFrames and totalPayloadBits must be positive");
    }
    MetricsSummary summary;
    summary.ber = static_cast<double>(metrics.bitErrors) / static_cast<double>(metrics.totalPayloadBits);
    summary.fer = static_cast<double>(metrics.frameErrors) / static_cast<double>(metrics.processedFrames);
    summary.successRate = static_cast<double>(metrics.successfulFrames) / static_cast<double>(metrics.processedFrames);
    summary.avgEncodeTimeUs = averageUs(metrics.latency.encodeTimeNsSum, metrics.processedFrames);
    summary.avgChannelTimeUs = averageUs(metrics.latency.channelTimeNsSum, metrics.processedFrames);
    summary.avgDecodeTimeUs = averageUs(metrics.latency.decodeTimeNsSum, metrics.processedFrames);
    summary.avgRecoveryTimeUs = averageUs(metrics.latency.recoveryTimeNsSum, metrics.processedFrames);
    summary.avgTotalTimeUs = averageUs(metrics.latency.totalTimeNsSum, metrics.processedFrames);
    summary.maxDecodeTimeUs = static_cast<double>(metrics.latency.maxDecodeTimeNs) / 1000.0;
    summary.maxTotalTimeUs = static_cast<double>(metrics.latency.maxTotalTimeNs) / 1000.0;
    return summary;
}

}  // namespace scl::common
