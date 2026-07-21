#include "common/simulation_pipeline.hpp"

#include "common/checkpoint.hpp"

#include <algorithm>
#include <stdexcept>

namespace scl::common {

SummaryRow runIdentitySimulation(const IdentitySimulationConfig& config) {
    CodeLengths lengths;
    lengths.payloadLength = config.payloadLength;
    lengths.codecInputLength = config.payloadLength;
    lengths.encodedLength = config.encodedLength;
    lengths.transmittedLength = config.encodedLength;
    const double sigma = computeAwgnSigma(lengths, config.ebN0_dB);

    ErrorMetrics metrics;
    for (std::uint64_t offset = 0; offset < config.frameCount; ++offset) {
        const FrameIndex frameIndex = config.frameStart + offset;
        BitVector payload = generatePayloadBits(config.payloadSeed, config.payloadLength, frameIndex);
        BitVector encoded = payload;
        encoded.resize(config.encodedLength, 0U);
        const RealVector symbols = bpskModulate(encoded);
        const RealVector noise = generateStandardGaussianFrame(config.masterNoiseSeed, config.noiseGroupId, frameIndex, config.encodedLength);
        const RealVector received = applyAwgn(symbols, noise, sigma);
        BitVector hard = config.decisionMode == DecisionMode::Hard ? hardDecision(received) : llrSignDecision(computeLlr(received, sigma));
        hard.resize(config.payloadLength);
        LatencyStats latency;
        latency.encodeTimeNsSum = 100;
        latency.channelTimeNsSum = 200;
        latency.decodeTimeNsSum = 300;
        latency.recoveryTimeNsSum = 100;
        latency.totalTimeNsSum = 700;
        latency.maxDecodeTimeNs = 300;
        latency.maxTotalTimeNs = 700;
        addFrameResult(metrics, payload, hard, latency);
        if (evaluateStop(config.stopConfig, metrics).shouldStop) {
            break;
        }
    }

    SummaryRow row;
    row.experimentId = config.experimentId;
    row.caseName = config.caseName;
    row.payloadLength = config.payloadLength;
    row.encodedLength = config.encodedLength;
    row.codeRate = computeCodeRate(lengths);
    row.ebN0_dB = config.ebN0_dB;
    row.snrIndex = config.snrIndex;
    row.metrics = metrics;
    row.stopReason = evaluateStop(config.stopConfig, metrics).reason;
    row.framePoolId = config.framePoolId;
    row.noisePoolId = config.noisePoolId;
    row.configHash = computeConfigHash(canonicalConfigText(row.caseName, row.payloadLength, row.encodedLength,
                                                           "frozen", row.framePoolId, row.noisePoolId,
                                                           "frozen", config.decisionMode == DecisionMode::Hard ? "HARD" : "LLR_SIGN"));
    validateSummaryRow(row);
    return row;
}

ErrorMetrics mergeShardMetrics(const std::vector<ErrorMetrics>& shards) {
    ErrorMetrics merged;
    for (const ErrorMetrics& shard : shards) {
        merged.processedFrames += shard.processedFrames;
        merged.totalPayloadBits += shard.totalPayloadBits;
        merged.bitErrors += shard.bitErrors;
        merged.frameErrors += shard.frameErrors;
        merged.successfulFrames += shard.successfulFrames;
        merged.latency.encodeTimeNsSum += shard.latency.encodeTimeNsSum;
        merged.latency.channelTimeNsSum += shard.latency.channelTimeNsSum;
        merged.latency.decodeTimeNsSum += shard.latency.decodeTimeNsSum;
        merged.latency.recoveryTimeNsSum += shard.latency.recoveryTimeNsSum;
        merged.latency.totalTimeNsSum += shard.latency.totalTimeNsSum;
        merged.latency.maxDecodeTimeNs = std::max(merged.latency.maxDecodeTimeNs, shard.latency.maxDecodeTimeNs);
        merged.latency.maxTotalTimeNs = std::max(merged.latency.maxTotalTimeNs, shard.latency.maxTotalTimeNs);
    }
    return merged;
}

}  // namespace scl::common
