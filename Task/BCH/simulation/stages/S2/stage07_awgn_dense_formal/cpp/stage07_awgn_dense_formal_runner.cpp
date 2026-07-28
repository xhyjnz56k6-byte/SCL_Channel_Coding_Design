#define main stage05_embedded_main
#include "../../stage05_awgn_trial/cpp/stage05_awgn_trial_runner.cpp"
#undef main

namespace {

constexpr const char* kStageId = "stage07_awgn_dense_formal";
constexpr std::uint64_t kMinFrames = 1000U;
constexpr std::uint64_t kTargetFrameErrors = 200U;
constexpr std::uint64_t kMaxFrames = 50000U;
constexpr std::uint64_t kCheckpointEvery = 1000U;

struct DensePoint {
    CaseId id;
    std::string caseId;
    std::size_t snrIndex = 0U;
    double snrDb = 0.0;
};

double snrLinear(double snrDb) {
    return std::pow(10.0, snrDb / 10.0);
}

double ebn0FromSnr(double snrDb, double rate) {
    return snrDb - 10.0 * std::log10(2.0 * rate);
}

double sigma2FromSnr(double snrDb) {
    return 1.0 / snrLinear(snrDb);
}

std::vector<DensePoint> readDensePoints(const fs::path& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot open dense point CSV");
    std::string line;
    std::getline(input, line);
    require(line == "caseId,snrIndex,snrDb", "dense point CSV header mismatch");
    std::vector<DensePoint> points;
    while (std::getline(input, line)) {
        if (line.empty()) continue;
        std::istringstream row(line);
        std::string id, index, db;
        std::getline(row, id, ',');
        std::getline(row, index, ',');
        std::getline(row, db, ',');
        points.push_back({parseCase(id), id, static_cast<std::size_t>(std::stoull(index)), std::stod(db)});
    }
    require(points.size() == 296U, "dense formal point count is not 296");
    return points;
}

std::string pointDirName(const DensePoint& point) {
    std::ostringstream out;
    out << point.caseId << "/snr_" << std::setw(3) << std::setfill('0') << point.snrIndex;
    return out.str();
}

std::string checkpointName(const DensePoint& point) {
    std::ostringstream out;
    out << kStageId << '_' << point.caseId << '_' << std::setw(3) << std::setfill('0')
        << point.snrIndex << "_checkpoint.json";
    return out.str();
}

Counters simulateDenseRange(const DensePoint& point, std::uint64_t start, std::uint64_t count,
                            std::uint64_t seed) {
    const auto& contract = scl::bch::s2::stage02::caseContract(point.id);
    Counters result;
    result.decodeTimesNs.reserve(static_cast<std::size_t>(count));
    const double sigma = std::sqrt(sigma2FromSnr(point.snrDb));
    for (std::uint64_t frame = start; frame < start + count; ++frame) {
        const auto payload = payloadFrame(kStageId, contract.caseId, point.snrIndex,
                                          frame, contract.payloadLength, seed);
        const auto encodeStart = std::chrono::steady_clock::now();
        const auto encoded = scl::bch::s2::stage02::encodeFrame(contract.id, payload).encodedBits;
        const auto encodeEnd = std::chrono::steady_clock::now();
        const scl::bch::s2::stage01::RandomIdentity identity{
            seed, kStageId, contract.caseId, point.snrIndex, frame};
        const auto z = scl::bch::s2::stage01::standardGaussianFrame(
            identity, scl::bch::s2::stage01::RandomDomain::Awgn, encoded.size());
        scl::common::BitVector hard(encoded.size(), 0U);
        for (std::size_t i = 0; i < encoded.size(); ++i) {
            hard[i] = static_cast<scl::common::Bit>(scl::bch::s2::stage01::hardDecision(
                scl::bch::s2::stage01::bpsk(encoded[i]) + sigma * z[i]));
        }
        const auto decodeStart = std::chrono::steady_clock::now();
        const auto decoded = decodeAudited(contract, hard);
        const auto decodeEnd = std::chrono::steady_clock::now();
        const auto errors = bitErrors(payload, decoded.payload);
        const bool success = errors == 0U;
        ++result.totalFrames;
        result.totalPayloadBits += contract.payloadLength;
        result.payloadErrorBits += errors;
        result.payloadErrorFrames += !success;
        result.decoderFailureFrames += !decoded.reportedSuccess;
        result.miscorrectionFrames += decoded.reportedSuccess && !success;
        result.undetectedErrorFrames += decoded.allNoError && !success;
        result.trueSuccessFrames += success;
        result.noiseChecksum += hashNoise(z);
        result.encodeTimeTotalNs += static_cast<std::uint64_t>(
            std::chrono::duration_cast<std::chrono::nanoseconds>(encodeEnd - encodeStart).count());
        const auto decodeNs = static_cast<std::uint64_t>(
            std::chrono::duration_cast<std::chrono::nanoseconds>(decodeEnd - decodeStart).count());
        result.decodeTimeTotalNs += decodeNs;
        result.decodeTimesNs.push_back(decodeNs);
    }
    return result;
}

void addWithTimes(Counters& target, const Counters& source) {
    add(target, source);
    target.encodeTimeTotalNs += source.encodeTimeTotalNs;
    target.decodeTimeTotalNs += source.decodeTimeTotalNs;
    target.decodeTimesNs.insert(target.decodeTimesNs.end(), source.decodeTimesNs.begin(), source.decodeTimesNs.end());
}

void writeDenseCheckpoint(const fs::path& path, const DensePoint& point, const Counters& c,
                          std::uint64_t seed, const std::string& configHash,
                          const std::string& gitCommit, const std::string& stopReason) {
    const auto& contract = scl::bch::s2::stage02::caseContract(point.id);
    const double rate = contract.actualRate;
    const double ebn0Db = ebn0FromSnr(point.snrDb, rate);
    std::ofstream out(path);
    if (!out) throw std::runtime_error("cannot write dense checkpoint");
    out << std::setprecision(17);
    out << "{\n  \"stageId\": \"" << kStageId << "\",\n  \"caseId\": \"" << point.caseId
        << "\",\n  \"snrIndex\": " << point.snrIndex << ",\n  \"snrDb\": " << point.snrDb
        << ",\n  \"ebn0Db\": " << ebn0Db << ",\n  \"actualRate\": " << rate
        << ",\n  \"nextFrameIndex\": " << c.totalFrames << ",\n  \"masterSeed\": " << seed
        << ",\n  \"configHash\": \"" << configHash << "\",\n  \"gitCommit\": \"" << gitCommit
        << "\",\n  \"totalFrames\": " << c.totalFrames << ",\n  \"totalPayloadBits\": " << c.totalPayloadBits
        << ",\n  \"payloadErrorBits\": " << c.payloadErrorBits
        << ",\n  \"payloadErrorFrames\": " << c.payloadErrorFrames
        << ",\n  \"decoderFailureFrames\": " << c.decoderFailureFrames
        << ",\n  \"miscorrectionFrames\": " << c.miscorrectionFrames
        << ",\n  \"undetectedErrorFrames\": " << c.undetectedErrorFrames
        << ",\n  \"trueSuccessFrames\": " << c.trueSuccessFrames
        << ",\n  \"noiseChecksum\": " << c.noiseChecksum
        << ",\n  \"encodeTimeTotalNs\": " << c.encodeTimeTotalNs
        << ",\n  \"decodeTimeTotalNs\": " << c.decodeTimeTotalNs
        << ",\n  \"stopReason\": \"" << stopReason << "\"\n}\n";
}

void writePointResult(std::ostream& results, const DensePoint& point, const Counters& counters,
                      std::uint64_t seed, const std::string& configHash,
                      const std::string& gitCommit, const std::string& checkpointId,
                      const std::string& pointRunId, const std::string& stopReason) {
    const auto& c = scl::bch::s2::stage02::caseContract(point.id);
    const double rate = c.actualRate;
    const double ebn0Db = ebn0FromSnr(point.snrDb, rate);
    const double sigma2A = sigma2FromSnr(point.snrDb);
    const double sigma2B = scl::bch::s2::stage01::awgnSigma2(rate, ebn0Db);
    require(std::abs(sigma2A - sigma2B) <= 1e-12, "sigma2 formula mismatch");
    results << kStageId << ',' << gitCommit << ',' << configHash << ','
            << c.caseId << ',' << c.displayName << ',' << c.legendLabel << ',' << c.plotStyle.id << ','
            << c.payloadLength << ',' << c.motherN << ',' << c.motherK << ',' << c.motherT << ','
            << c.blockCount << ',' << c.totalEncodedLength << ',' << rate << ','
            << point.snrIndex << ',' << point.snrDb << ',' << snrLinear(point.snrDb) << ','
            << ebn0Db << ',' << sigma2A << ',' << seed << ','
            << counters.totalFrames << ',' << counters.totalPayloadBits << ',' << counters.payloadErrorBits << ','
            << counters.payloadErrorFrames << ',' << counters.decoderFailureFrames << ','
            << counters.miscorrectionFrames << ',' << counters.undetectedErrorFrames << ','
            << counters.trueSuccessFrames << ','
            << static_cast<double>(counters.payloadErrorBits) / counters.totalPayloadBits << ','
            << static_cast<double>(counters.payloadErrorFrames) / counters.totalFrames << ','
            << static_cast<double>(counters.decoderFailureFrames) / counters.totalFrames << ','
            << static_cast<double>(counters.miscorrectionFrames) / counters.totalFrames << ','
            << static_cast<double>(counters.undetectedErrorFrames) / counters.totalFrames << ','
            << static_cast<double>(counters.trueSuccessFrames) / counters.totalFrames << ','
            << counters.encodeTimeTotalNs << ',' << counters.decodeTimeTotalNs << ','
            << counters.encodeTimeTotalNs / counters.totalFrames << ','
            << counters.decodeTimeTotalNs / counters.totalFrames << ','
            << percentile(counters.decodeTimesNs, 0.50) << ',' << percentile(counters.decodeTimesNs, 0.95) << ','
            << percentile(counters.decodeTimesNs, 0.99) << ','
            << *std::max_element(counters.decodeTimesNs.begin(), counters.decodeTimesNs.end()) << ','
            << counters.noiseChecksum << ',' << stopReason << ',' << checkpointId << ',' << pointRunId << '\n';
}

void writeProgressHeader(std::ostream& progress) {
    progress << "caseId,snrIndex,snrDb,status,processedFrames,frameErrors,stopReason,checkpointPath,lastUpdated\n";
}

void writeProgressRow(std::ostream& progress, const DensePoint& point, const Counters& counters,
                      const std::string& status, const std::string& stopReason, const fs::path& checkpointPath) {
    progress << point.caseId << ',' << point.snrIndex << ',' << point.snrDb << ',' << status << ','
             << counters.totalFrames << ',' << counters.payloadErrorFrames << ',' << stopReason << ','
             << checkpointPath.generic_string() << ',' << std::time(nullptr) << '\n';
}

Counters runPoint(const DensePoint& point, const fs::path& pointDir, std::uint64_t seed,
                  const std::string& configHash, const std::string& gitCommit,
                  std::ostream& pointLog, std::string& stopReason) {
    fs::create_directories(pointDir);
    const fs::path checkpointPath = pointDir / checkpointName(point);
    Counters counters;
    stopReason = "CONTINUE";
    while (counters.totalFrames < kMaxFrames) {
        const auto one = simulateDenseRange(point, counters.totalFrames, 1U, seed);
        addWithTimes(counters, one);
        if (counters.totalFrames >= kMinFrames && counters.payloadErrorFrames >= kTargetFrameErrors) {
            stopReason = "TARGET_FRAME_ERRORS_REACHED";
            break;
        }
        if (counters.totalFrames % kCheckpointEvery == 0U) {
            writeDenseCheckpoint(checkpointPath, point, counters, seed, configHash, gitCommit, "CONTINUE");
        }
    }
    if (stopReason == "CONTINUE") stopReason = "MAX_FRAMES_REACHED";
    writeDenseCheckpoint(checkpointPath, point, counters, seed, configHash, gitCommit, stopReason);
    pointLog << point.caseId << ',' << point.snrIndex << ',' << point.snrDb << ','
             << counters.totalFrames << ',' << counters.payloadErrorFrames << ',' << stopReason << '\n';
    return counters;
}

void runResumeEquivalence(const fs::path& output, std::uint64_t seed,
                          const std::string& configHash, const std::string& gitCommit) {
    const DensePoint point{CaseId::K200_S15, "K200_S15", 4U, 2.0};
    const auto continuous = simulateDenseRange(point, 0U, 3000U, seed);
    const auto prefix = simulateDenseRange(point, 0U, 1000U, seed);
    fs::create_directories(output / "resume_test");
    writeDenseCheckpoint(output / "resume_test" / checkpointName(point), point, prefix, seed,
                         configHash, gitCommit, "CONTINUE");
    auto resumed = prefix;
    addWithTimes(resumed, simulateDenseRange(point, 1000U, 2000U, seed));
    require(sameRaw(continuous, resumed), "resume raw counters mismatch");
    std::ofstream report(output / "stage07_awgn_dense_formal_resume_equivalence.csv");
    report << "caseId,snrIndex,continuousFrames,resumedFrames,continuousPayloadErrorBits,"
              "resumedPayloadErrorBits,continuousPayloadErrorFrames,resumedPayloadErrorFrames,"
              "continuousNoiseChecksum,resumedNoiseChecksum,passed\n";
    report << point.caseId << ',' << point.snrIndex << ',' << continuous.totalFrames << ','
           << resumed.totalFrames << ',' << continuous.payloadErrorBits << ',' << resumed.payloadErrorBits << ','
           << continuous.payloadErrorFrames << ',' << resumed.payloadErrorFrames << ','
           << continuous.noiseChecksum << ',' << resumed.noiseChecksum << ",true\n";
    std::cout << "PASS_STAGE07_RESUME_EQUIVALENCE\n";
}

void writeResultsHeader(std::ostream& results) {
    results << "stageId,gitCommit,configHash,caseId,displayName,legendLabel,styleId,payloadLength,"
               "motherN,motherK,motherT,blockCount,encodedLength,actualRate,snrIndex,snrDb,"
               "snrLinear,ebn0Db,sigma2,masterSeed,totalFrames,totalPayloadBits,payloadErrorBits,"
               "payloadErrorFrames,decoderFailureFrames,miscorrectionFrames,undetectedErrorFrames,"
               "trueSuccessFrames,ber,fer,decoderFailureRate,miscorrectionRate,undetectedErrorRate,"
               "trueSuccessRate,encodeTimeTotalNs,decodeTimeTotalNs,encodeTimeMeanNs,decodeTimeMeanNs,"
               "decodeTimeP50Ns,decodeTimeP95Ns,decodeTimeP99Ns,decodeTimeMaxNs,noiseChecksum,"
               "stopReason,checkpointId,pointRunId\n";
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc == 6 && std::string(argv[1]) == "--resume-test") {
            runResumeEquivalence(fs::path(argv[2]), std::stoull(argv[3]), argv[4], argv[5]);
            return 0;
        }
        if (argc != 6) throw std::invalid_argument(
            "usage: stage07_awgn_dense_formal_runner POINTS_CSV OUTPUT_DIR MASTER_SEED CONFIG_HASH GIT_COMMIT");
        const auto points = readDensePoints(argv[1]);
        const fs::path output(argv[2]);
        const fs::path pointsRoot = output / "points";
        const std::uint64_t seed = std::stoull(argv[3]);
        const std::string configHash = argv[4], gitCommit = argv[5];
        fs::create_directories(output);
        fs::create_directories(pointsRoot);
        std::ofstream results(output / "stage07_awgn_dense_formal_results.csv");
        std::ofstream progress(output / "stage07_awgn_dense_formal_progress.csv");
        if (!results || !progress) throw std::runtime_error("cannot open dense formal outputs");
        results << std::setprecision(17);
        progress << std::setprecision(17);
        writeResultsHeader(results);
        writeProgressHeader(progress);
        for (const auto& point : points) {
            const fs::path pointDir = pointsRoot / pointDirName(point);
            fs::create_directories(pointDir);
            std::ofstream pointLog(pointDir / ("stage07_awgn_dense_formal_" + point.caseId + "_" +
                                      std::to_string(point.snrIndex) + "_run.log"));
            std::ofstream pointCsv(pointDir / ("stage07_awgn_dense_formal_" + point.caseId + "_" +
                                      std::to_string(point.snrIndex) + "_result.csv"));
            if (!pointLog || !pointCsv) throw std::runtime_error("cannot open point output");
            std::string stopReason;
            const auto counters = runPoint(point, pointDir, seed, configHash, gitCommit, pointLog, stopReason);
            const std::string checkpointId = "dense_" + point.caseId + "_" + std::to_string(point.snrIndex);
            const std::string pointRunId = kStageId + std::string("_") + point.caseId + "_" + std::to_string(point.snrIndex);
            writeResultsHeader(pointCsv);
            writePointResult(pointCsv, point, counters, seed, configHash, gitCommit,
                             checkpointId, pointRunId, stopReason);
            writePointResult(results, point, counters, seed, configHash, gitCommit,
                             checkpointId, pointRunId, stopReason);
            writeProgressRow(progress, point, counters, "COMPLETE", stopReason,
                             pointDir / checkpointName(point));
            const bool accounting = counters.trueSuccessFrames + counters.payloadErrorFrames == counters.totalFrames;
            require(accounting, "dense formal raw accounting failed");
            std::cout << point.caseId << " snrIndex " << point.snrIndex << " snrDb " << point.snrDb
                      << " frames " << counters.totalFrames << " errors " << counters.payloadErrorFrames
                      << ' ' << stopReason << '\n';
        }
        std::cout << "PASS_STAGE07_AWGN_DENSE_FORMAL_RUNNER\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_STAGE07_AWGN_DENSE_FORMAL_RUNNER: " << error.what() << '\n';
        return 1;
    }
}
