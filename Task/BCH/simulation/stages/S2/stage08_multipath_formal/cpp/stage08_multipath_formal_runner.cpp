#include "stage07_multipath_validation_core.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
namespace s1 = scl::bch::s2::stage01;
namespace s2 = scl::bch::s2::stage02;
namespace s7 = scl::bch::s2::stage07;
using Clock = std::chrono::steady_clock;

namespace {

constexpr std::uint64_t kMasterSeed = 8080808U;
constexpr std::uint64_t kMinFrames = 5000U;
constexpr std::uint64_t kTargetFrameErrors = 200U;
constexpr std::uint64_t kMaxFrames = 50000U;

struct GridRow {
    std::string caseId;
    std::size_t ebn0Index = 0U;
    double ebn0Db = 0.0;
};

struct Counts {
    std::uint64_t totalFrames = 0U;
    std::uint64_t totalPayloadBits = 0U;
    std::uint64_t payloadErrorBits = 0U;
    std::uint64_t payloadErrorFrames = 0U;
    std::uint64_t decoderFailureFrames = 0U;
    std::uint64_t miscorrectionFrames = 0U;
    std::uint64_t undetectedErrorFrames = 0U;
    std::uint64_t trueSuccessFrames = 0U;
    std::uint64_t encodeTimeTotalNs = 0U;
    std::uint64_t channelTimeTotalNs = 0U;
    std::uint64_t equalizeTimeTotalNs = 0U;
    std::uint64_t hardDecisionTimeTotalNs = 0U;
    std::uint64_t decodeTimeTotalNs = 0U;
    std::vector<std::uint64_t> decodeTimesNs;
    std::vector<std::uint64_t> equalizeTimesNs;
    double solverResidualSum = 0.0;
    double solverResidualMax = 0.0;
};

std::uint64_t elapsed(Clock::time_point start) {
    return static_cast<std::uint64_t>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now() - start).count());
}

std::vector<std::string> split(const std::string& line) {
    std::vector<std::string> values;
    std::stringstream input(line);
    for (std::string value; std::getline(input, value, ',');) values.push_back(value);
    return values;
}

std::vector<GridRow> readGrid(const fs::path& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("frozen grid missing");
    std::string line;
    std::getline(input, line);
    if (line != "caseId,ebn0Index,ebn0Db,rationale") {
        throw std::runtime_error("frozen grid schema mismatch");
    }
    std::vector<GridRow> rows;
    while (std::getline(input, line)) {
        if (line.empty()) continue;
        const auto fields = split(line);
        if (fields.size() != 4U) throw std::runtime_error("invalid frozen grid row");
        rows.push_back({fields[0], static_cast<std::size_t>(std::stoull(fields[1])),
                        std::stod(fields[2])});
    }
    if (rows.size() != 24U) throw std::runtime_error("frozen grid must contain 24 points");
    return rows;
}

const s2::CaseContract& contractByName(const std::string& name) {
    for (const auto& contract : s2::allCaseContracts()) {
        if (contract.caseId == name) return contract;
    }
    throw std::invalid_argument("unknown frozen caseId");
}

scl::common::BitVector payload(const s2::CaseContract& contract,
                               std::size_t ebn0Index, std::uint64_t frameIndex) {
    s1::RandomIdentity identity{
        kMasterSeed, "stage08_multipath_formal:S2_FIXED_REAL_FIR_V1:P0",
        contract.caseId, ebn0Index, frameIndex};
    const auto source = s1::payloadFrame(identity, contract.payloadLength);
    return scl::common::BitVector(source.begin(), source.end());
}

void runFrame(Counts& counts, const s2::CaseContract& contract, std::size_t ebn0Index,
              double ebn0Db, std::uint64_t frameIndex) {
    const auto source = payload(contract, ebn0Index, frameIndex);
    auto start = Clock::now();
    const auto encoded = s2::encodeFrame(contract.id, source);
    counts.encodeTimeTotalNs += elapsed(start);
    std::vector<double> transmitted(encoded.encodedBits.size());
    for (std::size_t i = 0; i < transmitted.size(); ++i) {
        transmitted[i] = s1::bpsk(encoded.encodedBits[i]);
    }
    const double sigma2 = s1::awgnSigma2(contract.actualRate, ebn0Db);
    s7::LinearMmse equalizer(transmitted.size(), s7::frozenChannel().impulse, sigma2);
    s1::RandomIdentity noiseIdentity{
        kMasterSeed, "stage08_multipath_formal:S2_FIXED_REAL_FIR_V1:P0",
        contract.caseId, ebn0Index, frameIndex};
    const auto noise = s1::standardGaussianFrame(
        noiseIdentity, s1::RandomDomain::Awgn, equalizer.observationCount());
    const auto equalized = equalizer.apply(transmitted, noise);

    start = Clock::now();
    scl::common::BitVector hard(equalized.symbols.size());
    for (std::size_t i = 0; i < hard.size(); ++i) {
        hard[i] = static_cast<std::uint8_t>(s1::hardDecision(equalized.symbols[i]));
    }
    counts.hardDecisionTimeTotalNs += elapsed(start);
    start = Clock::now();
    const auto decoded = s2::decodeFrame(contract.id, hard);
    const auto decodeNs = elapsed(start);
    const auto errors = s7::countErrors(source, decoded.payload);
    ++counts.totalFrames;
    counts.totalPayloadBits += source.size();
    counts.payloadErrorBits += errors;
    counts.payloadErrorFrames += errors != 0U;
    counts.decoderFailureFrames += !decoded.reportedSuccess;
    counts.miscorrectionFrames += decoded.reportedSuccess && errors != 0U;
    counts.undetectedErrorFrames += decoded.reportedSuccess && errors != 0U;
    counts.trueSuccessFrames += errors == 0U;
    counts.channelTimeTotalNs += equalized.channelTimeNs;
    counts.equalizeTimeTotalNs += equalized.equalizeTimeNs;
    counts.decodeTimeTotalNs += decodeNs;
    counts.decodeTimesNs.push_back(decodeNs);
    counts.equalizeTimesNs.push_back(equalized.equalizeTimeNs);
    counts.solverResidualSum += equalized.residual;
    counts.solverResidualMax = std::max(counts.solverResidualMax, equalized.residual);
}

std::string header() {
    return "stageId,gitCommit,configHash,caseId,displayName,payloadLength,motherN,motherK,"
        "motherT,blockCount,encodedLength,actualRate,channelModelId,rawImpulseResponse,"
        "normalizedImpulseResponse,channelEnergy,equalizerType,solverType,ebn0Index,ebn0Db,"
        "snrLinear,snrDb,sigma2,masterSeed,totalFrames,totalPayloadBits,payloadErrorBits,"
        "payloadErrorFrames,decoderFailureFrames,miscorrectionFrames,undetectedErrorFrames,"
        "trueSuccessFrames,ber,fer,decoderFailureRate,miscorrectionRate,undetectedErrorRate,"
        "trueSuccessRate,encodeTimeTotalNs,channelTimeTotalNs,equalizeTimeTotalNs,"
        "hardDecisionTimeTotalNs,decodeTimeTotalNs,encodeTimeMeanNs,channelTimeMeanNs,"
        "equalizeTimeMeanNs,hardDecisionTimeMeanNs,decodeTimeMeanNs,decodeTimeP50Ns,"
        "decodeTimeP95Ns,decodeTimeP99Ns,decodeTimeMaxNs,equalizeTimeP50Ns,"
        "equalizeTimeP95Ns,equalizeTimeP99Ns,equalizeTimeMaxNs,solverResidualMean,"
        "solverResidualMax,stopReason,checkpointId,shardId\n";
}

std::set<std::string> completedKeys(const fs::path& output) {
    std::set<std::string> keys;
    std::ifstream input(output);
    std::string line;
    if (!std::getline(input, line)) return keys;
    while (std::getline(input, line)) {
        const auto fields = split(line);
        if (fields.size() > 19U) keys.insert(fields[3] + ":" + fields[18]);
    }
    return keys;
}

std::string u64List(const std::vector<std::uint64_t>& values) {
    std::ostringstream out;
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i) out << ';';
        out << values[i];
    }
    return out.str();
}

std::vector<std::uint64_t> parseU64List(const std::string& text) {
    std::vector<std::uint64_t> values;
    std::stringstream input(text);
    for (std::string value; std::getline(input, value, ';');) {
        if (!value.empty()) values.push_back(std::stoull(value));
    }
    return values;
}

fs::path checkpointPath(const fs::path& output, std::size_t shardIndex,
                        const GridRow& grid) {
    const fs::path stage = output.parent_path().parent_path();
    return stage / "checkpoints" /
        (output.stem().string() + "_shard" + std::to_string(shardIndex) + "_" +
         grid.caseId + "_" + std::to_string(grid.ebn0Index) + ".chk");
}

void saveCheckpoint(const fs::path& path, const GridRow& grid,
                    const std::string& gitCommit, const std::string& configHash,
                    const Counts& counts) {
    fs::create_directories(path.parent_path());
    const fs::path temporary = path.string() + ".tmp";
    std::ofstream out(temporary);
    if (!out) throw std::runtime_error("cannot write formal checkpoint");
    out << std::setprecision(17)
        << "schemaVersion=stage08.point.checkpoint.v1\n"
        << "caseId=" << grid.caseId << '\n'
        << "ebn0Index=" << grid.ebn0Index << '\n'
        << "ebn0Db=" << grid.ebn0Db << '\n'
        << "gitCommit=" << gitCommit << '\n'
        << "configHash=" << configHash << '\n'
        << "totalFrames=" << counts.totalFrames << '\n'
        << "totalPayloadBits=" << counts.totalPayloadBits << '\n'
        << "payloadErrorBits=" << counts.payloadErrorBits << '\n'
        << "payloadErrorFrames=" << counts.payloadErrorFrames << '\n'
        << "decoderFailureFrames=" << counts.decoderFailureFrames << '\n'
        << "miscorrectionFrames=" << counts.miscorrectionFrames << '\n'
        << "undetectedErrorFrames=" << counts.undetectedErrorFrames << '\n'
        << "trueSuccessFrames=" << counts.trueSuccessFrames << '\n'
        << "encodeTimeTotalNs=" << counts.encodeTimeTotalNs << '\n'
        << "channelTimeTotalNs=" << counts.channelTimeTotalNs << '\n'
        << "equalizeTimeTotalNs=" << counts.equalizeTimeTotalNs << '\n'
        << "hardDecisionTimeTotalNs=" << counts.hardDecisionTimeTotalNs << '\n'
        << "decodeTimeTotalNs=" << counts.decodeTimeTotalNs << '\n'
        << "solverResidualSum=" << counts.solverResidualSum << '\n'
        << "solverResidualMax=" << counts.solverResidualMax << '\n'
        << "decodeTimesNs=" << u64List(counts.decodeTimesNs) << '\n'
        << "equalizeTimesNs=" << u64List(counts.equalizeTimesNs) << '\n';
    out.close();
    if (fs::exists(path)) fs::remove(path);
    fs::rename(temporary, path);
}

std::map<std::string, std::string> readKeyValues(const fs::path& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("formal checkpoint missing");
    std::map<std::string, std::string> values;
    for (std::string line; std::getline(input, line);) {
        const auto position = line.find('=');
        if (position != std::string::npos) {
            values[line.substr(0U, position)] = line.substr(position + 1U);
        }
    }
    return values;
}

void restoreCheckpoint(const fs::path& path, const GridRow& grid,
                       const std::string& gitCommit, const std::string& configHash,
                       Counts& counts) {
    const auto values = readKeyValues(path);
    if (values.at("schemaVersion") != "stage08.point.checkpoint.v1" ||
        values.at("caseId") != grid.caseId ||
        std::stoull(values.at("ebn0Index")) != grid.ebn0Index ||
        values.at("gitCommit") != gitCommit || values.at("configHash") != configHash) {
        throw std::runtime_error("formal checkpoint identity mismatch");
    }
#define RESTORE_U64(name) counts.name = std::stoull(values.at(#name))
    RESTORE_U64(totalFrames); RESTORE_U64(totalPayloadBits);
    RESTORE_U64(payloadErrorBits); RESTORE_U64(payloadErrorFrames);
    RESTORE_U64(decoderFailureFrames); RESTORE_U64(miscorrectionFrames);
    RESTORE_U64(undetectedErrorFrames); RESTORE_U64(trueSuccessFrames);
    RESTORE_U64(encodeTimeTotalNs); RESTORE_U64(channelTimeTotalNs);
    RESTORE_U64(equalizeTimeTotalNs); RESTORE_U64(hardDecisionTimeTotalNs);
    RESTORE_U64(decodeTimeTotalNs);
#undef RESTORE_U64
    counts.solverResidualSum = std::stod(values.at("solverResidualSum"));
    counts.solverResidualMax = std::stod(values.at("solverResidualMax"));
    counts.decodeTimesNs = parseU64List(values.at("decodeTimesNs"));
    counts.equalizeTimesNs = parseU64List(values.at("equalizeTimesNs"));
    if (counts.decodeTimesNs.size() != counts.totalFrames ||
        counts.equalizeTimesNs.size() != counts.totalFrames) {
        throw std::runtime_error("formal checkpoint timing length mismatch");
    }
}

void writeResult(std::ofstream& output, const s2::CaseContract& contract,
                 const GridRow& grid, const Counts& counts,
                 const std::string& gitCommit, const std::string& configHash,
                 std::size_t shardIndex, const std::string& stopReason) {
    const double frames = static_cast<double>(counts.totalFrames);
    const double payloadBits = static_cast<double>(counts.totalPayloadBits);
    const auto channel = s7::frozenChannel();
    output << std::setprecision(17)
        << "stage08_multipath_formal," << gitCommit << ',' << configHash << ','
        << contract.caseId << ",\"" << contract.displayName << "\"," << contract.payloadLength
        << ',' << contract.motherN << ',' << contract.motherK << ',' << contract.motherT
        << ',' << contract.blockCount << ',' << contract.totalEncodedLength << ','
        << contract.actualRate << ',' << channel.id << ",\"1;0.65;0;0.35\",\""
        << channel.impulse[0] << ';' << channel.impulse[1] << ';' << channel.impulse[2]
        << ';' << channel.impulse[3] << "\"," << s7::energy(channel.impulse)
        << ",BLOCK_LINEAR_MMSE,BANDED_CHOLESKY_NORMAL_EQUATIONS," << grid.ebn0Index << ','
        << grid.ebn0Db << ',' << s1::snrLinear(contract.actualRate, grid.ebn0Db) << ','
        << s1::snrDb(contract.actualRate, grid.ebn0Db) << ','
        << s1::awgnSigma2(contract.actualRate, grid.ebn0Db) << ',' << kMasterSeed << ','
        << counts.totalFrames << ',' << counts.totalPayloadBits << ',' << counts.payloadErrorBits
        << ',' << counts.payloadErrorFrames << ',' << counts.decoderFailureFrames << ','
        << counts.miscorrectionFrames << ',' << counts.undetectedErrorFrames << ','
        << counts.trueSuccessFrames << ',' << counts.payloadErrorBits / payloadBits << ','
        << counts.payloadErrorFrames / frames << ',' << counts.decoderFailureFrames / frames << ','
        << counts.miscorrectionFrames / frames << ',' << counts.undetectedErrorFrames / frames << ','
        << counts.trueSuccessFrames / frames << ',' << counts.encodeTimeTotalNs << ','
        << counts.channelTimeTotalNs << ',' << counts.equalizeTimeTotalNs << ','
        << counts.hardDecisionTimeTotalNs << ',' << counts.decodeTimeTotalNs << ','
        << counts.encodeTimeTotalNs / frames << ',' << counts.channelTimeTotalNs / frames << ','
        << counts.equalizeTimeTotalNs / frames << ','
        << counts.hardDecisionTimeTotalNs / frames << ',' << counts.decodeTimeTotalNs / frames << ','
        << s7::percentile(counts.decodeTimesNs, .50) << ','
        << s7::percentile(counts.decodeTimesNs, .95) << ','
        << s7::percentile(counts.decodeTimesNs, .99) << ','
        << *std::max_element(counts.decodeTimesNs.begin(), counts.decodeTimesNs.end()) << ','
        << s7::percentile(counts.equalizeTimesNs, .50) << ','
        << s7::percentile(counts.equalizeTimesNs, .95) << ','
        << s7::percentile(counts.equalizeTimesNs, .99) << ','
        << *std::max_element(counts.equalizeTimesNs.begin(), counts.equalizeTimesNs.end()) << ','
        << counts.solverResidualSum / frames << ',' << counts.solverResidualMax << ','
        << stopReason << ",SHARD" << shardIndex << "_POINT_" << contract.caseId << '_'
        << grid.ebn0Index << ",SHARD_" << shardIndex << '\n';
    output.flush();
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc == 3 && std::string(argv[1]) == "--self-test") {
            const auto grid = readGrid(argv[2]);
            std::set<std::string> keys;
            for (const auto& row : grid) {
                const auto& contract = contractByName(row.caseId);
                if (!keys.insert(row.caseId + ":" + std::to_string(row.ebn0Index)).second) {
                    throw std::runtime_error("duplicate frozen point");
                }
                if (contract.actualRate !=
                    static_cast<double>(contract.payloadLength) /
                    static_cast<double>(contract.totalEncodedLength)) {
                    throw std::runtime_error("case actual rate mismatch");
                }
            }
            Counts counts;
            runFrame(counts, contractByName("K300_M255K207"), 0U, 6.0, 0U);
            if (counts.totalFrames != 1U || counts.totalPayloadBits != 300U ||
                counts.solverResidualMax > 1e-11) {
                throw std::runtime_error("formal frame self-test failed");
            }
            std::cout << "PASS_STAGE08_MULTIPATH_FORMAL_SELF_TEST\n";
            return 0;
        }
        if (argc != 7 && argc != 8) {
            throw std::invalid_argument(
                "usage: runner GRID OUTPUT GIT_COMMIT CONFIG_HASH SHARD_INDEX SHARD_COUNT [INTERRUPT_AFTER]");
        }
        const auto grid = readGrid(argv[1]);
        const fs::path outputPath(argv[2]);
        const std::string gitCommit(argv[3]);
        const std::string configHash(argv[4]);
        const std::size_t shardIndex = std::stoull(argv[5]);
        const std::size_t shardCount = std::stoull(argv[6]);
        const std::uint64_t interruptAfter = argc == 8 ? std::stoull(argv[7]) : 0U;
        if (gitCommit.size() != 40U || configHash.size() != 64U ||
            shardCount == 0U || shardIndex >= shardCount) {
            throw std::invalid_argument("invalid runner identity or shard");
        }
        fs::create_directories(outputPath.parent_path());
        const bool exists = fs::exists(outputPath) && fs::file_size(outputPath) > 0U;
        const auto completed = exists ? completedKeys(outputPath) : std::set<std::string>{};
        std::ofstream output(outputPath, std::ios::app);
        if (!output) throw std::runtime_error("cannot open shard output");
        if (!exists) output << header();
        std::size_t executed = 0U;
        std::size_t resumed = 0U;
        for (std::size_t point = 0; point < grid.size(); ++point) {
            if (point % shardCount != shardIndex) continue;
            const std::string key = grid[point].caseId + ":" + std::to_string(grid[point].ebn0Index);
            if (completed.count(key)) {
                ++resumed;
                continue;
            }
            const auto& contract = contractByName(grid[point].caseId);
            Counts counts;
            const auto checkpoint = checkpointPath(outputPath, shardIndex, grid[point]);
            if (fs::exists(checkpoint)) {
                restoreCheckpoint(checkpoint, grid[point], gitCommit, configHash, counts);
            }
            std::string stopReason;
            for (std::uint64_t frame = counts.totalFrames; frame < kMaxFrames; ++frame) {
                runFrame(counts, contract, grid[point].ebn0Index, grid[point].ebn0Db, frame);
                if (counts.totalFrames % 1000U == 0U) {
                    saveCheckpoint(checkpoint, grid[point], gitCommit, configHash, counts);
                }
                if (interruptAfter != 0U && counts.totalFrames == interruptAfter) {
                    saveCheckpoint(checkpoint, grid[point], gitCommit, configHash, counts);
                    std::cout << "INTERRUPTED_AFTER_CHECKPOINT frames=" << counts.totalFrames << '\n';
                    return 3;
                }
                if (counts.totalFrames >= kMinFrames &&
                    counts.payloadErrorFrames >= kTargetFrameErrors) {
                    stopReason = "TARGET_FRAME_ERRORS_REACHED";
                    break;
                }
                if (counts.totalFrames == kMaxFrames) stopReason = "MAX_FRAMES_REACHED";
            }
            if (stopReason.empty()) throw std::logic_error("formal stop reason missing");
            writeResult(output, contract, grid[point], counts, gitCommit, configHash,
                        shardIndex, stopReason);
            if (fs::exists(checkpoint)) fs::remove(checkpoint);
            ++executed;
            std::cout << "POINT_COMPLETE " << key << " frames=" << counts.totalFrames
                      << " errors=" << counts.payloadErrorFrames << '\n';
        }
        std::cout << "PASS_STAGE08_MULTIPATH_FORMAL_SHARD shard=" << shardIndex
                  << " executed=" << executed << " resumeSkipped=" << resumed << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_STAGE08_MULTIPATH_FORMAL_SHARD: " << error.what() << '\n';
        return 1;
    }
}
