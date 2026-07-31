#include "cc/block_encoder.hpp"
#include "cc/hard_viterbi.hpp"
#include "cc/puncturing.hpp"
#include "cc/soft_viterbi.hpp"
#include "cc/trellis.hpp"

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

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

std::string bits(const std::vector<std::uint8_t>& values) {
    std::string text;
    for (auto value : values) text.push_back(static_cast<char>('0' + value));
    return text;
}

std::string mask_text(const std::vector<std::uint8_t>& values) {
    return bits(values);
}

struct CandidateStats {
    std::string id;
    std::size_t frames = 0;
    std::size_t hard_errors = 0;
    std::size_t soft_errors = 0;
    std::size_t transmitted = 0;
};

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("expected results directory");
        const std::filesystem::path results(argv[1]);
        std::filesystem::create_directories(results);
        const std::vector<scl::cc::PuncturePattern> patterns = {
            {"R23_A_1110", {1,1,1,0}},
            {"R23_B_1101", {1,1,0,1}},
            {"R34_A_111001", {1,1,1,0,0,1}},
            {"R34_B_110110", {1,1,0,1,1,0}},
        };
        const scl::cc::Trellis trellis;
        scl::cc::ConvolutionalEncoder encoder(trellis);
        const scl::cc::HardViterbiDecoder hard(trellis);
        const scl::cc::SoftViterbiDecoder soft(trellis);
        std::mt19937 rng(2026072005U);
        std::normal_distribution<double> noise(0.0, 0.70);

        std::ofstream vectors(results/"stage06_puncturing_cpp_matlab_vectors.csv");
        vectors << "patternId,keepMask,payloadBits,puncturedBits,hardDecodedPayload,softDecodedPayload\n";
        std::vector<CandidateStats> stats;
        for (const auto& pattern : patterns) {
            scl::cc::validate_puncture_pattern(pattern);
            CandidateStats stat;
            stat.id = pattern.id;
            for (int frame = 0; frame < 120; ++frame) {
                std::vector<std::uint8_t> payload(300);
                for (auto& bit : payload) bit = static_cast<std::uint8_t>(rng() & 1U);
                const auto encoded = encoder.encode_block(payload, true);
                const auto punctured = scl::cc::puncture_bits(encoded.mother_bits, pattern);
                stat.transmitted = punctured.bits.size();
                require(
                    punctured.bits.size() == (pattern.keep_mask.size() == 4 ? 459U : 408U),
                    "punctured length mismatch");
                const auto hard_noiseless =
                    scl::cc::depuncture_hard(punctured.bits, 612, pattern);
                const auto hard_clean = hard.decode_terminated_masked(
                    hard_noiseless.expanded_bits, hard_noiseless.observed_mask, 306);
                std::vector<double> clean_tx;
                for (auto bit : punctured.bits) clean_tx.push_back(bit == 0 ? 1.0 : -1.0);
                const auto soft_noiseless = scl::cc::depuncture_soft(clean_tx, 612, pattern);
                const auto soft_clean = soft.decode_terminated_masked_symbols(
                    soft_noiseless.expanded_values, soft_noiseless.observed_mask, 306);
                require(hard_clean.payload_bits == payload, "hard punctured noiseless mismatch");
                require(soft_clean.payload_bits == payload, "soft punctured noiseless mismatch");
                if (frame == 0) {
                    vectors << pattern.id << ',' << mask_text(pattern.keep_mask) << ','
                            << bits(payload) << ',' << bits(punctured.bits) << ','
                            << bits(hard_clean.payload_bits) << ','
                            << bits(soft_clean.payload_bits) << '\n';
                }

                std::vector<double> received;
                std::vector<std::uint8_t> hard_bits;
                for (auto bit : punctured.bits) {
                    const double value = (bit == 0 ? 1.0 : -1.0) + noise(rng);
                    received.push_back(value);
                    hard_bits.push_back(value >= 0 ? 0 : 1);
                }
                const auto hard_dep = scl::cc::depuncture_hard(hard_bits, 612, pattern);
                const auto soft_dep = scl::cc::depuncture_soft(received, 612, pattern);
                const auto hard_result = hard.decode_terminated_masked(
                    hard_dep.expanded_bits, hard_dep.observed_mask, 306);
                const auto soft_result = soft.decode_terminated_masked_symbols(
                    soft_dep.expanded_values, soft_dep.observed_mask, 306);
                ++stat.frames;
                stat.hard_errors += hard_result.payload_bits != payload;
                stat.soft_errors += soft_result.payload_bits != payload;
            }
            stats.push_back(stat);
        }

        const std::vector<std::uint8_t> phase_test(37, 1);
        for (const auto& pattern : patterns) {
            const auto whole = scl::cc::puncture_bits(phase_test, pattern);
            const std::vector<std::uint8_t> first(phase_test.begin(), phase_test.begin()+13);
            const std::vector<std::uint8_t> second(phase_test.begin()+13, phase_test.end());
            const auto a = scl::cc::puncture_bits(first, pattern);
            const auto b = scl::cc::puncture_bits(second, pattern, a.final_phase);
            auto joined = a.bits;
            joined.insert(joined.end(), b.bits.begin(), b.bits.end());
            require(joined == whole.bits && b.final_phase == whole.final_phase, "phase carry mismatch");
        }

        std::ofstream summary(results/"stage06_puncturing_candidate_prescan.csv");
        summary << "patternId,frames,hardFrameErrors,softFrameErrors,N_mother,N_transmitted,actualRate\n";
        for (const auto& stat : stats) {
            summary << stat.id << ',' << stat.frames << ',' << stat.hard_errors << ','
                    << stat.soft_errors << ",612," << stat.transmitted << ','
                    << (300.0/static_cast<double>(stat.transmitted)) << '\n';
        }
        std::cout << "PASS_STAGE06_CPP_PUNCTURING\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_STAGE06_CPP_PUNCTURING: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
