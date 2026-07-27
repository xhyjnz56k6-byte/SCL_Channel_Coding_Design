#include "bch_simulation/bch_burst_simulation.hpp"
#include "bch_simulation/bch_interleaver.hpp"

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace fs = std::filesystem;
namespace sim = scl::bch::simulation;

namespace {

constexpr const char* kSchema = "bch.s2.burst_checkpoint.v1";

struct Counts {
    std::uint64_t processedFrames = 0U;
    std::uint64_t processedBits = 0U;
    std::uint64_t bitErrors = 0U;
    std::uint64_t frameErrors = 0U;
    std::uint64_t reportedSuccess = 0U;
    std::uint64_t decoderFailures = 0U;
    std::uint64_t miscorrections = 0U;
    std::uint64_t explicitFailureWrongPayload = 0U;
    std::uint64_t touchedSubblocksSum = 0U;
    std::uint64_t maximumSubblockErrorWeightSum = 0U;
    std::uint64_t withinGuaranteedRegionCount = 0U;
    std::uint64_t oneErrorBlocksSum = 0U;
    std::uint64_t multiErrorBlocksSum = 0U;
    std::uint64_t minimumFailingStart = std::numeric_limits<std::uint64_t>::max();
    std::uint64_t maximumSuccessfulStart = 0U;
};

struct Options {
    std::string stage;
    std::string caseName;
    std::size_t burstLength = 0U;
    sim::InterleaverMode interleaverMode = sim::InterleaverMode::None;
    std::uint64_t masterSeed = 2026072607ULL;
    std::uint64_t frameBegin = 0U;
    std::uint64_t frameEnd = 0U;
    std::uint64_t shardIndex = 0U;
    std::uint64_t shardCount = 1U;
    fs::path checkpointDir;
    std::uint64_t checkpointEveryFrames = 100U;
    std::uint64_t stopAfterFrames = 0U;
    bool resume = false;
    fs::path output;
    std::string configTag = "default";
};

std::map<std::string, std::string> parse(int argc, char** argv) {
    std::map<std::string, std::string> values;
    for (int index = 1; index < argc; ++index) {
        const std::string key(argv[index]);
        if (key == "--resume") {
            values[key] = "1";
        } else {
            if (index + 1 >= argc || key.rfind("--", 0U) != 0U) {
                throw std::invalid_argument("invalid audit-runner arguments");
            }
            values[key] = argv[++index];
        }
    }
    return values;
}

const std::string& required(
    const std::map<std::string, std::string>& values, const std::string& key) {
    const auto found = values.find(key);
    if (found == values.end()) throw std::invalid_argument("missing " + key);
    return found->second;
}

Options options(int argc, char** argv) {
    const auto values = parse(argc, argv);
    Options result;
    result.stage = required(values, "--stage");
    result.caseName = required(values, "--case");
    result.burstLength = std::stoull(required(values, "--burst-length"));
    const std::string mode = required(values, "--interleaver-mode");
    if (mode == "NONE") result.interleaverMode = sim::InterleaverMode::None;
    else if (mode == "FIXED_RANDOM")
        result.interleaverMode = sim::InterleaverMode::FixedRandom;
    else throw std::invalid_argument("unsupported interleaver mode");
    result.masterSeed = std::stoull(required(values, "--master-seed"));
    result.frameBegin = std::stoull(required(values, "--frame-begin"));
    result.frameEnd = std::stoull(required(values, "--frame-end"));
    result.shardIndex = std::stoull(required(values, "--shard-index"));
    result.shardCount = std::stoull(required(values, "--shard-count"));
    result.checkpointDir = required(values, "--checkpoint-dir");
    result.checkpointEveryFrames =
        std::stoull(required(values, "--checkpoint-every-frames"));
    result.output = required(values, "--output");
    if (values.count("--stop-after-frames"))
        result.stopAfterFrames = std::stoull(values.at("--stop-after-frames"));
    if (values.count("--config-tag")) result.configTag = values.at("--config-tag");
    result.resume = values.count("--resume") != 0U;
    if ((result.stage != "s2-07c" && result.stage != "s2-07d") ||
        result.frameEnd <= result.frameBegin || result.shardCount == 0U ||
        result.shardIndex >= result.shardCount ||
        result.checkpointEveryFrames == 0U) {
        throw std::invalid_argument("invalid audit-runner configuration");
    }
    if (result.stage == "s2-07c" &&
        result.interleaverMode != sim::InterleaverMode::None) {
        throw std::invalid_argument("S2-07C requires NONE interleaver");
    }
    return result;
}

std::uint64_t fnv1a(const std::string& value) {
    std::uint64_t hash = 1469598103934665603ULL;
    for (unsigned char byte : value) {
        hash ^= static_cast<std::uint64_t>(byte);
        hash *= 1099511628211ULL;
    }
    return hash;
}

std::string hexHash(const std::string& value) {
    std::ostringstream out;
    out << std::hex << std::setw(16) << std::setfill('0') << fnv1a(value);
    return out.str();
}

std::string timestamp() {
    const auto now = std::chrono::system_clock::now();
    const auto seconds = std::chrono::duration_cast<std::chrono::seconds>(
        now.time_since_epoch()).count();
    return std::to_string(seconds);
}

void atomicReplace(const fs::path& temporary, const fs::path& target) {
#ifdef _WIN32
    DWORD lastError = ERROR_SUCCESS;
    for (int attempt = 0; attempt < 100; ++attempt) {
        if (MoveFileExW(temporary.wstring().c_str(), target.wstring().c_str(),
                        MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) {
            return;
        }
        lastError = GetLastError();
        if (lastError != ERROR_ACCESS_DENIED &&
            lastError != ERROR_SHARING_VIOLATION &&
            lastError != ERROR_LOCK_VIOLATION) {
            break;
        }
        Sleep(10);
    }
    throw std::runtime_error(
        "atomic MoveFileEx checkpoint replacement failed, Win32 error=" +
        std::to_string(lastError));
#else
    std::error_code error;
    fs::rename(temporary, target, error);
    if (error) throw std::runtime_error("atomic checkpoint rename failed");
#endif
}

void atomicWrite(const fs::path& path, const std::string& content) {
    fs::create_directories(path.parent_path());
    const fs::path temporary = path.string() + ".tmp";
    {
        std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
        if (!output) throw std::runtime_error("cannot write temporary file");
        output << content;
        output.flush();
        if (!output) throw std::runtime_error("temporary file flush failed");
    }
    atomicReplace(temporary, path);
}

std::string joinIndices(const std::vector<std::uint64_t>& values) {
    std::ostringstream out;
    for (std::size_t index = 0U; index < values.size(); ++index) {
        if (index) out << ';';
        out << values[index];
    }
    return out.str();
}

std::string configIdentity(
    const Options& value, const sim::BchSimulationCase& simulationCase,
    const sim::BchInterleaver& interleaver) {
    std::ostringstream out;
    out << value.stage << '|' << value.caseName << '|' << value.burstLength
        << '|' << sim::interleaverModeName(value.interleaverMode) << '|'
        << value.masterSeed << '|' << value.frameBegin << '|' << value.frameEnd
        << '|' << simulationCase.encodedLength << '|' << interleaver.permutationHash
        << '|' << interleaver.inversePermutationHash << '|' << value.configTag;
    return hexHash(out.str());
}

std::string checkpointBody(
    const Options& value, const sim::BchInterleaver& interleaver,
    const std::string& configHash, std::uint64_t nextFrameIndex,
    const Counts& counts, const std::vector<std::uint64_t>& frameIndices) {
    std::ostringstream out;
    out << "schemaVersion=" << kSchema << '\n'
        << "stage=" << value.stage << '\n'
        << "caseName=" << value.caseName << '\n'
        << "burstLength=" << value.burstLength << '\n'
        << "interleaverMode="
        << sim::interleaverModeName(value.interleaverMode) << '\n'
        << "masterSeed=" << value.masterSeed << '\n'
        << "configHash=" << configHash << '\n'
        << "frameBegin=" << value.frameBegin << '\n'
        << "frameEnd=" << value.frameEnd << '\n'
        << "shardIndex=" << value.shardIndex << '\n'
        << "shardCount=" << value.shardCount << '\n'
        << "nextFrameIndex=" << nextFrameIndex << '\n'
        << "processedFrames=" << counts.processedFrames << '\n'
        << "processedBits=" << counts.processedBits << '\n'
        << "bitErrors=" << counts.bitErrors << '\n'
        << "frameErrors=" << counts.frameErrors << '\n'
        << "reportedSuccess=" << counts.reportedSuccess << '\n'
        << "decoderFailures=" << counts.decoderFailures << '\n'
        << "miscorrections=" << counts.miscorrections << '\n'
        << "explicitFailureWrongPayload="
        << counts.explicitFailureWrongPayload << '\n'
        << "touchedSubblocksSum=" << counts.touchedSubblocksSum << '\n'
        << "maximumSubblockErrorWeightSum="
        << counts.maximumSubblockErrorWeightSum << '\n'
        << "withinGuaranteedRegionCount="
        << counts.withinGuaranteedRegionCount << '\n'
        << "oneErrorBlocksSum=" << counts.oneErrorBlocksSum << '\n'
        << "multiErrorBlocksSum=" << counts.multiErrorBlocksSum << '\n'
        << "minimumFailingStart=" << counts.minimumFailingStart << '\n'
        << "maximumSuccessfulStart=" << counts.maximumSuccessfulStart << '\n'
        << "permutationHash=" << interleaver.permutationHash << '\n'
        << "inversePermutationHash=" << interleaver.inversePermutationHash << '\n'
        << "frameIndices=" << joinIndices(frameIndices) << '\n'
        << "timestamp=" << timestamp() << '\n';
    return out.str();
}

void saveCheckpoint(
    const fs::path& path, const Options& value,
    const sim::BchInterleaver& interleaver, const std::string& configHash,
    std::uint64_t nextFrameIndex, const Counts& counts,
    const std::vector<std::uint64_t>& frameIndices) {
    const std::string body = checkpointBody(
        value, interleaver, configHash, nextFrameIndex, counts, frameIndices);
    atomicWrite(path, body + "checkpointHash=" + hexHash(body) + "\n");
}

std::map<std::string, std::string> readKeyValues(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("resume checkpoint does not exist");
    std::map<std::string, std::string> values;
    std::string line;
    while (std::getline(input, line)) {
        const auto equals = line.find('=');
        if (equals == std::string::npos)
            throw std::runtime_error("checkpoint line is malformed");
        values[line.substr(0U, equals)] = line.substr(equals + 1U);
    }
    return values;
}

std::vector<std::uint64_t> parseIndices(const std::string& text) {
    std::vector<std::uint64_t> result;
    if (text.empty()) return result;
    std::istringstream input(text);
    std::string part;
    while (std::getline(input, part, ';')) result.push_back(std::stoull(part));
    return result;
}

void requireEqual(
    const std::map<std::string, std::string>& values,
    const std::string& key, const std::string& expected,
    const std::string& message) {
    const auto found = values.find(key);
    if (found == values.end() || found->second != expected)
        throw std::runtime_error(message);
}

void loadCheckpoint(
    const fs::path& path, const Options& value,
    const sim::BchInterleaver& interleaver, const std::string& configHash,
    std::uint64_t& nextFrameIndex, Counts& counts,
    std::vector<std::uint64_t>& frameIndices) {
    const auto values = readKeyValues(path);
    requireEqual(values, "schemaVersion", kSchema, "checkpoint schema mismatch");
    requireEqual(values, "stage", value.stage, "checkpoint stage mismatch");
    requireEqual(values, "caseName", value.caseName, "checkpoint Case mismatch");
    requireEqual(values, "burstLength", std::to_string(value.burstLength),
                 "checkpoint burstLength mismatch");
    requireEqual(values, "interleaverMode",
                 sim::interleaverModeName(value.interleaverMode),
                 "checkpoint interleaver mode mismatch");
    requireEqual(values, "masterSeed", std::to_string(value.masterSeed),
                 "checkpoint seed mismatch");
    requireEqual(values, "permutationHash", interleaver.permutationHash,
                 "checkpoint interleaver hash mismatch");
    requireEqual(values, "inversePermutationHash",
                 interleaver.inversePermutationHash,
                 "checkpoint inverse interleaver hash mismatch");
    requireEqual(values, "configHash", configHash,
                 "checkpoint configHash mismatch");
    requireEqual(values, "frameBegin", std::to_string(value.frameBegin),
                 "checkpoint frameBegin mismatch");
    requireEqual(values, "frameEnd", std::to_string(value.frameEnd),
                 "checkpoint frameEnd mismatch");
    requireEqual(values, "shardIndex", std::to_string(value.shardIndex),
                 "checkpoint shardIndex mismatch");
    requireEqual(values, "shardCount", std::to_string(value.shardCount),
                 "checkpoint shardCount mismatch");
    std::ostringstream body;
    for (const std::string key : {
             "schemaVersion", "stage", "caseName", "burstLength",
             "interleaverMode", "masterSeed", "configHash", "frameBegin",
             "frameEnd", "shardIndex", "shardCount", "nextFrameIndex",
             "processedFrames", "processedBits", "bitErrors", "frameErrors",
             "reportedSuccess", "decoderFailures", "miscorrections",
             "explicitFailureWrongPayload", "touchedSubblocksSum",
             "maximumSubblockErrorWeightSum", "withinGuaranteedRegionCount",
             "oneErrorBlocksSum", "multiErrorBlocksSum", "minimumFailingStart",
             "maximumSuccessfulStart", "permutationHash",
             "inversePermutationHash", "frameIndices", "timestamp"}) {
        const auto found = values.find(key);
        if (found == values.end()) throw std::runtime_error("checkpoint field missing");
        body << key << '=' << found->second << '\n';
    }
    requireEqual(values, "checkpointHash", hexHash(body.str()),
                 "checkpoint hash mismatch");
    nextFrameIndex = std::stoull(values.at("nextFrameIndex"));
    counts.processedFrames = std::stoull(values.at("processedFrames"));
    counts.processedBits = std::stoull(values.at("processedBits"));
    counts.bitErrors = std::stoull(values.at("bitErrors"));
    counts.frameErrors = std::stoull(values.at("frameErrors"));
    counts.reportedSuccess = std::stoull(values.at("reportedSuccess"));
    counts.decoderFailures = std::stoull(values.at("decoderFailures"));
    counts.miscorrections = std::stoull(values.at("miscorrections"));
    counts.explicitFailureWrongPayload =
        std::stoull(values.at("explicitFailureWrongPayload"));
    counts.touchedSubblocksSum = std::stoull(values.at("touchedSubblocksSum"));
    counts.maximumSubblockErrorWeightSum =
        std::stoull(values.at("maximumSubblockErrorWeightSum"));
    counts.withinGuaranteedRegionCount =
        std::stoull(values.at("withinGuaranteedRegionCount"));
    counts.oneErrorBlocksSum = std::stoull(values.at("oneErrorBlocksSum"));
    counts.multiErrorBlocksSum = std::stoull(values.at("multiErrorBlocksSum"));
    counts.minimumFailingStart = std::stoull(values.at("minimumFailingStart"));
    counts.maximumSuccessfulStart =
        std::stoull(values.at("maximumSuccessfulStart"));
    frameIndices = parseIndices(values.at("frameIndices"));
    if (frameIndices.size() != counts.processedFrames)
        throw std::runtime_error("checkpoint frame-index count mismatch");
}

scl::common::BitVector payload(
    const sim::BchSimulationCase& value, std::uint64_t seed,
    std::uint64_t frameIndex, std::uint64_t domain) {
    scl::common::BitVector result(value.payloadLength);
    for (std::size_t index = 0U; index < result.size(); ++index) {
        result[index] = static_cast<std::uint8_t>(
            sim::burstDomainValue(
                seed, frameIndex, domain + index * 0x9e3779b9ULL) & 1U);
    }
    return result;
}

void observe(
    Counts& counts, const sim::BchSimulationCase& value,
    const scl::common::BitVector& originalPayload,
    sim::DecodedBchFrame decoded, const sim::BurstStructure& structure,
    std::size_t start) {
    sim::auditDecodedBchFrame(originalPayload, decoded);
    ++counts.processedFrames;
    counts.processedBits += value.payloadLength;
    for (std::size_t index = 0U; index < originalPayload.size(); ++index)
        counts.bitErrors += originalPayload[index] != decoded.payload[index] ? 1U : 0U;
    counts.frameErrors += decoded.trueSuccess ? 0U : 1U;
    counts.reportedSuccess += decoded.reportedSuccess ? 1U : 0U;
    counts.decoderFailures += decoded.decoderFailure ? 1U : 0U;
    counts.miscorrections += decoded.miscorrected ? 1U : 0U;
    counts.explicitFailureWrongPayload +=
        decoded.decoderFailure && !decoded.trueSuccess ? 1U : 0U;
    counts.touchedSubblocksSum += structure.touchedSubblockCount;
    counts.maximumSubblockErrorWeightSum += structure.maximumSubblockErrorWeight;
    counts.withinGuaranteedRegionCount +=
        structure.allSubblocksWithinGuaranteedRegion ? 1U : 0U;
    counts.oneErrorBlocksSum += structure.numberOfSubblocksWithOneError;
    counts.multiErrorBlocksSum +=
        structure.numberOfSubblocksWithMoreThanOneError;
    if (decoded.trueSuccess)
        counts.maximumSuccessfulStart =
            std::max<std::uint64_t>(counts.maximumSuccessfulStart, start);
    else
        counts.minimumFailingStart =
            std::min<std::uint64_t>(counts.minimumFailingStart, start);
}

std::string resultBody(
    const Options& value, const sim::BchInterleaver& interleaver,
    const std::string& configHash, const Counts& counts,
    const std::vector<std::uint64_t>& frameIndices) {
    std::ostringstream out;
    out << "schemaVersion,stage,caseName,burstLength,interleaverMode,"
           "masterSeed,configHash,frameBegin,frameEnd,shardIndex,shardCount,"
           "frameIndices,processedFrames,processedBits,bitErrors,frameErrors,"
           "reportedSuccess,decoderFailures,miscorrections,"
           "explicitFailureWrongPayload,touchedSubblocksSum,"
           "maximumSubblockErrorWeightSum,withinGuaranteedRegionCount,"
           "oneErrorBlocksSum,multiErrorBlocksSum,minimumFailingStart,"
           "maximumSuccessfulStart,permutationHash,inversePermutationHash,"
           "resultHash\n";
    std::ostringstream record;
    record << kSchema << ',' << value.stage << ',' << value.caseName << ','
           << value.burstLength << ','
           << sim::interleaverModeName(value.interleaverMode) << ','
           << value.masterSeed << ',' << configHash << ',' << value.frameBegin
           << ',' << value.frameEnd << ',' << value.shardIndex << ','
           << value.shardCount << ',' << joinIndices(frameIndices) << ','
           << counts.processedFrames << ',' << counts.processedBits << ','
           << counts.bitErrors << ',' << counts.frameErrors << ','
           << counts.reportedSuccess << ',' << counts.decoderFailures << ','
           << counts.miscorrections << ','
           << counts.explicitFailureWrongPayload << ','
           << counts.touchedSubblocksSum << ','
           << counts.maximumSubblockErrorWeightSum << ','
           << counts.withinGuaranteedRegionCount << ','
           << counts.oneErrorBlocksSum << ',' << counts.multiErrorBlocksSum
           << ',' << counts.minimumFailingStart << ','
           << counts.maximumSuccessfulStart << ','
           << interleaver.permutationHash << ','
           << interleaver.inversePermutationHash << ',';
    const std::string withoutHash = record.str();
    out << withoutHash << hexHash(withoutHash) << '\n';
    return out.str();
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const Options value = options(argc, argv);
        const auto& simulationCase = sim::bchSimulationCase(value.caseName);
        if (value.burstLength > simulationCase.encodedLength)
            throw std::invalid_argument("burst length exceeds encoded length");
        sim::prepareBchCase(simulationCase);
        const std::uint64_t interleaverSeed = sim::burstDomainValue(
            value.masterSeed, simulationCase.encodedLength, 4001U);
        const auto interleaver = sim::makeBchInterleaver(
            simulationCase.encodedLength, value.interleaverMode,
            value.interleaverMode == sim::InterleaverMode::None
                ? 0U : interleaverSeed);
        const std::string configHash =
            configIdentity(value, simulationCase, interleaver);
        const std::string slug = value.stage + "_" + value.caseName + "_l" +
            std::to_string(value.burstLength) + "_" +
            sim::interleaverModeName(value.interleaverMode) + "_shard" +
            std::to_string(value.shardIndex);
        const fs::path checkpointPath = value.checkpointDir / (slug + ".checkpoint");
        Counts counts;
        std::vector<std::uint64_t> frameIndices;
        std::uint64_t nextFrameIndex = value.frameBegin;
        if (value.resume) {
            loadCheckpoint(checkpointPath, value, interleaver, configHash,
                           nextFrameIndex, counts, frameIndices);
        } else if (fs::exists(checkpointPath)) {
            throw std::runtime_error(
                "checkpoint already exists; use --resume or a clean directory");
        }
        std::uint64_t sinceCheckpoint = 0U;
        for (std::uint64_t frame = nextFrameIndex; frame < value.frameEnd; ++frame) {
            nextFrameIndex = frame + 1U;
            if (frame % value.shardCount != value.shardIndex) continue;
            const std::uint64_t lengthSeed = sim::burstDomainValue(
                value.masterSeed, simulationCase.encodedLength,
                value.stage == "s2-07c" ? value.burstLength :
                                          4100U + value.burstLength);
            const std::uint64_t payloadDomain =
                value.stage == "s2-07c" ? 3001U : 4003U;
            const std::uint64_t startDomain =
                value.stage == "s2-07c" ? 3003U : 4005U;
            const auto original =
                payload(simulationCase, lengthSeed, frame, payloadDomain);
            const auto encoded =
                sim::encodeBchFrame(simulationCase, original).codeword;
            const std::size_t start = sim::uniformBurstStart(
                simulationCase.encodedLength, value.burstLength,
                lengthSeed, frame, startDomain);
            const auto transmitted = sim::interleave(encoded, interleaver);
            const auto damaged = sim::injectConsecutiveBitBurst(
                transmitted, start, value.burstLength);
            const auto received = sim::deinterleave(damaged, interleaver);
            const auto positions = sim::errorPositions(encoded, received);
            if (positions.size() != value.burstLength)
                throw std::runtime_error(
                    "FAIL_BCH_S2_07D_ERROR_WEIGHT_CONSERVATION");
            const auto structure = sim::analyzeBurstStructure(
                simulationCase, positions, start, value.burstLength);
            observe(counts, simulationCase, original,
                    sim::decodeBchFrame(simulationCase, received),
                    structure, start);
            frameIndices.push_back(frame);
            ++sinceCheckpoint;
            if (sinceCheckpoint >= value.checkpointEveryFrames) {
                saveCheckpoint(checkpointPath, value, interleaver, configHash,
                               nextFrameIndex, counts, frameIndices);
                sinceCheckpoint = 0U;
            }
            if (value.stopAfterFrames != 0U &&
                counts.processedFrames >= value.stopAfterFrames) {
                saveCheckpoint(checkpointPath, value, interleaver, configHash,
                               nextFrameIndex, counts, frameIndices);
                std::cout << "PARTIAL_BCH_S2_BURST_CHECKPOINT frames="
                          << counts.processedFrames << '\n';
                return 0;
            }
        }
        saveCheckpoint(checkpointPath, value, interleaver, configHash,
                       nextFrameIndex, counts, frameIndices);
        atomicWrite(value.output, resultBody(
            value, interleaver, configHash, counts, frameIndices));
        std::cout << "PASS_BCH_S2_BURST_AUDIT_POINT frames="
                  << counts.processedFrames << " result=" << value.output << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_BCH_S2_BURST_AUDIT_POINT: "
                  << error.what() << '\n';
        return 1;
    }
}
