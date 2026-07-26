#include "bch_simulation/bch_case_adapter.hpp"
#include "bch_simulation/bch_impairment_channels.hpp"
#include "bch_simulation/bch_multipath_simulation.hpp"

#include "common/frame_pool.hpp"
#include "common/gaussian_noise.hpp"
#include "common/modulation.hpp"

#include <cmath>
#include <complex>
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
    for (std::size_t index = 0U; index < values.size(); ++index) {
        if (index) out << ';';
        out << values[index];
    }
    return out.str();
}

std::vector<double> parts(
    const std::vector<std::complex<double>>& values, bool imaginary) {
    std::vector<double> output(values.size());
    for (std::size_t index = 0U; index < values.size(); ++index) {
        output[index] = imaginary ? values[index].imag() : values[index].real();
    }
    return output;
}

void writeRow(
    std::ofstream& out,
    const std::string& experimentClass,
    const scl::bch::simulation::BchSimulationCase& simulationCase,
    std::uint64_t frame,
    double ebn0,
    double snr,
    double phase,
    double rotation,
    const scl::common::BitVector& payload,
    const scl::common::BitVector& encoded,
    const std::vector<double>& noise,
    const scl::bch::simulation::ResidualCfoOutput& noComp,
    const scl::bch::simulation::ResidualCfoOutput& perfect,
    const scl::bch::simulation::DecodedBchFrame& noCompDecoded,
    const scl::bch::simulation::DecodedBchFrame& perfectDecoded) {
    out << experimentClass << ',' << simulationCase.caseName << ','
        << simulationCase.payloadLength << ',' << simulationCase.encodedLength
        << ',' << std::setprecision(17) << simulationCase.frameRate << ','
        << frame << ',' << ebn0 << ',' << snr << ',' << phase << ','
        << rotation << ',' << bits(payload) << ',' << bits(encoded) << ",\""
        << doubles(noise) << "\",\"" << doubles(parts(noComp.receivedSamples, false))
        << "\",\"" << doubles(parts(noComp.receivedSamples, true)) << "\",\""
        << doubles(parts(perfect.compensatedSamples, false)) << "\",\""
        << doubles(parts(perfect.compensatedSamples, true)) << "\","
        << bits(noComp.hardBits) << ',' << bits(perfect.hardBits) << ','
        << bits(noCompDecoded.payload) << ',' << bits(perfectDecoded.payload)
        << ',' << noCompDecoded.trueSuccess << ',' << perfectDecoded.trueSuccess
        << '\n';
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 4) {
            throw std::invalid_argument(
                "usage: exporter k200_manifest k300_manifest output_csv");
        }
        scl::common::PackedFramePoolReader pools[] = {
            scl::common::PackedFramePoolReader(argv[1]),
            scl::common::PackedFramePoolReader(argv[2]),
        };
        fs::create_directories(fs::path(argv[3]).parent_path());
        std::ofstream out(argv[3]);
        if (!out) throw std::runtime_error("failed to open corrected CFO vectors");
        out << "experimentClass,caseName,payloadLength,encodedLength,frameRate,"
               "frameIndex,sourcePayloadEbN0Db,snrDb,initialPhaseDeg,"
               "frameRotationDeg,payloadBits,encodedBits,standardComplexNoise,"
               "cppReceivedReal,cppReceivedImag,cppPerfectReal,cppPerfectImag,"
               "cppNoCompHardBits,cppPerfectHardBits,cppNoCompDecodedPayload,"
               "cppPerfectDecodedPayload,cppNoCompTrueSuccess,"
               "cppPerfectTrueSuccess\n";
        constexpr std::uint64_t seed = 2026072601ULL;
        for (const std::string caseName :
             {"BCH-S200", "BCH-B200", "BCH-S300", "BCH-B300", "BCH-B300-426"}) {
            const auto& simulationCase =
                scl::bch::simulation::bchSimulationCase(caseName);
            auto& pool = pools[simulationCase.payloadLength == 200U ? 0 : 1];
            scl::bch::simulation::prepareBchCase(simulationCase);
            const double ebn0 = simulationCase.payloadLength == 200U ? 5.0 : 4.5;
            const double snr =
                ebn0 + 10.0 * std::log10(simulationCase.frameRate);
            const double realVariance =
                1.0 / (2.0 * std::pow(10.0, snr / 10.0));
            const std::uint64_t group =
                scl::bch::simulation::makePhysicalSnrNoiseGroup(
                    simulationCase.payloadLength, snr, 2U);
            for (std::uint64_t frame = 0U; frame < 100U; ++frame) {
                const auto payload = pool.readFrame(frame).payloadBits;
                const auto encoded = scl::bch::simulation::encodeBchFrame(
                    simulationCase, payload).codeword;
                const auto symbols = scl::common::bpskModulate(encoded);
                const auto noise = scl::common::generateStandardGaussianFrame(
                    seed, group, frame, simulationCase.encodedLength * 2U, 2U);
                for (double rotation : {0.0, 30.0, 60.0}) {
                    scl::bch::simulation::ResidualCfoConfig config;
                    config.initialPhaseDeg = 0.0;
                    config.frameRotationDeg = rotation;
                    config.noiseVariance = realVariance * 2.0;
                    const auto noComp =
                        scl::bch::simulation::applyResidualCfo(symbols, noise, config);
                    config.compensationMode =
                        scl::bch::simulation::CfoCompensationMode::Perfect;
                    const auto perfect =
                        scl::bch::simulation::applyResidualCfo(symbols, noise, config);
                    auto noCompDecoded = scl::bch::simulation::decodeBchFrame(
                        simulationCase, noComp.hardBits);
                    auto perfectDecoded = scl::bch::simulation::decodeBchFrame(
                        simulationCase, perfect.hardBits);
                    scl::bch::simulation::auditDecodedBchFrame(
                        payload, noCompDecoded);
                    scl::bch::simulation::auditDecodedBchFrame(
                        payload, perfectDecoded);
                    writeRow(
                        out, "RESIDUAL_CFO_PHI0_ZERO", simulationCase, frame,
                        ebn0, snr, 0.0, rotation, payload, encoded, noise,
                        noComp, perfect, noCompDecoded, perfectDecoded);
                }
                for (double phase : {0.0, 45.0, 90.0, 135.0}) {
                    scl::bch::simulation::ResidualCfoConfig config;
                    config.initialPhaseDeg = phase;
                    config.frameRotationDeg = 0.0;
                    config.noiseVariance = realVariance * 2.0;
                    const auto noComp =
                        scl::bch::simulation::applyResidualCfo(symbols, noise, config);
                    config.compensationMode =
                        scl::bch::simulation::CfoCompensationMode::Perfect;
                    const auto perfect =
                        scl::bch::simulation::applyResidualCfo(symbols, noise, config);
                    auto noCompDecoded = scl::bch::simulation::decodeBchFrame(
                        simulationCase, noComp.hardBits);
                    auto perfectDecoded = scl::bch::simulation::decodeBchFrame(
                        simulationCase, perfect.hardBits);
                    scl::bch::simulation::auditDecodedBchFrame(
                        payload, noCompDecoded);
                    scl::bch::simulation::auditDecodedBchFrame(
                        payload, perfectDecoded);
                    writeRow(
                        out, "INITIAL_PHASE_SENSITIVITY", simulationCase, frame,
                        ebn0, snr, phase, 0.0, payload, encoded, noise,
                        noComp, perfect, noCompDecoded, perfectDecoded);
                }
            }
        }
        std::cout << "PASS_BCH_S2_CORRECTED_CFO_MATLAB_VECTOR_EXPORT rows=3500\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_BCH_S2_CORRECTED_CFO_MATLAB_VECTOR_EXPORT: "
                  << error.what() << '\n';
        return 1;
    }
}
