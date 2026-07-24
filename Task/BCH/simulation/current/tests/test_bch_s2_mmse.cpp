#include "bch_simulation/fixed_multipath_mmse.hpp"

#include "common/modulation.hpp"

#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void checkPattern(const scl::common::BitVector& bits) {
    const auto symbols = scl::common::bpskModulate(bits);
    auto config = scl::bch::simulation::frozenFixedMultipathConfig();
    scl::bch::simulation::FixedMultipathMmseEqualizer equalizer(bits.size(), config, 0.0);
    const std::vector<double> zeroNoise(equalizer.observationCount(), 0.0);
    const auto result = equalizer.apply(symbols, zeroNoise);
    require(result.hardBits == bits, "noiseless multipath recovery mismatch");
    require(result.equalizedSymbols.size() == bits.size(), "equalized length mismatch");
    require(result.fullConvolutionOutput.size() == bits.size() + 3U, "full convolution tail missing");
    require(std::isfinite(result.equalizationTimeUs), "non-finite equalization time");
}

}  // namespace

int main() {
    try {
        const auto frozen = scl::bch::simulation::frozenFixedMultipathConfig();
        require(std::abs(scl::bch::simulation::channelEnergy(frozen.rawTaps) - 1.545) < 1e-14,
                "raw channel energy mismatch");
        require(std::abs(scl::bch::simulation::channelEnergy(frozen.normalizedTaps) - 1.0) < 1e-14,
                "normalized channel energy mismatch");
        for (std::size_t length : {248U, 285U, 390U, 420U, 426U}) {
            scl::common::BitVector zeros(length, 0U);
            scl::common::BitVector ones(length, 1U);
            scl::common::BitVector alternating(length, 0U);
            for (std::size_t i = 0; i < length; ++i) alternating[i] = static_cast<std::uint8_t>(i & 1U);
            checkPattern(zeros);
            checkPattern(ones);
            checkPattern(alternating);
        }
        auto identity = frozen;
        identity.rawTaps = {1.0};
        identity.delays = {0U};
        identity.normalizedTaps = {1.0};
        scl::common::BitVector bits{0U, 1U, 0U, 1U, 1U, 0U};
        const auto symbols = scl::common::bpskModulate(bits);
        scl::bch::simulation::FixedMultipathMmseEqualizer eq(bits.size(), identity, 0.25);
        std::vector<double> noise(eq.observationCount(), 0.0);
        const auto result = eq.apply(symbols, noise);
        require(result.hardBits == bits, "identity MMSE hard decisions differ from AWGN");

        bool rejected = false;
        try {
            noise[0] = std::numeric_limits<double>::quiet_NaN();
            static_cast<void>(eq.apply(symbols, noise));
        } catch (const std::invalid_argument&) {
            rejected = true;
        }
        require(rejected, "NaN input was not rejected");
        std::cout << "PASS_BCH_S2_02_MULTI_CHANNEL_FOUNDATION\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_BCH_S2_02_MMSE_TEST: " << error.what() << '\n';
        return 1;
    }
}
