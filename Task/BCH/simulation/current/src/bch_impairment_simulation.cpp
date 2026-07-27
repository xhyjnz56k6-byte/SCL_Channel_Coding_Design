#include "bch_simulation/bch_impairment_simulation.hpp"

#include "bch_simulation/bch_multipath_simulation.hpp"
#include "common/awgn_channel.hpp"
#include "common/demodulation.hpp"
#include "common/frame_pool.hpp"
#include "common/gaussian_noise.hpp"
#include "common/modulation.hpp"
#include "common/sha256.hpp"
#include "common/simulation_metrics.hpp"
#include "common/simulation_control.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>

namespace fs = std::filesystem;

namespace scl::bch::simulation {
namespace {

double percentile(std::vector<double> values, double fraction) {
    if (values.empty()) return 0.0;
    std::sort(values.begin(), values.end());
    const double position = fraction * static_cast<double>(values.size() - 1U);
    const std::size_t lower = static_cast<std::size_t>(position);
    const std::size_t upper = std::min(lower + 1U, values.size() - 1U);
    const double weight = position - static_cast<double>(lower);
    return values[lower] * (1.0 - weight) + values[upper] * weight;
}

double maximum(const std::vector<double>& values) {
    return values.empty() ? 0.0 : *std::max_element(values.begin(), values.end());
}

std::string makeConfigText(
    const ImpairmentPointConfig& config,
    const BchSimulationCase& value,
    const std::string& framePoolId,
    double snrDb) {
    std::ostringstream out;
    out << "channelType=" << impairmentChannelName(config.channel)
        << ";caseName=" << value.caseName
        << ";payloadLength=" << value.payloadLength
        << ";encodedLength=" << value.encodedLength
        << ";frameRate=" << std::setprecision(17) << value.frameRate
        << ";sourcePayloadEbN0Db=" << config.sourcePayloadEbN0Db
        << ";snrDb=" << snrDb
        << ";noisePolicyVersion=" << config.noisePolicyVersion
        << ";initialPhaseDeg=" << config.initialPhaseDeg
        << ";frameRotationDeg=" << config.frameRotationDeg
        << ";compensationMode="
        << (config.compensationMode == CfoCompensationMode::Perfect ? "PERFECT" : "NONE")
        << ";attenuationDb=" << config.attenuationDb
        << ";completeBlockage=" << config.completeBlockage
        << ";blockageLength=" << config.blockageLength
        << ";blockageStartPolicy=" << startPolicyName(config.blockageStartPolicy)
        << ";burstMode=" << burstModeName(config.burstMode)
        << ";burstLength=" << config.burstLength
        << ";burstStartPolicy=" << startPolicyName(config.burstStartPolicy)
        << ";backgroundAwgnEnabled="
        << (config.channel != ImpairmentChannel::Burst ||
            config.burstMode == BurstMode::Awgn)
        << ";framePoolId=" << framePoolId
        << ";seed=" << config.globalSeed
        << ";logicalFrameCount=" << config.logicalFrameCount
        << ";adaptiveStop=" << config.adaptiveStop
        << ";minFrames=" << config.minFrames
        << ";targetFrameErrors=" << config.targetFrameErrors
        << ";maxFrames=" << config.maxFrames
        << ";shardCount=" << config.shardCount;
    return out.str();
}

void validateAccounting(
    const ImpairmentPointResult& result, const BchSimulationCase& value) {
    if (result.processedPayloadBits !=
            result.processedFrames * value.payloadLength ||
        result.trueSuccessFrames + result.decodedFrameErrors !=
            result.processedFrames ||
        result.reportedSuccessFrames + result.decoderFailureFrames !=
            result.processedFrames) {
        throw std::logic_error("impairment metric accounting mismatch");
    }
}

void writeCheckpoint(const ImpairmentPointResult& result) {
    if (result.config.checkpointPath.empty()) return;
    fs::create_directories(fs::path(result.config.checkpointPath).parent_path());
    std::ofstream out(result.config.checkpointPath);
    if (!out) throw std::runtime_error("failed to write impairment checkpoint");
    out << "configHash=" << result.configHash << '\n'
        << "processedFrames=" << result.processedFrames << '\n'
        << "processedPayloadBits=" << result.processedPayloadBits << '\n'
        << "channelHardBitErrors=" << result.channelHardBitErrors << '\n'
        << "channelHardFrameErrors=" << result.channelHardFrameErrors << '\n'
        << "decodedBitErrors=" << result.decodedBitErrors << '\n'
        << "decodedFrameErrors=" << result.decodedFrameErrors << '\n'
        << "trueSuccessFrames=" << result.trueSuccessFrames << '\n'
        << "reportedSuccessFrames=" << result.reportedSuccessFrames << '\n'
        << "miscorrectedFrames=" << result.miscorrectedFrames << '\n'
        << "decoderFailureFrames=" << result.decoderFailureFrames << '\n';
}

std::map<std::string, std::string> readKeyValues(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("failed to read impairment checkpoint");
    std::map<std::string, std::string> values;
    std::string line;
    while (std::getline(in, line)) {
        const auto split = line.find('=');
        if (split != std::string::npos) {
            values[line.substr(0U, split)] = line.substr(split + 1U);
        }
    }
    return values;
}

void restoreCheckpoint(ImpairmentPointResult& result) {
    const auto values = readKeyValues(result.config.checkpointPath);
    if (values.at("configHash") != result.configHash) {
        throw std::invalid_argument("checkpoint config hash mismatch");
    }
    result.processedFrames = std::stoull(values.at("processedFrames"));
    result.processedPayloadBits = std::stoull(values.at("processedPayloadBits"));
    result.channelHardBitErrors = std::stoull(values.at("channelHardBitErrors"));
    result.channelHardFrameErrors = std::stoull(values.at("channelHardFrameErrors"));
    result.decodedBitErrors = std::stoull(values.at("decodedBitErrors"));
    result.decodedFrameErrors = std::stoull(values.at("decodedFrameErrors"));
    result.trueSuccessFrames = std::stoull(values.at("trueSuccessFrames"));
    result.reportedSuccessFrames = std::stoull(values.at("reportedSuccessFrames"));
    result.miscorrectedFrames = std::stoull(values.at("miscorrectedFrames"));
    result.decoderFailureFrames = std::stoull(values.at("decoderFailureFrames"));
    result.resumeCount = 1U;
}

}  // namespace

ImpairmentChannel parseImpairmentChannel(const std::string& value) {
    if (value == "RESIDUAL_CFO") return ImpairmentChannel::ResidualCfo;
    if (value == "SHORT_BLOCKAGE") return ImpairmentChannel::ShortBlockage;
    if (value == "BURST") return ImpairmentChannel::Burst;
    throw std::invalid_argument("unsupported impairment channel");
}

std::string impairmentChannelName(ImpairmentChannel value) {
    switch (value) {
        case ImpairmentChannel::ResidualCfo: return "RESIDUAL_CFO";
        case ImpairmentChannel::ShortBlockage: return "SHORT_BLOCKAGE";
        case ImpairmentChannel::Burst: return "BURST";
    }
    throw std::invalid_argument("unsupported impairment channel");
}

BurstMode parseBurstMode(const std::string& value) {
    if (value == "PURE") return BurstMode::Pure;
    if (value == "AWGN") return BurstMode::Awgn;
    throw std::invalid_argument("unsupported burst mode");
}

std::string burstModeName(BurstMode value) {
    return value == BurstMode::Pure ? "PURE" : "AWGN";
}

ImpairmentPointResult runImpairmentPoint(const ImpairmentPointConfig& config) {
    if (config.stage.empty() || config.frameCount == 0U ||
        config.framePoolManifest.empty() || config.outputDirectory.empty() ||
        config.noisePolicyVersion != 2U || config.shardCount == 0U ||
        config.shardIndex >= config.shardCount) {
        throw std::invalid_argument("invalid impairment point configuration");
    }
    if (config.adaptiveStop) {
        common::validateStopConfig(
            {config.minFrames, config.maxFrames,
             config.targetFrameErrors, true});
        if (config.maxFrames != config.frameCount) {
            throw std::invalid_argument("impairment maxFrames must equal frameCount");
        }
    }
    const auto& value = bchSimulationCase(config.caseId);
    common::PackedFramePoolReader pool(config.framePoolManifest);
    if (pool.payloadLength() != value.payloadLength ||
        config.frameStart + config.frameCount > pool.frameCount()) {
        throw std::invalid_argument("frame pool does not cover impairment point");
    }
    fs::create_directories(config.outputDirectory);
    ImpairmentPointResult result;
    result.config = config;
    if (result.config.logicalFrameCount == 0U) {
        result.config.logicalFrameCount = result.config.frameCount;
    }
    result.snrDb =
        config.sourcePayloadEbN0Db + 10.0 * std::log10(value.frameRate);
    result.configHash = common::sha256Hex(
        makeConfigText(result.config, value, pool.framePoolId(), result.snrDb));
    result.decodeTimesUs.reserve(static_cast<std::size_t>(config.frameCount));
    result.preprocessingTimesUs.reserve(static_cast<std::size_t>(config.frameCount));
    result.receiverTimesUs.reserve(static_cast<std::size_t>(config.frameCount));
    prepareBchCase(value);
    if (config.resume) {
        if (config.checkpointPath.empty()) {
            throw std::invalid_argument("resume requires checkpoint path");
        }
        restoreCheckpoint(result);
    }
    const double realNoiseVariance =
        1.0 / (2.0 * std::pow(10.0, result.snrDb / 10.0));
    const std::uint64_t noiseGroup = makePhysicalSnrNoiseGroup(
        value.payloadLength, result.snrDb, config.noisePolicyVersion);
    const auto started = std::chrono::steady_clock::now();
    auto lastProgress = started;
    for (std::uint64_t offset = result.processedFrames;
         offset < config.frameCount; ++offset) {
        const std::uint64_t frameIndex = config.frameStart + offset;
        const auto payload = pool.readFrame(frameIndex).payloadBits;
        const auto encoded = encodeBchFrame(value, payload);
        const auto symbols = common::bpskModulate(encoded.codeword);
        common::BitVector hardBits;
        const auto receiverStart = std::chrono::steady_clock::now();
        if (config.channel == ImpairmentChannel::ResidualCfo) {
            const auto noise = common::generateStandardGaussianFrame(
                config.globalSeed, noiseGroup, frameIndex,
                value.encodedLength * 2U, config.noisePolicyVersion);
            ResidualCfoConfig channelConfig;
            channelConfig.initialPhaseDeg = config.initialPhaseDeg;
            channelConfig.frameRotationDeg = config.frameRotationDeg;
            channelConfig.noiseVariance = realNoiseVariance * 2.0;
            channelConfig.compensationMode = config.compensationMode;
            hardBits = applyResidualCfo(symbols, noise, channelConfig).hardBits;
        } else if (config.channel == ImpairmentChannel::ShortBlockage) {
            const auto noise = common::generateStandardGaussianFrame(
                config.globalSeed, noiseGroup, frameIndex,
                value.encodedLength, config.noisePolicyVersion);
            BlockageConfig channelConfig;
            channelConfig.attenuationDb = config.attenuationDb;
            channelConfig.completeBlockage = config.completeBlockage;
            channelConfig.length = config.blockageLength;
            channelConfig.start = chooseStartIndex(
                config.blockageStartPolicy, value.encodedLength,
                config.blockageLength, 15U, config.globalSeed, frameIndex,
                "BLOCKAGE_START");
            channelConfig.noiseVariance = realNoiseVariance;
            hardBits = applyShortBlockage(symbols, noise, channelConfig).hardBits;
        } else {
            if (config.burstMode == BurstMode::Pure) {
                hardBits = encoded.codeword;
            } else {
                const auto noise = common::generateStandardGaussianFrame(
                    config.globalSeed, noiseGroup, frameIndex,
                    value.encodedLength, config.noisePolicyVersion);
                const auto received = common::applyAwgn(
                    symbols, noise, std::sqrt(realNoiseVariance));
                hardBits = common::hardDecision(received);
            }
            const std::size_t start = chooseStartIndex(
                config.burstStartPolicy, value.encodedLength,
                config.burstLength, 15U, config.globalSeed, frameIndex,
                "BURST_START");
            hardBits = applyPostHardDecisionBurst(
                hardBits, start, config.burstLength);
        }
        const std::uint64_t channelErrors =
            common::countBitErrors(encoded.codeword, hardBits);
        const auto decodeStart = std::chrono::steady_clock::now();
        auto decoded = decodeBchFrame(value, hardBits);
        const auto decodeEnd = std::chrono::steady_clock::now();
        auditDecodedBchFrame(payload, decoded);
        const auto receiverEnd = std::chrono::steady_clock::now();
        const std::uint64_t decodedErrors =
            common::countBitErrors(payload, decoded.payload);
        const double decodeUs =
            std::chrono::duration<double, std::micro>(decodeEnd - decodeStart).count();
        const double receiverUs =
            std::chrono::duration<double, std::micro>(
                receiverEnd - receiverStart).count();
        const double preprocessingUs = receiverUs - decodeUs;
        ++result.processedFrames;
        result.processedPayloadBits += value.payloadLength;
        result.channelHardBitErrors += channelErrors;
        result.channelHardFrameErrors += channelErrors != 0U;
        result.decodedBitErrors += decodedErrors;
        result.decodedFrameErrors += decodedErrors != 0U;
        result.trueSuccessFrames += decoded.trueSuccess;
        result.reportedSuccessFrames += decoded.reportedSuccess;
        result.miscorrectedFrames += decoded.miscorrected;
        result.decoderFailureFrames += decoded.decoderFailure;
        result.decodeTimeUsSum += decodeUs;
        result.preprocessingTimeUsSum += preprocessingUs;
        result.totalReceiverTimeUsSum += receiverUs;
        result.decodeTimesUs.push_back(decodeUs);
        result.preprocessingTimesUs.push_back(preprocessingUs);
        result.receiverTimesUs.push_back(receiverUs);
        const auto now = std::chrono::steady_clock::now();
        if (config.progress &&
            (std::chrono::duration<double>(now - lastProgress).count() >=
                 config.progressRefreshSeconds ||
             result.processedFrames == config.frameCount)) {
            lastProgress = now;
            const double elapsed =
                std::chrono::duration<double>(now - started).count();
            std::cerr << '[' << config.stage << "]["
                      << impairmentChannelName(config.channel) << "]["
                      << value.caseName << "] frames " << result.processedFrames
                      << '/' << config.frameCount << " FE "
                      << result.decodedFrameErrors << " FER " << std::scientific
                      << static_cast<double>(result.decodedFrameErrors) /
                             result.processedFrames
                      << std::fixed << " speed "
                      << static_cast<std::uint64_t>(
                             result.processedFrames / std::max(1e-9, elapsed))
                      << " frame/s\r";
        }
        bool saved = false;
        if (!config.checkpointPath.empty() && config.checkpointInterval > 0U &&
            result.processedFrames % config.checkpointInterval == 0U) {
            ++result.checkpointCount;
            writeCheckpoint(result);
            saved = true;
        }
        if (config.interruptAfterFrames > 0U &&
            result.processedFrames >= config.interruptAfterFrames) {
            result.stopReason = "INTERRUPTED_CHECKPOINT";
            if (!saved && !config.checkpointPath.empty()) {
                ++result.checkpointCount;
                writeCheckpoint(result);
            }
            break;
        }
        if (config.adaptiveStop) {
            common::ErrorMetrics metrics;
            metrics.processedFrames = result.processedFrames;
            metrics.frameErrors = result.decodedFrameErrors;
            const auto decision = common::evaluateStop(
                {config.minFrames, config.maxFrames,
                 config.targetFrameErrors, true}, metrics);
            if (decision.shouldStop) {
                result.stopReason = decision.reason == "TARGET_FRAME_ERRORS"
                    ? "TARGET_FRAME_ERRORS_REACHED" : "MAX_FRAMES_REACHED";
                break;
            }
        }
    }
    if (result.stopReason == "CONTINUE") {
        result.stopReason = config.adaptiveStop
            ? "MAX_FRAMES_REACHED" : "FIXED_FRAMES_REACHED";
    }
    if (!config.checkpointPath.empty() &&
        result.stopReason != "INTERRUPTED_CHECKPOINT") {
        ++result.checkpointCount;
        writeCheckpoint(result);
    }
    if (config.progress) std::cerr << '\n';
    validateAccounting(result, value);
    return result;
}

void writeImpairmentPointSummary(
    const ImpairmentPointResult& result, const std::string& path) {
    const auto& value = bchSimulationCase(result.config.caseId);
    const double frames = static_cast<double>(result.processedFrames);
    const double payloadBits = static_cast<double>(result.processedPayloadBits);
    const double encodedBits = frames * value.encodedLength;
    std::ofstream out(path);
    if (!out) throw std::runtime_error("failed to open impairment summary");
    out << "schemaVersion,stage,channelType,caseName,organization,decoderType,"
           "payloadLength,encodedLength,frameRate,sourcePayloadEbN0Db,snrDb,"
           "noisePolicyVersion,initialPhaseDeg,frameRotationDeg,compensationMode,"
           "attenuationDb,completeBlockage,blockageLength,blockageStartPolicy,"
           "burstMode,burstLength,burstStartPolicy,burstInjectionDomain,"
           "backgroundAwgnEnabled,processedFrames,processedPayloadBits,"
           "channelHardBitErrors,channelHardFrameErrors,channelHardBER,"
           "decodedBitErrors,decodedFrameErrors,BER,FER,trueSuccessFrames,"
           "trueSuccessRate,reportedSuccessFrames,reportedSuccessRate,"
           "miscorrectedFrames,miscorrectionRate,decoderFailureFrames,"
           "decoderFailureRate,avgDecodeTimeUs,p50DecodeTimeUs,p95DecodeTimeUs,"
           "p99DecodeTimeUs,maxDecodeTimeUs,avgPreprocessingTimeUs,"
           "medianPreprocessingTimeUs,p95PreprocessingTimeUs,"
           "p99PreprocessingTimeUs,maxPreprocessingTimeUs,avgTotalReceiverTimeUs,"
           "medianReceiverTimeUs,p95ReceiverTimeUs,p99ReceiverTimeUs,"
           "maxReceiverTimeUs,"
           "minFrames,targetFrameErrors,maxFrames,stopReason,"
           "checkpointCount,resumeCount,shardIndex,shardCount,"
           "configHash,gitCommit\n";
    out << "bch.s2.impairment.result.v1," << result.config.stage << ','
        << impairmentChannelName(result.config.channel) << ',' << value.caseName
        << ',' << organizationName(value.organization) << ','
        << decoderTypeName(value.decoderType) << ',' << value.payloadLength << ','
        << value.encodedLength << ',' << std::setprecision(17) << value.frameRate
        << ',' << result.config.sourcePayloadEbN0Db << ',' << result.snrDb << ','
        << result.config.noisePolicyVersion << ',' << result.config.initialPhaseDeg
        << ',' << result.config.frameRotationDeg << ','
        << (result.config.compensationMode == CfoCompensationMode::Perfect
                ? "PERFECT" : "NONE")
        << ',' << result.config.attenuationDb << ','
        << result.config.completeBlockage << ',' << result.config.blockageLength
        << ',' << startPolicyName(result.config.blockageStartPolicy) << ','
        << burstModeName(result.config.burstMode) << ','
        << result.config.burstLength << ','
        << startPolicyName(result.config.burstStartPolicy)
        << ",POST_HARD_DECISION_BIT_FLIP,"
        << (result.config.channel != ImpairmentChannel::Burst ||
            result.config.burstMode == BurstMode::Awgn)
        << ',' << result.processedFrames << ',' << result.processedPayloadBits
        << ',' << result.channelHardBitErrors << ','
        << result.channelHardFrameErrors << ','
        << result.channelHardBitErrors / encodedBits << ','
        << result.decodedBitErrors << ',' << result.decodedFrameErrors << ','
        << result.decodedBitErrors / payloadBits << ','
        << result.decodedFrameErrors / frames << ',' << result.trueSuccessFrames
        << ',' << result.trueSuccessFrames / frames << ','
        << result.reportedSuccessFrames << ','
        << result.reportedSuccessFrames / frames << ','
        << result.miscorrectedFrames << ','
        << result.miscorrectedFrames / frames << ','
        << result.decoderFailureFrames << ','
        << result.decoderFailureFrames / frames << ','
        << result.decodeTimeUsSum / frames << ','
        << percentile(result.decodeTimesUs, 0.50) << ','
        << percentile(result.decodeTimesUs, 0.95) << ','
        << percentile(result.decodeTimesUs, 0.99) << ','
        << maximum(result.decodeTimesUs) << ','
        << result.preprocessingTimeUsSum / frames << ','
        << percentile(result.preprocessingTimesUs, 0.50) << ','
        << percentile(result.preprocessingTimesUs, 0.95) << ','
        << percentile(result.preprocessingTimesUs, 0.99) << ','
        << maximum(result.preprocessingTimesUs) << ','
        << result.totalReceiverTimeUsSum / frames << ','
        << percentile(result.receiverTimesUs, 0.50) << ','
        << percentile(result.receiverTimesUs, 0.95) << ','
        << percentile(result.receiverTimesUs, 0.99) << ','
        << maximum(result.receiverTimesUs) << ','
        << result.config.minFrames << ','
        << result.config.targetFrameErrors << ','
        << result.config.maxFrames << ',' << result.stopReason
        << ',' << result.checkpointCount << ',' << result.resumeCount << ','
        << result.config.shardIndex << ',' << result.config.shardCount << ','
        << result.configHash << ",WORKTREE\n";
}

}  // namespace scl::bch::simulation
