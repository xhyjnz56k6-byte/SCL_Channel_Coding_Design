#include "bch_simulation/bch_burst_simulation.hpp"
#include "bch_simulation/bch_interleaver.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
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

namespace fs = std::filesystem;
namespace sim = scl::bch::simulation;

namespace {

struct Counts {
    std::uint64_t frames = 0U;
    std::uint64_t bits = 0U;
    std::uint64_t bitErrors = 0U;
    std::uint64_t errors = 0U;
    std::uint64_t reported = 0U;
    std::uint64_t failures = 0U;
    std::uint64_t misc = 0U;
    std::uint64_t explicitWrong = 0U;
    std::uint64_t touched = 0U;
    std::uint64_t maximumWeight = 0U;
    std::uint64_t within = 0U;
    std::uint64_t oneErrorBlocks = 0U;
    std::uint64_t multiErrorBlocks = 0U;
    std::size_t minimumFailingStart = std::numeric_limits<std::size_t>::max();
    std::size_t maximumSuccessfulStart = 0U;
};

struct Options {
    std::string stage;
    std::string mode;
    fs::path output;
    std::uint64_t seed = 2026072607ULL;
    bool progress = false;
};

std::map<std::string, std::string> parse(int argc, char** argv) {
    std::map<std::string, std::string> values;
    for (int index = 1; index < argc; ++index) {
        const std::string key(argv[index]);
        if (key == "--progress") {
            values[key] = "1";
            continue;
        }
        if (index + 1 >= argc || key.rfind("--", 0U) != 0U) {
            throw std::invalid_argument("invalid arguments");
        }
        values[key] = argv[++index];
    }
    return values;
}

Options options(int argc, char** argv) {
    const auto values = parse(argc, argv);
    Options result;
    result.stage = values.at("--stage");
    result.mode = values.at("--mode");
    result.output = values.at("--output");
    if (values.count("--seed")) result.seed = std::stoull(values.at("--seed"));
    result.progress = values.count("--progress") != 0U;
    if ((result.stage != "s2-07a" && result.stage != "s2-07b" &&
         result.stage != "s2-07c" && result.stage != "s2-07d") ||
        (result.mode != "smoke" && result.mode != "formal")) {
        throw std::invalid_argument("unsupported stage or mode");
    }
    return result;
}

std::vector<sim::BchCaseId> allCases() {
    return {sim::BchCaseId::S200, sim::BchCaseId::B200,
            sim::BchCaseId::S300, sim::BchCaseId::B300,
            sim::BchCaseId::B300_426};
}

scl::common::BitVector payload(
    const sim::BchSimulationCase& value, std::uint64_t seed,
    std::uint64_t frame, std::uint64_t domain) {
    scl::common::BitVector result(value.payloadLength);
    for (std::size_t index = 0U; index < result.size(); ++index) {
        result[index] = static_cast<std::uint8_t>(
            sim::burstDomainValue(seed, frame,
                                  domain + index * 0x9e3779b9ULL) & 1U);
    }
    return result;
}

std::size_t payloadBitErrors(
    const scl::common::BitVector& expected,
    const scl::common::BitVector& observed) {
    if (expected.size() != observed.size()) {
        throw std::logic_error("decoded payload length mismatch");
    }
    std::size_t errors = 0U;
    for (std::size_t index = 0U; index < expected.size(); ++index) {
        errors += expected[index] != observed[index] ? 1U : 0U;
    }
    return errors;
}

void observe(
    Counts& counts, const sim::BchSimulationCase& value,
    const scl::common::BitVector& originalPayload,
    sim::DecodedBchFrame decoded, const sim::BurstStructure& structure,
    std::size_t start) {
    sim::auditDecodedBchFrame(originalPayload, decoded);
    ++counts.frames;
    counts.bits += value.payloadLength;
    counts.bitErrors += payloadBitErrors(originalPayload, decoded.payload);
    counts.errors += decoded.trueSuccess ? 0U : 1U;
    counts.reported += decoded.reportedSuccess ? 1U : 0U;
    counts.failures += decoded.decoderFailure ? 1U : 0U;
    counts.misc += decoded.miscorrected ? 1U : 0U;
    counts.explicitWrong +=
        decoded.decoderFailure && !decoded.trueSuccess ? 1U : 0U;
    counts.touched += structure.touchedSubblockCount;
    counts.maximumWeight += structure.maximumSubblockErrorWeight;
    counts.within += structure.allSubblocksWithinGuaranteedRegion ? 1U : 0U;
    counts.oneErrorBlocks += structure.numberOfSubblocksWithOneError;
    counts.multiErrorBlocks += structure.numberOfSubblocksWithMoreThanOneError;
    if (decoded.trueSuccess) {
        counts.maximumSuccessfulStart =
            std::max(counts.maximumSuccessfulStart, start);
    } else {
        counts.minimumFailingStart =
            std::min(counts.minimumFailingStart, start);
    }
    if (structure.allSubblocksWithinGuaranteedRegion && !decoded.trueSuccess) {
        throw std::runtime_error("guaranteed-region decode failure");
    }
}

std::pair<double, double> wilson(std::uint64_t errors, std::uint64_t total) {
    if (total == 0U) return {0.0, 0.0};
    constexpr double z = 1.959963984540054;
    const double n = static_cast<double>(total);
    const double p = static_cast<double>(errors) / n;
    const double denominator = 1.0 + z * z / n;
    const double center = (p + z * z / (2.0 * n)) / denominator;
    const double half = z *
        std::sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) /
        denominator;
    return {std::max(0.0, center - half), std::min(1.0, center + half)};
}

std::string configHash(
    const std::string& stage, const sim::BchSimulationCase& value,
    std::size_t length, std::uint64_t seed) {
    const std::uint64_t hash = sim::burstDomainValue(
        seed, value.encodedLength,
        length ^ (stage.empty() ? 0U : static_cast<unsigned>(stage.back())));
    std::ostringstream text;
    text << std::hex << std::setw(16) << std::setfill('0') << hash;
    return text.str();
}

const char* header() {
    return "stage,mode,caseName,payloadLength,encodedLength,organization,"
           "correctionCapabilityT,burstLength,relativeStartInSubblock,"
           "interleaverMode,payloadCount,legalStartCountPerPayload,totalPatterns,"
           "processedFrames,processedBits,bitErrors,frameErrors,BER,FER,"
           "trueSuccessRate,reportedSuccessRate,decoderFailureRate,"
           "miscorrectionRate,explicitFailureWithWrongPayloadPatterns,"
           "averageTouchedSubblocks,averageMaximumSubblockErrorWeight,"
           "fractionAllSubblocksWithinGuaranteedRegion,"
           "averageSubblocksWithOneError,averageSubblocksWithMoreThanOneError,"
           "minimumFailingStart,maximumSuccessfulStart,allStartsGuaranteedCorrect,"
           "theoreticalGuaranteedRegion,ferWilson95Low,ferWilson95High,"
           "masterSeed,caseSeed,lengthSeed,randomStartSeed,stopReason,"
           "runtimeSeconds,configHash,permutationHash,inversePermutationHash,"
           "errorWeightConserved,pairedFrameCount\n";
}

void writeRow(
    std::ostream& output, const Options& options,
    const sim::BchSimulationCase& value, std::size_t length,
    const std::string& interleaverMode, std::size_t payloadCount,
    std::size_t legalStarts, int relativeStart, const Counts& counts,
    const std::string& stopReason, double runtime,
    const std::string& permutationHash = "",
    const std::string& inverseHash = "",
    bool weightConserved = true,
    std::uint64_t pairedFrameCount = 0U) {
    const double frames = static_cast<double>(counts.frames);
    const auto ci = wilson(counts.errors, counts.frames);
    const std::uint64_t caseSeed = sim::burstDomainValue(
        options.seed, value.encodedLength, 101U);
    const std::uint64_t lengthSeed = sim::burstDomainValue(
        caseSeed, length, 103U);
    const bool whole = value.organization == sim::BchOrganization::WholeBlockShortened;
    const bool theoretical = whole
        ? length <= value.correctionCapability
        : counts.frames > 0U && counts.within == counts.frames;
    output << options.stage << ',' << options.mode << ',' << value.caseName << ','
           << value.payloadLength << ',' << value.encodedLength << ','
           << sim::organizationName(value.organization) << ','
           << value.correctionCapability << ',' << length << ',';
    if (relativeStart >= 0) output << relativeStart;
    output << ',' << interleaverMode << ',' << payloadCount << ',' << legalStarts
           << ',' << counts.frames << ',' << counts.frames << ',' << counts.bits
           << ',' << counts.bitErrors << ',' << counts.errors << ','
           << (counts.bits ? static_cast<double>(counts.bitErrors) / counts.bits : 0.0)
           << ',' << (frames ? counts.errors / frames : 0.0)
           << ',' << (frames ? (frames - counts.errors) / frames : 0.0)
           << ',' << (frames ? counts.reported / frames : 0.0)
           << ',' << (frames ? counts.failures / frames : 0.0)
           << ',' << (frames ? counts.misc / frames : 0.0)
           << ',' << counts.explicitWrong
           << ',' << (frames ? counts.touched / frames : 0.0)
           << ',' << (frames ? counts.maximumWeight / frames : 0.0)
           << ',' << (frames ? counts.within / frames : 0.0)
           << ',' << (frames ? counts.oneErrorBlocks / frames : 0.0)
           << ',' << (frames ? counts.multiErrorBlocks / frames : 0.0) << ',';
    if (counts.minimumFailingStart != std::numeric_limits<std::size_t>::max()) {
        output << counts.minimumFailingStart;
    }
    output << ',' << counts.maximumSuccessfulStart << ','
           << (counts.errors == 0U ? "true" : "false") << ','
           << (theoretical ? "true" : "false") << ','
           << ci.first << ',' << ci.second << ',' << options.seed << ','
           << caseSeed << ',' << lengthSeed << ',' << lengthSeed << ','
           << stopReason << ',' << runtime << ','
           << configHash(options.stage, value, length, options.seed) << ','
           << permutationHash << ',' << inverseHash << ','
           << (weightConserved ? "true" : "false") << ','
           << pairedFrameCount << '\n';
}

void progress(const Options& options, const std::string& text) {
    if (options.progress) std::cout << text << '\n';
}

void runA(const Options& options, std::ostream& output) {
    const std::size_t payloads = options.mode == "smoke" ? 8U : 100U;
    for (sim::BchCaseId id :
         {sim::BchCaseId::B200, sim::BchCaseId::B300,
          sim::BchCaseId::B300_426}) {
        const auto& value = sim::bchSimulationCase(id);
        sim::prepareBchCase(value);
        const std::size_t maximum = id == sim::BchCaseId::B200 ? 10U :
                                    id == sim::BchCaseId::B300 ? 14U : 18U;
        for (std::size_t length = 0U; length <= maximum; ++length) {
            const auto begin = std::chrono::steady_clock::now();
            Counts counts;
            const std::size_t legal = length == 0U ? 1U :
                                      value.encodedLength - length + 1U;
            for (std::size_t payloadIndex = 0U;
                 payloadIndex < payloads; ++payloadIndex) {
                const auto source = payload(
                    value, options.seed, payloadIndex, length + value.encodedLength);
                const auto encoded = sim::encodeBchFrame(value, source).codeword;
                for (std::size_t start = 0U; start < legal; ++start) {
                    const auto received =
                        sim::injectConsecutiveBitBurst(encoded, start, length);
                    const auto structure = sim::analyzeBurstStructure(
                        value, sim::errorPositions(encoded, received), start, length);
                    observe(counts, value, source,
                            sim::decodeBchFrame(value, received), structure, start);
                }
            }
            const double seconds = std::chrono::duration<double>(
                std::chrono::steady_clock::now() - begin).count();
            writeRow(output, options, value, length, "NONE", payloads, legal, -1,
                     counts, "EXHAUSTIVE_ALL_STARTS", seconds);
            progress(options, "A " + value.caseName + " L=" +
                              std::to_string(length));
        }
    }
}

void runB(const Options& options, std::ostream& output) {
    const std::size_t payloads = options.mode == "smoke" ? 8U : 100U;
    for (sim::BchCaseId id : {sim::BchCaseId::S200, sim::BchCaseId::S300}) {
        const auto& value = sim::bchSimulationCase(id);
        sim::prepareBchCase(value);
        for (std::size_t length = 1U; length <= 30U; ++length) {
            const auto begin = std::chrono::steady_clock::now();
            std::vector<Counts> groups(15U);
            std::vector<std::size_t> legalPerPayload(15U, 0U);
            for (std::size_t start = 0U;
                 start + length <= value.encodedLength; ++start) {
                ++legalPerPayload[start % 15U];
            }
            for (std::size_t payloadIndex = 0U;
                 payloadIndex < payloads; ++payloadIndex) {
                const auto source = payload(
                    value, options.seed, payloadIndex, 2000U + length);
                const auto encoded = sim::encodeBchFrame(value, source).codeword;
                for (std::size_t start = 0U;
                     start + length <= value.encodedLength; ++start) {
                    const auto received =
                        sim::injectConsecutiveBitBurst(encoded, start, length);
                    const auto structure = sim::analyzeBurstStructure(
                        value, sim::errorPositions(encoded, received), start, length);
                    observe(groups[start % 15U], value, source,
                            sim::decodeBchFrame(value, received), structure, start);
                }
            }
            const double seconds = std::chrono::duration<double>(
                std::chrono::steady_clock::now() - begin).count() / 15.0;
            for (std::size_t relative = 0U; relative < 15U; ++relative) {
                writeRow(output, options, value, length, "NONE", payloads,
                         legalPerPayload[relative], static_cast<int>(relative),
                         groups[relative], "EXHAUSTIVE_GROUPED_BY_R", seconds);
            }
            progress(options, "B " + value.caseName + " L=" +
                              std::to_string(length));
        }
    }
}

std::vector<std::size_t> randomLengths() {
    std::vector<std::size_t> result;
    for (std::size_t value = 0U; value <= 32U; ++value) result.push_back(value);
    result.insert(result.end(), {40U, 48U, 56U, 64U});
    return result;
}

void runC(const Options& options, std::ostream& output) {
    for (sim::BchCaseId id : allCases()) {
        const auto& value = sim::bchSimulationCase(id);
        sim::prepareBchCase(value);
        for (std::size_t length : randomLengths()) {
            const auto begin = std::chrono::steady_clock::now();
            Counts counts;
            const std::uint64_t minimum = options.mode == "smoke" ? 500U : 5000U;
            const std::uint64_t maximum = options.mode == "smoke" ? 500U : 100000U;
            const std::uint64_t target = options.mode == "smoke" ? maximum : 300U;
            const std::uint64_t lengthSeed = sim::burstDomainValue(
                options.seed, value.encodedLength, length);
            for (std::uint64_t frame = 0U; frame < maximum; ++frame) {
                const auto source = payload(value, lengthSeed, frame, 3001U);
                const auto encoded = sim::encodeBchFrame(value, source).codeword;
                const std::size_t start = sim::uniformBurstStart(
                    value.encodedLength, length, lengthSeed, frame, 3003U);
                const auto received =
                    sim::injectConsecutiveBitBurst(encoded, start, length);
                const auto structure = sim::analyzeBurstStructure(
                    value, sim::errorPositions(encoded, received), start, length);
                observe(counts, value, source,
                        sim::decodeBchFrame(value, received), structure, start);
                if (counts.frames >= minimum && counts.errors >= target) break;
            }
            const std::string stop =
                counts.frames == maximum ? "MAXIMUM_FRAMES" :
                "TARGET_FRAME_ERRORS";
            const double seconds = std::chrono::duration<double>(
                std::chrono::steady_clock::now() - begin).count();
            writeRow(output, options, value, length, "NONE", counts.frames,
                     length == 0U ? 1U : value.encodedLength - length + 1U,
                     -1, counts, stop, seconds);
            progress(options, "C " + value.caseName + " L=" +
                              std::to_string(length) + " frames=" +
                              std::to_string(counts.frames));
        }
    }
}

void runD(const Options& options, std::ostream& output) {
    for (sim::BchCaseId id : allCases()) {
        const auto& value = sim::bchSimulationCase(id);
        sim::prepareBchCase(value);
        const auto none = sim::makeBchInterleaver(
            value.encodedLength, sim::InterleaverMode::None, 0U);
        const std::uint64_t interSeed =
            sim::burstDomainValue(options.seed, value.encodedLength, 4001U);
        const auto fixed = sim::makeBchInterleaver(
            value.encodedLength, sim::InterleaverMode::FixedRandom, interSeed);
        for (std::size_t length : randomLengths()) {
            const auto begin = std::chrono::steady_clock::now();
            Counts noneCounts;
            Counts fixedCounts;
            bool conserved = true;
            const std::uint64_t minimum = options.mode == "smoke" ? 500U : 5000U;
            const std::uint64_t maximum = options.mode == "smoke" ? 500U : 100000U;
            const std::uint64_t target = options.mode == "smoke" ? maximum : 300U;
            const std::uint64_t lengthSeed = sim::burstDomainValue(
                options.seed, value.encodedLength, 4100U + length);
            for (std::uint64_t frame = 0U; frame < maximum; ++frame) {
                const auto source = payload(value, lengthSeed, frame, 4003U);
                const auto encoded = sim::encodeBchFrame(value, source).codeword;
                const std::size_t start = sim::uniformBurstStart(
                    value.encodedLength, length, lengthSeed, frame, 4005U);
                const sim::BchInterleaver* interleavers[2] = {&none, &fixed};
                Counts* counters[2] = {&noneCounts, &fixedCounts};
                for (unsigned mode = 0U; mode < 2U; ++mode) {
                    const auto transmitted =
                        sim::interleave(encoded, *interleavers[mode]);
                    const auto damaged =
                        sim::injectConsecutiveBitBurst(transmitted, start, length);
                    const auto received =
                        sim::deinterleave(damaged, *interleavers[mode]);
                    const auto positions = sim::errorPositions(encoded, received);
                    conserved = conserved && positions.size() == length;
                    const auto structure = sim::analyzeBurstStructure(
                        value, positions, start, length);
                    observe(*counters[mode], value, source,
                            sim::decodeBchFrame(value, received), structure, start);
                }
                if (noneCounts.frames >= minimum &&
                    noneCounts.errors >= target &&
                    fixedCounts.errors >= target) break;
            }
            if (!conserved) {
                throw std::runtime_error(
                    "FAIL_BCH_S2_07D_ERROR_WEIGHT_CONSERVATION");
            }
            const std::string stop =
                noneCounts.frames == maximum ? "MAXIMUM_FRAMES" :
                "PAIRED_TARGET_FRAME_ERRORS";
            const double seconds = std::chrono::duration<double>(
                std::chrono::steady_clock::now() - begin).count() / 2.0;
            writeRow(output, options, value, length, "NONE", noneCounts.frames,
                     length == 0U ? 1U : value.encodedLength - length + 1U,
                     -1, noneCounts, stop, seconds, none.permutationHash,
                     none.inversePermutationHash, conserved, noneCounts.frames);
            writeRow(output, options, value, length, "FIXED_RANDOM",
                     fixedCounts.frames,
                     length == 0U ? 1U : value.encodedLength - length + 1U,
                     -1, fixedCounts, stop, seconds, fixed.permutationHash,
                     fixed.inversePermutationHash, conserved, fixedCounts.frames);
            progress(options, "D " + value.caseName + " L=" +
                              std::to_string(length) + " frames=" +
                              std::to_string(noneCounts.frames));
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const Options value = options(argc, argv);
        fs::create_directories(value.output.parent_path());
        std::ofstream output(value.output);
        if (!output) throw std::runtime_error("cannot open output CSV");
        output << std::setprecision(17) << header();
        if (value.stage == "s2-07a") runA(value, output);
        if (value.stage == "s2-07b") runB(value, output);
        if (value.stage == "s2-07c") runC(value, output);
        if (value.stage == "s2-07d") runD(value, output);
        std::cout << "PASS_BCH_" << value.stage << '_' << value.mode << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_BCH_S2_BURST_RUNNER: " << error.what() << '\n';
        return 1;
    }
}
