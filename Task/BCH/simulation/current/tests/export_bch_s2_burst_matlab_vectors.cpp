#include "bch_simulation/bch_burst_simulation.hpp"
#include "bch_simulation/bch_interleaver.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace fs = std::filesystem;
namespace sim = scl::bch::simulation;

namespace {

std::string bits(const scl::common::BitVector& value) {
    std::string result;
    result.reserve(value.size());
    for (auto bit : value) result.push_back(bit ? '1' : '0');
    return result;
}

std::string indices(const std::vector<std::size_t>& value) {
    std::ostringstream out;
    for (std::size_t i = 0; i < value.size(); ++i) {
        if (i) out << ';';
        out << value[i];
    }
    return out.str();
}

scl::common::BitVector payload(
    const sim::BchSimulationCase& value, std::uint64_t frame,
    std::uint64_t domain) {
    scl::common::BitVector result(value.payloadLength);
    for (std::size_t i = 0; i < result.size(); ++i) {
        result[i] = sim::burstDomainValue(2026072607ULL, frame, domain + i) & 1U;
    }
    return result;
}

void emit(
    std::ofstream& out, const std::string& stage,
    const sim::BchSimulationCase& value, const std::string& mode,
    std::uint64_t frame, std::size_t length, std::size_t start) {
    const auto source = payload(value, frame, length + value.encodedLength);
    const auto encoded = sim::encodeBchFrame(value, source).codeword;
    const auto inter = sim::makeBchInterleaver(
        value.encodedLength,
        mode == "FIXED_RANDOM" ? sim::InterleaverMode::FixedRandom :
                                 sim::InterleaverMode::None,
        2026072607ULL + value.encodedLength);
    const auto transmitted = sim::interleave(encoded, inter);
    const auto damaged = sim::injectConsecutiveBitBurst(transmitted, start, length);
    const auto received = sim::deinterleave(damaged, inter);
    auto decoded = sim::decodeBchFrame(value, received);
    sim::auditDecodedBchFrame(source, decoded);
    out << stage << ',' << value.caseName << ',' << mode << ',' << frame << ','
        << length << ',' << start << ',' << bits(source) << ',' << bits(encoded)
        << ',' << indices(inter.permutation) << ','
        << indices(inter.inversePermutation) << ',' << bits(damaged) << ','
        << bits(received) << ',' << bits(decoded.payload) << ','
        << decoded.reportedSuccess << ',' << decoded.trueSuccess << ','
        << decoded.miscorrected << ',' << decoded.decoderFailure << ','
        << sim::errorPositions(encoded, received).size() << '\n';
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("usage: exporter output.csv");
        fs::path path(argv[1]);
        fs::create_directories(path.parent_path());
        std::ofstream out(path);
        out << "stage,caseName,interleaverMode,frameIndex,burstLength,burstStart,"
               "payloadBits,encodedBits,permutation,inversePermutation,"
               "cppTransmittedDamagedBits,cppDeinterleavedBits,cppDecodedPayload,"
               "cppReportedSuccess,cppTrueSuccess,cppMiscorrection,"
               "cppDecoderFailure,cppPostDeinterleaveErrorWeight\n";
        const std::vector<sim::BchCaseId> all{
            sim::BchCaseId::S200, sim::BchCaseId::B200, sim::BchCaseId::S300,
            sim::BchCaseId::B300, sim::BchCaseId::B300_426};
        std::uint64_t frame = 0;
        for (auto id : {sim::BchCaseId::B200, sim::BchCaseId::B300,
                        sim::BchCaseId::B300_426}) {
            const auto& value = sim::bchSimulationCase(id);
            const std::vector<std::size_t> lengths{
                0U, static_cast<std::size_t>(value.correctionCapability),
                static_cast<std::size_t>(value.correctionCapability + 1U),
                static_cast<std::size_t>(value.correctionCapability + 2U)};
            for (std::size_t length : lengths) {
                for (std::size_t k = 0; k < 20; ++k, ++frame)
                    emit(out, "S2-07A", value, "NONE", frame, length,
                         length ? (k * 17U) % (value.encodedLength - length + 1U) : 0U);
            }
        }
        for (auto id : {sim::BchCaseId::S200, sim::BchCaseId::S300}) {
            const auto& value = sim::bchSimulationCase(id);
            for (std::size_t length : {1U, 2U, 3U, 15U, 16U})
                for (std::size_t r : {0U, 1U, 13U, 14U})
                    for (std::size_t k = 0; k < 20; ++k, ++frame) {
                        std::size_t start = r + 15U * (k % 10U);
                        if (start + length > value.encodedLength)
                            start = r;
                        emit(out, "S2-07B", value, "NONE", frame, length, start);
                    }
        }
        for (auto id : all) {
            const auto& value = sim::bchSimulationCase(id);
            for (std::size_t length : {0U, 1U, 2U, 8U, 16U, 32U})
                for (std::size_t k = 0; k < 100; ++k, ++frame)
                    emit(out, "S2-07C", value, "NONE", frame, length,
                         sim::uniformBurstStart(value.encodedLength, length,
                                                2026072607ULL, frame, 7U));
        }
        for (auto id : all) {
            const auto& value = sim::bchSimulationCase(id);
            for (const std::string mode : {"NONE", "FIXED_RANDOM"})
                for (std::size_t length : {1U, 2U, 8U, 16U, 32U})
                    for (std::size_t k = 0; k < 100; ++k, ++frame)
                        emit(out, "S2-07D", value, mode, frame, length,
                             sim::uniformBurstStart(value.encodedLength, length,
                                                    2026072607ULL, frame, 9U));
        }
        std::cout << "PASS_BCH_S2_BURST_MATLAB_VECTOR_EXPORT rows=" << frame << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "FAIL_BCH_S2_BURST_MATLAB_VECTOR_EXPORT " << e.what() << '\n';
        return 1;
    }
}
