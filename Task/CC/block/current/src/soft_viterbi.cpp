#include "cc/soft_viterbi.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace scl::cc {

namespace {

struct SoftSurvivor {
    std::uint8_t predecessor = 0;
    std::uint8_t input_bit = 0;
    bool valid = false;
};

bool better(
    double candidate,
    std::uint8_t predecessor,
    std::uint8_t input,
    double incumbent,
    const SoftSurvivor& survivor) {
    if (!survivor.valid || candidate < incumbent) {
        return true;
    }
    if (candidate > incumbent) {
        return false;
    }
    if (predecessor != survivor.predecessor) {
        return predecessor < survivor.predecessor;
    }
    return input < survivor.input_bit;
}

double symbol_for_bit(std::uint8_t bit) {
    return bit == 0 ? 1.0 : -1.0;
}

}  // namespace

SoftViterbiDecoder::SoftViterbiDecoder(const Trellis& trellis)
    : trellis_(trellis) {}

SoftViterbiResult SoftViterbiDecoder::decode_terminated_symbols(
    const std::vector<double>& received_symbols,
    const std::size_t codec_input_length,
    const std::size_t tail_length,
    const std::uint8_t initial_state,
    const std::uint8_t final_state) const {
    return decode_terminated_masked_symbols(
        received_symbols,
        std::vector<std::uint8_t>(received_symbols.size(), 1),
        codec_input_length,
        tail_length,
        initial_state,
        final_state);
}

SoftViterbiResult SoftViterbiDecoder::decode_terminated_masked_symbols(
    const std::vector<double>& received_symbols,
    const std::vector<std::uint8_t>& observed_mask,
    const std::size_t codec_input_length,
    const std::size_t tail_length,
    const std::uint8_t initial_state,
    const std::uint8_t final_state) const {
    if (initial_state >= kStateCount || final_state >= kStateCount) {
        throw std::invalid_argument("soft Viterbi state is outside [0, 63]");
    }
    if (codec_input_length < tail_length) {
        throw std::invalid_argument("soft Viterbi codec input is shorter than tail");
    }
    if (received_symbols.size() != codec_input_length * 2) {
        throw std::invalid_argument("soft Viterbi symbol length mismatch");
    }
    if (observed_mask.size() != received_symbols.size()) {
        throw std::invalid_argument("soft Viterbi observed mask length mismatch");
    }
    for (double value : received_symbols) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument("soft Viterbi received symbol is not finite");
        }
    }
    for (auto mask : observed_mask) {
        if (mask > 1) {
            throw std::invalid_argument("soft Viterbi observed mask is not binary");
        }
    }

    const double infinite = std::numeric_limits<double>::infinity();
    std::array<double, kStateCount> metrics{};
    std::array<double, kStateCount> next_metrics{};
    metrics.fill(infinite);
    metrics[initial_state] = 0.0;
    std::vector<SoftSurvivor> survivors(codec_input_length * kStateCount);
    SoftViterbiResult result;

    for (std::size_t time = 0; time < codec_input_length; ++time) {
        next_metrics.fill(infinite);
        auto* step = survivors.data() + time * kStateCount;
        std::fill(step, step + kStateCount, SoftSurvivor{});
        const double y0 = received_symbols[2 * time];
        const double y1 = received_symbols[2 * time + 1];

        for (std::size_t state = 0; state < kStateCount; ++state) {
            if (!std::isfinite(metrics[state])) {
                continue;
            }
            for (std::uint8_t input = 0; input < 2; ++input) {
                const auto& branch = trellis_.branch(static_cast<std::uint8_t>(state), input);
                const double d0 = y0 - symbol_for_bit(branch.output_bits[0]);
                const double d1 = y1 - symbol_for_bit(branch.output_bits[1]);
                const double candidate =
                    metrics[state] +
                    (observed_mask[2 * time] != 0 ? d0 * d0 : 0.0) +
                    (observed_mask[2 * time + 1] != 0 ? d1 * d1 : 0.0);
                if (!std::isfinite(candidate)) {
                    ++result.non_finite_metric_count;
                    continue;
                }
                auto& survivor = step[branch.next_state];
                if (survivor.valid && candidate == next_metrics[branch.next_state]) {
                    ++result.tie_count;
                }
                if (better(
                        candidate,
                        static_cast<std::uint8_t>(state),
                        input,
                        next_metrics[branch.next_state],
                        survivor)) {
                    next_metrics[branch.next_state] = candidate;
                    survivor.predecessor = static_cast<std::uint8_t>(state);
                    survivor.input_bit = input;
                    survivor.valid = true;
                }
            }
        }
        double minimum = infinite;
        for (double metric : next_metrics) {
            if (std::isfinite(metric) && metric < minimum) {
                minimum = metric;
            }
        }
        if (!std::isfinite(minimum)) {
            throw std::runtime_error("soft Viterbi has no finite reachable state");
        }
        for (double& metric : next_metrics) {
            if (std::isfinite(metric)) {
                metric -= minimum;
            }
        }
        ++result.normalization_count;
        metrics = next_metrics;
    }

    if (!std::isfinite(metrics[final_state])) {
        throw std::runtime_error("soft Viterbi final state is unreachable");
    }
    result.final_path_metric = metrics[final_state];
    result.traceback_final_state = final_state;
    result.codec_input_bits.resize(codec_input_length);
    std::uint8_t state = final_state;
    for (std::size_t time = codec_input_length; time > 0; --time) {
        const auto& survivor = survivors[(time - 1) * kStateCount + state];
        if (!survivor.valid) {
            throw std::runtime_error("invalid soft Viterbi survivor");
        }
        result.codec_input_bits[time - 1] = survivor.input_bit;
        state = survivor.predecessor;
    }
    if (state != initial_state) {
        throw std::runtime_error("soft Viterbi traceback initial state mismatch");
    }
    result.payload_bits.assign(
        result.codec_input_bits.begin(),
        result.codec_input_bits.end() - static_cast<std::ptrdiff_t>(tail_length));
    return result;
}

}  // namespace scl::cc
