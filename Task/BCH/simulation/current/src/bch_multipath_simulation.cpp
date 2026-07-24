#include "bch_simulation/bch_multipath_simulation.hpp"

#include "common/frame_pool.hpp"
#include "common/gaussian_noise.hpp"
#include "common/modulation.hpp"
#include "common/checkpoint.hpp"
#include "common/sha256.hpp"
#include "common/simulation_control.hpp"
#include "common/simulation_metrics.hpp"

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

void validateAccounting(const MultipathPointResult& result,
                        const BchSimulationCase& simulationCase) {
    if (result.processedFrames != result.trueSuccessFrames + result.decodedFrameErrors ||
        result.processedFrames != result.reportedSuccessFrames + result.decoderFailureFrames ||
        result.miscorrectedFrames > result.reportedSuccessFrames ||
        result.processedPayloadBits != result.processedFrames * simulationCase.payloadLength ||
        result.preEqualizationHardBitErrors > result.processedFrames * simulationCase.encodedLength ||
        result.postEqualizationHardBitErrors > result.processedFrames * simulationCase.encodedLength) {
        throw std::logic_error("multipath result accounting mismatch");
    }
}

void writeCheckpoint(const MultipathPointResult& result) {
    if (result.config.checkpointPath.empty()) return;
    const fs::path target(result.config.checkpointPath);
    fs::create_directories(target.parent_path());
    const fs::path temporary = target.string() + ".tmp";
    std::ofstream out(temporary);
    if (!out) throw std::runtime_error("failed to write multipath checkpoint");
    out << "schemaVersion=bch.s2.multipath.checkpoint.v1\n"
        << "configHash=" << result.configHash << '\n'
        << "processedFrames=" << result.processedFrames << '\n'
        << "processedPayloadBits=" << result.processedPayloadBits << '\n'
        << "preEqualizationHardBitErrors=" << result.preEqualizationHardBitErrors << '\n'
        << "preEqualizationHardFrameErrors=" << result.preEqualizationHardFrameErrors << '\n'
        << "postEqualizationHardBitErrors=" << result.postEqualizationHardBitErrors << '\n'
        << "postEqualizationHardFrameErrors=" << result.postEqualizationHardFrameErrors << '\n'
        << "decodedBitErrors=" << result.decodedBitErrors << '\n'
        << "decodedFrameErrors=" << result.decodedFrameErrors << '\n'
        << "trueSuccessFrames=" << result.trueSuccessFrames << '\n'
        << "reportedSuccessFrames=" << result.reportedSuccessFrames << '\n'
        << "miscorrectedFrames=" << result.miscorrectedFrames << '\n'
        << "decoderFailureFrames=" << result.decoderFailureFrames << '\n'
        << "equalizationTimeUsSum=" << std::setprecision(17) << result.equalizationTimeUsSum << '\n'
        << "decodeTimeUsSum=" << result.decodeTimeUsSum << '\n'
        << "totalReceiverTimeUsSum=" << result.totalReceiverTimeUsSum << '\n'
        << "checkpointCount=" << result.checkpointCount << '\n';
    out.close();
    if (fs::exists(target)) fs::remove(target);
    fs::rename(temporary, target);
}

std::map<std::string, std::string> readKeyValues(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("multipath checkpoint missing");
    std::map<std::string, std::string> values;
    for (std::string line; std::getline(in, line);) {
        const auto separator = line.find('=');
        if (separator != std::string::npos) values[line.substr(0U, separator)] = line.substr(separator + 1U);
    }
    return values;
}

void restoreCheckpoint(MultipathPointResult& result) {
    const auto values = readKeyValues(result.config.checkpointPath);
    if (values.at("schemaVersion") != "bch.s2.multipath.checkpoint.v1" ||
        values.at("configHash") != result.configHash) {
        throw std::invalid_argument("multipath checkpoint configuration mismatch");
    }
#define RESTORE_U64(field) result.field = std::stoull(values.at(#field))
    RESTORE_U64(processedFrames);
    RESTORE_U64(processedPayloadBits);
    RESTORE_U64(preEqualizationHardBitErrors);
    RESTORE_U64(preEqualizationHardFrameErrors);
    RESTORE_U64(postEqualizationHardBitErrors);
    RESTORE_U64(postEqualizationHardFrameErrors);
    RESTORE_U64(decodedBitErrors);
    RESTORE_U64(decodedFrameErrors);
    RESTORE_U64(trueSuccessFrames);
    RESTORE_U64(reportedSuccessFrames);
    RESTORE_U64(miscorrectedFrames);
    RESTORE_U64(decoderFailureFrames);
    RESTORE_U64(checkpointCount);
#undef RESTORE_U64
    result.equalizationTimeUsSum = std::stod(values.at("equalizationTimeUsSum"));
    result.decodeTimeUsSum = std::stod(values.at("decodeTimeUsSum"));
    result.totalReceiverTimeUsSum = std::stod(values.at("totalReceiverTimeUsSum"));
    result.resumeCount = 1U;
}

}  // namespace

MultipathPointResult runMultipathPoint(const MultipathPointConfig& config) {
    if (config.frameCount == 0U || config.framePoolManifest.empty() ||
        config.outputDirectory.empty() || config.shardCount == 0U ||
        config.shardIndex >= config.shardCount) {
        throw std::invalid_argument("invalid multipath point configuration");
    }
    if (config.adaptiveStop) {
        common::validateStopConfig(
            {config.minFrames, config.maxFrames, config.targetFrameErrors, true});
        if (config.maxFrames != config.frameCount) {
            throw std::invalid_argument("multipath maxFrames must equal frameCount");
        }
    }
    const auto& simulationCase = bchSimulationCase(config.caseId);
    common::PackedFramePoolReader pool(config.framePoolManifest);
    if (pool.payloadLength() != simulationCase.payloadLength ||
        config.frameStart + config.frameCount > pool.frameCount()) {
        throw std::invalid_argument("frame pool does not cover multipath point");
    }
    fs::create_directories(config.outputDirectory);
    MultipathPointResult result;
    result.config = config;
    result.snrDb = config.sourcePayloadEbN0Db + 10.0 * std::log10(simulationCase.frameRate);
    result.noiseVariance = 1.0 / (2.0 * std::pow(10.0, result.snrDb / 10.0));
    result.noiseSigma = std::sqrt(result.noiseVariance);
    const auto channel = frozenFixedMultipathConfig();
    const std::string channelText = "raw=1,0.65,0.35;delays=0,1,3;energy=1;known=1;mmse=banded_cholesky";
    const std::string stopText = "frames=" + std::to_string(config.frameCount) +
        ";min=" + std::to_string(config.minFrames) +
        ";target=" + std::to_string(config.targetFrameErrors);
    result.configHash = common::computeConfigHash(common::canonicalConfigText(
        simulationCase.caseName, simulationCase.payloadLength, simulationCase.encodedLength,
        std::to_string(config.sourcePayloadEbN0Db), pool.framePoolId(),
        "seed=" + std::to_string(config.globalSeed) + ";group=" +
            std::to_string(simulationCase.payloadLength * 1000000ULL + config.snrIndex),
        stopText, channelText + ";schema=bch.s2.multipath.result.v1"));
    FixedMultipathMmseEqualizer equalizer(
        simulationCase.encodedLength, channel, result.noiseVariance);
    result.equalizerSetupTimeUs = equalizer.setupTimeUs();
    result.equalizationTimesUs.reserve(static_cast<std::size_t>(config.frameCount));
    result.decodeTimesUs.reserve(static_cast<std::size_t>(config.frameCount));
    prepareBchCase(simulationCase);
    if (config.resume) {
        if (config.checkpointPath.empty()) throw std::invalid_argument("resume requires checkpoint");
        restoreCheckpoint(result);
        if (result.processedFrames > config.frameCount) throw std::invalid_argument("checkpoint beyond run");
    }

    std::ofstream detail;
    if (config.writeFrameDetail) {
        detail.open(fs::path(config.outputDirectory) / "frame_detail.csv");
        detail << "caseName,sourcePayloadEbN0Db,snrDb,snrIndex,frameIndex,preHardBitErrors,postHardBitErrors,decodedBitErrors,trueSuccess,reportedSuccess,miscorrection,decoderFailure\n";
    }
    const auto runStart = std::chrono::steady_clock::now();
    auto lastProgress = runStart;
    const std::uint64_t noiseGroup =
        simulationCase.payloadLength * 1000000ULL + config.snrIndex;
    for (std::uint64_t offset = result.processedFrames; offset < config.frameCount; ++offset) {
        const std::uint64_t frameIndex = config.frameStart + offset;
        const auto payload = pool.readFrame(frameIndex).payloadBits;
        const auto encoded = encodeBchFrame(simulationCase, payload);
        const auto symbols = common::bpskModulate(encoded.codeword);
        const auto noise = common::generateStandardGaussianFrame(
            config.globalSeed, noiseGroup, frameIndex,
            equalizer.observationCount(), 1U);
        const auto receiverStart = std::chrono::steady_clock::now();
        const auto channelOutput = equalizer.apply(symbols, noise);
        const std::uint64_t preErrors =
            common::countBitErrors(encoded.codeword, channelOutput.preEqualizationHardBits);
        const std::uint64_t postErrors =
            common::countBitErrors(encoded.codeword, channelOutput.hardBits);
        const auto decodeStart = std::chrono::steady_clock::now();
        auto decoded = decodeBchFrame(simulationCase, channelOutput.hardBits);
        const auto decodeEnd = std::chrono::steady_clock::now();
        auditDecodedBchFrame(payload, decoded);
        const auto receiverEnd = std::chrono::steady_clock::now();
        const std::uint64_t decodedErrors = common::countBitErrors(payload, decoded.payload);
        const double decodeUs =
            std::chrono::duration<double, std::micro>(decodeEnd - decodeStart).count();
        const double receiverUs =
            std::chrono::duration<double, std::micro>(receiverEnd - receiverStart).count();
        ++result.processedFrames;
        result.processedPayloadBits += simulationCase.payloadLength;
        result.preEqualizationHardBitErrors += preErrors;
        result.preEqualizationHardFrameErrors += preErrors != 0U;
        result.postEqualizationHardBitErrors += postErrors;
        result.postEqualizationHardFrameErrors += postErrors != 0U;
        result.decodedBitErrors += decodedErrors;
        result.decodedFrameErrors += decodedErrors != 0U;
        result.trueSuccessFrames += decoded.trueSuccess;
        result.reportedSuccessFrames += decoded.reportedSuccess;
        result.miscorrectedFrames += decoded.miscorrected;
        result.decoderFailureFrames += decoded.decoderFailure;
        result.equalizationTimeUsSum += channelOutput.equalizationTimeUs;
        result.decodeTimeUsSum += decodeUs;
        result.totalReceiverTimeUsSum += receiverUs;
        result.equalizationTimesUs.push_back(channelOutput.equalizationTimeUs);
        result.decodeTimesUs.push_back(decodeUs);
        if (detail) {
            detail << simulationCase.caseName << ',' << config.sourcePayloadEbN0Db << ','
                   << result.snrDb << ',' << config.snrIndex << ',' << frameIndex << ','
                   << preErrors << ',' << postErrors << ',' << decodedErrors << ','
                   << decoded.trueSuccess << ',' << decoded.reportedSuccess << ','
                   << decoded.miscorrected << ',' << decoded.decoderFailure << '\n';
        }
        const auto now = std::chrono::steady_clock::now();
        if (config.progress &&
            (std::chrono::duration<double>(now - lastProgress).count() >=
                 config.progressRefreshSeconds ||
             result.processedFrames == config.frameCount)) {
            lastProgress = now;
            const double fer = static_cast<double>(result.decodedFrameErrors) /
                               result.processedFrames;
            const double elapsed =
                std::chrono::duration<double>(now - runStart).count();
            std::cerr << "[S2-04][" << simulationCase.caseName << "][Es/N0 "
                      << result.snrDb << " dB] frames " << result.processedFrames
                      << '/' << config.frameCount << " FE " << result.decodedFrameErrors
                      << " FER " << std::scientific << fer << std::fixed
                      << " speed " << static_cast<std::uint64_t>(
                             result.processedFrames / std::max(1e-9, elapsed))
                      << " frame/s checkpoint " << result.checkpointCount << '\r';
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
    validateAccounting(result, simulationCase);
    return result;
}

void writeMultipathPointSummary(
    const MultipathPointResult& result, const std::string& path) {
    const auto& value = bchSimulationCase(result.config.caseId);
    const double frames = static_cast<double>(result.processedFrames);
    const double payloadBits = static_cast<double>(result.processedPayloadBits);
    const double encodedBits = frames * value.encodedLength;
    const auto channel = frozenFixedMultipathConfig();
    std::ofstream out(path);
    if (!out) throw std::runtime_error("failed to open multipath summary");
    out << "schemaVersion,runId,experimentName,channelType,channelProfileId,caseName,organization,decoderType,payloadLength,encodedLength,frameRate,sourcePayloadEbN0Db,snrDb,noiseSigma,noiseVariance,rawTaps,normalizedTaps,delays,channelEnergy,equalizerType,receiverKnowsChannel,equalizerMethod,equalizerSetupTimeUs,processedFrames,processedPayloadBits,preEqualizationHardBitErrors,preEqualizationHardFrameErrors,postEqualizationHardBitErrors,postEqualizationHardFrameErrors,decodedBitErrors,decodedFrameErrors,BER,FER,trueSuccessFrames,trueSuccessRate,reportedSuccessFrames,reportedSuccessRate,miscorrectedFrames,miscorrectionRate,decoderFailureFrames,decoderFailureRate,preEqualizationHardBER,postEqualizationHardBER,avgEqualizationTimeUs,p50EqualizationTimeUs,p95EqualizationTimeUs,p99EqualizationTimeUs,maxEqualizationTimeUs,avgDecodeTimeUs,p50DecodeTimeUs,p95DecodeTimeUs,p99DecodeTimeUs,maxDecodeTimeUs,avgTotalReceiverTimeUs,minFrames,targetFrameErrors,maxFrames,stopReason,checkpointCount,resumeCount,shardIndex,shardCount,configHash,gitCommit\n";
    out << "bch.s2.multipath.result.v1,bch-s2-seed" << result.config.globalSeed
        << ",fixed_multipath_mmse,FIXED_MULTIPATH_MMSE,fixed_1_065_035_d0_1_3,"
        << value.caseName << ',' << organizationName(value.organization) << ','
        << decoderTypeName(value.decoderType) << ',' << value.payloadLength << ','
        << value.encodedLength << ',' << std::setprecision(17) << value.frameRate << ','
        << result.config.sourcePayloadEbN0Db << ',' << result.snrDb << ','
        << result.noiseSigma << ',' << result.noiseVariance
        << ",\"1;0.65;0.35\",\"" << channel.normalizedTaps[0] << ';'
        << channel.normalizedTaps[1] << ';' << channel.normalizedTaps[2]
        << "\",\"0;1;3\"," << channelEnergy(channel.normalizedTaps)
        << ",KNOWN_CHANNEL_LINEAR_MMSE,1,BANDED_CHOLESKY_NORMAL_EQUATIONS,"
        << result.equalizerSetupTimeUs << ',' << result.processedFrames << ','
        << result.processedPayloadBits << ',' << result.preEqualizationHardBitErrors
        << ',' << result.preEqualizationHardFrameErrors << ','
        << result.postEqualizationHardBitErrors << ','
        << result.postEqualizationHardFrameErrors << ',' << result.decodedBitErrors
        << ',' << result.decodedFrameErrors << ',' << result.decodedBitErrors / payloadBits
        << ',' << result.decodedFrameErrors / frames << ',' << result.trueSuccessFrames
        << ',' << result.trueSuccessFrames / frames << ',' << result.reportedSuccessFrames
        << ',' << result.reportedSuccessFrames / frames << ',' << result.miscorrectedFrames
        << ',' << result.miscorrectedFrames / frames << ',' << result.decoderFailureFrames
        << ',' << result.decoderFailureFrames / frames << ','
        << result.preEqualizationHardBitErrors / encodedBits << ','
        << result.postEqualizationHardBitErrors / encodedBits << ','
        << result.equalizationTimeUsSum / frames << ','
        << percentile(result.equalizationTimesUs, 0.50) << ','
        << percentile(result.equalizationTimesUs, 0.95) << ','
        << percentile(result.equalizationTimesUs, 0.99) << ','
        << (result.equalizationTimesUs.empty() ? 0.0 :
            *std::max_element(result.equalizationTimesUs.begin(), result.equalizationTimesUs.end()))
        << ',' << result.decodeTimeUsSum / frames << ','
        << percentile(result.decodeTimesUs, 0.50) << ','
        << percentile(result.decodeTimesUs, 0.95) << ','
        << percentile(result.decodeTimesUs, 0.99) << ','
        << (result.decodeTimesUs.empty() ? 0.0 :
            *std::max_element(result.decodeTimesUs.begin(), result.decodeTimesUs.end()))
        << ',' << result.totalReceiverTimeUsSum / frames << ',' << result.config.minFrames
        << ',' << result.config.targetFrameErrors << ',' << result.config.maxFrames << ','
        << result.stopReason << ',' << result.checkpointCount << ',' << result.resumeCount
        << ',' << result.config.shardIndex << ',' << result.config.shardCount << ','
        << result.configHash << ",WORKTREE\n";
}

}  // namespace scl::bch::simulation
