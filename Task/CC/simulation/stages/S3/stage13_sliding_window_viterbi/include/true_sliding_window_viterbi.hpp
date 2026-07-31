#pragma once

#include "cc/trellis.hpp"

#include <cstddef>
#include <cstdint>
#include <vector>

namespace scl::cc::stage13 {

struct SlidingWindowConfig {
    std::size_t window_bits = 0;
    std::size_t slide_bits = 0;
    std::size_t traceback_depth = 0;
    std::size_t payload_bits = 300;
    std::size_t tail_bits = kMemory;
};

struct SlidingWindowResult {
    std::vector<std::uint8_t> payload;
    std::vector<std::size_t> emit_count_per_bit;
    std::vector<std::size_t> decision_input_time;
    std::vector<std::size_t> output_batch_index;
    std::vector<std::size_t> output_batch_available_input_time;
    std::size_t window_count = 0;
    std::size_t window_trigger_count = 0;
    std::size_t slot_trigger_count = 0;
    std::size_t output_batch_count = 0;
    std::size_t final_flush_bits = 0;
    std::size_t survivor_slots = 0;
    std::size_t survivor_allocated_bytes = 0;
    std::size_t path_metric_memory_bytes = 0;
    std::size_t acs_count = 0;
    std::size_t traceback_operations = 0;
    std::size_t metric_boundary_inputs = 0;
    std::size_t metric_boundary_outputs = 0;
    std::size_t peak_buffered_input_steps = 0;
    std::size_t buffered_input_step_sum = 0;
    std::size_t buffer_observations = 0;
    std::size_t lost_bits = 0;
    std::size_t duplicate_bits = 0;
    bool final_flush_pass = false;
};

void validate_sliding_window_config(
    const SlidingWindowConfig& config,
    std::size_t codec_input_length);

SlidingWindowResult true_sliding_window_viterbi(
    const Trellis& trellis,
    const std::vector<double>& received_symbols,
    const std::vector<std::uint8_t>& observed_mask,
    const SlidingWindowConfig& config);

SlidingWindowResult true_sliding_window_viterbi_scheduled(
    const Trellis& trellis,
    const std::vector<double>& received_symbols,
    const std::vector<std::uint8_t>& observed_mask,
    const SlidingWindowConfig& config,
    const std::vector<std::size_t>& available_codec_inputs_after_slot);

}  // namespace scl::cc::stage13
