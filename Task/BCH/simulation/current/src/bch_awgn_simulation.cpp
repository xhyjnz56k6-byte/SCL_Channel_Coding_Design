#include "bch_simulation/bch_awgn_simulation.hpp"

#include "common/awgn_channel.hpp"
#include "common/demodulation.hpp"
#include "common/gaussian_noise.hpp"
#include "common/modulation.hpp"
#include "common/sha256.hpp"
#include "common/simulation_metrics.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
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

std::string timestampUtc() {
    const auto now = std::chrono::system_clock::now();
    const std::time_t value = std::chrono::system_clock::to_time_t(now);
    std::tm tm{};
#ifdef _WIN32
    gmtime_s(&tm, &value);
#else
    gmtime_r(&value, &tm);
#endif
    std::ostringstream out;
    out << std::put_time(&tm, "%Y-%m-%dT%H:%M:%SZ");
    return out.str();
}

class ProgressReporter {
public:
    ProgressReporter(const AwgnPointConfig& config, const std::string& caseName, std::ofstream& jsonl)
        : config_(config), caseName_(caseName), jsonl_(jsonl), started_(Clock::now()), last_(started_) {}

    void update(const AwgnPointResult& result, bool force) {
        const auto now = Clock::now();
        const double since = std::chrono::duration<double>(now - last_).count();
        if (!force && since < config_.progressRefreshSeconds) return;
        last_ = now;
        const double elapsed = std::max(1e-9, std::chrono::duration<double>(now - started_).count());
        const double rate = static_cast<double>(result.processedFrames) / elapsed;
        const double remaining = static_cast<double>(config_.frameCount - result.processedFrames);
        const double eta = rate > 0.0 ? remaining / rate : 0.0;
        const double ber = result.processedPayloadBits == 0U ? 0.0 :
            static_cast<double>(result.decodedBitErrors) / result.processedPayloadBits;
        const double fer = result.processedFrames == 0U ? 0.0 :
            static_cast<double>(result.decodedFrameErrors) / result.processedFrames;
        if (config_.progress) {
            std::cerr << '[' << config_.stage << "][" << caseName_ << "][" << config_.ebN0Db << " dB] "
                      << "frames " << result.processedFrames << '/' << config_.frameCount
                      << " FE " << result.decodedFrameErrors << " BER " << std::scientific << ber
                      << " FER " << fer << std::fixed << " speed " << static_cast<std::uint64_t>(rate)
                      << " frame/s elapsed " << std::setprecision(1) << elapsed << "s ETA " << eta
                      << "s checkpoint 0 shard 1/1" << (force ? '\n' : '\r');
        }
        if (jsonl_) {
            jsonl_ << "{\"timestamp\":\"" << timestampUtc() << "\",\"stage\":\"" << config_.stage
                   << "\",\"caseName\":\"" << caseName_ << "\",\"ebn0Db\":" << config_.ebN0Db
                   << ",\"processedFrames\":" << result.processedFrames
                   << ",\"frameErrors\":" << result.decodedFrameErrors
                   << ",\"bitErrors\":" << result.decodedBitErrors
                   << ",\"elapsedSeconds\":" << elapsed << ",\"framesPerSecond\":" << rate
                   << ",\"etaSeconds\":" << eta << ",\"checkpointCount\":0,\"shardIndex\":0,\"status\":\""
                   << (force ? "COMPLETE" : "RUNNING") << "\"}\n";
        }
    }

private:
    using Clock = std::chrono::steady_clock;
    const AwgnPointConfig& config_;
    std::string caseName_;
    std::ofstream& jsonl_;
    Clock::time_point started_;
    Clock::time_point last_;
};

void validateResult(const AwgnPointResult& value, const BchSimulationCase& simulationCase) {
    if (value.processedFrames != value.trueSuccessFrames + value.decodedFrameErrors ||
        value.processedFrames != value.reportedSuccessFrames + value.decoderFailureFrames ||
        value.miscorrectedFrames > value.reportedSuccessFrames ||
        value.processedPayloadBits != value.processedFrames * simulationCase.payloadLength ||
        value.decodedBitErrors > value.processedPayloadBits ||
        value.noErrorStatusFrames + value.correctedStatusFrames + value.failedStatusFrames != value.processedFrames) {
        throw std::logic_error("AWGN result accounting mismatch");
    }
}

}  // namespace

std::uint64_t pairedNoiseGroupId(common::Length payloadLength, std::size_t snrIndex) {
    if (payloadLength != 200U && payloadLength != 300U) throw std::invalid_argument("unsupported paired payload group");
    return static_cast<std::uint64_t>(payloadLength) * 1000000ULL + static_cast<std::uint64_t>(snrIndex);
}

double independentSigmaReference(const BchSimulationCase& simulationCase, double ebN0Db) {
    const double rate = static_cast<double>(simulationCase.payloadLength) / simulationCase.encodedLength;
    return std::sqrt(1.0 / (2.0 * rate * std::pow(10.0, ebN0Db / 10.0)));
}

std::string standardNoiseHash(const common::RealVector& standardNoise) {
    common::Sha256 sha;
    for (double value : standardNoise) {
        std::uint64_t bits = 0U;
        static_assert(sizeof(bits) == sizeof(value), "double hash representation mismatch");
        std::memcpy(&bits, &value, sizeof(bits));
        std::uint8_t bytes[8];
        for (unsigned i = 0; i < 8U; ++i) bytes[i] = static_cast<std::uint8_t>((bits >> (8U * i)) & 0xffU);
        sha.update(bytes, 8U);
    }
    return sha.finalHex();
}

AwgnPointResult runAwgnPoint(const AwgnPointConfig& config) {
    if (config.frameCount == 0U || config.framePoolManifest.empty() || config.outputDirectory.empty() ||
        !std::isfinite(config.progressRefreshSeconds) || config.progressRefreshSeconds <= 0.0) {
        throw std::invalid_argument("invalid AWGN point configuration");
    }
    const BchSimulationCase& simulationCase = bchSimulationCase(config.caseId);
    common::PackedFramePoolReader pool(config.framePoolManifest);
    if (pool.payloadLength() != simulationCase.payloadLength ||
        config.frameStart + config.frameCount > pool.frameCount()) {
        throw std::invalid_argument("frame pool does not cover AWGN point");
    }
    fs::create_directories(config.outputDirectory);
    std::ofstream detail;
    if (config.writeFrameDetail) {
        detail.open(fs::path(config.outputDirectory) / "frame_detail.csv");
        if (!detail) throw std::runtime_error("failed to open frame detail output");
        detail << "caseName,ebn0Db,snrIndex,frameIndex,noiseHash,channelHardBitErrors,decodedBitErrors,trueSuccess,reportedSuccess,miscorrected,decoderFailure,frameStatus\n";
    }
    std::ofstream progress(fs::path(config.outputDirectory) / "progress.jsonl");
    if (!progress) throw std::runtime_error("failed to open progress output");
    ProgressReporter reporter(config, simulationCase.caseName, progress);

    common::CodeLengths lengths;
    lengths.payloadLength = simulationCase.payloadLength;
    lengths.codecInputLength = simulationCase.payloadLength + simulationCase.fillerLength + simulationCase.shorteningLength;
    lengths.encodedLength = simulationCase.encodedLength;
    lengths.transmittedLength = simulationCase.encodedLength;
    lengths.fillerLength = simulationCase.fillerLength;
    lengths.shortenedLength = simulationCase.shorteningLength;
    AwgnPointResult result;
    result.config = config;
    result.noiseSigma = common::computeAwgnSigma(lengths, config.ebN0Db);
    result.noiseVariance = result.noiseSigma * result.noiseSigma;
    result.decodeTimesUs.reserve(static_cast<std::size_t>(config.frameCount));
    const std::uint64_t noiseGroup = pairedNoiseGroupId(simulationCase.payloadLength, config.snrIndex);

    for (std::uint64_t offset = 0U; offset < config.frameCount; ++offset) {
        const common::FrameIndex frameIndex = config.frameStart + offset;
        const auto payload = pool.readFrame(frameIndex).payloadBits;
        const auto encodeStart = std::chrono::steady_clock::now();
        const auto encoded = encodeBchFrame(simulationCase, payload);
        const auto encodeEnd = std::chrono::steady_clock::now();
        const auto standardNoise = common::generateStandardGaussianFrame(
            config.globalSeed, noiseGroup, frameIndex, simulationCase.encodedLength, kBchNoisePolicyVersion);
        const std::string noiseHash = standardNoiseHash(standardNoise);
        if (offset == 0U) result.firstNoiseHash = noiseHash;
        result.lastNoiseHash = noiseHash;
        const auto received = common::applyAwgn(common::bpskModulate(encoded.codeword), standardNoise, result.noiseSigma);
        const auto hard = common::hardDecision(received);
        const std::uint64_t channelErrors = common::countBitErrors(encoded.codeword, hard);
        const auto decodeStart = std::chrono::steady_clock::now();
        auto decoded = decodeBchFrame(simulationCase, hard);
        const auto decodeEnd = std::chrono::steady_clock::now();
        auditDecodedBchFrame(payload, decoded);
        const std::uint64_t decodedErrors = common::countBitErrors(payload, decoded.payload);
        const double encodeUs = std::chrono::duration<double, std::micro>(encodeEnd - encodeStart).count();
        const double decodeUs = std::chrono::duration<double, std::micro>(decodeEnd - decodeStart).count();
        ++result.processedFrames;
        result.processedPayloadBits += simulationCase.payloadLength;
        result.channelHardBitErrors += channelErrors;
        result.channelHardFrameErrors += channelErrors != 0U;
        result.decodedBitErrors += decodedErrors;
        result.decodedFrameErrors += decodedErrors != 0U;
        result.trueSuccessFrames += decoded.trueSuccess;
        result.reportedSuccessFrames += decoded.reportedSuccess;
        result.miscorrectedFrames += decoded.miscorrected;
        result.decoderFailureFrames += decoded.decoderFailure;
        result.noErrorStatusFrames += decoded.frameStatus == "NO_ERROR";
        result.correctedStatusFrames += decoded.frameStatus == "CORRECTED";
        result.failedStatusFrames += decoded.frameStatus == "DECODER_FAILURE" || decoded.decoderFailure;
        result.encodeTimeUsSum += encodeUs;
        result.decodeTimeUsSum += decodeUs;
        result.decodeTimesUs.push_back(decodeUs);
        if (detail) {
            detail << simulationCase.caseName << ',' << config.ebN0Db << ',' << config.snrIndex << ','
                   << frameIndex << ',' << noiseHash << ',' << channelErrors << ',' << decodedErrors << ','
                   << decoded.trueSuccess << ',' << decoded.reportedSuccess << ',' << decoded.miscorrected << ','
                   << decoded.decoderFailure << ',' << decoded.frameStatus << '\n';
        }
        reporter.update(result, offset + 1U == config.frameCount);
    }
    validateResult(result, simulationCase);
    return result;
}

void writeAwgnPointSummary(const AwgnPointResult& result, const std::string& path) {
    const auto& value = bchSimulationCase(result.config.caseId);
    const double frames = static_cast<double>(result.processedFrames);
    const double bits = static_cast<double>(result.processedPayloadBits);
    const double ber = result.decodedBitErrors / bits;
    const double fer = result.decodedFrameErrors / frames;
    const double maxDecode = result.decodeTimesUs.empty() ? 0.0 : *std::max_element(result.decodeTimesUs.begin(), result.decodeTimesUs.end());
    std::ofstream out(path);
    if (!out) throw std::runtime_error("failed to open summary output");
    out << "schemaVersion,stage,caseName,organization,decoderType,payloadLength,encodedLength,frameRate,ebn0Db,ebn0Linear,noiseSigma,noiseVariance,globalSeed,noisePolicyVersion,snrIndex,processedFrames,processedPayloadBits,channelHardBitErrors,channelHardFrameErrors,decodedBitErrors,decodedFrameErrors,BER,FER,trueSuccessFrames,trueSuccessRate,reportedSuccessFrames,reportedSuccessRate,miscorrectedFrames,miscorrectionRate,decoderFailureFrames,decoderFailureRate,noErrorStatusFrames,correctedStatusFrames,failedStatusFrames,avgEncodeTimeUs,avgDecodeTimeUs,p50DecodeTimeUs,p95DecodeTimeUs,p99DecodeTimeUs,maxDecodeTimeUs,firstNoiseHash,lastNoiseHash,stopReason\n";
    out << "bch.group4.result.v1," << result.config.stage << ',' << value.caseName << ','
        << organizationName(value.organization) << ',' << decoderTypeName(value.decoderType) << ','
        << value.payloadLength << ',' << value.encodedLength << ',' << std::setprecision(17) << value.frameRate << ','
        << result.config.ebN0Db << ',' << common::ebN0Linear(result.config.ebN0Db) << ','
        << result.noiseSigma << ',' << result.noiseVariance << ',' << result.config.globalSeed << ','
        << kBchNoisePolicyVersion << ',' << result.config.snrIndex << ',' << result.processedFrames << ','
        << result.processedPayloadBits << ',' << result.channelHardBitErrors << ',' << result.channelHardFrameErrors << ','
        << result.decodedBitErrors << ',' << result.decodedFrameErrors << ',' << ber << ',' << fer << ','
        << result.trueSuccessFrames << ',' << result.trueSuccessFrames / frames << ','
        << result.reportedSuccessFrames << ',' << result.reportedSuccessFrames / frames << ','
        << result.miscorrectedFrames << ',' << result.miscorrectedFrames / frames << ','
        << result.decoderFailureFrames << ',' << result.decoderFailureFrames / frames << ','
        << result.noErrorStatusFrames << ',' << result.correctedStatusFrames << ',' << result.failedStatusFrames << ','
        << result.encodeTimeUsSum / frames << ',' << result.decodeTimeUsSum / frames << ','
        << percentile(result.decodeTimesUs, 0.50) << ',' << percentile(result.decodeTimesUs, 0.95) << ','
        << percentile(result.decodeTimesUs, 0.99) << ',' << maxDecode << ',' << result.firstNoiseHash << ','
        << result.lastNoiseHash << ",FIXED_FRAMES_REACHED\n";
}

}  // namespace scl::bch::simulation
