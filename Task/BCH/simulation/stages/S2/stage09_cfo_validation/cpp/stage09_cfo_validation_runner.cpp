#define main stage05_embedded_main
#include "../../stage05_awgn_trial/cpp/stage05_awgn_trial_runner.cpp"
#undef main

#include <complex>

namespace {

constexpr double kPi = 3.141592653589793238462643383279502884;

struct CfoSample {
    double phaseRad = 0.0;
    double real = 0.0;
    double imag = 0.0;
    scl::common::Bit hard = 0U;
};

double deltaPhase(std::size_t encodedLength, double targetEndPhaseDeg) {
    require(encodedLength > 0U, "encodedLength must be positive");
    if (encodedLength == 1U) return 0.0;
    return targetEndPhaseDeg * kPi / 180.0 / static_cast<double>(encodedLength - 1U);
}

CfoSample cfoSample(double bpsk, std::size_t k, std::size_t encodedLength,
                    double targetEndPhaseDeg, double noiseI, double noiseQ) {
    require(std::isfinite(targetEndPhaseDeg) && std::isfinite(noiseI) && std::isfinite(noiseQ),
            "CFO inputs must be finite");
    const double phase = static_cast<double>(k) * deltaPhase(encodedLength, targetEndPhaseDeg);
    CfoSample out;
    out.phaseRad = phase;
    out.real = bpsk * std::cos(phase) + noiseI;
    out.imag = bpsk * std::sin(phase) + noiseQ;
    out.hard = static_cast<scl::common::Bit>(scl::bch::s2::stage01::hardDecision(out.real));
    return out;
}

Counters simulateCfoRange(const Point& point, std::uint64_t start, std::uint64_t count,
                          std::uint64_t seed, double targetEndPhaseDeg) {
    const auto& contract = scl::bch::s2::stage02::caseContract(point.id);
    Counters result;
    const double sigma = std::sqrt(
        scl::bch::s2::stage01::awgnSigma2(contract.actualRate, point.ebn0Db));
    for (std::uint64_t frame = start; frame < start + count; ++frame) {
        const auto payload = payloadFrame("stage09_cfo_validation", contract.caseId,
                                          point.ebn0Index, frame,
                                          contract.payloadLength, seed);
        const auto encoded = scl::bch::s2::stage02::encodeFrame(contract.id, payload).encodedBits;
        const scl::bch::s2::stage01::RandomIdentity identity{
            seed, "stage09_cfo_validation", contract.caseId, point.ebn0Index, frame};
        const auto zI = scl::bch::s2::stage01::standardGaussianFrame(
            identity, scl::bch::s2::stage01::RandomDomain::Awgn, encoded.size());
        auto imagIdentity = identity;
        imagIdentity.stageId += "_IMAG";
        const auto zQ = scl::bch::s2::stage01::standardGaussianFrame(
            imagIdentity, scl::bch::s2::stage01::RandomDomain::Awgn, encoded.size());
        scl::common::BitVector hard(encoded.size(), 0U);
        for (std::size_t k = 0; k < encoded.size(); ++k) {
            hard[k] = cfoSample(scl::bch::s2::stage01::bpsk(encoded[k]), k,
                                encoded.size(), targetEndPhaseDeg,
                                sigma * zI[k], sigma * zQ[k]).hard;
        }
        const auto decoded = decodeAudited(contract, hard);
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
    }
    return result;
}

void writeVectors(const fs::path& output) {
    fs::create_directories(output);
    std::ofstream fixed(output / "stage09_cfo_validation_fixed_vectors.csv");
    std::ofstream cpp(output / "stage09_cfo_validation_cpp_outputs.csv");
    require(fixed && cpp, "cannot create fixed-vector outputs");
    fixed << "vectorId,k,encodedLength,inputBit,bpsk,targetEndPhaseDeg,noiseI,noiseQ\n";
    cpp << "vectorId,k,phaseRad,realValue,imagValue,hardBit\n";
    fixed << std::setprecision(17);
    cpp << std::setprecision(17);
    const int bits[] = {0, 1, 0, 1};
    const double noiseI[] = {0.0, 0.125, -0.25, 0.375};
    const double noiseQ[] = {0.5, -0.125, 0.25, -0.375};
    for (std::size_t k = 0; k < 4U; ++k) {
        const double x = bits[k] == 0 ? 1.0 : -1.0;
        fixed << "SHORT30," << k << ",4," << bits[k] << ',' << x
              << ",30," << noiseI[k] << ',' << noiseQ[k] << '\n';
        const auto out = cfoSample(x, k, 4U, 30.0, noiseI[k], noiseQ[k]);
        cpp << "SHORT30," << k << ',' << out.phaseRad << ',' << out.real
            << ',' << out.imag << ',' << static_cast<unsigned>(out.hard) << '\n';
    }
}

void validateModel(const fs::path& output) {
    require(std::abs(deltaPhase(4U, 30.0) - kPi / 18.0) < 1e-15,
            "four-symbol phase increment mismatch");
    require(std::abs(cfoSample(1.0, 0U, 4U, 30.0, 0.0, 0.0).phaseRad) < 1e-15,
            "first phase is not zero");
    require(std::abs(cfoSample(1.0, 3U, 4U, 30.0, 0.0, 0.0).phaseRad - kPi / 6.0) < 1e-15,
            "last phase is not pi/6");
    for (int bit = 0; bit <= 1; ++bit) {
        const double x = bit == 0 ? 1.0 : -1.0;
        for (std::size_t k = 0; k < 4U; ++k) {
            const auto zero = cfoSample(x, k, 4U, 0.0, 0.25, -0.5);
            require(zero.real == x + 0.25 && zero.imag == -0.5,
                    "zero-degree AWGN degeneration mismatch");
        }
    }
    const CaseId ids[] = {
        CaseId::K200_S15, CaseId::K200_M255K207, CaseId::K200_M511K421,
        CaseId::K200_M511K385, CaseId::K300_S15, CaseId::K300_M255K207,
        CaseId::K300_M511K421, CaseId::K300_M511K385};
    std::ofstream cases(output / "stage09_cfo_validation_case_results.csv");
    cases << "caseId,encodedLength,deltaPhaseRadPerSymbol,firstPhaseRad,lastPhaseRad,"
             "resumePass,shardMergePass\n";
    cases << std::setprecision(17);
    for (std::size_t i = 0; i < 8U; ++i) {
        const auto& contract = scl::bch::s2::stage02::caseContract(ids[i]);
        const Point point{ids[i], contract.caseId, i, 5.0};
        const auto continuous = simulateCfoRange(point, 0U, 24U, 2026072709ULL, 30.0);
        auto resumed = simulateCfoRange(point, 0U, 11U, 2026072709ULL, 30.0);
        add(resumed, simulateCfoRange(point, 11U, 13U, 2026072709ULL, 30.0));
        Counters merged;
        add(merged, simulateCfoRange(point, 0U, 8U, 2026072709ULL, 30.0));
        add(merged, simulateCfoRange(point, 8U, 8U, 2026072709ULL, 30.0));
        add(merged, simulateCfoRange(point, 16U, 8U, 2026072709ULL, 30.0));
        const bool resumePass = sameRaw(continuous, resumed);
        const bool shardPass = sameRaw(continuous, merged);
        require(resumePass && shardPass, "CFO resume/shard mismatch");
        const double delta = deltaPhase(contract.totalEncodedLength, 30.0);
        cases << contract.caseId << ',' << contract.totalEncodedLength << ',' << delta
              << ",0," << delta * static_cast<double>(contract.totalEncodedLength - 1U)
              << ',' << resumePass << ',' << shardPass << '\n';
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("usage: stage09_cfo_validation_runner OUTPUT_DIR");
        const fs::path output(argv[1]);
        writeVectors(output);
        validateModel(output);
        std::cout << "PASS_STAGE09_CFO_VALIDATION_RUNNER\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_STAGE09_CFO_VALIDATION_RUNNER: " << error.what() << '\n';
        return 1;
    }
}
