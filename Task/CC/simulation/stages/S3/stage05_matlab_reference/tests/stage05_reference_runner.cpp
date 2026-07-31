#include "cc/block_encoder.hpp"
#include "cc/hard_viterbi.hpp"
#include "cc/soft_viterbi.hpp"
#include "cc/trellis.hpp"

#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

std::string bits(const std::vector<std::uint8_t>& values) {
    std::string text;
    text.reserve(values.size());
    for (auto value : values) {
        text.push_back(static_cast<char>('0' + value));
    }
    return text;
}

std::string reals(const std::vector<double>& values) {
    std::string text;
    for (std::size_t index = 0; index < values.size(); ++index) {
        if (index != 0) {
            text.push_back(';');
        }
        text += std::to_string(values[index]);
    }
    return text;
}

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 2) {
            throw std::invalid_argument("expected output directory");
        }
        const std::filesystem::path output_dir(argv[1]);
        std::filesystem::create_directories(output_dir);
        const scl::cc::Trellis trellis;
        scl::cc::ConvolutionalEncoder encoder(trellis);
        const scl::cc::HardViterbiDecoder hard(trellis);
        const scl::cc::SoftViterbiDecoder soft(trellis);

        std::ofstream table(output_dir / "stage05_matlab_reference_cpp_vectors.csv");
        table << "vectorId,payloadBits,codecInputBits,motherBits,finalState,"
                 "receivedSymbols,llr,sigmaSquared,hardDecodedPayload,softDecodedPayload\n";
        std::mt19937 rng(2026072004U);
        std::normal_distribution<double> noise(0.0, 0.12);
        constexpr double sigma_squared = 0.36;
        for (int vector_id = 0; vector_id < 16; ++vector_id) {
            std::vector<std::uint8_t> payload(300);
            for (auto& bit : payload) {
                bit = static_cast<std::uint8_t>(rng() & 1U);
            }
            if (vector_id == 0) {
                std::fill(payload.begin(), payload.end(), 0);
            } else if (vector_id == 1) {
                std::fill(payload.begin(), payload.end(), 1);
            }
            const auto encoded = encoder.encode_block(payload, true);
            std::vector<double> received;
            std::vector<double> llr;
            std::vector<std::uint8_t> hard_bits;
            received.reserve(encoded.mother_bits.size());
            llr.reserve(encoded.mother_bits.size());
            hard_bits.reserve(encoded.mother_bits.size());
            for (auto bit : encoded.mother_bits) {
                double value = (bit == 0 ? 1.0 : -1.0) + noise(rng);
                received.push_back(value);
                llr.push_back(2.0 * value / sigma_squared);
                hard_bits.push_back(value >= 0.0 ? 0 : 1);
            }
            const auto hard_result = hard.decode_terminated_mother(hard_bits, 306);
            const auto soft_result = soft.decode_terminated_symbols(received, 306);
            require(hard_result.payload_bits == payload, "C++ hard reference mismatch");
            require(soft_result.payload_bits == payload, "C++ soft reference mismatch");
            table << vector_id << ',' << bits(payload) << ','
                  << bits(encoded.codec_input_bits) << ',' << bits(encoded.mother_bits) << ','
                  << static_cast<int>(encoded.final_state) << ','
                  << reals(received) << ',' << reals(llr) << ','
                  << std::setprecision(17) << sigma_squared << ','
                  << bits(hard_result.payload_bits) << ','
                  << bits(soft_result.payload_bits) << '\n';
        }

        std::ofstream branches(output_dir / "stage05_matlab_reference_cpp_trellis.csv");
        branches << "state,inputBit,nextState,outputDecimal\n";
        for (std::size_t state = 0; state < 64; ++state) {
            for (std::uint8_t input = 0; input < 2; ++input) {
                const auto& branch = trellis.branch(static_cast<std::uint8_t>(state), input);
                branches << state << ',' << static_cast<int>(input) << ','
                         << static_cast<int>(branch.next_state) << ','
                         << static_cast<int>(branch.output_bits[0] * 2 + branch.output_bits[1])
                         << '\n';
            }
        }
        std::cout << "PASS_STAGE05_CPP_REFERENCE_VECTORS\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_STAGE05_CPP_REFERENCE_VECTORS: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
