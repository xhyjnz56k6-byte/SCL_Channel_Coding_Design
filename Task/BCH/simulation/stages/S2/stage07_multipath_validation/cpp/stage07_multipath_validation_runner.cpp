#include "stage07_multipath_validation_core.hpp"

#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>

namespace fs = std::filesystem;
using scl::bch::s2::stage01::RandomDomain;
using scl::bch::s2::stage01::RandomIdentity;
using scl::bch::s2::stage02::CaseContract;
using scl::bch::s2::stage07::FrameCounts;

namespace {

std::string doubles(const std::vector<double>& values) {
    std::ostringstream out;
    out << std::setprecision(17);
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i) out << ';';
        out << values[i];
    }
    return out.str();
}

std::string bits(const scl::common::BitVector& values) {
    std::string out;
    out.reserve(values.size());
    for (unsigned value : values) out.push_back(value ? '1' : '0');
    return out;
}

std::vector<double> bpsk(const scl::common::BitVector& values) {
    std::vector<double> out(values.size());
    for (std::size_t i = 0; i < values.size(); ++i) {
        out[i] = scl::bch::s2::stage01::bpsk(values[i]);
    }
    return out;
}

void addCounts(FrameCounts& target, const FrameCounts& source) {
#define ADD_FIELD(name) target.name += source.name
    ADD_FIELD(totalFrames); ADD_FIELD(totalPayloadBits); ADD_FIELD(payloadErrorBits);
    ADD_FIELD(payloadErrorFrames); ADD_FIELD(decoderFailureFrames);
    ADD_FIELD(miscorrectionFrames); ADD_FIELD(undetectedErrorFrames);
    ADD_FIELD(trueSuccessFrames); ADD_FIELD(encodeTimeTotalNs);
    ADD_FIELD(channelTimeTotalNs); ADD_FIELD(equalizeTimeTotalNs);
    ADD_FIELD(decodeTimeTotalNs);
#undef ADD_FIELD
    target.decodeTimesNs.insert(target.decodeTimesNs.end(),
                                source.decodeTimesNs.begin(), source.decodeTimesNs.end());
    target.equalizeTimesNs.insert(target.equalizeTimesNs.end(),
                                  source.equalizeTimesNs.begin(), source.equalizeTimesNs.end());
    target.solverResidualSum += source.solverResidualSum;
    target.solverResidualMax = std::max(target.solverResidualMax, source.solverResidualMax);
}

static scl::common::BitVector payload(const CaseContract& contract, std::uint64_t masterSeed,
                                     std::uint64_t frameIndex, const std::string& stage) {
    RandomIdentity id{masterSeed, stage, contract.caseId, 0U, frameIndex};
    const auto source = scl::bch::s2::stage01::payloadFrame(id, contract.payloadLength);
    return scl::common::BitVector(source.begin(), source.end());
}

FrameCounts runRange(const CaseContract& contract, double ebn0Db,
                     std::uint64_t start, std::uint64_t end, std::uint64_t stride = 1U) {
    FrameCounts counts;
    for (std::uint64_t frame = start; frame < end; frame += stride) {
        const auto values = payload(contract, 7070707U, frame, "stage07_multipath_validation:P0");
        scl::bch::s2::stage07::addFrame(
            counts, contract.id, values, ebn0Db, 7070707U, 0U, frame, false);
    }
    return counts;
}

bool sameIntegerCounts(const FrameCounts& a, const FrameCounts& b) {
    return a.totalFrames == b.totalFrames &&
        a.totalPayloadBits == b.totalPayloadBits &&
        a.payloadErrorBits == b.payloadErrorBits &&
        a.payloadErrorFrames == b.payloadErrorFrames &&
        a.decoderFailureFrames == b.decoderFailureFrames &&
        a.miscorrectionFrames == b.miscorrectionFrames &&
        a.undetectedErrorFrames == b.undetectedErrorFrames &&
        a.trueSuccessFrames == b.trueSuccessFrames;
}

std::vector<double> trialGrid(const std::string& caseId) {
    if (caseId.find("_S15") != std::string::npos) return {8.0, 12.0, 16.0};
    if (caseId == "K200_M255K207" || caseId == "K300_M255K207") return {6.0, 8.0, 10.0};
    if (caseId == "K200_M511K421") return {4.0, 6.0, 8.0};
    if (caseId == "K200_M511K385") return {3.0, 5.0, 7.0};
    if (caseId == "K300_M511K421") return {6.0, 8.0, 10.0};
    return {5.0, 7.0, 9.0};
}

void writeFixedVectors(const fs::path& outDir) {
    const auto channel = scl::bch::s2::stage07::frozenChannel();
    const std::vector<std::pair<std::string, std::vector<double>>> vectors{
        {"IMPULSE", {1,0,0,0,0,0,0,0}},
        {"BPSK8", {1,-1,1,1,-1,-1,1,-1}},
        {"BPSK16", {1,-1,1,-1,-1,1,1,-1,1,1,-1,1,-1,-1,1,-1}},
        {"ALL_PLUS", std::vector<double>(16U, 1.0)},
        {"ALL_MINUS", std::vector<double>(16U, -1.0)},
        {"ALTERNATING", {1,-1,1,-1,1,-1,1,-1,1,-1,1,-1,1,-1,1,-1}},
        {"FRAME_EDGES", {-1,1,1,1,1,1,1,-1}}
    };
    std::ofstream input(outDir / "stage07_multipath_validation_test_vectors.csv");
    std::ofstream cpp(outDir / "stage07_multipath_validation_cpp_outputs.csv");
    input << "vectorId,kind,caseId,ebn0Db,sigma2,inputSymbols,standardGaussian\n";
    cpp << "vectorId,kind,caseId,ebn0Db,sigma2,outputLength,convolution,rhs,xHat,hardDecision,solverResidual\n";
    for (const auto& item : vectors) {
        const auto convolution = scl::bch::s2::stage07::convolveFull(item.second, channel.impulse);
        input << item.first << ",CONVOLUTION,,0,0,\"" << doubles(item.second) << "\",\"\"\n";
        cpp << item.first << ",CONVOLUTION,,0,0," << convolution.size() << ",\""
            << doubles(convolution) << "\",\"\",\"\",\"\",0\n";
    }
    for (const auto& contract : scl::bch::s2::stage02::allCaseContracts()) {
        for (double ebn0 : {-4.0, 4.0, 20.0, 80.0}) {
            const auto encoded = scl::bch::s2::stage02::encodeFrame(
                contract.id, payload(contract, 7070707U, 77U, "stage07_mmse_vectors"));
            const auto symbols = bpsk(encoded.encodedBits);
            const double sigma2 = scl::bch::s2::stage01::awgnSigma2(contract.actualRate, ebn0);
            scl::bch::s2::stage07::LinearMmse equalizer(symbols.size(), channel.impulse, sigma2);
            RandomIdentity id{7070707U, "stage07_mmse_vectors:" + channel.id + ":P0",
                              contract.caseId, static_cast<std::uint64_t>(ebn0 + 4.0), 77U};
            const auto noise = scl::bch::s2::stage01::standardGaussianFrame(
                id, RandomDomain::Awgn, equalizer.observationCount());
            const auto result = equalizer.apply(symbols, noise);
            const std::string vectorId = contract.caseId + "_E" + std::to_string(static_cast<int>(ebn0));
            input << vectorId << ",MMSE," << contract.caseId << ',' << ebn0 << ','
                  << std::setprecision(17) << sigma2 << ",\"" << doubles(symbols)
                  << "\",\"" << doubles(noise) << "\"\n";
            cpp << vectorId << ",MMSE," << contract.caseId << ',' << ebn0 << ','
                << sigma2 << ',' << result.convolution.size() << ",\""
                << doubles(result.convolution) << "\",\"" << doubles(result.rhs)
                << "\",\"" << doubles(result.symbols) << "\",\""
                << bits(result.hardBits) << "\"," << result.residual << '\n';
        }
    }
}

void writeH1(const fs::path& outDir) {
    std::ofstream out(outDir / "stage07_multipath_validation_h1_awgn_compare.csv");
    out << "caseId,receivedMaxAbsDiff,equalizerMaxAbsDiff,hardMismatch,payloadMismatch,"
           "payloadErrorBitsMismatch,payloadErrorFramesMismatch,decoderStatusMismatch,gate\n";
    for (const auto& contract : scl::bch::s2::stage02::allCaseContracts()) {
        const auto source = payload(contract, 7070707U, 5U, "stage07_h1");
        const auto encoded = scl::bch::s2::stage02::encodeFrame(contract.id, source);
        const auto symbols = bpsk(encoded.encodedBits);
        const double sigma2 = scl::bch::s2::stage01::awgnSigma2(contract.actualRate, 6.0);
        scl::bch::s2::stage07::LinearMmse equalizer(symbols.size(), {1.0}, sigma2);
        RandomIdentity id{7070707U, "stage07_h1:H1:P0", contract.caseId, 0U, 5U};
        const auto noise = scl::bch::s2::stage01::standardGaussianFrame(
            id, RandomDomain::Awgn, equalizer.observationCount());
        const auto result = equalizer.apply(symbols, noise);
        double receivedDiff = 0.0;
        double equalizedDiff = 0.0;
        scl::common::BitVector baselineHard(symbols.size());
        for (std::size_t i = 0; i < symbols.size(); ++i) {
            const double received = symbols[i] + std::sqrt(sigma2) * noise[i];
            const double xhat = received / (1.0 + sigma2);
            receivedDiff = std::max(receivedDiff, std::abs(received - result.received[i]));
            equalizedDiff = std::max(equalizedDiff, std::abs(xhat - result.symbols[i]));
            baselineHard[i] = scl::bch::s2::stage01::hardDecision(xhat);
        }
        const auto decodedA = scl::bch::s2::stage02::decodeFrame(contract.id, result.hardBits);
        const auto decodedB = scl::bch::s2::stage02::decodeFrame(contract.id, baselineHard);
        const auto hardMismatch = scl::bch::s2::stage07::countErrors(result.hardBits, baselineHard);
        const auto payloadMismatch = scl::bch::s2::stage07::countErrors(decodedA.payload, decodedB.payload);
        const auto errorA = scl::bch::s2::stage07::countErrors(source, decodedA.payload);
        const auto errorB = scl::bch::s2::stage07::countErrors(source, decodedB.payload);
        const bool pass = receivedDiff < 1e-15 && equalizedDiff < 1e-14 &&
                          hardMismatch == 0U && payloadMismatch == 0U &&
                          errorA == errorB && decodedA.reportedSuccess == decodedB.reportedSuccess;
        out << contract.caseId << ',' << receivedDiff << ',' << equalizedDiff << ','
            << hardMismatch << ',' << payloadMismatch << ',' << (errorA != errorB) << ','
            << ((errorA != 0U) != (errorB != 0U)) << ','
            << (decodedA.reportedSuccess != decodedB.reportedSuccess) << ','
            << (pass ? "PASS" : "BLOCKED") << '\n';
        if (!pass) throw std::runtime_error("h=[1] AWGN degeneration mismatch");
    }
}

void writeNoiseless(const fs::path& outDir) {
    std::ofstream out(outDir / "stage07_multipath_validation_noiseless_results.csv");
    out << "caseId,totalFrames,totalPayloadBits,payloadErrorBits,payloadErrorFrames,"
           "decoderFailureFrames,miscorrectionFrames,undetectedErrorFrames,trueSuccessFrames,ber,fer,solverResidualMax,gate\n";
    for (const auto& contract : scl::bch::s2::stage02::allCaseContracts()) {
        FrameCounts counts;
        std::vector<scl::common::BitVector> fixed;
        fixed.emplace_back(contract.payloadLength, 0U);
        fixed.emplace_back(contract.payloadLength, 1U);
        fixed.emplace_back(contract.payloadLength, 0U);
        fixed.emplace_back(contract.payloadLength, 0U);
        for (std::size_t i = 0; i < contract.payloadLength; ++i) {
            fixed[2][i] = i % 2U;
            fixed[3][i] = 1U - (i % 2U);
        }
        fixed.emplace_back(contract.payloadLength, 0U); fixed.back().front() = 1U;
        fixed.emplace_back(contract.payloadLength, 0U); fixed.back().back() = 1U;
        fixed.push_back(payload(contract, 7070707U, 999999U, "stage07_noiseless_fixed"));
        std::uint64_t frameIndex = 0U;
        for (const auto& values : fixed) {
            scl::bch::s2::stage07::addFrame(
                counts, contract.id, values, 100.0, 7070707U, 0U, frameIndex++, true);
        }
        for (std::uint64_t frame = 0; frame < 1000U; ++frame) {
            const auto values = payload(contract, 7070707U, frame, "stage07_noiseless_random");
            scl::bch::s2::stage07::addFrame(
                counts, contract.id, values, 100.0, 7070707U, 0U, frameIndex++, true);
        }
        const bool pass = counts.payloadErrorBits == 0U && counts.payloadErrorFrames == 0U &&
            counts.decoderFailureFrames == 0U && counts.miscorrectionFrames == 0U &&
            counts.undetectedErrorFrames == 0U && counts.trueSuccessFrames == counts.totalFrames &&
            counts.solverResidualMax < 1e-11;
        out << contract.caseId << ',' << counts.totalFrames << ',' << counts.totalPayloadBits << ','
            << counts.payloadErrorBits << ',' << counts.payloadErrorFrames << ','
            << counts.decoderFailureFrames << ',' << counts.miscorrectionFrames << ','
            << counts.undetectedErrorFrames << ',' << counts.trueSuccessFrames << ",0,0,"
            << std::setprecision(17) << counts.solverResidualMax << ','
            << (pass ? "PASS" : "BLOCKED") << '\n';
        if (!pass) throw std::runtime_error("noiseless validation failed");
    }
}

void writeExecutionEquivalence(const fs::path& outDir) {
    const auto& contract = scl::bch::s2::stage02::caseContract(
        scl::bch::s2::stage02::CaseId::K200_M255K207);
    const auto continuous = runRange(contract, 6.0, 0U, 60U);
    FrameCounts resumed;
    addCounts(resumed, runRange(contract, 6.0, 0U, 30U));
    addCounts(resumed, runRange(contract, 6.0, 30U, 60U));
    FrameCounts sharded;
    addCounts(sharded, runRange(contract, 6.0, 0U, 60U, 2U));
    addCounts(sharded, runRange(contract, 6.0, 1U, 60U, 2U));
    const bool resumePass = sameIntegerCounts(continuous, resumed);
    const bool shardPass = sameIntegerCounts(continuous, sharded);
    auto write = [&](const fs::path& path, const FrameCounts& candidate, bool pass) {
        std::ofstream out(path);
        out << "mode,totalFrames,totalPayloadBits,payloadErrorBits,payloadErrorFrames,"
               "decoderFailureFrames,miscorrectionFrames,undetectedErrorFrames,trueSuccessFrames,gate\n";
        out << "continuous," << continuous.totalFrames << ',' << continuous.totalPayloadBits << ','
            << continuous.payloadErrorBits << ',' << continuous.payloadErrorFrames << ','
            << continuous.decoderFailureFrames << ',' << continuous.miscorrectionFrames << ','
            << continuous.undetectedErrorFrames << ',' << continuous.trueSuccessFrames << ",REFERENCE\n";
        out << "candidate," << candidate.totalFrames << ',' << candidate.totalPayloadBits << ','
            << candidate.payloadErrorBits << ',' << candidate.payloadErrorFrames << ','
            << candidate.decoderFailureFrames << ',' << candidate.miscorrectionFrames << ','
            << candidate.undetectedErrorFrames << ',' << candidate.trueSuccessFrames << ','
            << (pass ? "PASS" : "BLOCKED") << '\n';
    };
    write(outDir / "stage07_multipath_validation_resume_compare.csv", resumed, resumePass);
    write(outDir / "stage07_multipath_validation_shard_merge_compare.csv", sharded, shardPass);
    if (!resumePass || !shardPass) throw std::runtime_error("resume/shard count mismatch");
}

void writeTrial(const fs::path& outDir) {
    std::ofstream out(outDir / "stage07_multipath_validation_trial_results.csv");
    out << "stageId,caseId,displayName,payloadLength,encodedLength,actualRate,ebn0Index,ebn0Db,"
           "snrLinear,snrDb,sigma2,totalFrames,totalPayloadBits,payloadErrorBits,payloadErrorFrames,"
           "decoderFailureFrames,miscorrectionFrames,undetectedErrorFrames,trueSuccessFrames,ber,fer,"
           "encodeTimeMeanNs,channelTimeMeanNs,equalizeTimeMeanNs,decodeTimeMeanNs,decodeTimeP95Ns,"
           "decodeTimeP99Ns,equalizeTimeP95Ns,equalizeTimeP99Ns,solverResidualMean,solverResidualMax\n";
    const auto wallStart = std::chrono::steady_clock::now();
    std::uint64_t allFrames = 0U;
    for (const auto& contract : scl::bch::s2::stage02::allCaseContracts()) {
        const auto grid = trialGrid(contract.caseId);
        for (std::size_t point = 0; point < grid.size(); ++point) {
            FrameCounts counts;
            for (std::uint64_t frame = 0; frame < 500U; ++frame) {
                const auto values = payload(contract, 7070707U, frame, "stage07_trial");
                scl::bch::s2::stage07::addFrame(
                    counts, contract.id, values, grid[point], 7070707U, point, frame, false);
            }
            allFrames += counts.totalFrames;
            const double frames = static_cast<double>(counts.totalFrames);
            const double bitsCount = static_cast<double>(counts.totalPayloadBits);
            out << "stage07_multipath_validation," << contract.caseId << ",\"" << contract.displayName
                << "\"," << contract.payloadLength << ',' << contract.totalEncodedLength << ','
                << std::setprecision(17) << contract.actualRate << ',' << point << ',' << grid[point]
                << ',' << scl::bch::s2::stage01::snrLinear(contract.actualRate, grid[point])
                << ',' << scl::bch::s2::stage01::snrDb(contract.actualRate, grid[point])
                << ',' << scl::bch::s2::stage01::awgnSigma2(contract.actualRate, grid[point])
                << ',' << counts.totalFrames << ',' << counts.totalPayloadBits << ','
                << counts.payloadErrorBits << ',' << counts.payloadErrorFrames << ','
                << counts.decoderFailureFrames << ',' << counts.miscorrectionFrames << ','
                << counts.undetectedErrorFrames << ',' << counts.trueSuccessFrames << ','
                << counts.payloadErrorBits / bitsCount << ',' << counts.payloadErrorFrames / frames
                << ',' << counts.encodeTimeTotalNs / frames << ',' << counts.channelTimeTotalNs / frames
                << ',' << counts.equalizeTimeTotalNs / frames << ',' << counts.decodeTimeTotalNs / frames
                << ',' << scl::bch::s2::stage07::percentile(counts.decodeTimesNs, .95)
                << ',' << scl::bch::s2::stage07::percentile(counts.decodeTimesNs, .99)
                << ',' << scl::bch::s2::stage07::percentile(counts.equalizeTimesNs, .95)
                << ',' << scl::bch::s2::stage07::percentile(counts.equalizeTimesNs, .99)
                << ',' << counts.solverResidualSum / frames << ',' << counts.solverResidualMax << '\n';
        }
    }
    const double seconds = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - wallStart).count();
    std::ofstream estimate(outDir / "stage07_multipath_validation_runtime_estimate.csv");
    estimate << "trialFrames,trialWallSeconds,framesPerSecond,formalMinimumFrames,"
                "estimatedMinimumFormalSeconds\n";
    estimate << allFrames << ',' << seconds << ',' << allFrames / seconds << ",120000,"
             << 120000.0 / (allFrames / seconds) << '\n';
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("usage: runner OUTPUT_DIRECTORY");
        const fs::path outDir(argv[1]);
        fs::create_directories(outDir);
        writeFixedVectors(outDir);
        writeH1(outDir);
        writeNoiseless(outDir);
        writeExecutionEquivalence(outDir);
        writeTrial(outDir);
        std::cout << "PASS_STAGE07_MULTIPATH_VALIDATION_CPP\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_STAGE07_MULTIPATH_VALIDATION_CPP: " << error.what() << '\n';
        return 1;
    }
}
