#include "bch_simulation/bch_impairment_channels.hpp"

#include "common/modulation.hpp"

#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void testCfo() {
    using namespace scl::bch::simulation;
    const scl::common::BitVector bits{0U, 0U, 0U, 0U};
    const auto symbols = scl::common::bpskModulate(bits);
    const scl::common::RealVector noise(symbols.size() * 2U, 0.0);
    auto zero = applyResidualCfo(symbols, noise, {});
    require(zero.hardBits == bits, "zero CFO differs from noiseless AWGN");
    ResidualCfoConfig quarter;
    quarter.frameRotationDeg = 90.0;
    auto rotated = applyResidualCfo(symbols, noise, quarter);
    require(std::abs(rotated.receivedSamples.back().real()) < 1e-14,
            "90-degree known vector real part mismatch");
    require(std::abs(rotated.receivedSamples.back().imag() - 1.0) < 1e-14,
            "positive CFO direction mismatch");
    quarter.frameRotationDeg = -90.0;
    rotated = applyResidualCfo(symbols, noise, quarter);
    require(std::abs(rotated.receivedSamples.back().imag() + 1.0) < 1e-14,
            "negative CFO direction mismatch");
    for (std::size_t length : {248U, 285U, 390U, 420U, 426U}) {
        const scl::common::RealVector values(length, 1.0);
        const scl::common::RealVector z(length * 2U, 0.0);
        ResidualCfoConfig config;
        config.initialPhaseDeg = 45.0;
        config.frameRotationDeg = 180.0;
        config.compensationMode = CfoCompensationMode::Perfect;
        const auto output = applyResidualCfo(values, z, config);
        require(std::abs(output.deltaPhiRad * static_cast<double>(length - 1U) -
                         degreesToRadians(180.0)) < 1e-14,
                "frame-length normalization mismatch");
        require(output.hardBits == scl::common::BitVector(length, 0U),
                "perfect compensation mismatch");
    }
    bool rejected = false;
    try {
        ResidualCfoConfig bad;
        bad.frameRotationDeg = std::numeric_limits<double>::quiet_NaN();
        static_cast<void>(applyResidualCfo(symbols, noise, bad));
    } catch (const std::invalid_argument&) {
        rejected = true;
    }
    require(rejected, "CFO NaN was not rejected");
}

void testBlockage() {
    using namespace scl::bch::simulation;
    const scl::common::RealVector symbols{1.0, -1.0, 1.0, -1.0};
    const scl::common::RealVector noise(symbols.size(), 0.0);
    BlockageConfig config;
    config.length = 2U;
    config.start = 1U;
    const auto unchanged = applyShortBlockage(symbols, noise, config);
    require(unchanged.receivedSamples == symbols, "0 dB blockage changed symbols");
    config.attenuationDb = -20.0;
    const auto attenuated = applyShortBlockage(symbols, noise, config);
    require(std::abs(attenuated.blockAmplitude - 0.1) < 1e-15,
            "-20 dB did not produce amplitude 0.1");
    config.completeBlockage = true;
    const auto complete = applyShortBlockage(symbols, noise, config);
    require(complete.receivedSamples[1] == 0.0 &&
            complete.receivedSamples[2] == 0.0,
            "complete blockage did not zero selected samples");
    config.start = symbols.size() - 1U;
    config.length = 1U;
    static_cast<void>(applyShortBlockage(symbols, noise, config));
    bool rejected = false;
    try {
        config.start = symbols.size();
        static_cast<void>(applyShortBlockage(symbols, noise, config));
    } catch (const std::invalid_argument&) {
        rejected = true;
    }
    require(rejected, "invalid blockage start was not rejected");
}

void testBurstAndStarts() {
    using namespace scl::bch::simulation;
    const scl::common::BitVector bits{0U, 1U, 0U, 1U};
    require(applyPostHardDecisionBurst(bits, 0U, 1U)[0] == 1U,
            "length-one burst mismatch");
    const auto full = applyPostHardDecisionBurst(bits, 0U, bits.size());
    require(full == scl::common::BitVector({1U, 0U, 1U, 0U}),
            "full-frame burst mismatch");
    require(applyPostHardDecisionBurst(bits, 3U, 1U)[3] == 0U,
            "end-boundary burst mismatch");
    bool rejected = false;
    try {
        static_cast<void>(applyPostHardDecisionBurst(bits, 0U, 0U));
    } catch (const std::invalid_argument&) {
        rejected = true;
    }
    require(rejected, "zero-length burst was not rejected");
    const auto randomA = chooseStartIndex(
        StartPolicy::UniformRandom, 285U, 16U, 15U, 123U, 9U, "BLOCKAGE_START");
    const auto randomB = chooseStartIndex(
        StartPolicy::UniformRandom, 285U, 16U, 15U, 123U, 9U, "BLOCKAGE_START");
    require(randomA == randomB, "random start is not deterministic");
    require(deterministicDomainValue(123U, 9U, "BLOCKAGE_START") !=
            deterministicDomainValue(123U, 9U, "BURST_START"),
            "domain separators collided");
    require(chooseStartIndex(StartPolicy::OneBeforeSegmentBoundary,
                             285U, 8U, 15U, 1U, 1U, "X") == 14U,
            "one-before-boundary start mismatch");
    require(chooseStartIndex(StartPolicy::OnSegmentBoundary,
                             285U, 8U, 15U, 1U, 1U, "X") == 15U,
            "on-boundary start mismatch");
}

}  // namespace

int main() {
    try {
        testCfo();
        testBlockage();
        testBurstAndStarts();
        std::cout << "PASS_BCH_S2_IMPAIRMENT_CHANNELS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_BCH_S2_IMPAIRMENT_CHANNELS: " << error.what() << '\n';
        return 1;
    }
}
