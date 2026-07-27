#ifndef SCL_BCH_SIMULATION_FIXED_MULTIPATH_MMSE_HPP
#define SCL_BCH_SIMULATION_FIXED_MULTIPATH_MMSE_HPP

#include "common/types.hpp"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace scl::bch::simulation {

enum class BchChannelType { AwgnBaselineReference, FixedMultipathMmse };

struct MmseConfig {
    std::string equalizerType = "KNOWN_CHANNEL_LINEAR_MMSE";
};

struct MultipathChannelConfig {
    std::vector<double> rawTaps{1.0, 0.65, 0.35};
    std::vector<std::size_t> delays{0U, 1U, 3U};
    std::vector<double> normalizedTaps;
    bool normalizeToUnitEnergy = true;
    bool receiverKnowsChannel = true;
    MmseConfig mmse;
};

struct ChannelKey {
    std::uint64_t globalSeed = 0U;
    std::uint64_t noiseGroup = 0U;
    std::uint64_t frameIndex = 0U;
    std::uint64_t noisePolicyVersion = 1U;
};

struct ChannelDiagnostics {
    double channelEnergy = 0.0;
    double noiseVariance = 0.0;
    std::size_t transmittedLength = 0U;
    std::size_t observationLength = 0U;
    std::string equalizerMethod;
};

struct ChannelOutput {
    std::vector<double> fullConvolutionOutput;
    std::vector<double> receivedSamples;
    std::vector<double> equalizedSymbols;
    common::BitVector preEqualizationHardBits;
    common::BitVector hardBits;
    std::vector<double> standardGaussianNoise;
    double equalizationTimeUs = 0.0;
    ChannelDiagnostics diagnostics;
};

MultipathChannelConfig frozenFixedMultipathConfig();
double channelEnergy(const std::vector<double>& taps);

class FixedMultipathMmseEqualizer {
public:
    FixedMultipathMmseEqualizer(std::size_t symbolCount,
                                const MultipathChannelConfig& channelConfig,
                                double noiseVariance);

    ChannelOutput apply(const std::vector<double>& transmittedSymbols,
                        const std::vector<double>& standardGaussianNoise) const;
    std::size_t symbolCount() const;
    std::size_t observationCount() const;
    double setupTimeUs() const;

private:
    std::size_t symbolCount_ = 0U;
    std::size_t maximumDelay_ = 0U;
    std::size_t bandwidth_ = 0U;
    MultipathChannelConfig config_;
    double noiseVariance_ = 0.0;
    double setupTimeUs_ = 0.0;
    std::vector<std::vector<double>> choleskyLowerBand_;
};

ChannelOutput applyFixedMultipathMmse(
    const std::vector<double>& transmittedSymbols,
    const MultipathChannelConfig& channelConfig,
    double noiseVariance,
    const ChannelKey& key);

}  // namespace scl::bch::simulation

#endif
