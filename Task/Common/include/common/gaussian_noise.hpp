#ifndef SCL_COMMON_GAUSSIAN_NOISE_HPP
#define SCL_COMMON_GAUSSIAN_NOISE_HPP

#include "common/random_policy.hpp"
#include "common/types.hpp"

#include <cstdint>
#include <vector>

namespace scl::common {

double openUnitIntervalFromWord(std::uint64_t word);
double standardGaussianSample(const NoiseKey& key);
RealVector generateStandardGaussianFrame(std::uint64_t masterNoiseSeed,
                                         std::uint64_t noiseGroupId,
                                         FrameIndex frameIndex,
                                         std::uint64_t symbolsPerFrame,
                                         std::uint64_t noisePolicyVersion = kNoisePolicyVersion);

}  // namespace scl::common

#endif  // SCL_COMMON_GAUSSIAN_NOISE_HPP
