#include "bch_simulation/bch_awgn_simulation.hpp"

#include "common/awgn_channel.hpp"
#include "common/gaussian_noise.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {
void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
}

int main() {
    try {
        using namespace scl::bch::simulation;
        for (BchCaseId id : {BchCaseId::S200, BchCaseId::B200, BchCaseId::S300, BchCaseId::B300}) {
            const auto& value = bchSimulationCase(id);
            for (double snr : {0.0, 3.5, 8.0}) {
                scl::common::CodeLengths lengths;
                lengths.payloadLength = value.payloadLength;
                lengths.codecInputLength = value.payloadLength + value.fillerLength + value.shorteningLength;
                lengths.encodedLength = value.encodedLength;
                lengths.transmittedLength = value.encodedLength;
                const double computed = scl::common::computeAwgnSigma(lengths, snr);
                const double reference = independentSigmaReference(value, snr);
                require(std::abs(computed - reference) <= 1e-15 * std::max(1.0, reference), "sigma scaling mismatch");
            }
        }
        const std::uint64_t seed = 2026072201U;
        for (std::size_t snrIndex = 0; snrIndex < 5U; ++snrIndex) {
            const auto zS200 = scl::common::generateStandardGaussianFrame(seed, pairedNoiseGroupId(200U, snrIndex), 7U, 285U, kBchNoisePolicyVersion);
            const auto zB200 = scl::common::generateStandardGaussianFrame(seed, pairedNoiseGroupId(200U, snrIndex), 7U, 248U, kBchNoisePolicyVersion);
            require(std::equal(zB200.begin(), zB200.end(), zS200.begin()), "paired 200-bit mother noise mismatch");
            const auto zS300 = scl::common::generateStandardGaussianFrame(seed, pairedNoiseGroupId(300U, snrIndex), 7U, 420U, kBchNoisePolicyVersion);
            const auto zB300 = scl::common::generateStandardGaussianFrame(seed, pairedNoiseGroupId(300U, snrIndex), 7U, 390U, kBchNoisePolicyVersion);
            require(std::equal(zB300.begin(), zB300.end(), zS300.begin()), "paired 300-bit mother noise mismatch");
            require(standardNoiseHash(zS200) == standardNoiseHash(scl::common::generateStandardGaussianFrame(seed, pairedNoiseGroupId(200U, snrIndex), 7U, 285U, kBchNoisePolicyVersion)), "noise reproducibility mismatch");
            require(standardNoiseHash(zS200) != standardNoiseHash(scl::common::generateStandardGaussianFrame(seed, pairedNoiseGroupId(200U, snrIndex), 8U, 285U, kBchNoisePolicyVersion)), "noise reused across frames");
        }
        std::cout << "PASS_BCH12_AWGN_UNIT\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_BCH12_SIGMA_RATE_SCALING_ERROR: " << error.what() << '\n';
        return 1;
    }
}
