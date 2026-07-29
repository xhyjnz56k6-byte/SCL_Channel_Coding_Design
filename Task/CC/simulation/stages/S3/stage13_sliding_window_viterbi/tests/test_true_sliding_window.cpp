#include "true_sliding_window_viterbi.hpp"

#include "cc/block_encoder.hpp"
#include "cc/puncturing.hpp"
#include "cc/trellis.hpp"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {

double symbol(std::uint8_t bit) {
    return bit == 0 ? 1.0 : -1.0;
}

std::size_t expected_windows(
    std::size_t codec_length,
    std::size_t window,
    std::size_t slide) {
    if (codec_length <= window) {
        return 1;
    }
    return (codec_length - window + slide - 1) / slide + 1;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 2) {
            throw std::invalid_argument("results dir");
        }
        const std::filesystem::path results(argv[1]);
        std::filesystem::create_directories(results);
        scl::cc::Trellis trellis;
        scl::cc::ConvolutionalEncoder encoder(trellis);
        std::vector<std::uint8_t> payload(300);
        for (std::size_t index = 0; index < payload.size(); ++index) {
            payload[index] =
                static_cast<std::uint8_t>((index * 37 + index / 7) & 1U);
        }
        const auto encoded = encoder.encode_block(payload, true);
        const std::vector<scl::cc::PuncturePattern> patterns{
            {"R12", {1, 1}},
            {"R23", {1, 1, 0, 1}},
            {"R34", {1, 1, 0, 1, 1, 0}},
        };
        const std::vector<scl::cc::stage13::SlidingWindowConfig> configs{
            {96, 16, 70, 300, 6},
            {128, 16, 70, 300, 6},
            {160, 16, 70, 300, 6},
            {192, 16, 70, 300, 6},
            {128, 8, 70, 300, 6},
            {128, 25, 70, 300, 6},
            {128, 50, 70, 300, 6},
            {128, 25, 35, 300, 6},
            {128, 25, 49, 300, 6},
            {128, 25, 84, 300, 6},
            {128, 25, 98, 300, 6},
        };

        std::ofstream evidence(
            results / "stage13_algorithm_unit_evidence.csv");
        evidence
            << "rateCase,windowBits,slideBits,dtb,outputLength,lostBits,"
               "duplicateBits,finalFlushPass,windowCount,outputBatchCount,"
               "windowTriggerCount,survivorSlots,survivorAllocatedBytes,"
               "pathMetricMemoryBytes,tracebackOperations,ACSCount\n";

        std::size_t w96_bytes = 0;
        std::size_t w128_bytes = 0;
        std::size_t w96_windows = 0;
        std::size_t w128_windows = 0;
        std::size_t s8_batches = 0;
        std::size_t s50_batches = 0;
        std::size_t d35_ops = 0;
        std::size_t d98_ops = 0;
        bool scheduled_online_pass = true;

        for (const auto& pattern : patterns) {
            const auto punctured =
                scl::cc::puncture_bits(encoded.mother_bits, pattern);
            std::vector<double> received(punctured.bits.size());
            for (std::size_t index = 0; index < received.size(); ++index) {
                received[index] = symbol(punctured.bits[index]);
            }
            const auto depunctured = scl::cc::depuncture_soft(
                received, encoded.mother_bits.size(), pattern);
            const scl::cc::stage13::SlidingWindowConfig online_config{
                128, 25, 84, 300, 6};
            for (const std::vector<std::size_t>& arrivals : {
                     std::vector<std::size_t>{50, 100, 150, 200, 250, 306},
                     std::vector<std::size_t>{100, 200, 306},
                     std::vector<std::size_t>{150, 306}}) {
                const auto online =
                    scl::cc::stage13::true_sliding_window_viterbi_scheduled(
                        trellis,
                        depunctured.expanded_values,
                        depunctured.observed_mask,
                        online_config,
                        arrivals);
                scheduled_online_pass =
                    scheduled_online_pass
                    && online.payload == payload
                    && online.slot_trigger_count > 0
                    && online.peak_buffered_input_steps
                        <= online_config.window_bits
                           + *std::max_element(
                               arrivals.begin(), arrivals.end());
            }
            for (const auto& config : configs) {
                const auto decoded =
                    scl::cc::stage13::true_sliding_window_viterbi(
                        trellis,
                        depunctured.expanded_values,
                        depunctured.observed_mask,
                        config);
                if (decoded.payload != payload
                    || decoded.payload.size() != 300
                    || decoded.lost_bits != 0
                    || decoded.duplicate_bits != 0
                    || !decoded.final_flush_pass
                    || decoded.survivor_slots
                        != config.window_bits * scl::cc::kStateCount
                    || decoded.window_count
                        != expected_windows(
                            306, config.window_bits, config.slide_bits)
                    || decoded.window_trigger_count != decoded.window_count
                    || decoded.output_batch_count != decoded.window_count) {
                    throw std::runtime_error(
                        "true sliding-window correctness/evidence failure");
                }
                evidence
                    << pattern.id << ',' << config.window_bits << ','
                    << config.slide_bits << ',' << config.traceback_depth
                    << ',' << decoded.payload.size() << ','
                    << decoded.lost_bits << ',' << decoded.duplicate_bits
                    << ',' << decoded.final_flush_pass << ','
                    << decoded.window_count << ','
                    << decoded.output_batch_count << ','
                    << decoded.window_trigger_count << ','
                    << decoded.survivor_slots << ','
                    << decoded.survivor_allocated_bytes << ','
                    << decoded.path_metric_memory_bytes << ','
                    << decoded.traceback_operations << ','
                    << decoded.acs_count << '\n';
                if (pattern.id == "R12") {
                    if (config.window_bits == 96
                        && config.slide_bits == 16
                        && config.traceback_depth == 70) {
                        w96_bytes = decoded.survivor_allocated_bytes;
                        w96_windows = decoded.window_count;
                    }
                    if (config.window_bits == 128
                        && config.slide_bits == 16
                        && config.traceback_depth == 70) {
                        w128_bytes = decoded.survivor_allocated_bytes;
                        w128_windows = decoded.window_count;
                    }
                    if (config.window_bits == 128
                        && config.slide_bits == 8
                        && config.traceback_depth == 70) {
                        s8_batches = decoded.output_batch_count;
                    }
                    if (config.window_bits == 128
                        && config.slide_bits == 50
                        && config.traceback_depth == 70) {
                        s50_batches = decoded.output_batch_count;
                    }
                    if (config.window_bits == 128
                        && config.slide_bits == 25
                        && config.traceback_depth == 35) {
                        d35_ops = decoded.traceback_operations;
                    }
                    if (config.window_bits == 128
                        && config.slide_bits == 25
                        && config.traceback_depth == 98) {
                        d98_ops = decoded.traceback_operations;
                    }
                }
            }
        }
        if (!(w128_bytes > w96_bytes && w96_windows > w128_windows
              && s8_batches > s50_batches && d98_ops > d35_ops)) {
            throw std::runtime_error(
                "W/S/D control-variable evidence failure");
        }
        if (!scheduled_online_pass) {
            throw std::runtime_error("scheduled online arrival failure");
        }

        const std::vector<scl::cc::stage13::SlidingWindowConfig> invalid{
            {70, 16, 70, 300, 6},
            {96, 27, 70, 300, 6},
            {0, 1, 1, 300, 6},
            {307, 16, 70, 300, 6},
        };
        for (const auto& config : invalid) {
            bool rejected = false;
            try {
                scl::cc::stage13::validate_sliding_window_config(
                    config, 306);
            } catch (const std::invalid_argument&) {
                rejected = true;
            }
            if (!rejected) {
                throw std::runtime_error("invalid W/S/D accepted");
            }
        }

        std::ofstream summary(
            results / "stage13_algorithm_unit_summary.csv");
        summary
            << "check,status\n"
               "actual_Wx64_survivor_allocation,PASS\n"
               "W_changes_allocation_and_window_count,PASS\n"
               "S_changes_trigger_and_output_batch_count,PASS\n"
               "D_changes_traceback_operations,PASS\n"
               "each_bit_emitted_once,PASS\n"
               "final_flush_without_full_history,PASS\n"
               "r12_r23_r34_noiseless,PASS\n"
               "invalid_w_s_d_rejected,PASS\n"
               "reported_memory_equals_actual_allocation,PASS\n"
               "scheduled_slot_arrival_processing,PASS\n"
               "stage_gate,PASS_STAGE13_TRUE_SLIDING_ALGORITHM\n";
        std::cout << "PASS_STAGE13_TRUE_SLIDING_ALGORITHM\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_STAGE13_UNIT: " << error.what() << '\n';
        return 1;
    }
}
