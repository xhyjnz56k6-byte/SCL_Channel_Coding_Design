#include "bch_simulation/bch_case_adapter.hpp"
#include "bch_simulation/bch_impairment_channels.hpp"
#include "bch_simulation/bch_multipath_simulation.hpp"

#include "common/awgn_channel.hpp"
#include "common/demodulation.hpp"
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

std::vector<double> realParts(const std::vector<std::complex<double>>& values) {
    std::vector<double> output(values.size());
    for (std::size_t index = 0U; index < values.size(); ++index) {
        output[index] = values[index].real();
    }
    return output;
}

std::vector<double> imagParts(const std::vector<std::complex<double>>& values) {
    std::vector<double> output(values.size());
    for (std::size_t index = 0U; index < values.size(); ++index) {
        output[index] = values[index].imag();
    }
    return output;
}

void writeRow(
    std::ofstream& out,
    const std::string& channel,
    unsigned point,
    const scl::bch::simulation::BchSimulationCase& simulationCase,
    double ebn0,
    double snr,
    std::uint64_t frame,
    const scl::common::BitVector& payload,
    const scl::common::BitVector& encoded,
    const std::vector<double>& noise,
    double phase,
    double rotation,
    const std::string& compensation,
    double attenuation,
    bool complete,
    std::size_t start,
    std::size_t length,
    const std::string& burstMode,
    const std::vector<double>& sampleReal,
    const std::vector<double>& sampleImag,
    const scl::common::BitVector& hard,
    const scl::bch::simulation::DecodedBchFrame& decoded) {
    out << channel << ',' << point << ',' << simulationCase.caseName << ','
        << simulationCase.payloadLength << ',' << simulationCase.encodedLength
        << ',' << std::setprecision(17) << simulationCase.frameRate << ','
        << ebn0 << ',' << snr << ',' << frame << ',' << phase << ','
        << rotation << ',' << compensation << ',' << attenuation << ','
        << complete << ',' << start << ',' << length << ',' << burstMode
        << ',' << bits(payload) << ',' << bits(encoded) << ",\""
        << doubles(noise) << "\",\"" << doubles(sampleReal) << "\",\""
        << doubles(sampleImag) << "\"," << bits(hard) << ','
        << bits(decoded.payload) << ',' << decoded.reportedSuccess << ','
        << decoded.trueSuccess << ',' << decoded.miscorrected << ','
        << decoded.decoderFailure << '\n';
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
        if (!out) throw std::runtime_error("failed to open batch2 MATLAB vectors");
        out << "channelType,parameterPoint,caseName,payloadLength,encodedLength,"
               "frameRate,sourcePayloadEbN0Db,snrDb,frameIndex,initialPhaseDeg,"
               "frameRotationDeg,compensationMode,attenuationDb,completeBlockage,"
               "startIndex,impairmentLength,burstMode,payloadBits,encodedBits,"
               "standardNoise,cppSampleReal,cppSampleImag,cppHardBits,"
               "cppDecodedPayload,cppReportedSuccess,cppTrueSuccess,"
               "cppMiscorrection,cppDecoderFailure\n";
        constexpr std::uint64_t seed = 2026072601ULL;
        for (const std::string caseName :
             {"BCH-S200", "BCH-B200", "BCH-S300", "BCH-B300", "BCH-B300-426"}) {
            const auto& simulationCase =
                scl::bch::simulation::bchSimulationCase(caseName);
            auto& pool = pools[simulationCase.payloadLength == 200U ? 0 : 1];
            scl::bch::simulation::prepareBchCase(simulationCase);
            for (unsigned point = 0U; point < 3U; ++point) {
                const double ebn0 = point == 0U ? 8.0 : (point == 1U ? 10.0 : 14.0);
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
                    {
                        const double phase = point == 0U ? 0.0 : (point == 1U ? 45.0 : 90.0);
                        const double rotation = point == 0U ? 0.0 : (point == 1U ? 30.0 : 60.0);
                        const auto noise = scl::common::generateStandardGaussianFrame(
                            seed, group, frame, simulationCase.encodedLength * 2U, 2U);
                        scl::bch::simulation::ResidualCfoConfig config;
                        config.initialPhaseDeg = phase;
                        config.frameRotationDeg = rotation;
                        config.noiseVariance = realVariance * 2.0;
                        config.compensationMode = point == 0U
                            ? scl::bch::simulation::CfoCompensationMode::Perfect
                            : scl::bch::simulation::CfoCompensationMode::None;
                        const auto channel =
                            scl::bch::simulation::applyResidualCfo(symbols, noise, config);
                        auto decoded = scl::bch::simulation::decodeBchFrame(
                            simulationCase, channel.hardBits);
                        scl::bch::simulation::auditDecodedBchFrame(payload, decoded);
                        writeRow(out, "RESIDUAL_CFO", point, simulationCase, ebn0,
                                 snr, frame, payload, encoded, noise, phase,
                                 rotation, point == 0U ? "PERFECT" : "NONE",
                                 0.0, false, 0U, 0U, "NONE",
                                 realParts(channel.compensatedSamples),
                                 imagParts(channel.compensatedSamples),
                                 channel.hardBits, decoded);
                    }
                    {
                        const double attenuation = point == 0U ? -6.0 :
                                                   (point == 1U ? -12.0 : 0.0);
                        const bool complete = point == 2U;
                        const std::size_t length = point == 0U ? 8U :
                                                   (point == 1U ? 16U : 32U);
                        const std::size_t start = point == 0U ? 0U :
                            (point == 1U
                                ? (simulationCase.encodedLength - length) / 2U
                                : simulationCase.encodedLength - length);
                        const auto noise = scl::common::generateStandardGaussianFrame(
                            seed, group, frame, simulationCase.encodedLength, 2U);
                        scl::bch::simulation::BlockageConfig config;
                        config.attenuationDb = attenuation;
                        config.completeBlockage = complete;
                        config.start = start;
                        config.length = length;
                        config.noiseVariance = realVariance;
                        const auto channel =
                            scl::bch::simulation::applyShortBlockage(symbols, noise, config);
                        auto decoded = scl::bch::simulation::decodeBchFrame(
                            simulationCase, channel.hardBits);
                        scl::bch::simulation::auditDecodedBchFrame(payload, decoded);
                        writeRow(out, "SHORT_BLOCKAGE", point, simulationCase,
                                 ebn0, snr, frame, payload, encoded, noise, 0.0,
                                 0.0, "NONE", attenuation, complete, start,
                                 length, "NONE", channel.receivedSamples,
                                 std::vector<double>(channel.receivedSamples.size(), 0.0),
                                 channel.hardBits, decoded);
                    }
                    {
                        const bool pure = point == 0U;
                        const std::size_t length = point == 0U ? 6U :
                                                   (point == 1U ? 16U : 32U);
                        const std::size_t start = point == 0U ? 14U :
                            (point == 1U ? 15U : simulationCase.encodedLength - length);
                        std::vector<double> noise(simulationCase.encodedLength, 0.0);
                        std::vector<double> received = symbols;
                        scl::common::BitVector hard = encoded;
                        if (!pure) {
                            noise = scl::common::generateStandardGaussianFrame(
                                seed, group, frame, simulationCase.encodedLength, 2U);
                            received = scl::common::applyAwgn(
                                symbols, noise, std::sqrt(realVariance));
                            hard = scl::common::hardDecision(received);
                        }
                        hard = scl::bch::simulation::applyPostHardDecisionBurst(
                            hard, start, length);
                        auto decoded = scl::bch::simulation::decodeBchFrame(
                            simulationCase, hard);
                        scl::bch::simulation::auditDecodedBchFrame(payload, decoded);
                        writeRow(out, "BURST", point, simulationCase, ebn0,
                                 snr, frame, payload, encoded, noise, 0.0, 0.0,
                                 "NONE", 0.0, false, start, length,
                                 pure ? "PURE" : "AWGN", received,
                                 std::vector<double>(received.size(), 0.0),
                                 hard, decoded);
                    }
                }
            }
        }
        std::cout << "PASS_BCH_S2_BATCH2_MATLAB_VECTOR_EXPORT rows=4500\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_BCH_S2_BATCH2_MATLAB_VECTOR_EXPORT: "
                  << error.what() << '\n';
        return 1;
    }
}
