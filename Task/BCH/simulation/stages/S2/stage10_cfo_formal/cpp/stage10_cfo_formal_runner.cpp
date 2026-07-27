#define main stage05_embedded_main
#include "../../stage05_awgn_trial/cpp/stage05_awgn_trial_runner.cpp"
#undef main

namespace {

constexpr double kPi10 = 3.141592653589793238462643383279502884;

struct CfoSample10 {
    double real = 0.0;
    double imag = 0.0;
    scl::common::Bit hard = 0U;
};

double deltaPhase(std::size_t encodedLength, double targetEndPhaseDeg) {
    require(encodedLength > 0U, "encodedLength must be positive");
    return encodedLength == 1U ? 0.0 :
        targetEndPhaseDeg*kPi10/180.0/static_cast<double>(encodedLength-1U);
}

CfoSample10 cfoSample(double bpsk, std::size_t k, std::size_t encodedLength,
                      double targetEndPhaseDeg, double noiseI, double noiseQ) {
    const double phase = static_cast<double>(k)*deltaPhase(encodedLength,targetEndPhaseDeg);
    CfoSample10 out;
    out.real = bpsk*std::cos(phase)+noiseI;
    out.imag = bpsk*std::sin(phase)+noiseQ;
    out.hard = static_cast<scl::common::Bit>(
        scl::bch::s2::stage01::hardDecision(out.real));
    return out;
}

struct FormalCounters : Counters {
    std::vector<std::uint64_t> latency;
};

void addFormal(FormalCounters& target, const FormalCounters& source) {
    add(target, source);
    target.decodeTimeTotalNs += source.decodeTimeTotalNs;
    target.latency.insert(target.latency.end(), source.latency.begin(), source.latency.end());
}

FormalCounters simulateFormal(const Point& point, std::uint64_t start, std::uint64_t count,
                              std::uint64_t seed) {
    const auto& contract = scl::bch::s2::stage02::caseContract(point.id);
    FormalCounters result;
    result.latency.reserve(static_cast<std::size_t>(count));
    const double sigma = std::sqrt(
        scl::bch::s2::stage01::awgnSigma2(contract.actualRate, point.ebn0Db));
    for (std::uint64_t frame = start; frame < start + count; ++frame) {
        const auto payload = payloadFrame("stage10_cfo_formal", contract.caseId,
                                          point.ebn0Index, frame,
                                          contract.payloadLength, seed);
        const auto encoded = scl::bch::s2::stage02::encodeFrame(contract.id, payload).encodedBits;
        const scl::bch::s2::stage01::RandomIdentity identity{
            seed, "stage10_cfo_formal", contract.caseId, point.ebn0Index, frame};
        const auto zI = scl::bch::s2::stage01::standardGaussianFrame(
            identity, scl::bch::s2::stage01::RandomDomain::Awgn, encoded.size());
        auto qIdentity = identity;
        qIdentity.stageId += "_IMAG";
        const auto zQ = scl::bch::s2::stage01::standardGaussianFrame(
            qIdentity, scl::bch::s2::stage01::RandomDomain::Awgn, encoded.size());
        scl::common::BitVector hard(encoded.size(), 0U);
        double imagAudit = 0.0;
        for (std::size_t k = 0; k < encoded.size(); ++k) {
            const auto sample = cfoSample(scl::bch::s2::stage01::bpsk(encoded[k]), k,
                                          encoded.size(), 30.0,
                                          sigma*zI[k], sigma*zQ[k]);
            hard[k] = sample.hard;
            imagAudit += sample.imag;
        }
        require(std::isfinite(imagAudit), "non-finite complex CFO sample");
        const auto begin = std::chrono::steady_clock::now();
        const auto decoded = decodeAudited(contract, hard);
        const auto end = std::chrono::steady_clock::now();
        const auto ns = static_cast<std::uint64_t>(
            std::chrono::duration_cast<std::chrono::nanoseconds>(end-begin).count());
        const auto errors = bitErrors(payload, decoded.payload);
        ++result.totalFrames;
        result.totalPayloadBits += contract.payloadLength;
        result.payloadErrorBits += errors;
        result.payloadErrorFrames += errors != 0U;
        result.decoderFailureFrames += !decoded.reportedSuccess;
        result.miscorrectionFrames += decoded.reportedSuccess && errors != 0U;
        result.undetectedErrorFrames += decoded.allNoError && errors != 0U;
        result.trueSuccessFrames += errors == 0U;
        result.noiseChecksum += hashNoise(zI);
        result.decodeTimeTotalNs += ns;
        result.latency.push_back(ns);
    }
    return result;
}

std::vector<Point> readCfoPoints(const fs::path& path) {
    std::ifstream input(path);
    require(static_cast<bool>(input), "cannot open CFO point CSV");
    std::string line;
    std::getline(input, line);
    require(line == "caseId,ebn0Index,ebn0Db", "CFO point header mismatch");
    std::vector<Point> points;
    while (std::getline(input, line)) {
        if (line.empty()) continue;
        std::istringstream row(line);
        std::string id, index, db;
        std::getline(row,id,','); std::getline(row,index,','); std::getline(row,db,',');
        points.push_back({parseCase(id),id,static_cast<std::size_t>(std::stoull(index)),std::stod(db)});
    }
    require(!points.empty(), "CFO point list is empty");
    return points;
}

void writeHeader(std::ostream& out) {
    out << "stageId,gitCommit,caseId,legendLabel,payloadLength,encodedLength,actualRate,"
           "initialPhaseDeg,targetEndPhaseDeg,deltaPhaseRadPerSymbol,actualEndPhaseDeg,"
           "ebn0Index,ebn0Db,snrDb,sigmaDimension2,totalFrames,totalPayloadBits,"
           "payloadErrorBits,payloadErrorFrames,decoderFailureFrames,miscorrectionFrames,"
           "undetectedErrorFrames,trueSuccessFrames,decodeTimeTotalNs,decodeTimeMeanNs,"
           "decodeTimeP50Ns,decodeTimeP95Ns,decodeTimeP99Ns,ber,fer,decoderFailureRate,"
           "miscorrectionRate,undetectedErrorRate,trueSuccessRate,noiseChecksum,stopReason,"
           "checkpointId,shardId\n";
}

void writeRow(std::ostream& out, const Point& point, const FormalCounters& c,
              const std::string& gitCommit, const std::string& stopReason) {
    const auto& contract = scl::bch::s2::stage02::caseContract(point.id);
    const auto rate = [](std::uint64_t n, std::uint64_t d) {
        return static_cast<double>(n)/static_cast<double>(d);
    };
    const double delta = deltaPhase(contract.totalEncodedLength, 30.0);
    out << std::setprecision(17)
        << "stage10_cfo_formal," << gitCommit << ',' << contract.caseId << ','
        << contract.legendLabel << ',' << contract.payloadLength << ','
        << contract.totalEncodedLength << ',' << contract.actualRate << ",0,30,"
        << delta << ",30"
        << ',' << point.ebn0Index << ',' << point.ebn0Db << ','
        << point.ebn0Db+10.0*std::log10(contract.actualRate) << ','
        << scl::bch::s2::stage01::awgnSigma2(contract.actualRate,point.ebn0Db) << ','
        << c.totalFrames << ',' << c.totalPayloadBits << ',' << c.payloadErrorBits << ','
        << c.payloadErrorFrames << ',' << c.decoderFailureFrames << ','
        << c.miscorrectionFrames << ',' << c.undetectedErrorFrames << ','
        << c.trueSuccessFrames << ',' << c.decodeTimeTotalNs << ','
        << c.decodeTimeTotalNs/c.totalFrames << ',' << percentile(c.latency,0.50) << ','
        << percentile(c.latency,0.95) << ',' << percentile(c.latency,0.99) << ','
        << rate(c.payloadErrorBits,c.totalPayloadBits) << ','
        << rate(c.payloadErrorFrames,c.totalFrames) << ','
        << rate(c.decoderFailureFrames,c.totalFrames) << ','
        << rate(c.miscorrectionFrames,c.totalFrames) << ','
        << rate(c.undetectedErrorFrames,c.totalFrames) << ','
        << rate(c.trueSuccessFrames,c.totalFrames) << ',' << c.noiseChecksum << ','
        << stopReason << ",stage10_" << contract.caseId << '_' << point.ebn0Index
        << ",0\n";
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 7) throw std::invalid_argument(
            "usage: runner POINTS OUTPUT_DIR SEED GIT_COMMIT MODE FRAMES");
        const auto points = readCfoPoints(argv[1]);
        const fs::path output(argv[2]);
        const std::uint64_t seed = std::stoull(argv[3]);
        const std::string gitCommit = argv[4], mode = argv[5];
        const std::uint64_t fixedFrames = std::stoull(argv[6]);
        require(mode == "trial" || mode == "formal", "mode must be trial or formal");
        fs::create_directories(output/"checkpoints");
        std::ofstream raw(output/"stage10_cfo_formal_result_raw.csv");
        std::ofstream summary(output/"stage10_cfo_formal_result_summary.csv");
        std::ofstream merge(output/"stage10_cfo_formal_merge_audit.csv");
        require(raw && summary && merge, "cannot create CFO outputs");
        writeHeader(raw); writeHeader(summary);
        merge << "caseId,ebn0Index,totalFrames,integerAccountingPass,passed\n";
        for (const auto& point : points) {
            FormalCounters counters;
            std::string stop = mode == "trial" ? "TRIAL_FIXED_FRAMES" : "CONTINUE";
            const std::uint64_t maximum = mode == "trial" ? fixedFrames : 50000U;
            while (counters.totalFrames < maximum) {
                const std::uint64_t count = std::min<std::uint64_t>(
                    100U, maximum-counters.totalFrames);
                addFormal(counters, simulateFormal(point,counters.totalFrames,count,seed));
                if (mode == "formal" && counters.totalFrames >= 5000U &&
                    counters.payloadErrorFrames >= 200U) {
                    stop = "TARGET_FRAME_ERRORS_REACHED";
                    break;
                }
            }
            if (mode == "formal" && stop == "CONTINUE") stop = "MAX_FRAMES_REACHED";
            const bool accounting =
                counters.trueSuccessFrames+counters.payloadErrorFrames==counters.totalFrames;
            require(accounting && counters.totalFrames<=50000U, "formal accounting/frame cap failed");
            writeRow(raw,point,counters,gitCommit,stop);
            writeRow(summary,point,counters,gitCommit,stop);
            merge << point.caseId << ',' << point.ebn0Index << ',' << counters.totalFrames
                  << ',' << accounting << ',' << accounting << '\n';
            std::ofstream checkpoint(output/"checkpoints"/(
                "stage10_cfo_formal_"+point.caseId+"_"+std::to_string(point.ebn0Index)+".json"));
            checkpoint << "{\"nextFrameIndex\":" << counters.totalFrames
                       << ",\"stopReason\":\"" << stop << "\"}\n";
            std::cout << point.caseId << " point " << point.ebn0Index
                      << " frames " << counters.totalFrames << " errors "
                      << counters.payloadErrorFrames << ' ' << stop << '\n';
        }
        std::cout << (mode=="formal" ? "PASS_STAGE10_CFO_FORMAL_RUNNER\n"
                                      : "PASS_STAGE10_CFO_TRIAL_RUNNER\n");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_STAGE10_CFO_FORMAL_RUNNER: " << error.what() << '\n';
        return 1;
    }
}
