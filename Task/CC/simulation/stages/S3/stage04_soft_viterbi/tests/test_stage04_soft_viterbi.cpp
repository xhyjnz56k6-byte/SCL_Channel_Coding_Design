#include "cc/block_encoder.hpp"
#include "cc/hard_viterbi.hpp"
#include "cc/soft_viterbi.hpp"
#include "cc/trellis.hpp"

#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
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

std::string bits_text(const std::vector<std::uint8_t>& bits) {
    std::string result;
    for (auto bit : bits) {
        result.push_back(static_cast<char>('0' + bit));
    }
    return result;
}

std::string symbols_text(const std::vector<double>& symbols) {
    std::string result;
    for (std::size_t index = 0; index < symbols.size(); ++index) {
        if (index != 0) {
            result.push_back(';');
        }
        result += std::to_string(symbols[index]);
    }
    return result;
}

std::vector<double> bpsk(const std::vector<std::uint8_t>& bits) {
    std::vector<double> symbols;
    symbols.reserve(bits.size());
    for (auto bit : bits) {
        symbols.push_back(bit == 0 ? 1.0 : -1.0);
    }
    return symbols;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const scl::cc::Trellis trellis;
        scl::cc::ConvolutionalEncoder encoder(trellis);
        const scl::cc::HardViterbiDecoder hard(trellis);
        const scl::cc::SoftViterbiDecoder soft(trellis);
        std::ofstream vectors;
        if (argc == 2) {
            const std::filesystem::path path(argv[1]);
            std::filesystem::create_directories(path.parent_path());
            vectors.open(path);
            require(vectors.good(), "cannot write MATLAB vectors");
            vectors << "vectorId,receivedSymbols,cppCodecInputBits,cppPayloadBits\n";
        }

        std::mt19937 rng(2026072003U);
        std::normal_distribution<double> low_noise(0.0, 0.18);
        for (int frame = 0; frame < 100; ++frame) {
            std::vector<std::uint8_t> payload(300);
            for (auto& bit : payload) {
                bit = static_cast<std::uint8_t>(rng() & 1U);
            }
            const auto encoded = encoder.encode_block(payload, true);
            auto symbols = bpsk(encoded.mother_bits);
            if (frame >= 3) {
                for (auto& value : symbols) {
                    value += low_noise(rng);
                }
            }
            const auto decoded = soft.decode_terminated_symbols(symbols, 306);
            require(decoded.payload_bits == payload, "soft noiseless/low-noise mismatch");
            require(decoded.normalization_count == 306, "soft normalization count");
            require(decoded.non_finite_metric_count == 0, "soft non-finite metric");
            const auto repeated = soft.decode_terminated_symbols(symbols, 306);
            require(repeated.payload_bits == decoded.payload_bits, "soft non-deterministic");

            std::vector<std::uint8_t> hard_bits;
            hard_bits.reserve(symbols.size());
            for (double value : symbols) {
                hard_bits.push_back(value >= 0.0 ? 0 : 1);
            }
            const auto hard_result = hard.decode_terminated_mother(hard_bits, 306);
            if (frame < 3) {
                require(hard_result.payload_bits == decoded.payload_bits, "shared-symbol hard/soft mismatch");
                if (vectors.is_open()) {
                    vectors << frame << ',' << symbols_text(symbols) << ','
                            << bits_text(decoded.codec_input_bits) << ','
                            << bits_text(decoded.payload_bits) << '\n';
                }
            }
        }

        bool rejected_nan = false;
        try {
            soft.decode_terminated_symbols(
                {std::numeric_limits<double>::quiet_NaN(), 1.0}, 1, 0);
        } catch (const std::invalid_argument&) {
            rejected_nan = true;
        }
        require(rejected_nan, "NaN was not rejected");

        bool rejected_inf = false;
        try {
            soft.decode_terminated_symbols(
                {std::numeric_limits<double>::infinity(), 1.0}, 1, 0);
        } catch (const std::invalid_argument&) {
            rejected_inf = true;
        }
        require(rejected_inf, "Inf was not rejected");

        std::cout << "PASS_STAGE04_CC_SOFT_VITERBI\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_STAGE04_CC_SOFT_VITERBI: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
