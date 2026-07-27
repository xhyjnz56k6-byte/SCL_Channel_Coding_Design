#include "bch_simulation/bch_case_adapter.hpp"
#include "bch_simulation/fixed_multipath_mmse.hpp"

#include "common/frame_pool.hpp"
#include "common/gaussian_noise.hpp"
#include "common/modulation.hpp"
#include "common/simulation_metrics.hpp"

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

namespace {

std::string bits(const scl::common::BitVector& values) {
    std::string text;
    text.reserve(values.size());
    for (auto bit : values) text.push_back(bit ? '1' : '0');
    return text;
}

std::string doubles(const std::vector<double>& values) {
    std::ostringstream out;
    out << std::setprecision(17);
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i) out << ';';
        out << values[i];
    }
    return out.str();
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 4) {
            throw std::invalid_argument("usage: exporter k200_manifest k300_manifest output_csv");
        }
        scl::common::PackedFramePoolReader pools[] = {
            scl::common::PackedFramePoolReader(argv[1]),
            scl::common::PackedFramePoolReader(argv[2]),
        };
        fs::create_directories(fs::path(argv[3]).parent_path());
        std::ofstream out(argv[3]);
        if (!out) throw std::runtime_error("failed to open MATLAB vector CSV");
        out << "caseName,payloadLength,encodedLength,sourcePayloadEbN0Db,snrDb,noiseVariance,frameIndex,payloadBits,encodedBits,standardNoise,cppFullConvolution,cppReceivedSamples,cppEqualizedSymbols,cppHardBits,cppDecodedPayload,cppDecodedFrameError\n";
        const auto channel = scl::bch::simulation::frozenFixedMultipathConfig();
        for (const std::string caseName :
             {"BCH-S200", "BCH-B200", "BCH-S300", "BCH-B300", "BCH-B300-426"}) {
            const auto& simulationCase =
                scl::bch::simulation::bchSimulationCase(caseName);
            auto& pool = pools[simulationCase.payloadLength == 200U ? 0 : 1];
            scl::bch::simulation::prepareBchCase(simulationCase);
            for (double ebn0 : {8.0, 10.0, 14.0}) {
                const double snr =
                    ebn0 + 10.0 * std::log10(simulationCase.frameRate);
                const double variance = 1.0 / (2.0 * std::pow(10.0, snr / 10.0));
                scl::bch::simulation::FixedMultipathMmseEqualizer equalizer(
                    simulationCase.encodedLength, channel, variance);
                const std::uint64_t snrIndex =
                    static_cast<std::uint64_t>(std::llround(ebn0 * 10.0));
                const std::uint64_t noiseGroup =
                    simulationCase.payloadLength * 1000000ULL + snrIndex;
                for (std::uint64_t frame = 0; frame < 100U; ++frame) {
                    const auto payload = pool.readFrame(frame).payloadBits;
                    const auto encoded =
                        scl::bch::simulation::encodeBchFrame(simulationCase, payload);
                    const auto noise = scl::common::generateStandardGaussianFrame(
                        2026072401ULL, noiseGroup, frame,
                        equalizer.observationCount(), 1U);
                    const auto result = equalizer.apply(
                        scl::common::bpskModulate(encoded.codeword), noise);
                    auto decoded = scl::bch::simulation::decodeBchFrame(
                        simulationCase, result.hardBits);
                    scl::bch::simulation::auditDecodedBchFrame(payload, decoded);
                    out << caseName << ',' << simulationCase.payloadLength << ','
                        << simulationCase.encodedLength << ',' << std::setprecision(17)
                        << ebn0 << ',' << snr << ',' << variance << ',' << frame << ','
                        << bits(payload) << ',' << bits(encoded.codeword) << ",\""
                        << doubles(noise) << "\",\"" << doubles(result.fullConvolutionOutput)
                        << "\",\"" << doubles(result.receivedSamples) << "\",\""
                        << doubles(result.equalizedSymbols) << "\"," << bits(result.hardBits)
                        << ',' << bits(decoded.payload) << ',' << (!decoded.trueSuccess) << '\n';
                }
            }
        }
        std::cout << "PASS_BCH_S2_MATLAB_VECTOR_EXPORT rows=1500\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_BCH_S2_MATLAB_VECTOR_EXPORT: " << error.what() << '\n';
        return 1;
    }
}
