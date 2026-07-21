#include "common/common.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <type_traits>

using namespace scl::common;

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

template <typename Fn>
void requireThrows(Fn&& fn, const char* message) {
    bool thrown = false;
    try {
        fn();
    } catch (const std::invalid_argument&) {
        thrown = true;
    }
    require(thrown, message);
}

void testBitTypeAndValidation() {
    static_assert(std::is_same<Bit, std::uint8_t>::value, "Bit must be uint8_t");
    static_assert(!std::is_same<Bit, bool>::value, "Bit must not be bool");
    validateBit(0, "bit");
    validateBit(1, "bit");
    requireThrows([] { validateBit(2, "bit"); }, "payload bit = 2 must be rejected");
}

void testCodeLengthsAndRate() {
    const CodeLengths bchSegmented{200, 209, 285, 285, 9, 0, 0, 0, 0};
    const CodeLengths bchBlock{200, 200, 248, 248, 0, 0, 0, 0, 0};
    const CodeLengths ccZeroTail{300, 306, 612, 612, 0, 0, 6, 0, 0};
    const CodeLengths ldpc480{300, 300, 480, 480, 0, 0, 0, 0, 0};
    const CodeLengths ldpc576{300, 300, 576, 576, 0, 0, 0, 0, 0};

    require(std::fabs(computeCodeRate(bchSegmented) - (200.0 / 285.0)) < 1e-15, "BCH segmented rate mismatch");
    require(std::fabs(computeCodeRate(bchSegmented) - (static_cast<double>(bchSegmented.codecInputLength) / 285.0)) > 1e-6,
            "rate must not use codecInputLength");
    require(std::fabs(computeCodeRate(bchBlock) - (200.0 / 248.0)) < 1e-15, "BCH block rate mismatch");
    require(std::fabs(computeCodeRate(ccZeroTail) - (300.0 / 612.0)) < 1e-15, "CC rate mismatch");
    require(std::fabs(computeCodeRate(ldpc480) - 0.625) < 1e-15, "LDPC 480 rate mismatch");
    require(std::fabs(computeCodeRate(ldpc576) - (300.0 / 576.0)) < 1e-15, "LDPC 576 rate mismatch");

    CodeLengths bad = bchBlock;
    bad.encodedLength = 0;
    requireThrows([&] { validateCodeLengths(bad); }, "encodedLength=0 must be rejected");
}

void testPayloadFrame() {
    const PayloadFrame frame{"pool_k200", 3, 4, 123, BitVector{0, 1, 1, 0}};
    validatePayloadFrame(frame);

    PayloadFrame badSize = frame;
    badSize.payloadLength = 5;
    requireThrows([&] { validatePayloadFrame(badSize); }, "payload size mismatch must be rejected");

    PayloadFrame badBit = frame;
    badBit.payloadBits[1] = 2;
    requireThrows([&] { validatePayloadFrame(badBit); }, "payload bit 2 must be rejected");
}

void testDecoderInputVariant() {
    DecoderInput hard = HardBitInput{BitVector{0, 1}};
    DecoderInput rx = ReceivedSymbolInput{RealVector{1.0, -0.5}};
    DecoderInput llr = LlrInput{RealVector{3.0, -2.0}};

    require(decoderInputKind(hard) == DecoderInputKind::HardBits, "hard input kind mismatch");
    require(decoderInputKind(rx) == DecoderInputKind::ReceivedSymbols, "received-symbol input kind mismatch");
    require(decoderInputKind(llr) == DecoderInputKind::LlrValues, "LLR input kind mismatch");
    static_assert(std::variant_size<DecoderInput>::value == 3, "DecoderInput must have three alternatives");
}

void testInterfaceDestructors() {
    static_assert(std::has_virtual_destructor<IChannelEncoder>::value, "encoder interface must have virtual destructor");
    static_assert(std::has_virtual_destructor<IChannelDecoder>::value, "decoder interface must have virtual destructor");
    static_assert(std::has_virtual_destructor<IChannel>::value, "channel interface must have virtual destructor");
    static_assert(std::has_virtual_destructor<IFramePoolReader>::value, "frame pool reader must have virtual destructor");
}

void testCheckpointFields() {
    CheckpointRecord checkpoint;
    checkpoint.snrIndex = 2;
    checkpoint.ebN0_dB = 1.5;
    require(checkpoint.snrIndex == 2, "checkpoint snrIndex missing");
    require(std::fabs(checkpoint.ebN0_dB - 1.5) < 1e-15, "checkpoint ebN0_dB missing");
}

}  // namespace

int main() {
    try {
        testBitTypeAndValidation();
        testCodeLengthsAndRate();
        testPayloadFrame();
        testDecoderInputVariant();
        testInterfaceDestructors();
        testCheckpointFields();
    } catch (const std::exception& ex) {
        std::cerr << "COMMON-02 TEST FAIL: " << ex.what() << '\n';
        return 1;
    }

    std::cout << "COMMON-02 TEST PASS\n";
    return 0;
}
