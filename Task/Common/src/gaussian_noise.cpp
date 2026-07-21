#include "common/gaussian_noise.hpp"

#include <cmath>
#include <stdexcept>

namespace scl::common {

namespace {
constexpr double kTwoPi = 6.283185307179586476925286766559;
}

double openUnitIntervalFromWord(std::uint64_t word) {
    const double numerator = static_cast<double>((word >> 11U) + 1ULL);
    const double denominator = 9007199254740994.0;
    return numerator / denominator;
}

double standardGaussianSample(const NoiseKey& key) {
    validateNoiseKey(key);
    const NoiseKey first{key.masterNoiseSeed, key.noiseGroupId, key.frameIndex, key.symbolIndex * 2ULL, key.noisePolicyVersion};
    const NoiseKey second{key.masterNoiseSeed, key.noiseGroupId, key.frameIndex, key.symbolIndex * 2ULL + 1ULL, key.noisePolicyVersion};
    const double u1 = openUnitIntervalFromWord(noiseUniformWord(first));
    const double u2 = openUnitIntervalFromWord(noiseUniformWord(second));
    return std::sqrt(-2.0 * std::log(u1)) * std::cos(kTwoPi * u2);
}

RealVector generateStandardGaussianFrame(std::uint64_t masterNoiseSeed,
                                         std::uint64_t noiseGroupId,
                                         FrameIndex frameIndex,
                                         std::uint64_t symbolsPerFrame,
                                         std::uint64_t noisePolicyVersion) {
    if (symbolsPerFrame == 0U || symbolsPerFrame > 1000U) {
        throw std::invalid_argument("symbolsPerFrame outside supported range");
    }
    RealVector samples(static_cast<std::size_t>(symbolsPerFrame));
    for (std::uint64_t symbolIndex = 0; symbolIndex < symbolsPerFrame; ++symbolIndex) {
        samples[static_cast<std::size_t>(symbolIndex)] =
            standardGaussianSample({masterNoiseSeed, noiseGroupId, frameIndex, symbolIndex, noisePolicyVersion});
    }
    return samples;
}

}  // namespace scl::common
