#include "common/noise_pool.hpp"

#include "common/frame_pool.hpp"
#include "common/sha256.hpp"

#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <set>
#include <sstream>
#include <stdexcept>

namespace scl::common {

namespace fs = std::filesystem;

namespace {
void writeU32(std::ostream& out, std::uint32_t value) {
    for (unsigned i = 0; i < 4U; ++i) {
        out.put(static_cast<char>((value >> (i * 8U)) & 0xFFU));
    }
}

void writeU64(std::ostream& out, std::uint64_t value) {
    for (unsigned i = 0; i < 8U; ++i) {
        out.put(static_cast<char>((value >> (i * 8U)) & 0xFFU));
    }
}

std::uint32_t readU32(std::istream& in) {
    std::uint32_t value = 0;
    for (unsigned i = 0; i < 4U; ++i) {
        const int byte = in.get();
        if (byte == EOF) {
            throw std::runtime_error("short noise shard header");
        }
        value |= static_cast<std::uint32_t>(static_cast<unsigned char>(byte)) << (i * 8U);
    }
    return value;
}

std::uint64_t readU64(std::istream& in) {
    std::uint64_t value = 0;
    for (unsigned i = 0; i < 8U; ++i) {
        const int byte = in.get();
        if (byte == EOF) {
            throw std::runtime_error("short noise shard header");
        }
        value |= static_cast<std::uint64_t>(static_cast<unsigned char>(byte)) << (i * 8U);
    }
    return value;
}

void writeDoubleLE(std::ostream& out, double value) {
    static_assert(sizeof(double) == 8U, "Common-04 requires 64-bit double");
    std::uint64_t bits = 0;
    std::memcpy(&bits, &value, sizeof(bits));
    writeU64(out, bits);
}

double readDoubleLE(std::istream& in) {
    const std::uint64_t bits = readU64(in);
    double value = 0.0;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

std::string shardName(FrameIndex firstFrame, std::uint64_t frameCount) {
    std::ostringstream out;
    out << "noise_" << std::setw(6) << std::setfill('0') << firstFrame << "_" << std::setw(6) << std::setfill('0')
        << (firstFrame + frameCount - 1U) << ".bin";
    return out.str();
}
}

std::string canonicalNoisePoolHashText(const NoisePoolManifest& manifest) {
    std::ostringstream out;
    out << "schemaVersion=" << manifest.schemaVersion << '\n';
    out << "masterNoiseSeed=" << manifest.masterNoiseSeed << '\n';
    out << "noiseGroupId=" << manifest.noiseGroupId << '\n';
    out << "noisePolicyVersion=" << manifest.noisePolicyVersion << '\n';
    out << "totalFrames=" << manifest.totalFrames << '\n';
    out << "symbolsPerFrame=" << manifest.symbolsPerFrame << '\n';
    out << "framesPerShard=" << manifest.framesPerShard << '\n';
    out << "samplePrecision=" << manifest.samplePrecision << '\n';
    out << "sampleByteOrder=" << manifest.sampleByteOrder << '\n';
    out << "generationAlgorithm=" << manifest.generationAlgorithm << '\n';
    for (const auto& shard : manifest.shards) {
        out << "shard.fileName=" << shard.fileName << '\n';
        out << "shard.firstFrameIndex=" << shard.firstFrameIndex << '\n';
        out << "shard.frameCount=" << shard.frameCount << '\n';
        out << "shard.sizeBytes=" << shard.sizeBytes << '\n';
        out << "shard.sha256=" << shard.sha256 << '\n';
    }
    return out.str();
}

std::string computeNoisePoolOverallHash(const NoisePoolManifest& manifest) {
    return sha256Hex(canonicalNoisePoolHashText(manifest));
}

void validateNoisePoolManifest(const NoisePoolManifest& manifest) {
    if (manifest.schemaVersion != kNoisePoolSchemaVersion) {
        throw std::invalid_argument("unsupported noise pool schemaVersion");
    }
    if (manifest.noisePolicyVersion != kNoisePolicyVersion) {
        throw std::invalid_argument("unsupported noisePolicyVersion");
    }
    if (manifest.noisePoolId.empty()) {
        throw std::invalid_argument("noisePoolId must not be empty");
    }
    if (manifest.samplePrecision != "float64" || manifest.sampleByteOrder != "little_endian" ||
        manifest.generationAlgorithm != "splitmix64_box_muller_v1") {
        throw std::invalid_argument("unsupported noise pool sample format or algorithm");
    }
    if (manifest.totalFrames == 0U || manifest.totalFrames > kMaxNoisePoolFrames) {
        throw std::invalid_argument("noise pool frame count outside supported range");
    }
    if (manifest.symbolsPerFrame == 0U || manifest.symbolsPerFrame > kMaxNoiseSymbolsPerFrame) {
        throw std::invalid_argument("symbolsPerFrame outside supported range");
    }
    if (manifest.framesPerShard == 0U) {
        throw std::invalid_argument("framesPerShard must be positive");
    }
    if (manifest.shards.empty()) {
        throw std::invalid_argument("noise pool requires shards");
    }
    FrameIndex expected = 0;
    std::set<std::string> fileNames;
    for (std::size_t i = 0; i < manifest.shards.size(); ++i) {
        const auto& shard = manifest.shards[i];
        if (shard.firstFrameIndex != expected) {
            throw std::invalid_argument("noise shards must be contiguous");
        }
        if (shard.frameCount == 0U || (i + 1U < manifest.shards.size() && shard.frameCount != manifest.framesPerShard) ||
            (i + 1U == manifest.shards.size() && shard.frameCount > manifest.framesPerShard)) {
            throw std::invalid_argument("noise shard frameCount mismatch");
        }
        if (hasUnsafeShardFileName(shard.fileName) || !fileNames.insert(shard.fileName).second || !isLowerHexSha256(shard.sha256)) {
            throw std::invalid_argument("invalid noise shard metadata");
        }
        if (shard.sizeBytes != kNoiseShardHeaderBytes + shard.frameCount * manifest.symbolsPerFrame * 8U) {
            throw std::invalid_argument("noise shard sizeBytes mismatch");
        }
        expected += shard.frameCount;
    }
    if (!isLowerHexSha256(manifest.overallHash) || expected != manifest.totalFrames ||
        computeNoisePoolOverallHash(manifest) != manifest.overallHash || manifest.noisePoolId != manifest.overallHash.substr(0, 16)) {
        throw std::invalid_argument("noise pool overallHash mismatch");
    }
}

void writeNoiseShard(const std::string& path, const NoiseShardHeader& header) {
    if (header.frameCount == 0U || header.symbolsPerFrame == 0U || header.symbolsPerFrame > kMaxNoiseSymbolsPerFrame) {
        throw std::invalid_argument("invalid noise shard header");
    }
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!out) {
        throw std::runtime_error("failed to open noise shard for writing");
    }
    out.write(kNoiseShardMagic, 6);
    writeU32(out, header.headerVersion);
    writeU64(out, header.firstFrameIndex);
    writeU64(out, header.frameCount);
    writeU64(out, header.symbolsPerFrame);
    writeU64(out, header.masterNoiseSeed);
    writeU64(out, header.noiseGroupId);
    writeU64(out, header.noisePolicyVersion);
    for (std::uint64_t frame = 0; frame < header.frameCount; ++frame) {
        const RealVector samples = generateStandardGaussianFrame(header.masterNoiseSeed, header.noiseGroupId,
                                                                 header.firstFrameIndex + frame, header.symbolsPerFrame,
                                                                 header.noisePolicyVersion);
        for (double sample : samples) {
            writeDoubleLE(out, sample);
        }
    }
}

NoiseShardHeader readNoiseShardHeader(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        throw std::runtime_error("failed to open noise shard");
    }
    char magic[6] = {};
    in.read(magic, 6);
    if (in.gcount() != 6 || std::string(magic, 6) != kNoiseShardMagic) {
        throw std::runtime_error("bad noise shard magic");
    }
    NoiseShardHeader header;
    header.headerVersion = readU32(in);
    header.firstFrameIndex = readU64(in);
    header.frameCount = readU64(in);
    header.symbolsPerFrame = readU64(in);
    header.masterNoiseSeed = readU64(in);
    header.noiseGroupId = readU64(in);
    header.noisePolicyVersion = readU64(in);
    if (header.headerVersion != kNoiseShardHeaderVersion) {
        throw std::runtime_error("unsupported noise shard header version");
    }
    return header;
}

NoisePoolManifest generateNoisePool(const std::string& outputDirectory,
                                    std::uint64_t masterNoiseSeed,
                                    std::uint64_t noiseGroupId,
                                    std::uint64_t totalFrames,
                                    std::uint64_t symbolsPerFrame,
                                    std::uint64_t framesPerShard) {
    NoisePoolManifest manifest;
    manifest.masterNoiseSeed = masterNoiseSeed;
    manifest.noiseGroupId = noiseGroupId;
    manifest.totalFrames = totalFrames;
    manifest.symbolsPerFrame = symbolsPerFrame;
    manifest.framesPerShard = framesPerShard;
    fs::create_directories(outputDirectory);
    for (FrameIndex first = 0; first < totalFrames; first += framesPerShard) {
        const std::uint64_t count = std::min<std::uint64_t>(framesPerShard, totalFrames - first);
        const std::string name = shardName(first, count);
        const fs::path path = fs::path(outputDirectory) / name;
        writeNoiseShard(path.string(), {kNoiseShardMagic, kNoiseShardHeaderVersion, first, count, symbolsPerFrame,
                                        masterNoiseSeed, noiseGroupId, kNoisePolicyVersion});
        NoisePoolShard shard;
        shard.fileName = name;
        shard.firstFrameIndex = first;
        shard.frameCount = count;
        shard.sizeBytes = static_cast<std::uint64_t>(fs::file_size(path));
        shard.sha256 = sha256FileHex(path.string());
        manifest.shards.push_back(shard);
    }
    manifest.overallHash = computeNoisePoolOverallHash(manifest);
    manifest.noisePoolId = manifest.overallHash.substr(0, 16);
    validateNoisePoolManifest(manifest);
    return manifest;
}

std::string noisePoolManifestToJson(const NoisePoolManifest& manifest) {
    std::ostringstream out;
    out << "{\n";
    out << "\"schemaVersion\":\"" << manifest.schemaVersion << "\",\n";
    out << "\"noisePoolId\":\"" << manifest.noisePoolId << "\",\n";
    out << "\"masterNoiseSeed\":" << manifest.masterNoiseSeed << ",\n";
    out << "\"noiseGroupId\":" << manifest.noiseGroupId << ",\n";
    out << "\"noisePolicyVersion\":" << manifest.noisePolicyVersion << ",\n";
    out << "\"totalFrames\":" << manifest.totalFrames << ",\n";
    out << "\"symbolsPerFrame\":" << manifest.symbolsPerFrame << ",\n";
    out << "\"framesPerShard\":" << manifest.framesPerShard << ",\n";
    out << "\"samplePrecision\":\"" << manifest.samplePrecision << "\",\n";
    out << "\"sampleByteOrder\":\"" << manifest.sampleByteOrder << "\",\n";
    out << "\"generationAlgorithm\":\"" << manifest.generationAlgorithm << "\",\n";
    out << "\"shards\":[\n";
    for (std::size_t i = 0; i < manifest.shards.size(); ++i) {
        const auto& shard = manifest.shards[i];
        out << "{\"fileName\":\"" << shard.fileName << "\",\"firstFrameIndex\":" << shard.firstFrameIndex
            << ",\"frameCount\":" << shard.frameCount << ",\"sizeBytes\":" << shard.sizeBytes
            << ",\"sha256\":\"" << shard.sha256 << "\"}";
        out << (i + 1U == manifest.shards.size() ? "\n" : ",\n");
    }
    out << "],\n\"overallHash\":\"" << manifest.overallHash << "\"\n}\n";
    return out.str();
}

NoisePoolManifest noisePoolManifestFromJson(const std::string& text) {
    NoisePoolManifest manifest;
    manifest.schemaVersion = extractJsonString(text, "schemaVersion");
    manifest.noisePoolId = extractJsonString(text, "noisePoolId");
    manifest.masterNoiseSeed = extractJsonUInt64(text, "masterNoiseSeed");
    manifest.noiseGroupId = extractJsonUInt64(text, "noiseGroupId");
    manifest.noisePolicyVersion = extractJsonUInt64(text, "noisePolicyVersion");
    manifest.totalFrames = extractJsonUInt64(text, "totalFrames");
    manifest.symbolsPerFrame = extractJsonUInt64(text, "symbolsPerFrame");
    manifest.framesPerShard = extractJsonUInt64(text, "framesPerShard");
    manifest.samplePrecision = extractJsonString(text, "samplePrecision");
    manifest.sampleByteOrder = extractJsonString(text, "sampleByteOrder");
    manifest.generationAlgorithm = extractJsonString(text, "generationAlgorithm");
    manifest.overallHash = extractJsonString(text, "overallHash");
    const std::regex shardPattern("\\{[^{}]*\"fileName\"[^{}]*\\}");
    for (std::sregex_iterator it(text.begin(), text.end(), shardPattern), end; it != end; ++it) {
        const std::string shardText = it->str();
        NoisePoolShard shard;
        shard.fileName = extractJsonString(shardText, "fileName");
        shard.firstFrameIndex = extractJsonUInt64(shardText, "firstFrameIndex");
        shard.frameCount = extractJsonUInt64(shardText, "frameCount");
        shard.sizeBytes = extractJsonUInt64(shardText, "sizeBytes");
        shard.sha256 = extractJsonString(shardText, "sha256");
        manifest.shards.push_back(shard);
    }
    validateNoisePoolManifest(manifest);
    return manifest;
}

NoisePoolReader::NoisePoolReader(const std::string& manifestPath)
    : manifest_(noisePoolManifestFromJson(readTextFile(manifestPath))), directory_(dirnameOf(manifestPath)) {
    for (const auto& shard : manifest_.shards) {
        const std::string path = joinPath(directory_, shard.fileName);
        if (sha256FileHex(path) != shard.sha256) {
            throw std::runtime_error("noise shard SHA256 mismatch");
        }
        const NoiseShardHeader header = readNoiseShardHeader(path);
        if (header.firstFrameIndex != shard.firstFrameIndex || header.frameCount != shard.frameCount ||
            header.symbolsPerFrame != manifest_.symbolsPerFrame ||
            header.masterNoiseSeed != manifest_.masterNoiseSeed || header.noiseGroupId != manifest_.noiseGroupId ||
            header.noisePolicyVersion != manifest_.noisePolicyVersion) {
            throw std::runtime_error("noise shard header mismatch");
        }
    }
}

std::string NoisePoolReader::noisePoolId() const {
    return manifest_.noisePoolId;
}

RealVector NoisePoolReader::readFramePrefix(FrameIndex frameIndex, std::uint64_t symbolCount) const {
    if (frameIndex >= manifest_.totalFrames || symbolCount > manifest_.symbolsPerFrame) {
        throw std::out_of_range("noise frame or symbol prefix outside range");
    }
    for (const auto& shard : manifest_.shards) {
        if (frameIndex >= shard.firstFrameIndex && frameIndex < shard.firstFrameIndex + shard.frameCount) {
            const std::uint64_t frameOffset = frameIndex - shard.firstFrameIndex;
            const std::uint64_t byteOffset = kNoiseShardHeaderBytes + frameOffset * manifest_.symbolsPerFrame * 8U;
            std::ifstream in(joinPath(directory_, shard.fileName), std::ios::binary);
            in.seekg(static_cast<std::streamoff>(byteOffset), std::ios::beg);
            RealVector samples(static_cast<std::size_t>(symbolCount));
            for (std::uint64_t i = 0; i < symbolCount; ++i) {
                samples[static_cast<std::size_t>(i)] = readDoubleLE(in);
            }
            return samples;
        }
    }
    throw std::out_of_range("noise frame not covered by shard");
}

std::uint64_t NoisePoolReader::frameCount() const {
    return manifest_.totalFrames;
}

std::uint64_t NoisePoolReader::symbolsPerFrame() const {
    return manifest_.symbolsPerFrame;
}

}  // namespace scl::common
