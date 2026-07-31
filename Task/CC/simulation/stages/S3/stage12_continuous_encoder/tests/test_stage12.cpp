#include "continuous_encoder.hpp"
#include "cc/trellis.hpp"
#include "common/frame_pool.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <vector>

using namespace scl::cc;

namespace {

void append(std::vector<std::uint8_t>& destination,
            const std::vector<std::uint8_t>& source) {
    destination.insert(destination.end(), source.begin(), source.end());
}

bool same_state(const stage12::ContinuousState& lhs,
                const stage12::ContinuousState& rhs) {
    return lhs.encoder_state == rhs.encoder_state
        && lhs.puncture_phase == rhs.puncture_phase
        && lhs.slot_index == rhs.slot_index
        && lhs.payload_bits == rhs.payload_bits
        && lhs.mother_bits == rhs.mother_bits
        && lhs.transmitted_bits == rhs.transmitted_bits;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 2) {
            throw std::invalid_argument("results dir");
        }
        const std::filesystem::path results(argv[1]);
        std::filesystem::create_directories(results);
        Trellis trellis;
        const std::vector<PuncturePattern> patterns{
            {"R12", {1, 1}},
            {"R23", {1, 1, 0, 1}},
            {"R34", {1, 1, 0, 1, 1, 0}},
        };
        const std::vector<std::size_t> slot_sizes{300, 50, 100, 150};

        std::ofstream metadata(results / "stage12_slot_metadata.csv");
        metadata
            << "pattern,slotSize,slotIndex,payloadStart,payloadCount,"
               "initialState,finalState,initialPhase,finalPhase,motherCount,"
               "transmittedCount,appendedTail,checkpointResumeVerified\n";

        for (const auto& pattern : patterns) {
            for (const std::size_t slot_size : slot_sizes) {
                if (300 % slot_size != 0) {
                    throw std::logic_error("slot size must divide payload");
                }
                for (std::uint64_t frame = 0; frame < 100; ++frame) {
                    const auto payload = scl::common::generatePayloadBits(
                        2026072001, 300, frame);
                    ConvolutionalEncoder block(trellis);
                    const auto expected = block.encode_block(payload, true);
                    const auto expected_punctured =
                        puncture_bits(expected.mother_bits, pattern);

                    auto continuous =
                        std::make_unique<stage12::ContinuousEncoder>(
                            trellis, pattern);
                    std::vector<std::uint8_t> mother;
                    std::vector<std::uint8_t> transmitted;
                    stage12::ContinuousState previous;
                    for (std::size_t start = 0; start < payload.size();
                         start += slot_size) {
                        const bool final_slot =
                            start + slot_size == payload.size();
                        const std::vector<std::uint8_t> part(
                            payload.begin() + static_cast<std::ptrdiff_t>(start),
                            payload.begin()
                                + static_cast<std::ptrdiff_t>(start + slot_size));
                        const auto result = continuous->encode_slot(
                            part, final_slot, final_slot);
                        if (result.metadata.initial_state
                                != previous.encoder_state
                            || result.metadata.initial_phase
                                != previous.puncture_phase
                            || result.metadata.payload_start
                                != previous.payload_bits
                            || result.metadata.appended_tail != final_slot) {
                            throw std::runtime_error(
                                "slot state/phase/tail continuity");
                        }
                        append(mother, result.mother_bits);
                        append(transmitted, result.transmitted_bits);

                        const auto checkpoint = continuous->export_state();
                        auto resumed =
                            std::make_unique<stage12::ContinuousEncoder>(
                                trellis, pattern);
                        resumed->import_state(checkpoint);
                        if (!same_state(
                                checkpoint, resumed->export_state())) {
                            throw std::runtime_error(
                                "checkpoint/resume state mismatch");
                        }
                        continuous.swap(resumed);
                        previous = checkpoint;

                        if (frame == 0) {
                            metadata
                                << pattern.id << ',' << slot_size << ','
                                << result.metadata.slot_index << ','
                                << result.metadata.payload_start << ','
                                << result.metadata.payload_count << ','
                                << static_cast<int>(
                                       result.metadata.initial_state)
                                << ','
                                << static_cast<int>(result.metadata.final_state)
                                << ',' << result.metadata.initial_phase << ','
                                << result.metadata.final_phase << ','
                                << result.metadata.mother_count << ','
                                << result.metadata.transmitted_count << ','
                                << result.metadata.appended_tail << ",1\n";
                        }
                    }
                    const auto final_state = continuous->export_state();
                    if (mother != expected.mother_bits
                        || transmitted != expected_punctured.bits
                        || final_state.encoder_state != 0
                        || final_state.payload_bits != 300
                        || final_state.mother_bits != 2 * 306
                        || final_state.transmitted_bits
                            != expected_punctured.bits.size()) {
                        throw std::runtime_error(
                            "segmented/full equivalence or final state");
                    }
                }
            }
        }

        bool rejected_middle_tail = false;
        try {
            stage12::ContinuousEncoder invalid(trellis, patterns[1]);
            invalid.encode_slot({1}, false, true);
        } catch (const std::invalid_argument&) {
            rejected_middle_tail = true;
        }
        if (!rejected_middle_tail) {
            throw std::runtime_error("middle-slot tail accepted");
        }

        std::ofstream summary(
            results / "stage12_continuous_encoder_test_summary.csv");
        summary
            << "check,status\n"
               "block300_equivalence,PASS\n"
               "segmented_50x6_equivalence,PASS\n"
               "segmented_100x3_equivalence,PASS\n"
               "segmented_150x2_equivalence,PASS\n"
               "r12_r23_r34_coverage,PASS\n"
               "state_cross_slot,PASS\n"
               "puncture_phase_cross_slot,PASS\n"
               "tail_only_final_slot,PASS\n"
               "final_zero_state,PASS\n"
               "checkpoint_resume_every_slot,PASS\n"
               "negative_middle_tail,PASS\n"
               "stage_gate,PASS_STAGE12_CC_CONTINUOUS_ENCODER\n";
        std::cout << "PASS_STAGE12_CC_CONTINUOUS_ENCODER\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_STAGE12: " << error.what() << '\n';
        return 1;
    }
}
