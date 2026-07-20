#ifndef SCL_COMMON_FRAME_POOL_HPP
#define SCL_COMMON_FRAME_POOL_HPP

#include "common/frame.hpp"
#include "common/interfaces.hpp"
#include "common/sha256.hpp"
#include "common/types.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <fstream>
#include <regex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace scl::common {

constexpr std::uint64_t kMaxFramePoolFrames = 50000;
constexpr std::uint64_t kDefaultFramePoolShardSize = 1000;
constexpr std::uint64_t kSupportedPayloadPolicyVersion = 1;
constexpr const char* kFramePoolSchemaVersion = "common03.frame_pool_manifest.v2";
constexpr const char* kFramePoolGenerationAlgorithm = "splitmix64_payload_v2";
constexpr const char* kFramePoolBitStorageFormat = "packed_bits";
constexpr const char* kFramePoolBitOrderWithinByte = "lsb_first";
constexpr const char* kFramePoolIntegerByteOrder = "not_applicable";

struct FramePoolShard {
    FrameIndex startFrame = 0;
    std::uint64_t frameCount = 0;
    std::string fileName;
    std::uint64_t sizeBytes = 0;
    std::string sha256;
};

struct FramePoolManifest {
    std::string schemaVersion;
    std::string framePoolId;
    Length payloadLength = 0;
    std::uint64_t totalFrames = 0;
    std::uint64_t shardSize = 0;
    SeedValue masterSeed = 0;
    std::uint64_t payloadPolicyVersion = 0;
    std::string generationAlgorithm;
    std::string bitStorageFormat;
    std::string bitOrderWithinByte;
    std::string integerByteOrder;
    std::uint64_t bytesPerFrame = 0;
    std::string overallHash;
    std::vector<FramePoolShard> shards;
};

inline std::size_t packedPayloadByteCount(Length payloadLength) {
    if (payloadLength == 0) {
        throw std::invalid_argument("payloadLength must be positive");
    }
    return (payloadLength + 7U) / 8U;
}

inline std::uint64_t splitmix64(std::uint64_t value) {
    value += 0x9E3779B97F4A7C15ULL;
    value = (value ^ (value >> 30U)) * 0xBF58476D1CE4E5B9ULL;
    value = (value ^ (value >> 27U)) * 0x94D049BB133111EBULL;
    return value ^ (value >> 31U);
}

inline void validatePayloadPolicyVersion(std::uint64_t payloadPolicyVersion) {
    if (payloadPolicyVersion != kSupportedPayloadPolicyVersion) {
        throw std::invalid_argument("unsupported payloadPolicyVersion");
    }
}

inline Bit deterministicPayloadBit(SeedValue masterSeed,
                                   Length payloadLength,
                                   FrameIndex frameIndex,
                                   Length bitIndex,
                                   std::uint64_t payloadPolicyVersion = kSupportedPayloadPolicyVersion) {
    validatePayloadPolicyVersion(payloadPolicyVersion);
    if (payloadLength == 0) {
        throw std::invalid_argument("payloadLength must be positive");
    }
    if (bitIndex >= payloadLength) {
        throw std::out_of_range("bitIndex outside payloadLength");
    }
    std::uint64_t value = static_cast<std::uint64_t>(masterSeed);
    value ^= payloadPolicyVersion * 0xA24BAED4963EE407ULL;
    value ^= static_cast<std::uint64_t>(payloadLength) * 0xD1B54A32D192ED03ULL;
    value ^= static_cast<std::uint64_t>(frameIndex) * 0xABC98388FB8FAC03ULL;
    value ^= static_cast<std::uint64_t>(bitIndex) * 0x8CB92BA72F3D8DD7ULL;
    return static_cast<Bit>(splitmix64(value) & 1ULL);
}

inline BitVector generatePayloadBits(SeedValue masterSeed,
                                     Length payloadLength,
                                     FrameIndex frameIndex,
                                     std::uint64_t payloadPolicyVersion = kSupportedPayloadPolicyVersion) {
    BitVector bits(payloadLength);
    for (Length bitIndex = 0; bitIndex < payloadLength; ++bitIndex) {
        bits[bitIndex] = deterministicPayloadBit(masterSeed, payloadLength, frameIndex, bitIndex, payloadPolicyVersion);
    }
    return bits;
}

inline std::vector<std::uint8_t> packPayloadBits(const BitVector& bits) {
    validateBits(bits, "payloadBits");
    std::vector<std::uint8_t> packed(packedPayloadByteCount(bits.size()), 0U);
    for (std::size_t bitIndex = 0; bitIndex < bits.size(); ++bitIndex) {
        if (bits[bitIndex] != 0U) {
            packed[bitIndex / 8U] |= static_cast<std::uint8_t>(1U << (bitIndex % 8U));
        }
    }
    return packed;
}

inline BitVector unpackPayloadBits(const std::vector<std::uint8_t>& packed, Length payloadLength) {
    const std::size_t expectedBytes = packedPayloadByteCount(payloadLength);
    if (packed.size() != expectedBytes) {
        throw std::invalid_argument("packed payload byte count mismatch");
    }
    BitVector bits(payloadLength);
    for (Length bitIndex = 0; bitIndex < payloadLength; ++bitIndex) {
        bits[bitIndex] = static_cast<Bit>((packed[bitIndex / 8U] >> (bitIndex % 8U)) & 1U);
    }
    return bits;
}

inline std::string readTextFile(const std::string& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw std::runtime_error("failed to open text file: " + path);
    }
    std::ostringstream buffer;
    buffer << input.rdbuf();
    return buffer.str();
}

inline std::string dirnameOf(const std::string& path) {
    const std::size_t slash = path.find_last_of("/\\");
    if (slash == std::string::npos) {
        return ".";
    }
    return path.substr(0, slash);
}

inline std::string joinPath(const std::string& directory, const std::string& fileName) {
    if (directory.empty() || directory == ".") {
        return fileName;
    }
    const char last = directory[directory.size() - 1U];
    if (last == '/' || last == '\\') {
        return directory + fileName;
    }
    return directory + "/" + fileName;
}

inline bool isLowerHexSha256(const std::string& value) {
    if (value.size() != 64U) {
        return false;
    }
    return std::all_of(value.begin(), value.end(), [](char c) {
        return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
    });
}

inline std::string extractJsonString(const std::string& text, const std::string& key) {
    const std::regex pattern("\"" + key + "\"\\s*:\\s*\"([^\"]*)\"");
    std::smatch match;
    if (!std::regex_search(text, match, pattern)) {
        throw std::runtime_error("manifest missing string field: " + key);
    }
    return match[1].str();
}

inline std::uint64_t extractJsonUInt64(const std::string& text, const std::string& key) {
    const std::regex pattern("\"" + key + "\"\\s*:\\s*([0-9]+)");
    std::smatch match;
    if (!std::regex_search(text, match, pattern)) {
        throw std::runtime_error("manifest missing integer field: " + key);
    }
    return static_cast<std::uint64_t>(std::stoull(match[1].str()));
}

inline bool hasUnsafeShardFileName(const std::string& fileName) {
    return fileName.empty() || fileName.find("..") != std::string::npos ||
           fileName.find('/') != std::string::npos || fileName.find('\\') != std::string::npos ||
           fileName.find(':') != std::string::npos;
}

inline std::string canonicalOverallHashText(const FramePoolManifest& manifest) {
    std::ostringstream out;
    out << "schemaVersion=" << manifest.schemaVersion << '\n';
    out << "framePoolId=" << manifest.framePoolId << '\n';
    out << "payloadLength=" << manifest.payloadLength << '\n';
    out << "totalFrames=" << manifest.totalFrames << '\n';
    out << "shardSize=" << manifest.shardSize << '\n';
    out << "masterSeed=" << manifest.masterSeed << '\n';
    out << "payloadPolicyVersion=" << manifest.payloadPolicyVersion << '\n';
    out << "generationAlgorithm=" << manifest.generationAlgorithm << '\n';
    out << "bitStorageFormat=" << manifest.bitStorageFormat << '\n';
    out << "bitOrderWithinByte=" << manifest.bitOrderWithinByte << '\n';
    out << "bytesPerFrame=" << manifest.bytesPerFrame << '\n';
    for (const FramePoolShard& shard : manifest.shards) {
        out << "shard.startFrame=" << shard.startFrame << '\n';
        out << "shard.frameCount=" << shard.frameCount << '\n';
        out << "shard.fileName=" << shard.fileName << '\n';
        out << "shard.sizeBytes=" << shard.sizeBytes << '\n';
        out << "shard.sha256=" << shard.sha256 << '\n';
    }
    return out.str();
}

inline std::string computeFramePoolOverallHash(const FramePoolManifest& manifest) {
    return sha256Hex(canonicalOverallHashText(manifest));
}

inline void validateFramePoolManifest(const FramePoolManifest& manifest) {
    if (manifest.schemaVersion != kFramePoolSchemaVersion) {
        throw std::invalid_argument("unsupported schemaVersion");
    }
    if (manifest.framePoolId.empty()) {
        throw std::invalid_argument("framePoolId must not be empty");
    }
    if (manifest.payloadLength != 200U && manifest.payloadLength != 300U) {
        throw std::invalid_argument("payloadLength must be 200 or 300");
    }
    if (manifest.totalFrames == 0U || manifest.totalFrames > kMaxFramePoolFrames) {
        throw std::invalid_argument("totalFrames outside supported range");
    }
    if (manifest.shardSize == 0U) {
        throw std::invalid_argument("shardSize must be positive");
    }
    if (manifest.bytesPerFrame != packedPayloadByteCount(manifest.payloadLength)) {
        throw std::invalid_argument("bytesPerFrame mismatch");
    }
    if (manifest.generationAlgorithm != kFramePoolGenerationAlgorithm) {
        throw std::invalid_argument("unsupported generationAlgorithm");
    }
    validatePayloadPolicyVersion(manifest.payloadPolicyVersion);
    if (manifest.bitStorageFormat != kFramePoolBitStorageFormat) {
        throw std::invalid_argument("unsupported bitStorageFormat");
    }
    if (manifest.bitOrderWithinByte != kFramePoolBitOrderWithinByte) {
        throw std::invalid_argument("unsupported bitOrderWithinByte");
    }
    if (manifest.integerByteOrder != kFramePoolIntegerByteOrder) {
        throw std::invalid_argument("unsupported integerByteOrder");
    }
    if (manifest.shards.empty()) {
        throw std::invalid_argument("manifest must contain at least one shard");
    }
    if (manifest.shards.front().startFrame != 0U) {
        throw std::invalid_argument("first shard startFrame must be 0");
    }

    std::uint64_t expectedStart = 0U;
    std::set<std::string> fileNames;
    std::uint64_t total = 0U;
    for (std::size_t i = 0; i < manifest.shards.size(); ++i) {
        const FramePoolShard& shard = manifest.shards[i];
        if (shard.frameCount == 0U) {
            throw std::invalid_argument("shard frameCount must be positive");
        }
        if (shard.startFrame != expectedStart) {
            throw std::invalid_argument("shards must be contiguous without gaps or overlap");
        }
        if (hasUnsafeShardFileName(shard.fileName)) {
            throw std::invalid_argument("unsafe shard fileName");
        }
        if (!fileNames.insert(shard.fileName).second) {
            throw std::invalid_argument("duplicate shard fileName");
        }
        if (!isLowerHexSha256(shard.sha256)) {
            throw std::invalid_argument("shard sha256 must be 64 lowercase hex characters");
        }
        if (i + 1U < manifest.shards.size() && shard.frameCount != manifest.shardSize) {
            throw std::invalid_argument("non-final shard frameCount must equal shardSize");
        }
        if (i + 1U == manifest.shards.size() && shard.frameCount > manifest.shardSize) {
            throw std::invalid_argument("final shard frameCount must not exceed shardSize");
        }
        const std::uint64_t expectedSize = shard.frameCount * manifest.bytesPerFrame;
        if (shard.sizeBytes != expectedSize) {
            throw std::invalid_argument("shard sizeBytes mismatch");
        }
        total += shard.frameCount;
        expectedStart += shard.frameCount;
    }
    if (total != manifest.totalFrames || expectedStart != manifest.totalFrames) {
        throw std::invalid_argument("shard frame counts must sum to totalFrames");
    }
    if (!isLowerHexSha256(manifest.overallHash)) {
        throw std::invalid_argument("overallHash must be 64 lowercase hex characters");
    }
    if (computeFramePoolOverallHash(manifest) != manifest.overallHash) {
        throw std::invalid_argument("overallHash mismatch");
    }
}

inline FramePoolManifest loadFramePoolManifest(const std::string& manifestPath) {
    const std::string text = readTextFile(manifestPath);
    FramePoolManifest manifest;
    manifest.schemaVersion = extractJsonString(text, "schemaVersion");
    manifest.framePoolId = extractJsonString(text, "framePoolId");
    manifest.payloadLength = static_cast<Length>(extractJsonUInt64(text, "payloadLength"));
    manifest.totalFrames = extractJsonUInt64(text, "totalFrames");
    manifest.shardSize = extractJsonUInt64(text, "shardSize");
    manifest.masterSeed = extractJsonUInt64(text, "masterSeed");
    manifest.payloadPolicyVersion = extractJsonUInt64(text, "payloadPolicyVersion");
    manifest.generationAlgorithm = extractJsonString(text, "generationAlgorithm");
    manifest.bitStorageFormat = extractJsonString(text, "bitStorageFormat");
    manifest.bitOrderWithinByte = extractJsonString(text, "bitOrderWithinByte");
    manifest.integerByteOrder = extractJsonString(text, "integerByteOrder");
    manifest.bytesPerFrame = extractJsonUInt64(text, "bytesPerFrame");
    manifest.overallHash = extractJsonString(text, "overallHash");

    const std::regex shardPattern("\\{[^{}]*\"startFrame\"[^{}]*\\}");
    for (std::sregex_iterator it(text.begin(), text.end(), shardPattern), end; it != end; ++it) {
        const std::string shardText = it->str();
        FramePoolShard shard;
        shard.startFrame = static_cast<FrameIndex>(extractJsonUInt64(shardText, "startFrame"));
        shard.frameCount = extractJsonUInt64(shardText, "frameCount");
        shard.fileName = extractJsonString(shardText, "fileName");
        shard.sizeBytes = extractJsonUInt64(shardText, "sizeBytes");
        shard.sha256 = extractJsonString(shardText, "sha256");
        manifest.shards.push_back(shard);
    }
    validateFramePoolManifest(manifest);
    return manifest;
}

class PackedFramePoolReader final : public IFramePoolReader {
public:
    explicit PackedFramePoolReader(const std::string& manifestPath, bool verifyShardHashes = true)
        : manifest_(loadFramePoolManifest(manifestPath)),
          directory_(dirnameOf(manifestPath)),
          verifyShardHashes_(verifyShardHashes),
          verifiedShards_(manifest_.shards.size(), 0U) {
        if (verifyShardHashes_) {
            verifyAllShards();
        }
    }

    std::string framePoolId() const override {
        return manifest_.framePoolId;
    }

    Length payloadLength() const override {
        return manifest_.payloadLength;
    }

    std::uint64_t frameCount() const override {
        return manifest_.totalFrames;
    }

    bool verifyShard(std::size_t shardIndex) const {
        if (shardIndex >= manifest_.shards.size()) {
            throw std::out_of_range("shardIndex outside manifest");
        }
        if (verifiedShards_[shardIndex] != 0U) {
            return true;
        }
        const FramePoolShard& shard = manifest_.shards[shardIndex];
        const std::string path = joinPath(directory_, shard.fileName);
        std::ifstream input(path, std::ios::binary | std::ios::ate);
        if (!input) {
            throw std::runtime_error("failed to open shard: " + shard.fileName);
        }
        const std::uint64_t size = static_cast<std::uint64_t>(input.tellg());
        if (size != shard.sizeBytes) {
            throw std::runtime_error("shard sizeBytes mismatch: " + shard.fileName);
        }
        const std::string actual = sha256FileHex(path);
        if (actual != shard.sha256) {
            throw std::runtime_error("shard SHA256 mismatch: " + shard.fileName);
        }
        verifiedShards_[shardIndex] = 1U;
        return true;
    }

    void verifyAllShards() const {
        for (std::size_t i = 0; i < manifest_.shards.size(); ++i) {
            verifyShard(i);
        }
    }

    PayloadFrame readFrame(FrameIndex index) const override {
        if (index >= manifest_.totalFrames) {
            throw std::out_of_range("frameIndex outside frame pool");
        }
        std::size_t shardIndex = manifest_.shards.size();
        for (std::size_t i = 0; i < manifest_.shards.size(); ++i) {
            const FramePoolShard& shard = manifest_.shards[i];
            if (index >= shard.startFrame && index < shard.startFrame + shard.frameCount) {
                shardIndex = i;
                break;
            }
        }
        if (shardIndex == manifest_.shards.size()) {
            throw std::runtime_error("frameIndex not covered by any shard");
        }
        if (verifyShardHashes_) {
            verifyShard(shardIndex);
        }
        const FramePoolShard& selected = manifest_.shards[shardIndex];
        const std::uint64_t frameInShard = index - selected.startFrame;
        const std::uint64_t offset = frameInShard * manifest_.bytesPerFrame;
        std::ifstream input(joinPath(directory_, selected.fileName), std::ios::binary);
        if (!input) {
            throw std::runtime_error("failed to open shard: " + selected.fileName);
        }
        input.seekg(static_cast<std::streamoff>(offset), std::ios::beg);
        std::vector<std::uint8_t> packed(static_cast<std::size_t>(manifest_.bytesPerFrame));
        input.read(reinterpret_cast<char*>(packed.data()), static_cast<std::streamsize>(packed.size()));
        if (input.gcount() != static_cast<std::streamsize>(packed.size())) {
            throw std::runtime_error("short read from shard");
        }

        PayloadFrame frame;
        frame.framePoolId = manifest_.framePoolId;
        frame.frameIndex = index;
        frame.payloadLength = manifest_.payloadLength;
        frame.masterSeed = manifest_.masterSeed;
        frame.payloadBits = unpackPayloadBits(packed, manifest_.payloadLength);
        validatePayloadFrame(frame);
        return frame;
    }

    std::vector<PayloadFrame> readFrames(FrameIndex startIndex, std::uint64_t count) const {
        if (count > 0U && (startIndex >= manifest_.totalFrames || count > manifest_.totalFrames - startIndex)) {
            throw std::out_of_range("readFrames range outside frame pool");
        }
        std::vector<PayloadFrame> frames;
        frames.reserve(static_cast<std::size_t>(count));
        for (std::uint64_t offset = 0; offset < count; ++offset) {
            frames.push_back(readFrame(startIndex + offset));
        }
        return frames;
    }

private:
    FramePoolManifest manifest_;
    std::string directory_;
    bool verifyShardHashes_ = true;
    mutable std::vector<std::uint8_t> verifiedShards_;
};

}  // namespace scl::common

#endif  // SCL_COMMON_FRAME_POOL_HPP
