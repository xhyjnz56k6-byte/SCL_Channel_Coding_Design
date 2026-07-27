#include "stage01_foundation_awgn.hpp"
#include "stage02_case_contract.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace {

using scl::bch::s2::stage02::CaseContract;
using scl::bch::s2::stage02::CaseId;

struct Counts {
    std::uint64_t totalFrames = 0U;
    std::uint64_t totalPayloadBits = 0U;
    std::uint64_t payloadErrorBits = 0U;
    std::uint64_t payloadErrorFrames = 0U;
    std::uint64_t decoderFailureFrames = 0U;
    std::uint64_t miscorrectionFrames = 0U;
    std::uint64_t undetectedErrorFrames = 0U;
    std::uint64_t trueSuccessFrames = 0U;
};

void require(bool value, const std::string& message) {
    if (!value) throw std::runtime_error(message);
}

std::string bitsText(const scl::common::BitVector& bits) {
    std::string text;
    text.reserve(bits.size());
    for (auto bit : bits) text.push_back(bit == 0U ? '0' : '1');
    return text;
}

scl::common::BitVector fixedPattern(std::size_t length, unsigned pattern) {
    scl::common::BitVector bits(length, 0U);
    if (pattern == 1U) std::fill(bits.begin(), bits.end(), 1U);
    if (pattern == 2U || pattern == 3U) {
        for (std::size_t i = 0; i < length; ++i) bits[i] = static_cast<scl::common::Bit>((i + pattern) & 1U);
    }
    if (pattern == 4U) bits.front() = 1U;
    if (pattern == 5U) bits.back() = 1U;
    return bits;
}

scl::common::BitVector randomPayload(
    const scl::bch::s2::stage01::RandomIdentity& identity,
    std::size_t length) {
    const auto source = scl::bch::s2::stage01::payloadFrame(identity, length);
    return scl::common::BitVector(source.begin(), source.end());
}

std::uint64_t bitErrors(const scl::common::BitVector& left, const scl::common::BitVector& right) {
    require(left.size() == right.size(), "payload comparison length mismatch");
    std::uint64_t count = 0U;
    for (std::size_t i = 0; i < left.size(); ++i) count += left[i] != right[i];
    return count;
}

void exercise(const CaseContract& contract,
              const scl::common::BitVector& payload,
              const std::string& source,
              std::uint64_t frameIndex,
              Counts& counts,
              std::ofstream& results,
              std::ofstream& samples) {
    const auto encoded = scl::bch::s2::stage02::encodeFrame(contract.id, payload);
    std::vector<double> symbols(encoded.encodedBits.size());
    scl::common::BitVector hard(encoded.encodedBits.size(), 0U);
    for (std::size_t i = 0; i < encoded.encodedBits.size(); ++i) {
        symbols[i] = scl::bch::s2::stage01::bpsk(encoded.encodedBits[i]);
        hard[i] = static_cast<scl::common::Bit>(scl::bch::s2::stage01::hardDecision(symbols[i]));
    }
    const auto decoded = scl::bch::s2::stage02::decodeFrame(contract.id, hard);
    const std::uint64_t errors = bitErrors(payload, decoded.payload);
    const bool trueSuccess = errors == 0U;
    const bool miscorrection = decoded.reportedSuccess && !trueSuccess;
    const bool decoderFailure = !decoded.reportedSuccess;
    const bool undetected = miscorrection;
    ++counts.totalFrames;
    counts.totalPayloadBits += payload.size();
    counts.payloadErrorBits += errors;
    counts.payloadErrorFrames += !trueSuccess;
    counts.decoderFailureFrames += decoderFailure;
    counts.miscorrectionFrames += miscorrection;
    counts.undetectedErrorFrames += undetected;
    counts.trueSuccessFrames += trueSuccess;
    results << contract.caseId << ',' << source << ',' << frameIndex << ',' << errors << ','
            << (!trueSuccess) << ',' << decoderFailure << ',' << miscorrection << ',' << undetected << ','
            << trueSuccess << '\n';
    if (source == "FIXED_SEED_SAMPLE") {
        samples << contract.caseId << ',' << frameIndex << ',' << bitsText(payload) << ','
                << bitsText(encoded.encodedBits) << ',' << bitsText(decoded.payload) << '\n';
    }
    require(hard == encoded.encodedBits, "noiseless hard decision changed codeword");
    require(trueSuccess && decoded.reportedSuccess, "noiseless payload recovery failed");
    require(!miscorrection && !decoderFailure && !undetected, "noiseless status classification failed");
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("usage: stage03_noiseless_runner OUTPUT_DIR");
        const fs::path output(argv[1]);
        fs::create_directories(output);
        std::ofstream results(output / "stage03_noiseless_results.csv");
        std::ofstream summary(output / "stage03_noiseless_case_summary.csv");
        std::ofstream samples(output / "stage03_noiseless_cpp_matlab_samples.csv");
        if (!results || !summary || !samples) throw std::runtime_error("cannot open stage03 output");
        results << "caseId,source,frameIndex,payloadErrorBits,payloadErrorFrame,decoderFailure,"
                   "miscorrection,undetectedError,trueSuccess\n";
        summary << "caseId,totalFrames,totalPayloadBits,payloadErrorBits,payloadErrorFrames,"
                   "decoderFailureFrames,miscorrectionFrames,undetectedErrorFrames,trueSuccessFrames,ber,fer,stopReason\n";
        samples << "caseId,sampleId,payloadBits,cppEncodedBits,cppRecoveredBits\n";

        for (const auto& contract : scl::bch::s2::stage02::allCaseContracts()) {
            Counts counts;
            for (unsigned pattern = 0U; pattern < 6U; ++pattern) {
                static const char* names[] = {"ALL_ZERO","ALL_ONE","ALT_0101","ALT_1010","FIRST_ONE","LAST_ONE"};
                exercise(contract, fixedPattern(contract.payloadLength, pattern), names[pattern], pattern,
                         counts, results, samples);
            }
            scl::bch::s2::stage01::RandomIdentity sampleIdentity{
                2026072703ULL, "stage03_noiseless", contract.caseId, 0U, 1000000U};
            exercise(contract,
                     randomPayload(sampleIdentity, contract.payloadLength),
                     "FIXED_SEED_SAMPLE", sampleIdentity.frameIndex, counts, results, samples);
            for (std::uint64_t frame = 0U; frame < 1000U; ++frame) {
                scl::bch::s2::stage01::RandomIdentity identity{
                    2026072703ULL, "stage03_noiseless", contract.caseId, 0U, frame};
                exercise(contract,
                         randomPayload(identity, contract.payloadLength),
                         "RANDOM", frame, counts, results, samples);
            }
            require(counts.totalFrames == 1007U, "stage03 frame count mismatch");
            require(counts.payloadErrorBits == 0U && counts.payloadErrorFrames == 0U &&
                    counts.decoderFailureFrames == 0U && counts.miscorrectionFrames == 0U &&
                    counts.undetectedErrorFrames == 0U && counts.trueSuccessFrames == counts.totalFrames,
                    "stage03 zero-error Gate mismatch");
            summary << contract.caseId << ',' << counts.totalFrames << ',' << counts.totalPayloadBits << ','
                    << counts.payloadErrorBits << ',' << counts.payloadErrorFrames << ','
                    << counts.decoderFailureFrames << ',' << counts.miscorrectionFrames << ','
                    << counts.undetectedErrorFrames << ',' << counts.trueSuccessFrames
                    << ",0,0,NOISELESS_FIXED_FRAMES\n";
        }
        std::cout << "PASS_STAGE03_NOISELESS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_STAGE03_NOISELESS: " << error.what() << '\n';
        return 1;
    }
}
