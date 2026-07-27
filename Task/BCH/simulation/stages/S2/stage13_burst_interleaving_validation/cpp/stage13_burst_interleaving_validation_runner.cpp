#include "stage13_burst_interleaving_validation_core.hpp"
#include "stage13_burst_interleaving_validation_simulation.hpp"
#include "stage02_case_contract.hpp"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace {

namespace stage02 = scl::bch::s2::stage02;
namespace stage13 = scl::bch::s2::stage13;

using stage13::InterleaverMode;
using stage13::SimulationPoint;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

std::string bitsToString(const scl::common::BitVector& bits) {
    std::string text;
    text.reserve(bits.size());
    for (const auto bit : bits) text.push_back(bit == 0U ? '0' : '1');
    return text;
}

bool expectInvalid(const std::function<void()>& operation) {
    try {
        operation();
    } catch (const std::invalid_argument&) {
        return true;
    }
    return false;
}

std::string statusName(const stage13::FrameTrace& trace) {
    if (stage13::bitErrors(trace.payload, trace.recoveredPayload) == 0U) {
        return "TRUE_SUCCESS";
    }
    return trace.decoderDeclaredSuccess
        ? "MISCORRECTION" : "DECODER_FAILURE";
}

std::vector<std::pair<InterleaverMode, std::size_t>>
prescanConfigurations() {
    std::vector<std::pair<InterleaverMode, std::size_t>> result{
        {InterleaverMode::None, 1U}};
    for (const auto mode : {InterleaverMode::Block,
                            InterleaverMode::RowColumn,
                            InterleaverMode::Pseudorandom}) {
        for (const std::size_t depth : {4U, 8U, 16U, 32U}) {
            result.push_back({mode, depth});
        }
    }
    return result;
}

std::vector<std::pair<InterleaverMode, std::size_t>>
validationConfigurations() {
    std::vector<std::pair<InterleaverMode, std::size_t>> result{
        {InterleaverMode::None, 1U}};
    for (const auto mode : {InterleaverMode::Block,
                            InterleaverMode::RowColumn,
                            InterleaverMode::Pseudorandom}) {
        for (const std::size_t depth : {4U, 8U, 16U}) {
            result.push_back({mode, depth});
        }
    }
    return result;
}

void writeCaseContracts(const fs::path& path) {
    std::ofstream output(path);
    if (!output) throw std::runtime_error("cannot create case contract CSV");
    output <<
        "caseId,legendLabel,payloadLength,motherN,motherK,motherT,"
        "blockCount,encodedLength,actualRate\n";
    output << std::setprecision(17);
    for (const auto& contract : stage02::allCaseContracts()) {
        output << contract.caseId << ',' << contract.legendLabel << ','
               << contract.payloadLength << ',' << contract.motherN << ','
               << contract.motherK << ',' << contract.motherT << ','
               << contract.blockCount << ',' << contract.totalEncodedLength
               << ',' << contract.actualRate << '\n';
    }
}

void writePermutations(const fs::path& path, std::uint64_t seed) {
    std::ofstream output(path);
    if (!output) throw std::runtime_error("cannot create permutation CSV");
    output <<
        "caseId,encodedLength,interleaverMode,interleaverDepth,"
        "interleaverSeed,outputIndex,inputIndex,permutationFnv1a64\n";
    for (const auto& contract : stage02::allCaseContracts()) {
        for (const auto [mode, depth] : validationConfigurations()) {
            const auto permutation = stage13::makePermutation(
                contract.totalEncodedLength,
                {mode, depth,
                 mode == InterleaverMode::Pseudorandom ? seed : 0U,
                 contract.caseId});
            const auto hash = stage13::fnv1a64(permutation);
            for (std::size_t outputIndex = 0U;
                 outputIndex < permutation.size(); ++outputIndex) {
                output << contract.caseId << ','
                       << contract.totalEncodedLength << ','
                       << stage13::interleaverModeName(mode) << ',' << depth
                       << ',' << (mode == InterleaverMode::Pseudorandom
                                      ? seed : 0U)
                       << ',' << outputIndex << ','
                       << permutation[outputIndex] << ',' << hash << '\n';
            }
        }
    }
}

void writeValidationVectors(const fs::path& vectorsPath,
                            const fs::path& cppPath,
                            std::uint64_t masterSeed,
                            std::uint64_t interleaverSeed) {
    std::ofstream vectors(vectorsPath);
    std::ofstream output(cppPath);
    if (!vectors || !output) {
        throw std::runtime_error("cannot create validation vector CSV");
    }
    vectors <<
        "caseId,vectorId,interleaverMode,interleaverDepth,"
        "burstLengthBits,burstStart\n";
    output <<
        "caseId,vectorId,interleaverMode,interleaverDepth,"
        "interleaverSeed,encodedLength,payloadBits,encodedBits,"
        "interleavedBits,burstStart,burstLengthBits,burstBits,"
        "deinterleavedBits,cppRecoveredBits,cppStatus\n";
    for (const auto& contract : stage02::allCaseContracts()) {
        for (const auto mode : {InterleaverMode::None,
                                InterleaverMode::Block,
                                InterleaverMode::RowColumn,
                                InterleaverMode::Pseudorandom}) {
            const std::size_t depth =
                mode == InterleaverMode::None ? 1U : 8U;
            const auto permutation = stage13::makePermutation(
                contract.totalEncodedLength,
                {mode, depth,
                 mode == InterleaverMode::Pseudorandom
                     ? interleaverSeed : 0U,
                 contract.caseId});
            const std::vector<std::size_t> lengths{
                0U,
                std::min<std::size_t>(contract.motherT,
                                      contract.totalEncodedLength),
                std::min<std::size_t>(
                    static_cast<std::size_t>(contract.motherT) + 3U,
                    contract.totalEncodedLength)};
            for (std::size_t vectorIndex = 0U;
                 vectorIndex < lengths.size(); ++vectorIndex) {
                const SimulationPoint point{
                    contract.id, mode, depth, interleaverSeed,
                    lengths[vectorIndex], vectorIndex, 0U, 0.0, false};
                const auto trace = stage13::simulateFrame(
                    point, masterSeed, vectorIndex, permutation);
                const std::string vectorId =
                    "V" + std::to_string(vectorIndex);
                vectors << contract.caseId << ',' << vectorId << ','
                        << stage13::interleaverModeName(mode) << ','
                        << depth << ',' << lengths[vectorIndex] << ','
                        << trace.burstStart << '\n';
                output << contract.caseId << ',' << vectorId << ','
                       << stage13::interleaverModeName(mode) << ','
                       << depth << ','
                       << (mode == InterleaverMode::Pseudorandom
                               ? interleaverSeed : 0U)
                       << ',' << contract.totalEncodedLength << ','
                       << bitsToString(trace.payload) << ','
                       << bitsToString(trace.encoded) << ','
                       << bitsToString(trace.interleaved) << ','
                       << trace.burstStart << ',' << lengths[vectorIndex]
                       << ',' << bitsToString(trace.channelBitsAfterBurst)
                       << ',' << bitsToString(trace.deinterleaved) << ','
                       << bitsToString(trace.recoveredPayload) << ','
                       << statusName(trace) << '\n';
            }
        }
    }
}

void writeCoreNegativeTests(const fs::path& path) {
    std::ofstream output(path);
    if (!output) throw std::runtime_error("cannot create negative test CSV");
    output << "testId,expectedOutcome,observedOutcome,passed\n";
    const scl::common::BitVector bits{0U, 1U, 0U, 1U};
    const stage13::BurstIdentity identity{
        1U, "bch_s2_burst_shared", "case", 0U, 0U, 0U, 0U};
    const std::vector<std::pair<std::string, std::function<void()>>> tests{
        {"BURST_L_GREATER_N", [&] {
             static_cast<void>(stage13::burstStart(identity, 4U, 5U));
         }},
        {"BURST_START_NEGATIVE_EQUIVALENT", [&] {
             stage13::flipContiguousBits(
                 bits, std::numeric_limits<std::size_t>::max(), 1U);
         }},
        {"BURST_START_PLUS_L_GREATER_N", [&] {
             stage13::flipContiguousBits(bits, 3U, 2U);
         }},
        {"ILLEGAL_MODE", [] {
             static_cast<void>(stage13::parseInterleaverMode("BAD"));
         }},
        {"DEPTH_ZERO", [] {
             stage13::makePermutation(
                 10U, {InterleaverMode::Block, 0U, 0U, "case"});
         }},
        {"DEPTH_GREATER_N", [] {
             stage13::makePermutation(
                 10U, {InterleaverMode::RowColumn, 11U, 0U, "case"});
         }},
        {"DUPLICATE_PERMUTATION", [] {
             stage13::validatePermutation({0U, 1U, 1U});
         }},
        {"OMITTED_PERMUTATION_INDEX", [] {
             stage13::validatePermutation({0U, 1U, 3U});
         }},
        {"OUT_OF_RANGE_PERMUTATION_INDEX", [] {
             stage13::validatePermutation({0U, 2U});
         }},
        {"PSEUDORANDOM_SEED_MISSING", [] {
             stage13::makePermutation(
                 10U,
                 {InterleaverMode::Pseudorandom, 4U, 0U, "case"});
         }},
        {"INTERLEAVER_LENGTH_CHANGED", [&] {
             static_cast<void>(stage13::applyPermutation(
                 bits, {0U, 1U, 2U}));
         }},
        {"DEINTERLEAVER_LENGTH_CHANGED", [&] {
             static_cast<void>(stage13::removePermutation(
                 bits, {0U, 1U, 2U}));
         }}
    };
    for (const auto& test : tests) {
        const bool passed = expectInvalid(test.second);
        output << test.first << ",REJECTED,"
               << (passed ? "REJECTED" : "ACCEPTED") << ','
               << (passed ? "true" : "false") << '\n';
        require(passed, "negative test accepted invalid input: " + test.first);
    }
}

void writeDeterminismTests(const fs::path& checkpointPath,
                           const fs::path& shardPath,
                           std::uint64_t masterSeed,
                           std::uint64_t interleaverSeed) {
    std::ofstream checkpoint(checkpointPath);
    std::ofstream shard(shardPath);
    if (!checkpoint || !shard) {
        throw std::runtime_error("cannot create determinism JSON");
    }
    checkpoint << "{\n  \"stageId\": "
                  "\"stage13_burst_interleaving_validation\",\n"
                  "  \"tests\": [\n";
    shard << "{\n  \"stageId\": "
             "\"stage13_burst_interleaving_validation\",\n"
             "  \"tests\": [\n";
    bool first = true;
    for (const auto& contract : stage02::allCaseContracts()) {
        const SimulationPoint point{
            contract.id, InterleaverMode::Pseudorandom, 8U,
            interleaverSeed, 8U, 6U, 0U, 0.0, false};
        const auto continuous =
            stage13::simulateRange(point, masterSeed, 0U, 120U, false);
        auto resumed =
            stage13::simulateRange(point, masterSeed, 0U, 47U, false);
        stage13::addCounters(
            resumed,
            stage13::simulateRange(
                point, masterSeed, 47U, 73U, false),
            false);
        auto merged =
            stage13::simulateRange(point, masterSeed, 60U, 60U, false);
        stage13::addCounters(
            merged,
            stage13::simulateRange(
                point, masterSeed, 0U, 60U, false),
            false);
        const bool resumePass =
            stage13::sameDeterministicCounters(continuous, resumed);
        const bool shardPass =
            stage13::sameDeterministicCounters(continuous, merged);
        if (!first) {
            checkpoint << ",\n";
            shard << ",\n";
        }
        first = false;
        checkpoint << "    {\"caseId\": \"" << contract.caseId
                   << "\", \"continuousFrames\": 120, "
                      "\"resumeSplit\": [47, 73], "
                      "\"allIntegerCountsEqual\": "
                   << (resumePass ? "true" : "false")
                   << ", \"passed\": "
                   << (resumePass ? "true" : "false") << '}';
        shard << "    {\"caseId\": \"" << contract.caseId
              << "\", \"continuousFrames\": 120, "
                 "\"shards\": [[60, 60], [0, 60]], "
                 "\"executionOrderReversed\": true, "
                 "\"allIntegerCountsEqual\": "
              << (shardPass ? "true" : "false")
              << ", \"passed\": "
              << (shardPass ? "true" : "false") << '}';
        require(resumePass && shardPass,
                "checkpoint/resume or shard/merge mismatch");
    }
    checkpoint << "\n  ],\n  \"passed\": true\n}\n";
    shard << "\n  ],\n  \"passed\": true\n}\n";
}

void writePrescan(const fs::path& path,
                  std::uint64_t masterSeed,
                  std::uint64_t interleaverSeed) {
    const std::vector<std::size_t> burstLengths{
        0U, 1U, 2U, 3U, 4U, 5U, 6U, 8U, 10U, 12U, 15U,
        20U, 25U, 30U, 40U, 50U};
    std::ofstream output(path);
    if (!output) throw std::runtime_error("cannot create prescan CSV");
    output <<
        "stageId,caseId,interleaverMode,interleaverDepth,"
        "burstLengthIndex,burstLengthBits,framesProcessed,"
        "payloadBitsProcessed,payloadErrorBits,payloadErrorFrames,"
        "decoderDeclaredFailureFrames,miscorrectionFrames,"
        "undetectedErrorFrames,trueSuccessFrames,"
        "affectedCodeBlocksTotal,maxAffectedCodeBlocks,"
        "maxErrorsInOneCodeBlockObserved,burstStartChecksum,"
        "payloadChecksum,permutationFnv1a64,ber,fer,stopReason\n";
    output << std::setprecision(17);
    std::size_t completed = 0U;
    const auto configurations = prescanConfigurations();
    for (const auto& contract : stage02::allCaseContracts()) {
        for (const auto [mode, depth] : configurations) {
            const auto permutation = stage13::makePermutation(
                contract.totalEncodedLength,
                {mode, depth,
                 mode == InterleaverMode::Pseudorandom
                     ? interleaverSeed : 0U,
                 contract.caseId});
            for (std::size_t lengthIndex = 0U;
                 lengthIndex < burstLengths.size(); ++lengthIndex) {
                const std::size_t length = burstLengths[lengthIndex];
                require(length <= contract.totalEncodedLength,
                        "prescan burst length exceeds encoded frame");
                const SimulationPoint point{
                    contract.id, mode, depth, interleaverSeed,
                    length, lengthIndex, 0U, 0.0, false};
                const auto counters = stage13::simulateRange(
                    point, masterSeed, 0U, 200U, false);
                const double ber =
                    static_cast<double>(counters.payloadErrorBits) /
                    static_cast<double>(counters.payloadBitsProcessed);
                const double fer =
                    static_cast<double>(counters.payloadErrorFrames) /
                    static_cast<double>(counters.framesProcessed);
                output <<
                    "stage13_burst_interleaving_validation,"
                    << contract.caseId << ','
                    << stage13::interleaverModeName(mode) << ',' << depth
                    << ',' << lengthIndex << ',' << length << ','
                    << counters.framesProcessed << ','
                    << counters.payloadBitsProcessed << ','
                    << counters.payloadErrorBits << ','
                    << counters.payloadErrorFrames << ','
                    << counters.decoderDeclaredFailureFrames << ','
                    << counters.miscorrectionFrames << ','
                    << counters.undetectedErrorFrames << ','
                    << counters.trueSuccessFrames << ','
                    << counters.affectedCodeBlocksTotal << ','
                    << counters.maxAffectedCodeBlocks << ','
                    << counters.maxErrorsInOneCodeBlockObserved << ','
                    << counters.burstStartChecksum << ','
                    << counters.payloadChecksum << ','
                    << stage13::fnv1a64(permutation) << ','
                    << ber << ',' << fer
                    << ",VALIDATION_FIXED_FRAMES\n";
                ++completed;
            }
        }
        std::cout << "prescan " << contract.caseId << " complete\n";
    }
    require(completed ==
                stage02::allCaseContracts().size() *
                configurations.size() * burstLengths.size(),
            "prescan point count mismatch");
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 4) {
            throw std::invalid_argument(
                "usage: stage13_burst_interleaving_validation_runner "
                "OUTPUT_DIR MASTER_SEED INTERLEAVER_SEED");
        }
        const fs::path outputDirectory(argv[1]);
        const std::uint64_t masterSeed = std::stoull(argv[2]);
        const std::uint64_t interleaverSeed = std::stoull(argv[3]);
        fs::create_directories(outputDirectory);
        writeCaseContracts(
            outputDirectory /
            "stage13_burst_interleaving_validation_case_contracts.csv");
        writePermutations(
            outputDirectory /
            "stage13_burst_interleaving_validation_permutations.csv",
            interleaverSeed);
        writeValidationVectors(
            outputDirectory /
                "stage13_burst_interleaving_validation_vectors.csv",
            outputDirectory /
                "stage13_burst_interleaving_validation_cpp_outputs.csv",
            masterSeed, interleaverSeed);
        writeCoreNegativeTests(
            outputDirectory /
                "stage13_burst_interleaving_validation_negative_tests.csv");
        writeDeterminismTests(
            outputDirectory /
                "stage13_burst_interleaving_validation_checkpoint_test.json",
            outputDirectory /
                "stage13_burst_interleaving_validation_shard_merge_test.json",
            masterSeed, interleaverSeed);
        writePrescan(
            outputDirectory /
                "stage13_burst_interleaving_validation_prescan.csv",
            masterSeed, interleaverSeed);
        std::cout <<
            "PASS_STAGE13_BURST_INTERLEAVING_VALIDATION_RUNNER\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr <<
            "BLOCKED_STAGE13_BURST_INTERLEAVING_VALIDATION_RUNNER: "
                  << error.what() << '\n';
        return 1;
    }
}

