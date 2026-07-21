#include "common/random_policy.hpp"

#include "common/frame_pool.hpp"

#include <stdexcept>

namespace scl::common {

void validateNoiseKey(const NoiseKey& key) {
    if (key.noisePolicyVersion != kNoisePolicyVersion) {
        throw std::invalid_argument("unsupported noisePolicyVersion");
    }
}

std::uint64_t noiseUniformWord(const NoiseKey& key) {
    validateNoiseKey(key);
    std::uint64_t value = kNoiseDomainSeparator;
    value ^= key.masterNoiseSeed * 0xD6E8FEB86659FD93ULL;
    value ^= key.noiseGroupId * 0xA0761D6478BD642FULL;
    value ^= static_cast<std::uint64_t>(key.frameIndex) * 0xE7037ED1A0B428DBULL;
    value ^= key.symbolIndex * 0x8EBC6AF09C88C6E3ULL;
    value ^= key.noisePolicyVersion * 0x589965CC75374CC3ULL;
    return splitmix64(value);
}

std::vector<std::uint64_t> generateNoiseWords(std::uint64_t masterNoiseSeed,
                                              std::uint64_t noiseGroupId,
                                              FrameIndex frameStart,
                                              std::uint64_t frameCount,
                                              std::uint64_t symbolsPerFrame,
                                              std::uint64_t noisePolicyVersion) {
    std::vector<std::uint64_t> words;
    words.reserve(static_cast<std::size_t>(frameCount * symbolsPerFrame));
    for (std::uint64_t frameOffset = 0; frameOffset < frameCount; ++frameOffset) {
        for (std::uint64_t symbolIndex = 0; symbolIndex < symbolsPerFrame; ++symbolIndex) {
            words.push_back(noiseUniformWord({masterNoiseSeed, noiseGroupId, frameStart + frameOffset, symbolIndex, noisePolicyVersion}));
        }
    }
    return words;
}

}  // namespace scl::common
