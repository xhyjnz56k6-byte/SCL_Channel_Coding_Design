#include "stage13_burst_interleaving_validation_simulation.hpp"
#include "stage02_case_contract.hpp"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace {

namespace stage02 = scl::bch::s2::stage02;
namespace stage13 = scl::bch::s2::stage13;

struct Point {
    stage02::CaseId caseId;
    std::string caseIdText;
    std::size_t burstLengthIndex;
    std::size_t burstLength;
};

struct StopRule {
    std::uint64_t minFrames;
    std::uint64_t targetFrameErrors;
    std::uint64_t maxFrames;
    std::uint64_t checkpointInterval;
};

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

stage02::CaseId parseCase(const std::string& value) {
    using C = stage02::CaseId;
    if (value == "K200_S15") return C::K200_S15;
    if (value == "K200_M255K207") return C::K200_M255K207;
    if (value == "K200_M511K421") return C::K200_M511K421;
    if (value == "K200_M511K385") return C::K200_M511K385;
    if (value == "K300_S15") return C::K300_S15;
    if (value == "K300_M255K207") return C::K300_M255K207;
    if (value == "K300_M511K421") return C::K300_M511K421;
    if (value == "K300_M511K385") return C::K300_M511K385;
    throw std::invalid_argument("unknown Stage14 caseId");
}

std::vector<Point> readPoints(const fs::path& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot open Stage14 point CSV");
    std::string line;
    std::getline(input, line);
    require(line == "caseId,burstLengthIndex,burstLengthBits",
            "Stage14 point header mismatch");
    std::vector<Point> points;
    while (std::getline(input, line)) {
        if (line.empty()) continue;
        std::istringstream row(line);
        std::string caseId, index, length;
        std::getline(row, caseId, ',');
        std::getline(row, index, ',');
        std::getline(row, length, ',');
        points.push_back({
            parseCase(caseId), caseId,
            static_cast<std::size_t>(std::stoull(index)),
            static_cast<std::size_t>(std::stoull(length))});
    }
    require(!points.empty(), "Stage14 point CSV is empty");
    return points;
}

std::vector<std::size_t> blockOffsets(
    const stage02::CaseContract& contract) {
    std::vector<std::size_t> offsets{0U};
    for (const auto length : contract.encodedLengthPerBlock) {
        offsets.push_back(offsets.back() + length);
    }
    return offsets;
}

void writeCheckpoint(const fs::path& path,
                     const Point& point,
                     const stage13::SimulationCounters& counters,
                     const StopRule& rule,
                     std::uint64_t masterSeed,
                     const std::string& configSha256,
                     const std::string& gitCommit,
                     const std::string& stopReason) {
    std::ofstream output(path);
    if (!output) throw std::runtime_error("cannot write Stage14 checkpoint");
    output << "{\n"
           << "  \"stageId\": \"stage14_burst_formal\",\n"
           << "  \"configSha256\": \"" << configSha256 << "\",\n"
           << "  \"gitCommit\": \"" << gitCommit << "\",\n"
           << "  \"caseId\": \"" << point.caseIdText << "\",\n"
           << "  \"parameterSetId\": " << point.burstLengthIndex << ",\n"
           << "  \"burstLengthBits\": " << point.burstLength << ",\n"
           << "  \"framesProcessed\": " << counters.framesProcessed << ",\n"
           << "  \"payloadBitsProcessed\": "
           << counters.payloadBitsProcessed << ",\n"
           << "  \"payloadErrorBits\": " << counters.payloadErrorBits << ",\n"
           << "  \"payloadErrorFrames\": "
           << counters.payloadErrorFrames << ",\n"
           << "  \"decoderDeclaredSuccessFrames\": "
           << counters.decoderDeclaredSuccessFrames << ",\n"
           << "  \"decoderDeclaredFailureFrames\": "
           << counters.decoderDeclaredFailureFrames << ",\n"
           << "  \"trueSuccessFrames\": "
           << counters.trueSuccessFrames << ",\n"
           << "  \"miscorrectionFrames\": "
           << counters.miscorrectionFrames << ",\n"
           << "  \"undetectedErrorFrames\": "
           << counters.undetectedErrorFrames << ",\n"
           << "  \"affectedCodeBlocksTotal\": "
           << counters.affectedCodeBlocksTotal << ",\n"
           << "  \"maxAffectedCodeBlocks\": "
           << counters.maxAffectedCodeBlocks << ",\n"
           << "  \"maxErrorsInOneCodeBlockObserved\": "
           << counters.maxErrorsInOneCodeBlockObserved << ",\n"
           << "  \"sumMaxErrorsInOneCodeBlock\": "
           << counters.sumMaxErrorsInOneCodeBlock << ",\n"
           << "  \"burstStartChecksum\": "
           << counters.burstStartChecksum << ",\n"
           << "  \"payloadChecksum\": " << counters.payloadChecksum << ",\n"
           << "  \"frameIndexNext\": " << counters.framesProcessed << ",\n"
           << "  \"masterSeed\": " << masterSeed << ",\n"
           << "  \"checkpointIntervalFrames\": "
           << rule.checkpointInterval << ",\n"
           << "  \"stopReason\": \"" << stopReason << "\"\n"
           << "}\n";
}

std::string simulatePoint(
    const Point& point,
    const StopRule& rule,
    std::uint64_t masterSeed,
    const fs::path& checkpoint,
    const std::string& configSha256,
    const std::string& gitCommit,
    stage13::SimulationCounters& counters) {
    const stage13::SimulationPoint simulationPoint{
        point.caseId, stage13::InterleaverMode::None, 1U, 0U,
        point.burstLength, point.burstLengthIndex, 0U, 0.0, false};
    while (counters.framesProcessed < rule.maxFrames) {
        const std::uint64_t remaining =
            rule.maxFrames - counters.framesProcessed;
        const std::uint64_t chunkSize =
            std::min(rule.checkpointInterval, remaining);
        const auto chunk = stage13::simulateRange(
            simulationPoint, masterSeed, counters.framesProcessed,
            chunkSize, true);
        const bool targetWouldBeReached =
            counters.framesProcessed + chunk.framesProcessed >=
                rule.minFrames &&
            counters.payloadErrorFrames + chunk.payloadErrorFrames >=
                rule.targetFrameErrors;
        if (targetWouldBeReached) {
            while (counters.framesProcessed < rule.maxFrames) {
                const auto one = stage13::simulateRange(
                    simulationPoint, masterSeed, counters.framesProcessed,
                    1U, true);
                stage13::addCounters(counters, one, true);
                if (counters.framesProcessed >= rule.minFrames &&
                    counters.payloadErrorFrames >=
                        rule.targetFrameErrors) {
                    writeCheckpoint(
                        checkpoint, point, counters, rule, masterSeed,
                        configSha256, gitCommit,
                        "TARGET_FRAME_ERRORS_REACHED");
                    return "TARGET_FRAME_ERRORS_REACHED";
                }
            }
        } else {
            stage13::addCounters(counters, chunk, true);
            writeCheckpoint(
                checkpoint, point, counters, rule, masterSeed,
                configSha256, gitCommit, "CONTINUE");
        }
    }
    writeCheckpoint(
        checkpoint, point, counters, rule, masterSeed,
        configSha256, gitCommit, "MAX_FRAMES_REACHED");
    return "MAX_FRAMES_REACHED";
}

void writeHeader(std::ofstream& output) {
    output <<
        "stageId,runId,gitCommit,caseId,legendLabel,payloadLength,"
        "encodedLength,actualRate,motherN,motherK,motherT,blockCount,"
        "burstLengthIndex,burstLengthBits,burstRatio,burstStartPolicy,"
        "burstWrapAround,masterSeed,framesProcessed,payloadBitsProcessed,"
        "payloadErrorBits,payloadErrorFrames,"
        "decoderDeclaredSuccessFrames,decoderDeclaredFailureFrames,"
        "trueSuccessFrames,miscorrectionFrames,undetectedErrorFrames,"
        "affectedCodeBlocksTotal,meanAffectedCodeBlocks,"
        "maxAffectedCodeBlocks,maxErrorsInOneCodeBlockObserved,"
        "meanMaxErrorsInOneCodeBlock,decoderTimeTotalNs,"
        "decoderTimeMeanNs,decoderTimeP50Ns,decoderTimeP95Ns,"
        "decoderTimeP99Ns,decoderTimeMaxNs,ber,fer,decoderFailureRate,"
        "miscorrectionRate,undetectedErrorRate,trueSuccessRate,"
        "stopReason,checkpointPath,resultSha256\n";
}

void writeResult(std::ofstream& output,
                 const Point& point,
                 const stage13::SimulationCounters& counters,
                 std::uint64_t masterSeed,
                 const std::string& gitCommit,
                 const std::string& stopReason,
                 const std::string& checkpointPath) {
    const auto& contract = stage02::caseContract(point.caseId);
    const double frames = static_cast<double>(counters.framesProcessed);
    const double bits = static_cast<double>(counters.payloadBitsProcessed);
    const double meanAffected =
        static_cast<double>(counters.affectedCodeBlocksTotal) / frames;
    const double meanMaxErrors =
        static_cast<double>(counters.sumMaxErrorsInOneCodeBlock) / frames;
    const auto maximumDecode = counters.decoderTimesNs.empty()
        ? 0U : *std::max_element(
            counters.decoderTimesNs.begin(), counters.decoderTimesNs.end());
    output << std::setprecision(17)
           << "stage14_burst_formal,stage14_formal_v1," << gitCommit << ','
           << contract.caseId << ',' << contract.legendLabel << ','
           << contract.payloadLength << ',' << contract.totalEncodedLength
           << ',' << contract.actualRate << ',' << contract.motherN << ','
           << contract.motherK << ',' << contract.motherT << ','
           << contract.blockCount << ',' << point.burstLengthIndex << ','
           << point.burstLength << ','
           << static_cast<double>(point.burstLength) /
                contract.totalEncodedLength
           << ",RANDOM_PER_FRAME,false," << masterSeed << ','
           << counters.framesProcessed << ','
           << counters.payloadBitsProcessed << ','
           << counters.payloadErrorBits << ','
           << counters.payloadErrorFrames << ','
           << counters.decoderDeclaredSuccessFrames << ','
           << counters.decoderDeclaredFailureFrames << ','
           << counters.trueSuccessFrames << ','
           << counters.miscorrectionFrames << ','
           << counters.undetectedErrorFrames << ','
           << counters.affectedCodeBlocksTotal << ',' << meanAffected << ','
           << counters.maxAffectedCodeBlocks << ','
           << counters.maxErrorsInOneCodeBlockObserved << ','
           << meanMaxErrors << ',' << counters.decoderTimeTotalNs << ','
           << counters.decoderTimeTotalNs / counters.framesProcessed << ','
           << stage13::percentile(counters.decoderTimesNs, 0.50) << ','
           << stage13::percentile(counters.decoderTimesNs, 0.95) << ','
           << stage13::percentile(counters.decoderTimesNs, 0.99) << ','
           << maximumDecode << ','
           << static_cast<double>(counters.payloadErrorBits) / bits << ','
           << static_cast<double>(counters.payloadErrorFrames) / frames
           << ',' << static_cast<double>(
                counters.decoderDeclaredFailureFrames) / frames
           << ',' << static_cast<double>(counters.miscorrectionFrames) /
                frames
           << ',' << static_cast<double>(counters.undetectedErrorFrames) /
                frames
           << ',' << static_cast<double>(counters.trueSuccessFrames) /
                frames
           << ',' << stopReason << ',' << checkpointPath << ",\n";
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 11) {
            throw std::invalid_argument(
                "usage: stage14_burst_formal_runner POINTS_CSV OUTPUT_CSV "
                "CHECKPOINT_DIR MASTER_SEED CONFIG_SHA GIT_COMMIT "
                "MIN_FRAMES TARGET_ERRORS MAX_FRAMES CHECKPOINT_INTERVAL");
        }
        const auto points = readPoints(argv[1]);
        const fs::path outputPath(argv[2]);
        const fs::path checkpointDirectory(argv[3]);
        const std::uint64_t masterSeed = std::stoull(argv[4]);
        const std::string configSha256(argv[5]);
        const std::string gitCommit(argv[6]);
        const StopRule rule{
            std::stoull(argv[7]), std::stoull(argv[8]),
            std::stoull(argv[9]), std::stoull(argv[10])};
        require(rule.minFrames > 0U &&
                    rule.targetFrameErrors > 0U &&
                    rule.minFrames <= rule.maxFrames &&
                    rule.checkpointInterval > 0U,
                "invalid Stage14 stop rule");
        fs::create_directories(checkpointDirectory);
        fs::create_directories(outputPath.parent_path());
        std::ofstream output(outputPath);
        if (!output) throw std::runtime_error("cannot create Stage14 result");
        writeHeader(output);
        for (const auto& point : points) {
            const auto& contract = stage02::caseContract(point.caseId);
            require(point.burstLength <= contract.totalEncodedLength,
                    "Stage14 burst exceeds encoded frame");
            stage13::SimulationCounters counters;
            const std::string checkpointName =
                "stage14_burst_formal_" + point.caseIdText + "_L" +
                std::to_string(point.burstLength) + ".json";
            const auto stopReason = simulatePoint(
                point, rule, masterSeed,
                checkpointDirectory / checkpointName,
                configSha256, gitCommit, counters);
            require(counters.framesProcessed >= rule.minFrames &&
                        counters.framesProcessed <= rule.maxFrames,
                    "Stage14 frame count outside stop rule");
            writeResult(
                output, point, counters, masterSeed, gitCommit, stopReason,
                "results/checkpoints/" + checkpointName);
            std::cout << point.caseIdText << " L=" << point.burstLength
                      << " frames=" << counters.framesProcessed
                      << " errors=" << counters.payloadErrorFrames << ' '
                      << stopReason << '\n';
        }
        std::cout << "PASS_STAGE14_BURST_FORMAL_RUNNER\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_STAGE14_BURST_FORMAL_RUNNER: "
                  << error.what() << '\n';
        return 1;
    }
}

