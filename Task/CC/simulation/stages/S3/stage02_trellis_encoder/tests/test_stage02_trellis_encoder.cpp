#include "cc/block_encoder.hpp"
#include "cc/trellis.hpp"

#include <algorithm>
#include <array>
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

using scl::cc::ConvolutionalEncoder;
using scl::cc::EncodeResult;
using scl::cc::Trellis;

void require(const bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

std::vector<std::uint8_t> reference_encode(
    const std::vector<std::uint8_t>& input,
    std::uint8_t initial_state,
    std::uint8_t& final_state) {
    std::vector<std::uint8_t> output;
    output.reserve(input.size() * 2);
    std::array<std::uint8_t, 6> memory{};
    for (std::size_t index = 0; index < memory.size(); ++index) {
        memory[index] = static_cast<std::uint8_t>((initial_state >> (5U - index)) & 1U);
    }
    for (const std::uint8_t bit : input) {
        const std::uint8_t g1 =
            static_cast<std::uint8_t>(bit ^ memory[0] ^ memory[1] ^ memory[2] ^ memory[5]);
        const std::uint8_t g2 =
            static_cast<std::uint8_t>(bit ^ memory[1] ^ memory[2] ^ memory[4] ^ memory[5]);
        output.push_back(g1);
        output.push_back(g2);
        for (std::size_t index = memory.size() - 1; index > 0; --index) {
            memory[index] = memory[index - 1];
        }
        memory[0] = bit;
    }
    final_state = 0;
    for (std::size_t index = 0; index < memory.size(); ++index) {
        final_state = static_cast<std::uint8_t>(
            final_state | static_cast<std::uint8_t>(memory[index] << (5U - index)));
    }
    return output;
}

void check_trellis() {
    const Trellis trellis;
    require(trellis.branches().size() == 64, "trellis must have 64 states");
    for (std::size_t state = 0; state < 64; ++state) {
        for (std::size_t input = 0; input < 2; ++input) {
            const auto& branch = trellis.branch(
                static_cast<std::uint8_t>(state),
                static_cast<std::uint8_t>(input));
            require(branch.input_bit == input, "branch input mismatch");
            require(branch.next_state == (((input & 1U) << 5U) | (state >> 1U)), "next state mismatch");
            require(branch.output_bits[0] <= 1 && branch.output_bits[1] <= 1, "non-binary output");
            const auto& repeated = trellis.branch(
                static_cast<std::uint8_t>(state),
                static_cast<std::uint8_t>(input));
            require(
                repeated.next_state == branch.next_state &&
                    repeated.output_bits == branch.output_bits,
                "trellis lookup is not deterministic");
        }
    }
    require(trellis.branch(0, 1).next_state == 32, "known next state 0/1");
    require(trellis.branch(0, 1).output_bits == std::array<std::uint8_t, 2>{1, 1}, "known output 0/1");
    require(trellis.branch(32, 0).output_bits == std::array<std::uint8_t, 2>{1, 0}, "known output 32/0");
}

void check_vector(
    ConvolutionalEncoder& encoder,
    const std::vector<std::uint8_t>& payload,
    const bool tail) {
    const EncodeResult result = encoder.encode_block(payload, tail);
    std::uint8_t expected_final = 0;
    const auto expected = reference_encode(result.codec_input_bits, 0, expected_final);
    require(result.mother_bits == expected, "reference encoder mismatch");
    require(result.final_state == expected_final, "reference final state mismatch");
    require(result.mother_bits.size() == 2 * (payload.size() + (tail ? 6 : 0)), "encoded length");
    if (tail) {
        require(result.final_state == 0, "tail termination");
    }
}

void check_segments() {
    const Trellis trellis;
    ConvolutionalEncoder one_shot(trellis);
    ConvolutionalEncoder segmented(trellis);
    std::vector<std::uint8_t> input(300);
    std::mt19937 rng(2026072001U);
    for (auto& bit : input) {
        bit = static_cast<std::uint8_t>(rng() & 1U);
    }

    std::vector<std::uint8_t> combined;
    one_shot.encode_segment(input, combined);
    const auto one_shot_state = one_shot.state();

    std::vector<std::uint8_t> segmented_output;
    segmented.encode_segment(
        std::vector<std::uint8_t>(input.begin(), input.begin() + 73),
        segmented_output);
    const auto exported = segmented.state();
    segmented.import_state(exported);
    segmented.encode_segment(
        std::vector<std::uint8_t>(input.begin() + 73, input.begin() + 201),
        segmented_output);
    segmented.encode_segment(
        std::vector<std::uint8_t>(input.begin() + 201, input.end()),
        segmented_output);

    require(segmented_output == combined, "segmented encoding mismatch");
    require(segmented.state() == one_shot_state, "segmented final state mismatch");
}

void write_matlab_vectors(
    const std::filesystem::path& output_path,
    ConvolutionalEncoder& encoder,
    const Trellis& trellis) {
    std::filesystem::create_directories(output_path.parent_path());
    std::ofstream output(output_path);
    require(output.good(), "cannot write MATLAB vectors");
    output << "vectorId,inputBits,cppMotherBits,finalState\n";

    const std::vector<std::vector<std::uint8_t>> vectors = {
        {0, 0, 0, 0, 0, 0, 0, 0},
        {1, 0, 0, 0, 0, 0, 0},
        {1, 0, 1, 1, 0, 1, 0, 0, 1},
        {1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1}
    };

    for (std::size_t vector_id = 0; vector_id < vectors.size(); ++vector_id) {
        const auto result = encoder.encode_block(vectors[vector_id], false);
        output << vector_id << ',';
        for (const auto bit : vectors[vector_id]) {
            output << static_cast<int>(bit);
        }
        output << ',';
        for (const auto bit : result.mother_bits) {
            output << static_cast<int>(bit);
        }
        output << ',' << static_cast<int>(result.final_state) << '\n';
    }

    const auto trellis_path =
        output_path.parent_path() / "stage02_trellis_encoder_cpp_trellis.csv";
    std::ofstream table(trellis_path);
    require(table.good(), "cannot write C++ trellis table");
    table << "state,inputBit,nextState,g1,g2,outputDecimal\n";
    for (std::size_t state = 0; state < 64; ++state) {
        for (std::size_t input = 0; input < 2; ++input) {
            const auto& branch = trellis.branch(
                static_cast<std::uint8_t>(state),
                static_cast<std::uint8_t>(input));
            const int output_decimal =
                static_cast<int>(branch.output_bits[0]) * 2 +
                static_cast<int>(branch.output_bits[1]);
            table << state << ',' << input << ','
                  << static_cast<int>(branch.next_state) << ','
                  << static_cast<int>(branch.output_bits[0]) << ','
                  << static_cast<int>(branch.output_bits[1]) << ','
                  << output_decimal << '\n';
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        check_trellis();
        const Trellis trellis;
        ConvolutionalEncoder encoder(trellis);

        check_vector(encoder, std::vector<std::uint8_t>(300, 0), true);
        check_vector(encoder, std::vector<std::uint8_t>(300, 1), true);
        check_vector(encoder, {1}, true);
        check_vector(encoder, {1, 0, 1, 1, 0, 1, 0, 0, 1}, true);
        check_vector(encoder, std::vector<std::uint8_t>(200, 1), true);

        std::mt19937 rng(2026072001U);
        for (int trial = 0; trial < 100; ++trial) {
            std::vector<std::uint8_t> random_payload(300);
            for (auto& bit : random_payload) {
                bit = static_cast<std::uint8_t>(rng() & 1U);
            }
            check_vector(encoder, random_payload, true);
        }
        check_segments();

        bool rejected = false;
        try {
            encoder.encode_block({0, 1, 2, 0}, false);
        } catch (const std::invalid_argument&) {
            rejected = true;
        }
        require(rejected, "non-binary input must be rejected");

        if (argc == 2) {
            write_matlab_vectors(argv[1], encoder, trellis);
        }
        std::cout << "PASS_STAGE02_CC_TRELLIS_ENCODER\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_STAGE02_CC_TRELLIS_ENCODER: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
