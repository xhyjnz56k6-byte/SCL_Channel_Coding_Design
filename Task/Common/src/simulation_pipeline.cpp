#include "common/simulation_pipeline.hpp"

#include "common/checkpoint.hpp"

#include <algorithm>
#include <chrono>
#include <filesystem>
#include <limits>
#include <memory>
#include <set>
#include <stdexcept>

namespace scl::common {

namespace {
using Clock = std::chrono::steady_clock;

std::uint64_t elapsedNs(const Clock::time_point& start) {
    return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now() - start).count());
}

CodeLengths identityLengths(const IdentitySimulationConfig& config) {
    if (config.payloadLength == 0U || config.encodedLength != config.payloadLength) {
        throw std::invalid_argument("identity baseline requires encodedLength == payloadLength: payload=" +
                                    std::to_string(config.payloadLength) + " encoded=" + std::to_string(config.encodedLength));
    }
    return {config.payloadLength, config.payloadLength, config.encodedLength, config.encodedLength};
}

std::string decisionModeName(DecisionMode mode) {
    return mode == DecisionMode::Hard ? "HARD" : "LLR_SIGN";
}

SimulationCheckpointRecord checkpointIdentity(const IdentitySimulationConfig& config, const std::string& framePoolId,
                                              const std::string& noisePoolId, const std::string& configHash,
                                              FrameIndex nextFrameIndex, const ErrorMetrics& metrics,
                                              const std::string& stopReason) {
    SimulationCheckpointRecord record;
    record.experimentId = config.experimentId;
    record.configHash = configHash;
    record.framePoolId = framePoolId;
    record.noisePoolId = noisePoolId;
    record.payloadLength = config.payloadLength;
    record.encodedLength = config.encodedLength;
    record.snrIndex = config.snrIndex;
    record.ebN0_dB = config.ebN0_dB;
    record.nextFrameIndex = nextFrameIndex;
    record.metrics = metrics;
    record.stopReason = stopReason;
    return record;
}

void checkedMerge(std::uint64_t& target, std::uint64_t value, const char* field) {
    if (value > std::numeric_limits<std::uint64_t>::max() - target) {
        throw std::overflow_error(std::string("shard ") + field + " overflow");
    }
    target += value;
}

void mergeMetrics(ErrorMetrics& target, const ErrorMetrics& source) {
    checkedMerge(target.processedFrames, source.processedFrames, "processedFrames");
    checkedMerge(target.totalPayloadBits, source.totalPayloadBits, "totalPayloadBits");
    checkedMerge(target.bitErrors, source.bitErrors, "bitErrors");
    checkedMerge(target.frameErrors, source.frameErrors, "frameErrors");
    checkedMerge(target.successfulFrames, source.successfulFrames, "successfulFrames");
    checkedMerge(target.latency.encodeTimeNsSum, source.latency.encodeTimeNsSum, "encodeTimeNsSum");
    checkedMerge(target.latency.channelTimeNsSum, source.latency.channelTimeNsSum, "channelTimeNsSum");
    checkedMerge(target.latency.decodeTimeNsSum, source.latency.decodeTimeNsSum, "decodeTimeNsSum");
    checkedMerge(target.latency.recoveryTimeNsSum, source.latency.recoveryTimeNsSum, "recoveryTimeNsSum");
    checkedMerge(target.latency.totalTimeNsSum, source.latency.totalTimeNsSum, "totalTimeNsSum");
    target.latency.maxDecodeTimeNs = std::max(target.latency.maxDecodeTimeNs, source.latency.maxDecodeTimeNs);
    target.latency.maxTotalTimeNs = std::max(target.latency.maxTotalTimeNs, source.latency.maxTotalTimeNs);
}
}  // namespace

SummaryRow runIdentitySimulation(const IdentitySimulationConfig& config) {
    return runIdentitySimulation(config, {}).summary;
}

IdentitySimulationRunResult runIdentitySimulation(const IdentitySimulationConfig& config,
                                                  const IdentitySimulationRunOptions& options) {
    const CodeLengths lengths = identityLengths(config);
    const double sigma = computeAwgnSigma(lengths, config.ebN0_dB);
    std::unique_ptr<PackedFramePoolReader> frameReader;
    std::unique_ptr<NoisePoolReader> noiseReader;
    std::string framePoolId = config.framePoolId;
    std::string noisePoolId = config.noisePoolId;
    if (config.inputMode == SimulationInputMode::PoolBacked) {
        if (config.framePoolManifestPath.empty() || config.noisePoolManifestPath.empty()) {
            throw std::invalid_argument("pool-backed simulation requires both manifest paths");
        }
        frameReader = std::make_unique<PackedFramePoolReader>(config.framePoolManifestPath);
        noiseReader = std::make_unique<NoisePoolReader>(config.noisePoolManifestPath);
        framePoolId = frameReader->framePoolId();
        noisePoolId = noiseReader->noisePoolId();
        if ((!config.framePoolId.empty() && config.framePoolId != "generated" && config.framePoolId != framePoolId) ||
            (!config.noisePoolId.empty() && config.noisePoolId != "generated" && config.noisePoolId != noisePoolId)) {
            throw std::invalid_argument("configured pool identity does not match reader identity");
        }
        if (frameReader->payloadLength() != config.payloadLength || frameReader->frameCount() < config.frameStart + config.frameCount ||
            noiseReader->frameCount() < config.frameStart + config.frameCount || noiseReader->symbolsPerFrame() < config.encodedLength) {
            throw std::invalid_argument("pool-backed simulation range or length mismatch");
        }
    }
    const std::string configHash = computeConfigHash(canonicalConfigText(
        config.caseName, config.payloadLength, config.encodedLength, std::to_string(config.ebN0_dB), framePoolId, noisePoolId,
        std::to_string(config.stopConfig.minFrames) + ";" + std::to_string(config.stopConfig.maxFrames) + ";" +
            std::to_string(config.stopConfig.targetFrameErrors),
        decisionModeName(config.decisionMode)));

    ErrorMetrics metrics;
    FrameIndex nextFrameIndex = config.frameStart;
    if (options.resumeCheckpoint) {
        const SimulationCheckpointRecord expected = checkpointIdentity(config, framePoolId, noisePoolId, configHash,
                                                                         config.frameStart, {}, "CONTINUE");
        validateResumeCompatibility(expected, *options.resumeCheckpoint);
        validateCheckpointState(*options.resumeCheckpoint, config.frameStart, config.frameCount);
        metrics = options.resumeCheckpoint->metrics;
        nextFrameIndex = options.resumeCheckpoint->nextFrameIndex;
    }

    while (nextFrameIndex < config.frameStart + config.frameCount && !evaluateStop(config.stopConfig, metrics).shouldStop) {
        const Clock::time_point totalStart = Clock::now();
        const Clock::time_point encodeStart = Clock::now();
        const BitVector payload = frameReader ? frameReader->readFrame(nextFrameIndex).payloadBits :
                                                generatePayloadBits(config.payloadSeed, config.payloadLength, nextFrameIndex);
        const BitVector encoded = payload;
        const RealVector symbols = bpskModulate(encoded);
        const std::uint64_t encodeNs = elapsedNs(encodeStart);

        const Clock::time_point channelStart = Clock::now();
        const RealVector noise = noiseReader ? noiseReader->readFramePrefix(nextFrameIndex, config.encodedLength) :
                                               generateStandardGaussianFrame(config.masterNoiseSeed, config.noiseGroupId,
                                                                             nextFrameIndex, config.encodedLength);
        const RealVector received = applyAwgn(symbols, noise, sigma);
        const std::uint64_t channelNs = elapsedNs(channelStart);

        const Clock::time_point decodeStart = Clock::now();
        const BitVector decoded = config.decisionMode == DecisionMode::Hard ? hardDecision(received) :
                                                                              llrSignDecision(computeLlr(received, sigma));
        const std::uint64_t decodeNs = elapsedNs(decodeStart);

        const Clock::time_point recoveryStart = Clock::now();
        BitVector recoveredPayload(decoded.begin(), decoded.begin() + static_cast<std::ptrdiff_t>(config.payloadLength));
        const std::uint64_t recoveryNs = elapsedNs(recoveryStart);
        const std::uint64_t totalNs = elapsedNs(totalStart);
        addFrameResult(metrics, payload, recoveredPayload,
                       {encodeNs, channelNs, decodeNs, recoveryNs, totalNs, decodeNs, totalNs});
        ++nextFrameIndex;

        if (options.checkpointIntervalFrames != 0U && !options.checkpointOutputPath.empty() &&
            metrics.processedFrames % options.checkpointIntervalFrames == 0U) {
            writeCheckpointFile(options.checkpointOutputPath,
                                checkpointIdentity(config, framePoolId, noisePoolId, configHash, nextFrameIndex, metrics,
                                                   evaluateStop(config.stopConfig, metrics).reason));
        }
    }
    const std::string stopReason = evaluateStop(config.stopConfig, metrics).reason == "CONTINUE" ? "RANGE_COMPLETE" :
                                                                                                       evaluateStop(config.stopConfig, metrics).reason;
    IdentitySimulationRunResult result;
    result.summary.experimentId = config.experimentId;
    result.summary.caseName = config.caseName;
    result.summary.payloadLength = config.payloadLength;
    result.summary.encodedLength = config.encodedLength;
    result.summary.codeRate = computeCodeRate(lengths);
    result.summary.ebN0_dB = config.ebN0_dB;
    result.summary.snrIndex = config.snrIndex;
    result.summary.metrics = metrics;
    result.summary.stopReason = stopReason;
    result.summary.framePoolId = framePoolId;
    result.summary.noisePoolId = noisePoolId;
    result.summary.configHash = configHash;
    validateSummaryRow(result.summary);
    result.finalCheckpoint = checkpointIdentity(config, framePoolId, noisePoolId, configHash, nextFrameIndex, metrics, stopReason);
    if (!options.checkpointOutputPath.empty()) {
        writeCheckpointFile(options.checkpointOutputPath, result.finalCheckpoint);
    }
    return result;
}

ErrorMetrics mergeShardMetrics(const std::vector<ErrorMetrics>& shards) {
    ErrorMetrics merged;
    for (const ErrorMetrics& shard : shards) {
        mergeMetrics(merged, shard);
    }
    return merged;
}

MergedShardResult mergeSimulationShards(std::vector<SimulationShardResult> shards) {
    if (shards.empty()) {
        throw std::invalid_argument("cannot merge empty shard list");
    }
    std::sort(shards.begin(), shards.end(), [](const auto& left, const auto& right) { return left.frameStart < right.frameStart; });
    const SimulationShardResult& first = shards.front();
    MergedShardResult result;
    result.frameStart = first.frameStart;
    FrameIndex expected = first.frameStart;
    std::set<std::uint64_t> shardIndices;
    for (const SimulationShardResult& shard : shards) {
        if (!shardIndices.insert(shard.shardIndex).second) {
            throw std::invalid_argument("duplicate shardIndex");
        }
        if (shard.frameStart != expected || shard.frameCount == 0U) {
            throw std::invalid_argument("shard frame ranges contain gap or overlap");
        }
        if (shard.experimentId != first.experimentId || shard.configHash != first.configHash ||
            shard.framePoolId != first.framePoolId || shard.noisePoolId != first.noisePoolId ||
            shard.payloadLength != first.payloadLength || shard.encodedLength != first.encodedLength ||
            shard.snrIndex != first.snrIndex || shard.ebN0_dB != first.ebN0_dB) {
            throw std::invalid_argument("shard configuration mismatch");
        }
        if (shard.metrics.processedFrames != shard.frameCount ||
            shard.metrics.totalPayloadBits != shard.frameCount * shard.payloadLength ||
            shard.metrics.successfulFrames + shard.metrics.frameErrors != shard.frameCount) {
            throw std::invalid_argument("shard metrics contradict frame range");
        }
        mergeMetrics(result.metrics, shard.metrics);
        expected += shard.frameCount;
        result.frameCount += shard.frameCount;
    }
    return result;
}

}  // namespace scl::common
