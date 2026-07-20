#ifndef SCL_COMMON_FRAME_POOL_HPP
#define SCL_COMMON_FRAME_POOL_HPP

#include "common/frame.hpp"
#include "common/types.hpp"

#include <cstddef>
#include <cstdint>
#include <fstream>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace scl::common {

constexpr std::uint64_t kMaxFramePoolFrames = 50000;
constexpr std::uint64_t kDefaultFramePoolShardSize = 10000;

struct FramePoolShard {
    FrameIndex startFrame = 0;
    std::uint64_t frameCount = 0;
    std::string fileName;
    std::string sha256;
};

struct FramePoolManifest {
    std::string framePoolId;
    Length payloadLength = 0;
    std::uint64_t totalFrames = 0;
    std::uint64_t shardSize = 0;
    SeedValue masterSeed = 0;
    std::string generationAlgorithm;
    std::string bitStorageFormat;
    std::string endianness;
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

inline Bit deterministicPayloadBit(SeedValue masterSeed,
                                   Length payloadLength,
                                   FrameIndex frameIndex,
                                   Length bitIndex) {
    if (payloadLength == 0) {
        throw std::invalid_argument("payloadLength must be positive");
    }
    if (bitIndex >= payloadLength) {
        throw std::out_of_range("bitIndex outside payloadLength");
    }
    std::uint64_t value = static_cast<std::uint64_t>(masterSeed);
    value ^= static_cast<std::uint64_t>(payloadLength) * 0xD1B54A32D192ED03ULL;
    value ^= static_cast<std::uint64_t>(frameIndex) * 0xABC98388FB8FAC03ULL;
    value ^= static_cast<std::uint64_t>(bitIndex) * 0x8CB92BA72F3D8DD7ULL;
    return static_cast<Bit>(splitmix64(value) & 1ULL);
}

inline BitVector generatePayloadBits(SeedValue masterSeed,
                                     Length payloadLength,
                                     FrameIndex frameIndex) {
    BitVector bits(payloadLength);
    for (Length bitIndex = 0; bitIndex < payloadLength; ++bitIndex) {
        bits[bitIndex] = deterministicPayloadBit(masterSeed, payloadLength, frameIndex, bitIndex);
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

inline FramePoolManifest loadFramePoolManifest(const std::string& manifestPath) {
    const std::string text = readTextFile(manifestPath);
    FramePoolManifest manifest;
    manifest.framePoolId = extractJsonString(text, "framePoolId");
    manifest.payloadLength = static_cast<Length>(extractJsonUInt64(text, "payloadLength"));
    manifest.totalFrames = extractJsonUInt64(text, "totalFrames");
    manifest.shardSize = extractJsonUInt64(text, "shardSize");
    manifest.masterSeed = extractJsonUInt64(text, "masterSeed");
    manifest.generationAlgorithm = extractJsonString(text, "generationAlgorithm");
    manifest.bitStorageFormat = extractJsonString(text, "bitStorageFormat");
    manifest.endianness = extractJsonString(text, "endianness");

    if (manifest.payloadLength != 200U && manifest.payloadLength != 300U) {
        throw std::invalid_argument("payloadLength must be 200 or 300");
    }
    if (manifest.totalFrames == 0U || manifest.totalFrames > kMaxFramePoolFrames) {
        throw std::invalid_argument("totalFrames outside supported range");
    }
    if (manifest.shardSize == 0U) {
        throw std::invalid_argument("shardSize must be positive");
    }
    if (manifest.bitStorageFormat != "packed_bits_lsb_first") {
        throw std::invalid_argument("unsupported bitStorageFormat");
    }
    if (manifest.endianness != "little") {
        throw std::invalid_argument("unsupported endianness");
    }

    const std::regex shardPattern("\\{[^{}]*\"startFrame\"[^{}]*\\}");
    for (std::sregex_iterator it(text.begin(), text.end(), shardPattern), end; it != end; ++it) {
        const std::string shardText = it->str();
        FramePoolShard shard;
        shard.startFrame = static_cast<FrameIndex>(extractJsonUInt64(shardText, "startFrame"));
        shard.frameCount = extractJsonUInt64(shardText, "frameCount");
        shard.fileName = extractJsonString(shardText, "fileName");
        shard.sha256 = extractJsonString(shardText, "sha256");
        manifest.shards.push_back(shard);
    }
    if (manifest.shards.empty()) {
        throw std::runtime_error("manifest must contain at least one shard");
    }
    return manifest;
}

class PackedFramePoolReader {
public:
    explicit PackedFramePoolReader(const std::string& manifestPath)
        : manifest_(loadFramePoolManifest(manifestPath)), directory_(dirnameOf(manifestPath)) {}

    std::string framePoolId() const {
        return manifest_.framePoolId;
    }

    Length payloadLength() const {
        return manifest_.payloadLength;
    }

    std::uint64_t frameCount() const {
        return manifest_.totalFrames;
    }

    PayloadFrame readFrame(FrameIndex index) const {
        if (index >= manifest_.totalFrames) {
            throw std::out_of_range("frameIndex outside frame pool");
        }
        const FramePoolShard* selected = nullptr;
        for (const FramePoolShard& shard : manifest_.shards) {
            if (index >= shard.startFrame && index < shard.startFrame + shard.frameCount) {
                selected = &shard;
                break;
            }
        }
        if (selected == nullptr) {
            throw std::runtime_error("frameIndex not covered by any shard");
        }

        const std::size_t bytesPerFrame = packedPayloadByteCount(manifest_.payloadLength);
        const std::uint64_t frameInShard = index - selected->startFrame;
        const std::uint64_t offset = frameInShard * static_cast<std::uint64_t>(bytesPerFrame);
        std::ifstream input(joinPath(directory_, selected->fileName), std::ios::binary);
        if (!input) {
            throw std::runtime_error("failed to open shard: " + selected->fileName);
        }
        input.seekg(static_cast<std::streamoff>(offset), std::ios::beg);
        std::vector<std::uint8_t> packed(bytesPerFrame);
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
};

}  // namespace scl::common

#endif  // SCL_COMMON_FRAME_POOL_HPP
