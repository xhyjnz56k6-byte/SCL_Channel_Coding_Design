#include "true_sliding_window_viterbi.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <limits>
#include <stdexcept>

namespace scl::cc::stage13 {
namespace {

struct Survivor {
    std::uint8_t predecessor = 0;
    std::uint8_t input = 0;
    bool valid = false;
};

double symbol(std::uint8_t bit) {
    return bit == 0 ? 1.0 : -1.0;
}

bool better(double candidate,
            std::uint8_t predecessor,
            std::uint8_t input,
            double incumbent,
            const Survivor& survivor) {
    if (!survivor.valid || candidate < incumbent) {
        return true;
    }
    if (candidate > incumbent) {
        return false;
    }
    if (predecessor != survivor.predecessor) {
        return predecessor < survivor.predecessor;
    }
    return input < survivor.input;
}

std::uint8_t best_state(
    const std::array<double, kStateCount>& metrics) {
    std::uint8_t selected = 0;
    for (std::size_t state = 1; state < kStateCount; ++state) {
        if (metrics[state] < metrics[selected]) {
            selected = static_cast<std::uint8_t>(state);
        }
    }
    return selected;
}

void normalize(std::array<double, kStateCount>& metrics) {
    const double infinite = std::numeric_limits<double>::infinity();
    double minimum = infinite;
    for (const double metric : metrics) {
        if (std::isfinite(metric) && metric < minimum) {
            minimum = metric;
        }
    }
    if (!std::isfinite(minimum)) {
        throw std::runtime_error("sliding window has no reachable state");
    }
    for (double& metric : metrics) {
        if (std::isfinite(metric)) {
            metric -= minimum;
        }
    }
}

}  // namespace

void validate_sliding_window_config(
    const SlidingWindowConfig& config,
    const std::size_t codec_input_length) {
    if (config.payload_bits + config.tail_bits != codec_input_length) {
        throw std::invalid_argument(
            "payload plus tail must equal codec input length");
    }
    if (config.window_bits == 0 || config.slide_bits == 0
        || config.traceback_depth == 0) {
        throw std::invalid_argument("W, S and D must be non-zero");
    }
    if (config.window_bits <= config.traceback_depth) {
        throw std::invalid_argument("W must be greater than D");
    }
    if (config.slide_bits
        > config.window_bits - config.traceback_depth) {
        throw std::invalid_argument("S must be no greater than W-D");
    }
    if (config.window_bits > codec_input_length) {
        throw std::invalid_argument(
            "W must not exceed terminated codec input length");
    }
}

SlidingWindowResult true_sliding_window_viterbi_scheduled(
    const Trellis& trellis,
    const std::vector<double>& received_symbols,
    const std::vector<std::uint8_t>& observed_mask,
    const SlidingWindowConfig& config,
    const std::vector<std::size_t>& available_codec_inputs_after_slot) {
    if (received_symbols.size() % kOutputBitsPerInput != 0
        || observed_mask.size() != received_symbols.size()) {
        throw std::invalid_argument("sliding window symbol/mask length mismatch");
    }
    const std::size_t codec_input_length =
        received_symbols.size() / kOutputBitsPerInput;
    validate_sliding_window_config(config, codec_input_length);
    if (available_codec_inputs_after_slot.empty()
        || available_codec_inputs_after_slot.back()
            != codec_input_length) {
        throw std::invalid_argument(
            "arrival schedule must end at codec input length");
    }
    std::size_t previous_available = 0;
    for (const std::size_t available :
         available_codec_inputs_after_slot) {
        if (available <= previous_available
            || available > codec_input_length) {
            throw std::invalid_argument(
                "arrival schedule must be strictly increasing");
        }
        previous_available = available;
    }
    for (const double value : received_symbols) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "sliding window received symbol is not finite");
        }
    }
    for (const std::uint8_t mask : observed_mask) {
        if (mask > 1) {
            throw std::invalid_argument("sliding window mask is not binary");
        }
    }

    const double infinite = std::numeric_limits<double>::infinity();
    std::array<double, kStateCount> start_metrics{};
    start_metrics.fill(infinite);
    start_metrics[kInitialState] = 0.0;

    std::vector<Survivor> survivors(
        config.window_bits * kStateCount);
    if (survivors.capacity() != survivors.size()) {
        throw std::runtime_error(
            "survivor allocation is not the exact W x 64 capacity");
    }

    SlidingWindowResult result;
    result.payload.reserve(config.payload_bits);
    result.emit_count_per_bit.assign(config.payload_bits, 0);
    result.decision_input_time.assign(config.payload_bits, 0);
    result.output_batch_index.assign(config.payload_bits, 0);
    result.survivor_slots = survivors.size();
    result.survivor_allocated_bytes =
        survivors.capacity() * sizeof(Survivor);
    result.path_metric_memory_bytes =
        3 * kStateCount * sizeof(double);

    std::size_t window_start = 0;
    std::size_t emitted = 0;
    for (const std::size_t available :
         available_codec_inputs_after_slot) {
      if (emitted == config.payload_bits) {
        break;
      }
      if (available < window_start) {
        throw std::logic_error("arrival precedes active window");
      }
      const std::size_t buffered_before_processing =
          available - window_start;
      result.peak_buffered_input_steps = std::max(
          result.peak_buffered_input_steps,
          buffered_before_processing);
      result.buffered_input_step_sum += buffered_before_processing;
      ++result.buffer_observations;
      const std::size_t windows_before_slot = result.window_count;
      while (emitted < config.payload_bits) {
        const std::size_t buffered = available - window_start;
        const bool final_window =
            available == codec_input_length
            && codec_input_length - window_start <= config.window_bits;
        if (!final_window && buffered < config.window_bits) {
            break;
        }
        if (window_start != emitted) {
            throw std::logic_error(
                "window start must equal first uncommitted payload bit");
        }
        const std::size_t window_end = final_window
            ? codec_input_length
            : window_start + config.window_bits;
        const std::size_t span = window_end - window_start;
        std::fill(survivors.begin(), survivors.end(), Survivor{});

        auto metrics = start_metrics;
        std::array<double, kStateCount> next{};
        std::array<double, kStateCount> metrics_after_slide{};
        std::array<double, kStateCount> metrics_at_decision{};
        const std::size_t decision_span = final_window
            ? span
            : std::min(span, config.slide_bits + config.traceback_depth);
        bool have_slide_metrics = false;
        bool have_decision_metrics = false;

        for (std::size_t local_time = 0; local_time < span; ++local_time) {
            next.fill(infinite);
            Survivor* const step =
                survivors.data() + local_time * kStateCount;
            const std::size_t global_time = window_start + local_time;
            const double y0 = received_symbols[2 * global_time];
            const double y1 = received_symbols[2 * global_time + 1];
            for (std::size_t state = 0; state < kStateCount; ++state) {
                if (!std::isfinite(metrics[state])) {
                    continue;
                }
                for (std::uint8_t input = 0; input < 2; ++input) {
                    const auto& branch = trellis.branch(
                        static_cast<std::uint8_t>(state), input);
                    const double d0 =
                        y0 - symbol(branch.output_bits[0]);
                    const double d1 =
                        y1 - symbol(branch.output_bits[1]);
                    const double candidate =
                        metrics[state]
                        + (observed_mask[2 * global_time] != 0
                               ? d0 * d0
                               : 0.0)
                        + (observed_mask[2 * global_time + 1] != 0
                               ? d1 * d1
                               : 0.0);
                    ++result.acs_count;
                    auto& survivor = step[branch.next_state];
                    if (better(candidate,
                               static_cast<std::uint8_t>(state),
                               input,
                               next[branch.next_state],
                               survivor)) {
                        next[branch.next_state] = candidate;
                        survivor = {
                            static_cast<std::uint8_t>(state), input, true};
                    }
                }
            }
            normalize(next);
            metrics = next;
            if (local_time + 1 == config.slide_bits) {
                metrics_after_slide = metrics;
                have_slide_metrics = true;
            }
            if (local_time + 1 == decision_span) {
                metrics_at_decision = metrics;
                have_decision_metrics = true;
            }
        }
        ++result.window_count;
        ++result.window_trigger_count;
        ++result.metric_boundary_inputs;
        ++result.metric_boundary_outputs;
        if (!have_decision_metrics) {
            throw std::logic_error("missing decision-boundary metrics");
        }

        const std::uint8_t terminal_state = final_window
            ? kInitialState
            : best_state(metrics_at_decision);
        std::vector<std::uint8_t> local_bits(decision_span);
        std::uint8_t state = terminal_state;
        for (std::size_t time = decision_span; time > 0; --time) {
            const Survivor& survivor =
                survivors[(time - 1) * kStateCount + state];
            if (!survivor.valid) {
                throw std::runtime_error(
                    "invalid bounded sliding-window survivor");
            }
            local_bits[time - 1] = survivor.input;
            state = survivor.predecessor;
            ++result.traceback_operations;
        }

        const std::size_t emit_now = final_window
            ? config.payload_bits - emitted
            : std::min(
                  config.slide_bits, config.payload_bits - emitted);
        if (emit_now > local_bits.size()) {
            throw std::logic_error("window cannot emit requested payload");
        }
        const std::size_t batch = result.output_batch_count++;
        result.output_batch_available_input_time.push_back(available - 1);
        const std::size_t decision_time =
            window_start + decision_span - 1;
        for (std::size_t offset = 0; offset < emit_now; ++offset) {
            const std::size_t payload_index = emitted + offset;
            result.payload.push_back(local_bits[offset]);
            ++result.emit_count_per_bit[payload_index];
            result.decision_input_time[payload_index] = decision_time;
            result.output_batch_index[payload_index] = batch;
        }
        emitted += emit_now;
        if (final_window) {
            result.final_flush_bits = emit_now;
            result.final_flush_pass = emitted == config.payload_bits;
            break;
        }
        if (!have_slide_metrics) {
            throw std::logic_error("missing slide-boundary metrics");
        }
        start_metrics = metrics_after_slide;
        window_start += config.slide_bits;
      }
      if (result.window_count > windows_before_slot) {
        ++result.slot_trigger_count;
      }
    }

    if (result.payload.size() != config.payload_bits) {
        throw std::runtime_error("sliding window output length mismatch");
    }
    for (const std::size_t count : result.emit_count_per_bit) {
        if (count == 0) {
            ++result.lost_bits;
        } else if (count > 1) {
            result.duplicate_bits += count - 1;
        }
    }
    if (result.lost_bits != 0 || result.duplicate_bits != 0
        || !result.final_flush_pass) {
        throw std::runtime_error(
            "sliding window lost/duplicate/final flush failure");
    }
    return result;
}

SlidingWindowResult true_sliding_window_viterbi(
    const Trellis& trellis,
    const std::vector<double>& received_symbols,
    const std::vector<std::uint8_t>& observed_mask,
    const SlidingWindowConfig& config) {
    return true_sliding_window_viterbi_scheduled(
        trellis,
        received_symbols,
        observed_mask,
        config,
        {received_symbols.size() / kOutputBitsPerInput});
}

}  // namespace scl::cc::stage13
