#include "common/frame_pool.hpp"

#include <cstdlib>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void requireThrowsOutOfRange(const scl::common::PackedFramePoolReader& reader,
                             scl::common::FrameIndex index) {
    bool thrown = false;
    try {
        (void)reader.readFrame(index);
    } catch (const std::out_of_range&) {
        thrown = true;
    }
    require(thrown, "out-of-range frame read must throw");
}

void verifyManifest(const std::string& manifestPath) {
    const scl::common::FramePoolManifest manifest = scl::common::loadFramePoolManifest(manifestPath);
    require(!manifest.framePoolId.empty(), "framePoolId must not be empty");
    require(manifest.payloadLength == 200U || manifest.payloadLength == 300U,
            "payloadLength must be 200 or 300");
    require(manifest.totalFrames > 0U, "totalFrames must be positive");
    require(manifest.totalFrames <= scl::common::kMaxFramePoolFrames,
            "totalFrames must respect max support");
    require(manifest.shardSize > 0U, "shardSize must be positive");
    require(manifest.generationAlgorithm == "splitmix64_payload_v1",
            "generationAlgorithm mismatch");
    require(manifest.bitStorageFormat == "packed_bits_lsb_first",
            "bitStorageFormat mismatch");
    require(manifest.endianness == "little", "endianness mismatch");
    require(!manifest.shards.empty(), "manifest must include shards");
}

void verifyReader(const std::string& manifestPath) {
    scl::common::PackedFramePoolReader reader(manifestPath);
    require(reader.payloadLength() == 200U || reader.payloadLength() == 300U,
            "reader payloadLength mismatch");
    require(reader.frameCount() > 0U, "reader frameCount must be positive");

    const std::vector<scl::common::FrameIndex> indices{
        0U,
        reader.frameCount() / 2U,
        reader.frameCount() - 1U,
    };
    for (const scl::common::FrameIndex index : indices) {
        const scl::common::PayloadFrame frame = reader.readFrame(index);
        require(frame.framePoolId == reader.framePoolId(), "framePoolId mismatch");
        require(frame.frameIndex == index, "frameIndex mismatch");
        require(frame.payloadLength == reader.payloadLength(), "payloadLength mismatch");
        require(frame.payloadBits.size() == reader.payloadLength(), "payload bit count mismatch");
        const scl::common::BitVector expected =
            scl::common::generatePayloadBits(frame.masterSeed, frame.payloadLength, frame.frameIndex);
        require(frame.payloadBits == expected, "payload bits do not match deterministic generator");
    }

    if (reader.frameCount() >= 3U) {
        const std::vector<scl::common::PayloadFrame> frames = reader.readFrames(1U, 2U);
        require(frames.size() == 2U, "sequential read count mismatch");
        require(frames[0].frameIndex == 1U && frames[1].frameIndex == 2U,
                "sequential read index mismatch");
    }
    requireThrowsOutOfRange(reader, reader.frameCount());
}

void verifyLocalPacking() {
    const scl::common::BitVector bits{0U, 1U, 1U, 0U, 1U, 0U, 0U, 1U, 1U};
    const std::vector<std::uint8_t> packed = scl::common::packPayloadBits(bits);
    const scl::common::BitVector unpacked = scl::common::unpackPayloadBits(packed, bits.size());
    require(unpacked == bits, "pack/unpack round trip mismatch");

    const scl::common::BitVector a = scl::common::generatePayloadBits(2026072001ULL, 200U, 3U);
    const scl::common::BitVector b = scl::common::generatePayloadBits(2026072001ULL, 200U, 3U);
    const scl::common::BitVector c = scl::common::generatePayloadBits(2026072002ULL, 200U, 3U);
    require(a == b, "same seed must regenerate identical payload");
    require(a != c, "different seed should change payload");
}

}  // namespace

int main(int argc, char** argv) {
    try {
        verifyLocalPacking();
        for (int arg = 1; arg < argc; ++arg) {
            verifyManifest(argv[arg]);
            verifyReader(argv[arg]);
        }
        std::cout << "COMMON-03 TEST PASS\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& ex) {
        std::cerr << "COMMON-03 TEST FAIL: " << ex.what() << '\n';
        return EXIT_FAILURE;
    }
}
