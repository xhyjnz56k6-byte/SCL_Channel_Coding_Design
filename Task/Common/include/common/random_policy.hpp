#ifndef SCL_COMMON_RANDOM_POLICY_HPP
#define SCL_COMMON_RANDOM_POLICY_HPP

#include "common/types.hpp"

#include <cstdint>
#include <vector>

namespace scl::common {

constexpr std::uint64_t kNoisePolicyVersion = 1ULL;
constexpr std::uint64_t kNoiseDomainSeparator = 0x4E4F4953455F3034ULL;
constexpr std::uint64_t kDefaultNoiseGroupId = 0ULL;

struct NoiseKey {
    std::uint64_t masterNoiseSeed = 0;
    std::uint64_t noiseGroupId = kDefaultNoiseGroupId;
    FrameIndex frameIndex = 0;
    std::uint64_t symbolIndex = 0;
    std::uint64_t noisePolicyVersion = kNoisePolicyVersion;
};

void validateNoiseKey(const NoiseKey& key);
std::uint64_t noiseUniformWord(const NoiseKey& key);
std::vector<std::uint64_t> generateNoiseWords(std::uint64_t masterNoiseSeed,
                                              std::uint64_t noiseGroupId,
                                              FrameIndex frameStart,
                                              std::uint64_t frameCount,
                                              std::uint64_t symbolsPerFrame,
                                              std::uint64_t noisePolicyVersion = kNoisePolicyVersion);

}  // namespace scl::common

#endif  // SCL_COMMON_RANDOM_POLICY_HPP
