#include "stage13_burst_interleaving_validation_simulation.hpp"
#include "stage02_case_contract.hpp"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
namespace stage02 = scl::bch::s2::stage02;
namespace stage13 = scl::bch::s2::stage13;

namespace {

struct Point {
    stage02::CaseId caseId;
    std::string caseIdText;
    std::string configurationId;
    stage13::InterleaverMode mode;
    std::size_t depth;
    std::size_t burstIndex;
    std::size_t burstLength;
    std::size_t snrIndex;
    double targetSnrDb;
    double derivedEbN0Db;
    std::string permutationSha256;
};

struct StopRule {
    std::uint64_t minFrames, targetErrors, maxFrames, interval;
};

void require(bool value, const std::string& message) {
    if (!value) throw std::runtime_error(message);
}

stage02::CaseId parseCase(const std::string& value) {
    for (const auto& contract : stage02::allCaseContracts()) {
        if (contract.caseId == value) return contract.id;
    }
    throw std::invalid_argument("unknown Stage16 caseId");
}

std::vector<Point> readPoints(const fs::path& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot open Stage16 points");
    std::string line;
    std::getline(input, line);
    require(
        line == "caseId,configurationId,interleaverMode,interleaverDepth,"
                "burstLengthIndex,burstLengthBits,snrIndex,targetSnrDb,"
                "derivedEbN0Db,permutationSha256",
        "Stage16 point header mismatch");
    std::vector<Point> points;
    while (std::getline(input, line)) {
        if (line.empty()) continue;
        std::istringstream row(line);
        std::vector<std::string> values;
        std::string value;
        while (std::getline(row, value, ',')) values.push_back(value);
        require(values.size() == 10U, "Stage16 point field count mismatch");
        const auto id = parseCase(values[0]);
        const auto mode = stage13::parseInterleaverMode(values[2]);
        Point point{
            id, values[0], values[1], mode,
            static_cast<std::size_t>(std::stoull(values[3])),
            static_cast<std::size_t>(std::stoull(values[4])),
            static_cast<std::size_t>(std::stoull(values[5])),
            static_cast<std::size_t>(std::stoull(values[6])),
            std::stod(values[7]), std::stod(values[8]), values[9]};
        const auto& contract = stage02::caseContract(id);
        const double expected =
            point.targetSnrDb - 10.0 * std::log10(contract.actualRate);
        require(std::abs(expected - point.derivedEbN0Db) < 1e-9,
                "Stage16 target SNR/EbN0 conversion mismatch");
        require(point.snrIndex < 37U &&
                std::abs(point.targetSnrDb -
                         0.5 * static_cast<double>(point.snrIndex)) < 1e-12,
                "Stage16 SNR grid mismatch");
        points.push_back(point);
    }
    require(!points.empty(), "Stage16 points empty");
    return points;
}

stage13::SimulationPoint simulationPoint(
    const Point& point, std::uint64_t interleaverSeed) {
    return {
        point.caseId, point.mode, point.depth, interleaverSeed,
        point.burstLength, point.burstIndex, point.snrIndex,
        point.targetSnrDb, true};
}

void writeCheckpoint(
    const fs::path& path, const Point& point,
    const stage13::SimulationCounters& counters, std::uint64_t masterSeed,
    const std::string& configSha, const std::string& commit,
    const std::string& reason) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Stage16 checkpoint write failed");
    out << std::setprecision(17)
        << "{\n  \"stageId\": \"stage16_burst_interleaving_comparison\",\n"
        << "  \"configSha256\": \"" << configSha << "\",\n"
        << "  \"gitCommit\": \"" << commit << "\",\n"
        << "  \"caseId\": \"" << point.caseIdText << "\",\n"
        << "  \"parameterSetId\": \"" << point.configurationId
        << "_S" << point.snrIndex << "\",\n"
        << "  \"configurationId\": \"" << point.configurationId << "\",\n"
        << "  \"interleaverMode\": \""
        << stage13::interleaverModeName(point.mode) << "\",\n"
        << "  \"interleaverDepth\": " << point.depth << ",\n"
        << "  \"burstLengthBits\": " << point.burstLength << ",\n"
        << "  \"snrIndex\": " << point.snrIndex << ",\n"
        << "  \"targetSnrDb\": " << point.targetSnrDb << ",\n"
        << "  \"derivedEbN0Db\": " << point.derivedEbN0Db << ",\n"
        << "  \"framesProcessed\": " << counters.framesProcessed << ",\n"
        << "  \"payloadBitsProcessed\": " << counters.payloadBitsProcessed << ",\n"
        << "  \"payloadErrorBits\": " << counters.payloadErrorBits << ",\n"
        << "  \"payloadErrorFrames\": " << counters.payloadErrorFrames << ",\n"
        << "  \"decoderDeclaredSuccessFrames\": "
        << counters.decoderDeclaredSuccessFrames << ",\n"
        << "  \"decoderDeclaredFailureFrames\": "
        << counters.decoderDeclaredFailureFrames << ",\n"
        << "  \"trueSuccessFrames\": " << counters.trueSuccessFrames << ",\n"
        << "  \"miscorrectionFrames\": " << counters.miscorrectionFrames << ",\n"
        << "  \"undetectedErrorFrames\": " << counters.undetectedErrorFrames << ",\n"
        << "  \"affectedCodeBlocksTotal\": "
        << counters.affectedCodeBlocksTotal << ",\n"
        << "  \"burstStartChecksum\": " << counters.burstStartChecksum << ",\n"
        << "  \"payloadChecksum\": " << counters.payloadChecksum << ",\n"
        << "  \"awgnChecksum\": " << counters.awgnChecksum << ",\n"
        << "  \"frameIndexNext\": " << counters.framesProcessed << ",\n"
        << "  \"masterSeed\": " << masterSeed << ",\n"
        << "  \"stopReason\": \"" << reason << "\"\n}\n";
}

std::string simulate(
    const Point& point, const StopRule& rule, std::uint64_t masterSeed,
    std::uint64_t interleaverSeed, const fs::path& checkpointPath,
    const std::string& configSha, const std::string& commit,
    stage13::SimulationCounters& counters) {
    const auto simulation = simulationPoint(point, interleaverSeed);
    while (counters.framesProcessed < rule.maxFrames) {
        const auto count = std::min(
            rule.interval, rule.maxFrames - counters.framesProcessed);
        const auto chunk = stage13::simulateRange(
            simulation, masterSeed, counters.framesProcessed, count, true);
        const bool crossing =
            counters.framesProcessed + count >= rule.minFrames &&
            counters.payloadErrorFrames + chunk.payloadErrorFrames >=
                rule.targetErrors;
        if (crossing) {
            while (counters.framesProcessed < rule.maxFrames) {
                const auto one = stage13::simulateRange(
                    simulation, masterSeed, counters.framesProcessed, 1U, true);
                stage13::addCounters(counters, one, true);
                if (counters.framesProcessed >= rule.minFrames &&
                    counters.payloadErrorFrames >= rule.targetErrors) {
                    writeCheckpoint(
                        checkpointPath, point, counters, masterSeed,
                        configSha, commit, "TARGET_FRAME_ERRORS_REACHED");
                    return "TARGET_FRAME_ERRORS_REACHED";
                }
            }
        } else {
            stage13::addCounters(counters, chunk, true);
            writeCheckpoint(
                checkpointPath, point, counters, masterSeed,
                configSha, commit, "CONTINUE");
        }
    }
    writeCheckpoint(
        checkpointPath, point, counters, masterSeed,
        configSha, commit, "MAX_FRAMES_REACHED");
    return "MAX_FRAMES_REACHED";
}

void header(std::ofstream& out) {
    out << "stageId,runId,gitCommit,caseId,legendLabel,payloadLength,"
           "encodedLength,actualRate,motherN,motherK,motherT,blockCount,"
           "configurationId,interleaverMode,interleaverDepth,interleaverSeed,"
           "permutationFile,permutationSha256,burstLengthIndex,burstLengthBits,"
           "burstRatio,snrIndex,targetSnrDb,derivedEbN0Db,sigma2,masterSeed,"
           "framesProcessed,payloadBitsProcessed,payloadErrorBits,"
           "payloadErrorFrames,decoderDeclaredSuccessFrames,"
           "decoderDeclaredFailureFrames,trueSuccessFrames,miscorrectionFrames,"
           "undetectedErrorFrames,affectedCodeBlocksTotal,meanAffectedCodeBlocks,"
           "maxAffectedCodeBlocks,maxErrorsInOneCodeBlockObserved,"
           "meanMaxErrorsInOneCodeBlock,interleaverApplyTimeTotalNs,"
           "deinterleaverApplyTimeTotalNs,decoderTimeTotalNs,"
           "interleaverTimeMeanNs,deinterleaverTimeMeanNs,decoderTimeMeanNs,"
           "decoderTimeP50Ns,decoderTimeP95Ns,decoderTimeP99Ns,decoderTimeMaxNs,"
           "interleaverBufferBits,interleaverBufferBytes,"
           "interleaverStartupDelayBits,burstStartChecksum,payloadChecksum,"
           "awgnChecksum,ber,fer,decoderFailureRate,miscorrectionRate,"
           "undetectedErrorRate,trueSuccessRate,stopReason,checkpointPath,"
           "resultSha256\n";
}

void writeResult(
    std::ofstream& out, const Point& point,
    const stage13::SimulationCounters& counters, std::uint64_t masterSeed,
    std::uint64_t interleaverSeed, const std::string& commit,
    const std::string& reason, const std::string& checkpointPath) {
    const auto& contract = stage02::caseContract(point.caseId);
    const double frames = counters.framesProcessed;
    const double payloadBits = counters.payloadBitsProcessed;
    const double sigma2 =
        0.5 / std::pow(10.0, point.targetSnrDb / 10.0);
    const auto maximum =
        *std::max_element(counters.decoderTimesNs.begin(),
                          counters.decoderTimesNs.end());
    out << std::setprecision(17)
        << "stage16_burst_interleaving_comparison,stage16_formal_v1,"
        << commit << ',' << contract.caseId << ',' << contract.legendLabel << ','
        << contract.payloadLength << ',' << contract.totalEncodedLength << ','
        << contract.actualRate << ',' << contract.motherN << ','
        << contract.motherK << ',' << contract.motherT << ','
        << contract.blockCount << ',' << point.configurationId << ','
        << stage13::interleaverModeName(point.mode) << ',' << point.depth << ','
        << interleaverSeed
        << ",../stage13_burst_interleaving_validation/results/"
           "stage13_burst_interleaving_validation_permutations.csv,"
        << point.permutationSha256 << ',' << point.burstIndex << ','
        << point.burstLength << ','
        << static_cast<double>(point.burstLength) /
               contract.totalEncodedLength
        << ',' << point.snrIndex << ',' << point.targetSnrDb << ','
        << point.derivedEbN0Db << ',' << sigma2 << ',' << masterSeed << ','
        << counters.framesProcessed << ',' << counters.payloadBitsProcessed << ','
        << counters.payloadErrorBits << ',' << counters.payloadErrorFrames << ','
        << counters.decoderDeclaredSuccessFrames << ','
        << counters.decoderDeclaredFailureFrames << ','
        << counters.trueSuccessFrames << ',' << counters.miscorrectionFrames
        << ',' << counters.undetectedErrorFrames << ','
        << counters.affectedCodeBlocksTotal << ','
        << counters.affectedCodeBlocksTotal / frames << ','
        << counters.maxAffectedCodeBlocks << ','
        << counters.maxErrorsInOneCodeBlockObserved << ','
        << counters.sumMaxErrorsInOneCodeBlock / frames << ','
        << counters.interleaverApplyTimeTotalNs << ','
        << counters.deinterleaverApplyTimeTotalNs << ','
        << counters.decoderTimeTotalNs << ','
        << counters.interleaverApplyTimeTotalNs / counters.framesProcessed << ','
        << counters.deinterleaverApplyTimeTotalNs / counters.framesProcessed
        << ',' << counters.decoderTimeTotalNs / counters.framesProcessed << ','
        << stage13::percentile(counters.decoderTimesNs, .50) << ','
        << stage13::percentile(counters.decoderTimesNs, .95) << ','
        << stage13::percentile(counters.decoderTimesNs, .99) << ',' << maximum
        << ',' << contract.totalEncodedLength << ','
        << (contract.totalEncodedLength + 7U) / 8U << ','
        << contract.totalEncodedLength << ',' << counters.burstStartChecksum
        << ',' << counters.payloadChecksum << ',' << counters.awgnChecksum << ','
        << counters.payloadErrorBits / payloadBits << ','
        << counters.payloadErrorFrames / frames << ','
        << counters.decoderDeclaredFailureFrames / frames << ','
        << counters.miscorrectionFrames / frames << ','
        << counters.undetectedErrorFrames / frames << ','
        << counters.trueSuccessFrames / frames << ',' << reason << ','
        << checkpointPath << ",\n";
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 12) {
            throw std::invalid_argument(
                "usage: stage16_burst_interleaving_comparison_runner POINTS "
                "OUTPUT CHECKPOINTS MASTER INTERSEED CONFIGSHA COMMIT MIN "
                "TARGET MAX INTERVAL");
        }
        const auto points = readPoints(argv[1]);
        const fs::path outputPath(argv[2]), checkpoints(argv[3]);
        const std::uint64_t masterSeed = std::stoull(argv[4]);
        const std::uint64_t interleaverSeed = std::stoull(argv[5]);
        const std::string configSha(argv[6]), commit(argv[7]);
        const StopRule rule{
            std::stoull(argv[8]), std::stoull(argv[9]),
            std::stoull(argv[10]), std::stoull(argv[11])};
        require(
            rule.minFrames && rule.targetErrors &&
            rule.minFrames <= rule.maxFrames && rule.interval,
            "invalid Stage16 stop rule");
        fs::create_directories(checkpoints);
        fs::create_directories(outputPath.parent_path());
        std::ofstream out(outputPath);
        if (!out) throw std::runtime_error("cannot create Stage16 output");
        header(out);
        for (const auto& point : points) {
            stage13::SimulationCounters counters;
            const std::string name =
                "stage16_burst_interleaving_comparison_" + point.caseIdText +
                "_" + point.configurationId + "_S" +
                std::to_string(point.snrIndex) + ".json";
            const auto reason = simulate(
                point, rule, masterSeed, interleaverSeed, checkpoints / name,
                configSha, commit, counters);
            writeResult(
                out, point, counters, masterSeed, interleaverSeed, commit,
                reason, "results/checkpoints/" + name);
            std::cout << point.caseIdText << ' ' << point.configurationId
                      << " SNR=" << point.targetSnrDb
                      << " frames=" << counters.framesProcessed
                      << " errors=" << counters.payloadErrorFrames << ' '
                      << reason << '\n';
        }
        std::cout << "PASS_STAGE16_BURST_INTERLEAVING_COMPARISON_RUNNER\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr
            << "BLOCKED_STAGE16_BURST_INTERLEAVING_COMPARISON_RUNNER: "
            << error.what() << '\n';
        return 1;
    }
}
