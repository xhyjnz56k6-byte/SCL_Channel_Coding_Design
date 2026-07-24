#include "bch_simulation/bch_case_adapter.hpp"

#include "common/demodulation.hpp"
#include "common/frame_pool.hpp"
#include "common/modulation.hpp"
#include "common/simulation_metrics.hpp"

#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using scl::bch::simulation::BchCaseId;

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

scl::common::BitVector alternating(std::size_t size, scl::common::Bit first) {
    scl::common::BitVector bits(size);
    for (std::size_t i = 0; i < size; ++i) bits[i] = static_cast<scl::common::Bit>((first + i) & 1U);
    return bits;
}

std::vector<scl::common::BitVector> boundaryPayloads(std::size_t size) {
    std::vector<scl::common::BitVector> values;
    values.emplace_back(size, 0U);
    values.emplace_back(size, 1U);
    values.emplace_back(size, 0U); values.back().front() = 1U;
    values.emplace_back(size, 0U); values.back().back() = 1U;
    values.push_back(alternating(size, 0U));
    values.push_back(alternating(size, 1U));
    scl::common::BitVector middle(size, 0U); middle[size / 2U] = 1U; values.push_back(middle);
    return values;
}

struct Counts {
    std::uint64_t frames = 0U;
    std::uint64_t bitErrors = 0U;
    std::uint64_t frameErrors = 0U;
    std::uint64_t trueSuccess = 0U;
    std::uint64_t reportedSuccess = 0U;
    std::uint64_t miscorrected = 0U;
    std::uint64_t decoderFailure = 0U;
    std::uint64_t channelHardBitErrors = 0U;
};

void exercise(const scl::bch::simulation::BchSimulationCase& simulationCase,
              const scl::common::BitVector& payload,
              const std::string& source,
              std::uint64_t frameIndex,
              Counts& counts,
              std::ofstream& detail) {
    const auto encoded = scl::bch::simulation::encodeBchFrame(simulationCase, payload);
    const auto symbols = scl::common::bpskModulate(encoded.codeword);
    const auto hard = scl::common::hardDecision(symbols);
    const std::uint64_t hardErrors = scl::common::countBitErrors(encoded.codeword, hard);
    auto decoded = scl::bch::simulation::decodeBchFrame(simulationCase, hard);
    scl::bch::simulation::auditDecodedBchFrame(payload, decoded);
    const std::uint64_t payloadErrors = scl::common::countBitErrors(payload, decoded.payload);
    ++counts.frames;
    counts.bitErrors += payloadErrors;
    counts.frameErrors += payloadErrors != 0U;
    counts.trueSuccess += decoded.trueSuccess;
    counts.reportedSuccess += decoded.reportedSuccess;
    counts.miscorrected += decoded.miscorrected;
    counts.decoderFailure += decoded.decoderFailure;
    counts.channelHardBitErrors += hardErrors;
    detail << simulationCase.caseName << ',' << source << ',' << frameIndex << ','
           << payloadErrors << ',' << hardErrors << ',' << decoded.trueSuccess << ','
           << decoded.reportedSuccess << ',' << decoded.miscorrected << ','
           << decoded.decoderFailure << ',' << decoded.frameStatus << '\n';
    require(encoded.codeword.size() == simulationCase.encodedLength, "encoded length mismatch");
    require(symbols.size() == simulationCase.encodedLength, "BPSK length mismatch");
    require(hard == encoded.codeword, "identity hard decision changed codeword");
    require(payloadErrors == 0U && decoded.trueSuccess, "noiseless payload mismatch");
    require(decoded.reportedSuccess && !decoded.miscorrected && !decoded.decoderFailure,
            "noiseless decoder status mismatch");
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 4) throw std::invalid_argument("usage: test_bch11_noiseless K200_MANIFEST K300_MANIFEST OUTPUT_DIR");
        const fs::path output(argv[3]);
        fs::create_directories(output);
        scl::common::PackedFramePoolReader pool200(argv[1]);
        scl::common::PackedFramePoolReader pool300(argv[2]);
        require(pool200.payloadLength() == 200U && pool200.frameCount() >= 200U, "K200 pool mismatch");
        require(pool300.payloadLength() == 300U && pool300.frameCount() >= 200U, "K300 pool mismatch");
        require(scl::common::hardDecisionBit(0.0) == 0U, "hard decision y=0 boundary mismatch");

        std::ofstream detail(output / "noiseless_frame_detail.csv");
        std::ofstream summary(output / "noiseless_summary.csv");
        std::ofstream config(output / "case_config.csv");
        require(detail && summary && config, "failed to open BCH-11 CSV output");
        detail << "caseName,source,frameIndex,decodedBitErrors,channelHardBitErrors,trueSuccess,reportedSuccess,miscorrected,decoderFailure,frameStatus\n";
        summary << "caseName,processedFrames,decodedBitErrors,frameErrors,BER,FER,trueSuccessRate,reportedSuccessRate,miscorrectionRate,decoderFailureRate,channelHardBitErrors\n";
        config << "caseName,payloadLength,encodedLength,frameRate,organization,decoderType\n";

        for (BchCaseId id : {BchCaseId::S200, BchCaseId::B200, BchCaseId::S300, BchCaseId::B300, BchCaseId::B300_426}) {
            const auto& value = scl::bch::simulation::bchSimulationCase(id);
            require(std::abs(value.frameRate - static_cast<double>(value.payloadLength) / value.encodedLength) < 1e-15,
                    "frame rate mismatch");
            Counts counts;
            auto& pool = value.payloadLength == 200U ? pool200 : pool300;
            for (std::uint64_t frame = 0U; frame < 200U; ++frame) {
                exercise(value, pool.readFrame(frame).payloadBits, "COMMON_POOL", frame, counts, detail);
            }
            const auto boundaries = boundaryPayloads(value.payloadLength);
            for (std::size_t i = 0; i < boundaries.size(); ++i) {
                exercise(value, boundaries[i], "BOUNDARY", i, counts, detail);
            }
            require(counts.frames == 207U, "BCH-11 frame count mismatch");
            require(counts.bitErrors == 0U && counts.frameErrors == 0U && counts.channelHardBitErrors == 0U,
                    "BCH-11 noiseless error counter mismatch");
            require(counts.trueSuccess == counts.frames && counts.reportedSuccess == counts.frames &&
                    counts.miscorrected == 0U && counts.decoderFailure == 0U,
                    "BCH-11 status counter mismatch");
            summary << value.caseName << ',' << counts.frames << ',' << counts.bitErrors << ','
                    << counts.frameErrors << ",0,0,1,1,0,0," << counts.channelHardBitErrors << '\n';
            config << value.caseName << ',' << value.payloadLength << ',' << value.encodedLength << ','
                   << value.frameRate << ',' << scl::bch::simulation::organizationName(value.organization) << ','
                   << scl::bch::simulation::decoderTypeName(value.decoderType) << '\n';
        }

        bool rejected = false;
        try { static_cast<void>(scl::bch::simulation::bchSimulationCase("BCH-INVALID")); }
        catch (const std::invalid_argument&) { rejected = true; }
        require(rejected, "invalid case name was not rejected");
        rejected = false;
        try {
            const auto& value = scl::bch::simulation::bchSimulationCase(BchCaseId::S200);
            static_cast<void>(scl::bch::simulation::encodeBchFrame(value, scl::common::BitVector(199U, 0U)));
        } catch (const std::invalid_argument&) { rejected = true; }
        require(rejected, "invalid payload length was not rejected");
        std::cout << "PASS_BCH11_COMMON_INTEGRATION_NOISELESS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_BCH11_NOISELESS_PAYLOAD_MISMATCH: " << error.what() << '\n';
        return 1;
    }
}
