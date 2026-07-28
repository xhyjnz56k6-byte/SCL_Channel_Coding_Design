#include "stage07_multipath_validation_core.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {
void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
}

int main() {
    try {
        using namespace scl::bch::s2;
        const auto channel = stage07::frozenChannel();
        require(std::abs(stage07::energy(channel.rawImpulse) - 1.545) < 1e-15,
                "raw channel energy mismatch");
        require(std::abs(stage07::energy(channel.impulse) - 1.0) < 1e-14,
                "normalized channel energy mismatch");
        const auto impulse = stage07::convolveFull({1.0, 0.0, 0.0}, channel.impulse);
        require(impulse.size() == 6U, "linear convolution length mismatch");
        for (std::size_t i = 0; i < channel.impulse.size(); ++i) {
            require(std::abs(impulse[i] - channel.impulse[i]) < 1e-15,
                    "impulse convolution mismatch");
        }
        for (const auto& contract : stage02::allCaseContracts()) {
            scl::common::BitVector payload(contract.payloadLength, 0U);
            for (std::size_t i = 0; i < payload.size(); ++i) payload[i] = i % 2U;
            stage07::FrameCounts counts;
            stage07::addFrame(counts, contract.id, payload, 100.0, 7070707U, 0U, 0U, true);
            require(counts.payloadErrorBits == 0U && counts.decoderFailureFrames == 0U,
                    "noiseless case mismatch");
            require(counts.solverResidualMax < 1e-11, "solver residual exceeds tolerance");
        }
        bool rejected = false;
        try { stage07::LinearMmse invalid(0U, channel.impulse, 1.0); }
        catch (const std::invalid_argument&) { rejected = true; }
        require(rejected, "invalid MMSE dimensions accepted");
        stage01::RandomIdentity first{7070707U,
            "stage07_multipath_validation:" + channel.id + ":P0",
            "K200_S15", 0U, 10U};
        auto second = first;
        second.frameIndex = 11U;
        const auto noiseA = stage01::standardGaussianFrame(
            first, stage01::RandomDomain::Awgn, 32U);
        const auto noiseB = stage01::standardGaussianFrame(
            second, stage01::RandomDomain::Awgn, 32U);
        require(noiseA != noiseB, "different frameIndex reused AWGN vector");
        require(noiseA == stage01::standardGaussianFrame(
            first, stage01::RandomDomain::Awgn, 32U),
            "same complete frame identity is not reproducible");
        std::cout << "PASS_STAGE07_MULTIPATH_VALIDATION_UNIT\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_STAGE07_MULTIPATH_VALIDATION_UNIT: " << error.what() << '\n';
        return 1;
    }
}
