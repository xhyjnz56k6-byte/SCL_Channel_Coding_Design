#ifndef SCL_COMMON_SIMULATION_METRICS_HPP
#define SCL_COMMON_SIMULATION_METRICS_HPP

#include "common/types.hpp"

#include <cstdint>
#include <string>

namespace scl::common {

struct LatencyStats {
    std::uint64_t encodeTimeNsSum = 0;
    std::uint64_t channelTimeNsSum = 0;
    std::uint64_t decodeTimeNsSum = 0;
    std::uint64_t recoveryTimeNsSum = 0;
    std::uint64_t totalTimeNsSum = 0;
    std::uint64_t maxDecodeTimeNs = 0;
    std::uint64_t maxTotalTimeNs = 0;
};

struct ErrorMetrics {
    std::uint64_t processedFrames = 0;
    std::uint64_t totalPayloadBits = 0;
    std::uint64_t bitErrors = 0;
    std::uint64_t frameErrors = 0;
    std::uint64_t successfulFrames = 0;
    LatencyStats latency;
};

struct MetricsSummary {
    double ber = 0.0;
    double fer = 0.0;
    double successRate = 0.0;
    double avgEncodeTimeUs = 0.0;
    double avgChannelTimeUs = 0.0;
    double avgDecodeTimeUs = 0.0;
    double avgRecoveryTimeUs = 0.0;
    double avgTotalTimeUs = 0.0;
    double maxDecodeTimeUs = 0.0;
    double maxTotalTimeUs = 0.0;
};

std::uint64_t countBitErrors(const BitVector& originalPayload, const BitVector& recoveredPayload);
void addFrameResult(ErrorMetrics& metrics,
                    const BitVector& originalPayload,
                    const BitVector& recoveredPayload,
                    const LatencyStats& frameLatency = {});
MetricsSummary summarizeMetrics(const ErrorMetrics& metrics);

}  // namespace scl::common

#endif  // SCL_COMMON_SIMULATION_METRICS_HPP
