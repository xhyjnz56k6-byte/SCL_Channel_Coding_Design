#include "s7/s7.hpp"

#include <cmath>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {
void require(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }
void requireThrows(const std::function<void()>& action, const char* message) {
    try { action(); } catch (const std::exception&) { return; } throw std::runtime_error(message);
}
}

int main() {
    try {
        const std::vector<s7::BchInterleaver> bchMethods{s7::BchInterleaver::None, s7::BchInterleaver::Codeblock, s7::BchInterleaver::RowColumn, s7::BchInterleaver::GlobalPseudorandom};
        const std::vector<std::size_t> bchParameters{0, 4, 19, 285};
        std::vector<std::uint8_t> bchBits(s7::kBchEncodedBits); for (std::size_t i = 0; i < bchBits.size(); ++i) bchBits[i] = i & 1U;
        for (std::size_t i = 0; i < bchMethods.size(); ++i) {
            const auto mapping = s7::makeBchMapping(bchMethods[i], bchParameters[i]);
            require(s7::deinterleaveBits(s7::interleaveBits(bchBits, mapping), mapping) == bchBits, "BCH inverse mismatch");
            require(mapping.sha256.size() == 64, "BCH hash length mismatch");
        }
        for (std::size_t depth : {4U, 8U, 16U, 19U}) s7::validateMapping(s7::makeBchMapping(s7::BchInterleaver::Codeblock, depth), s7::kBchEncodedBits);
        for (std::size_t rows : {4U, 8U, 15U, 19U}) s7::validateMapping(s7::makeBchMapping(s7::BchInterleaver::RowColumn, rows), s7::kBchEncodedBits);
        requireThrows([] { (void)s7::makeBchMapping(s7::BchInterleaver::Codeblock, 3); }, "illegal BCH depth accepted");

        for (std::size_t depth : {4U, 8U, 16U}) {
            const auto mapping = s7::makeCcMapping(s7::CcInterleaver::ShortDepthBlock, depth);
            s7::validateMapping(mapping, s7::kCcEncodedBits);
        }
        for (std::size_t span : {32U, 64U, 128U}) {
            const auto mapping = s7::makeCcMapping(s7::CcInterleaver::Pseudorandom, span);
            require(mapping.preserveMotherOutputPair && mapping.permutationUnit == "TRELLIS_STEP", "CC pair convention mismatch");
        }
        requireThrows([] { (void)s7::makeCcMapping(s7::CcInterleaver::Pseudorandom, 31); }, "illegal CC span accepted");

        const auto zeroBurst = s7::makeBurstSpec(8, 0.0, s7::BurstPosition::Middle, 0);
        const std::vector<std::uint8_t> channelBits{0,1,0,1,1,0,0,1};
        const std::vector<double> zeroNoise(8, 0.0);
        const auto symbols = s7::bpskModulate(channelBits);
        require(s7::applyPolarityReversalAwgn(symbols, zeroNoise, 0.0, zeroBurst) == symbols, "L=0 did not reduce to AWGN");
        const auto fullBurst = s7::makeBurstSpec(8, 1.0, s7::BurstPosition::Tail, 0);
        const auto flipped = s7::applyPolarityReversalAwgn(symbols, zeroNoise, 0.0, fullBurst);
        for (std::size_t i = 0; i < symbols.size(); ++i) require(flipped[i] == -symbols[i], "full-frame polarity reversal mismatch");
        requireThrows([&] { auto invalid = zeroBurst; invalid.wrapAround = true; (void)s7::applyPolarityReversalAwgn(symbols, zeroNoise, 0.0, invalid); }, "wrap-around accepted");

        const auto bchPayload = s7::deterministicPayload(s7::kBchPayloadBits, 0);
        const s7::BchCodecContext bchContext;
        for (const auto& mapping : {s7::makeBchMapping(s7::BchInterleaver::None), s7::makeBchMapping(s7::BchInterleaver::Codeblock, 19), s7::makeBchMapping(s7::BchInterleaver::RowColumn, 19), s7::makeBchMapping(s7::BchInterleaver::GlobalPseudorandom, 285)}) {
            const auto result = s7::runBchFrame(bchContext, bchPayload, mapping, std::vector<double>(s7::kBchEncodedBits, 0.0), 0.0, s7::makeBurstSpec(s7::kBchEncodedBits, 0.0, s7::BurstPosition::Head, 0));
            require(result.bitErrors == 0 && result.decodedPayload == bchPayload, "BCH noiseless chain failed");
        }

        const auto ccPayload = s7::deterministicPayload(s7::kCcPayloadBits, 0);
        for (const auto& mapping : {s7::makeCcMapping(s7::CcInterleaver::None), s7::makeCcMapping(s7::CcInterleaver::ShortDepthBlock, 8), s7::makeCcMapping(s7::CcInterleaver::Pseudorandom, 64)}) {
            const auto result = s7::runCcFrame(ccPayload, mapping, std::vector<double>(s7::kCcEncodedBits, 0.0), 0.0, s7::makeBurstSpec(s7::kCcEncodedBits, 0.0, s7::BurstPosition::Head, 0));
            require(result.bitErrors == 0 && result.decodedPayload == ccPayload && result.tracebackFinalState == 0, "CC noiseless chain failed");
        }
        require(std::abs(s7::sigmaSquaredFromEsN0(0.0) - 0.5) < 1e-15, "noise formula mismatch");
        std::cout << "PASS_S7_UNIT_TESTS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_S7_UNIT_TESTS: " << error.what() << '\n'; return 1;
    }
}
