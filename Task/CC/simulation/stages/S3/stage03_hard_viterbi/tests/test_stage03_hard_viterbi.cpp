#include "cc/block_encoder.hpp"
#include "cc/hard_viterbi.hpp"
#include "cc/trellis.hpp"

#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

std::string bits_to_string(const std::vector<std::uint8_t>& bits) {
    std::string text;
    text.reserve(bits.size());
    for (const auto bit : bits) {
        text.push_back(static_cast<char>('0' + bit));
    }
    return text;
}

void run_case(
    scl::cc::ConvolutionalEncoder& encoder,
    const scl::cc::HardViterbiDecoder& decoder,
    const std::vector<std::uint8_t>& payload,
    const std::vector<std::size_t>& flips,
    bool require_recovery,
    std::ofstream* matlab_vectors,
    std::size_t vector_id) {
    const auto encoded = encoder.encode_block(payload, true);
    auto received = encoded.mother_bits;
    for (const auto index : flips) {
        require(index < received.size(), "flip index");
        received[index] ^= 1U;
    }
    const auto decoded = decoder.decode_terminated_mother(
        received, encoded.codec_input_bits.size(), encoded.tail_length);
    require(decoded.codec_input_bits.size() == 306, "codec output length");
    require(decoded.payload_bits.size() == payload.size(), "payload output length");
    require(decoded.normalization_count == 306, "normalization count");
    require(decoded.traceback_final_state == 0, "traceback final state");
    require(decoded.overflow_count == 0, "integer overflow");
    if (require_recovery) {
        require(decoded.payload_bits == payload, "payload mismatch");
        require(
            std::all_of(
                decoded.codec_input_bits.end() - 6,
                decoded.codec_input_bits.end(),
                [](std::uint8_t bit) { return bit == 0; }),
            "decoded tail is not zero");
    }
    const auto repeated = decoder.decode_terminated_mother(
        received, encoded.codec_input_bits.size(), encoded.tail_length);
    require(repeated.payload_bits == decoded.payload_bits, "non-deterministic decoded payload");
    require(repeated.tie_count == decoded.tie_count, "non-deterministic tie count");

    if (matlab_vectors != nullptr) {
        *matlab_vectors << vector_id << ','
                        << bits_to_string(received) << ','
                        << bits_to_string(decoded.codec_input_bits) << ','
                        << bits_to_string(decoded.payload_bits) << ','
                        << decoded.tie_count << '\n';
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const scl::cc::Trellis trellis;
        scl::cc::ConvolutionalEncoder encoder(trellis);
        const scl::cc::HardViterbiDecoder decoder(trellis);

        std::ofstream matlab_vectors;
        if (argc == 2) {
            const std::filesystem::path path(argv[1]);
            std::filesystem::create_directories(path.parent_path());
            matlab_vectors.open(path);
            require(matlab_vectors.good(), "cannot write MATLAB vectors");
            matlab_vectors << "vectorId,receivedMotherBits,cppCodecInputBits,cppPayloadBits,tieCount\n";
        }
        std::ofstream* output = matlab_vectors.is_open() ? &matlab_vectors : nullptr;

        run_case(encoder, decoder, std::vector<std::uint8_t>(300, 0), {}, true, output, 0);
        run_case(encoder, decoder, std::vector<std::uint8_t>(300, 1), {}, true, output, 1);

        std::vector<std::uint8_t> fixed(300);
        for (std::size_t index = 0; index < fixed.size(); ++index) {
            fixed[index] = static_cast<std::uint8_t>(((index * 17U + 3U) % 11U) < 5U);
        }
        run_case(encoder, decoder, fixed, {}, true, output, 2);
        run_case(encoder, decoder, fixed, {117}, true, output, 3);
        run_case(encoder, decoder, fixed, {17, 18, 101, 344}, false, output, 4);

        std::mt19937 rng(2026072002U);
        for (int frame = 0; frame < 100; ++frame) {
            std::vector<std::uint8_t> payload(300);
            for (auto& bit : payload) {
                bit = static_cast<std::uint8_t>(rng() & 1U);
            }
            run_case(encoder, decoder, payload, {}, true, nullptr, 0);
        }

        bool rejected_length = false;
        try {
            decoder.decode_terminated_mother({0, 0, 0}, 2);
        } catch (const std::invalid_argument&) {
            rejected_length = true;
        }
        require(rejected_length, "invalid length was not rejected");

        bool rejected_value = false;
        try {
            decoder.decode_terminated_mother({0, 2}, 1, 0);
        } catch (const std::invalid_argument&) {
            rejected_value = true;
        }
        require(rejected_value, "non-binary hard input was not rejected");

        std::cout << "PASS_STAGE03_CC_HARD_VITERBI\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_STAGE03_CC_HARD_VITERBI: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
