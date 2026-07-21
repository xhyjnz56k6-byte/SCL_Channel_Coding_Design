#include "common/frame_pool.hpp"
#include "common/sha256.hpp"

#include <cstdlib>
#include <exception>
#include <filesystem>
#include <functional>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>

namespace fs = std::filesystem;

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void requireThrows(const std::string& name, const std::function<void()>& fn, const std::string& expected) {
    try {
        fn();
    } catch (const std::exception& ex) {
        if (std::string(ex.what()).find(expected) == std::string::npos) {
            throw std::runtime_error(name + " failed for unexpected reason: " + ex.what());
        }
        return;
    }
    throw std::runtime_error(name + " did not fail");
}

std::string bitsToString(const scl::common::BitVector& bits, std::size_t count) {
    std::string out;
    for (std::size_t i = 0; i < count && i < bits.size(); ++i) {
        out.push_back(bits[i] == 0U ? '0' : '1');
    }
    return out;
}

void replaceFirst(const fs::path& path, const std::string& from, const std::string& to) {
    std::string text = scl::common::readTextFile(path.string());
    const std::size_t pos = text.find(from);
    if (pos == std::string::npos) {
        throw std::runtime_error("replace target not found");
    }
    text.replace(pos, from.size(), to);
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    output << text;
}

fs::path copyPool(const fs::path& manifestPath, const std::string& suffix) {
    const fs::path target = manifestPath.parent_path().parent_path() / suffix;
    fs::remove_all(target);
    fs::create_directories(target);
    fs::copy(manifestPath.parent_path(), target, fs::copy_options::recursive | fs::copy_options::overwrite_existing);
    return target / "manifest.json";
}

void flipFirstShardByte(const fs::path& manifestPath) {
    const scl::common::FramePoolManifest manifest = scl::common::loadFramePoolManifest(manifestPath.string());
    const fs::path shard = manifestPath.parent_path() / manifest.shards.front().fileName;
    std::fstream file(shard, std::ios::binary | std::ios::in | std::ios::out);
    char byte = 0;
    file.read(&byte, 1);
    byte = static_cast<char>(byte ^ 0x01);
    file.seekp(0);
    file.write(&byte, 1);
}

void truncateFirstShard(const fs::path& manifestPath) {
    const scl::common::FramePoolManifest manifest = scl::common::loadFramePoolManifest(manifestPath.string());
    const fs::path shard = manifestPath.parent_path() / manifest.shards.front().fileName;
    const std::uintmax_t size = fs::file_size(shard);
    fs::resize_file(shard, size - 1U);
}

void verifyLocalUtilities() {
    static_assert(std::is_base_of<scl::common::IFramePoolReader, scl::common::PackedFramePoolReader>::value,
                  "PackedFramePoolReader must implement IFramePoolReader");
    static_assert(std::has_virtual_destructor<scl::common::IFramePoolReader>::value,
                  "IFramePoolReader must have virtual destructor");
    require(scl::common::sha256Hex("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            "C++ SHA256 must match known vector");

    const scl::common::BitVector bits{0U, 1U, 1U, 0U, 1U, 0U, 0U, 1U, 1U};
    const std::vector<std::uint8_t> packed = scl::common::packPayloadBits(bits);
    require(packed.size() == 2U, "packed byte count mismatch");
    require(packed[0] == 0x96U && packed[1] == 0x01U, "explicit packed byte value mismatch");
    require(scl::common::unpackPayloadBits(packed, bits.size()) == bits, "pack/unpack round trip mismatch");

    const scl::common::BitVector k200f0 = scl::common::generatePayloadBits(2026072001ULL, 200U, 0U);
    const scl::common::BitVector k200f999 = scl::common::generatePayloadBits(2026072001ULL, 200U, 999U);
    const scl::common::BitVector k300f0 = scl::common::generatePayloadBits(2026072001ULL, 300U, 0U);
    const scl::common::BitVector k300f1000 = scl::common::generatePayloadBits(2026072001ULL, 300U, 1000U);
    require(bitsToString(k200f0, 64U) == "1110101101010011100010111010110001010011111111100111000101000100", "K200 frame0 golden mismatch");
    require(bitsToString(k200f999, 64U) == "1001101010011010100000111010011100011111101001111000100011011110", "K200 frame999 golden mismatch");
    require(bitsToString(k300f0, 64U) == "0011100101011101010000100100101010100011110011100010101101101110", "K300 frame0 golden mismatch");
    require(bitsToString(k300f1000, 64U) == "0101001010010011011011011001100111101001000000101110101100101101", "K300 frame1000 golden mismatch");
    require(k200f0 == scl::common::generatePayloadBits(2026072001ULL, 200U, 0U), "same seed/frame mismatch");
    require(k200f0 != scl::common::generatePayloadBits(2026072002ULL, 200U, 0U), "different seed should differ");

    const auto packed200 = scl::common::packPayloadBits(k200f0);
    const auto packed300 = scl::common::packPayloadBits(k300f0);
    require((packed200.back() & 0xF0U) == 0U, "K=200 unused tail bits must be zero");
    require((packed300.back() & 0xF0U) == 0U, "K=300 unused tail bits must be zero");
}

void verifyReader(const fs::path& manifestPath) {
    const scl::common::FramePoolManifest manifest = scl::common::loadFramePoolManifest(manifestPath.string());
    scl::common::validateFramePoolManifest(manifest);
    scl::common::PackedFramePoolReader reader(manifestPath.string());
    reader.verifyAllShards();
    require(reader.payloadLength() == manifest.payloadLength, "reader payloadLength mismatch");
    require(reader.frameCount() == manifest.totalFrames, "reader frameCount mismatch");

    std::vector<scl::common::FrameIndex> indices{0U, manifest.shards.front().frameCount - 1U};
    if (manifest.shards.size() > 1U) {
        indices.push_back(manifest.shards[1].startFrame);
    }
    indices.push_back(reader.frameCount() / 2U);
    indices.push_back(reader.frameCount() - 1U);
    for (const scl::common::FrameIndex index : indices) {
        const scl::common::PayloadFrame frame = reader.readFrame(index);
        const scl::common::BitVector expected =
            scl::common::generatePayloadBits(frame.masterSeed, frame.payloadLength, frame.frameIndex, manifest.payloadPolicyVersion);
        require(frame.payloadBits == expected, "payload bits do not match deterministic generator");
    }

    if (manifest.shards.size() > 1U) {
        const scl::common::FrameIndex start = manifest.shards.front().frameCount - 1U;
        const auto frames = reader.readFrames(start, 2U);
        require(frames.size() == 2U && frames[0].frameIndex == start && frames[1].frameIndex == start + 1U,
                "sequential cross-shard read mismatch");
    }
    requireThrows("frameIndex==frameCount", [&] { (void)reader.readFrame(reader.frameCount()); }, "frameIndex");
    requireThrows("readFrames past end", [&] { (void)reader.readFrames(reader.frameCount() - 1U, 2U); }, "readFrames");
}

void verifyNegativeManifests(const fs::path& manifestPath) {
    fs::path corrupted = copyPool(manifestPath, "cpp_corrupt_byte");
    flipFirstShardByte(corrupted);
    requireThrows("corrupted shard", [&] { scl::common::PackedFramePoolReader reader(corrupted.string()); }, "SHA256");

    fs::path truncated = copyPool(manifestPath, "cpp_truncated_shard");
    truncateFirstShard(truncated);
    requireThrows("truncated shard", [&] { scl::common::PackedFramePoolReader reader(truncated.string()); }, "sizeBytes");

    fs::path gap = copyPool(manifestPath, "cpp_gap_manifest");
    replaceFirst(gap, "\"startFrame\": 10", "\"startFrame\": 11");
    requireThrows("manifest gap", [&] { (void)scl::common::loadFramePoolManifest(gap.string()); }, "contiguous");

    fs::path overlap = copyPool(manifestPath, "cpp_overlap_manifest");
    replaceFirst(overlap, "\"startFrame\": 10", "\"startFrame\": 9");
    requireThrows("manifest overlap", [&] { (void)scl::common::loadFramePoolManifest(overlap.string()); }, "contiguous");

    fs::path badCount = copyPool(manifestPath, "cpp_bad_count_manifest");
    replaceFirst(badCount, "\"totalFrames\": 24", "\"totalFrames\": 23");
    requireThrows("manifest totalFrames", [&] { (void)scl::common::loadFramePoolManifest(badCount.string()); }, "totalFrames");

    fs::path badSha = copyPool(manifestPath, "cpp_bad_sha_manifest");
    replaceFirst(badSha, "\"sha256\": ", "\"sha256\": \"bad\", \"oldSha\": ");
    requireThrows("manifest sha format", [&] { (void)scl::common::loadFramePoolManifest(badSha.string()); }, "sha256");

    fs::path badOverall = copyPool(manifestPath, "cpp_bad_overall_manifest");
    replaceFirst(badOverall, "\"overallHash\": ", "\"overallHash\": \"0000000000000000000000000000000000000000000000000000000000000000\", \"oldOverallHash\": ");
    requireThrows("manifest overallHash", [&] { (void)scl::common::loadFramePoolManifest(badOverall.string()); }, "overallHash");
}

}  // namespace

int main(int argc, char** argv) {
    try {
        verifyLocalUtilities();
        for (int arg = 1; arg < argc; ++arg) {
            const fs::path manifestPath(argv[arg]);
            verifyReader(manifestPath);
            if (arg == 1) {
                verifyNegativeManifests(manifestPath);
            }
        }
        std::cout << "COMMON-03 TEST PASS\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& ex) {
        std::cerr << "COMMON-03 TEST FAIL: " << ex.what() << '\n';
        return EXIT_FAILURE;
    }
}
