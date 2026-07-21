#ifndef SCL_COMMON_NOISE_POOL_HPP
#define SCL_COMMON_NOISE_POOL_HPP

#include "common/gaussian_noise.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace scl::common {

constexpr const char* kNoisePoolSchemaVersion = "common04.noise_pool_manifest.v1";
constexpr const char* kNoiseShardMagic = "SCLN04";
constexpr std::uint32_t kNoiseShardHeaderVersion = 1U;
constexpr std::uint64_t kMaxNoisePoolFrames = 50000ULL;
constexpr std::uint64_t kMaxNoiseSymbolsPerFrame = 1000ULL;

struct NoisePoolShard {
    std::string fileName;
    FrameIndex firstFrameIndex = 0;
    std::uint64_t frameCount = 0;
    std::uint64_t sizeBytes = 0;
    std::string sha256;
};

struct NoisePoolManifest {
    std::string schemaVersion = kNoisePoolSchemaVersion;
    std::string noisePoolId;
    std::uint64_t masterNoiseSeed = 0;
    std::uint64_t noiseGroupId = kDefaultNoiseGroupId;
    std::uint64_t noisePolicyVersion = kNoisePolicyVersion;
    std::uint64_t totalFrames = 0;
    std::uint64_t symbolsPerFrame = 0;
    std::uint64_t framesPerShard = 0;
    std::string samplePrecision = "float64";
    std::string sampleByteOrder = "little_endian";
    std::string generationAlgorithm = "splitmix64_box_muller_v1";
    std::string overallHash;
    std::vector<NoisePoolShard> shards;
};

struct NoiseShardHeader {
    std::string magic = kNoiseShardMagic;
    std::uint32_t headerVersion = kNoiseShardHeaderVersion;
    FrameIndex firstFrameIndex = 0;
    std::uint64_t frameCount = 0;
    std::uint64_t symbolsPerFrame = 0;
    std::uint64_t masterNoiseSeed = 0;
    std::uint64_t noiseGroupId = 0;
    std::uint64_t noisePolicyVersion = kNoisePolicyVersion;
};

std::string canonicalNoisePoolHashText(const NoisePoolManifest& manifest);
std::string computeNoisePoolOverallHash(const NoisePoolManifest& manifest);
void validateNoisePoolManifest(const NoisePoolManifest& manifest);
void writeNoiseShard(const std::string& path, const NoiseShardHeader& header);
NoiseShardHeader readNoiseShardHeader(const std::string& path);
NoisePoolManifest generateNoisePool(const std::string& outputDirectory,
                                    std::uint64_t masterNoiseSeed,
                                    std::uint64_t noiseGroupId,
                                    std::uint64_t totalFrames,
                                    std::uint64_t symbolsPerFrame,
                                    std::uint64_t framesPerShard);
std::string noisePoolManifestToJson(const NoisePoolManifest& manifest);
NoisePoolManifest noisePoolManifestFromJson(const std::string& text);

class NoisePoolReader {
public:
    explicit NoisePoolReader(const std::string& manifestPath);
    std::string noisePoolId() const;
    RealVector readFramePrefix(FrameIndex frameIndex, std::uint64_t symbolCount) const;

private:
    NoisePoolManifest manifest_;
    std::string directory_;
};

}  // namespace scl::common

#endif  // SCL_COMMON_NOISE_POOL_HPP
