#include "cc/hard_viterbi.hpp"

#include <algorithm>
#include <array>
#include <limits>
#include <stdexcept>

namespace scl::cc {

namespace {

constexpr std::int32_t kInfiniteMetric = std::numeric_limits<std::int32_t>::max() / 8;

struct Survivor {
    std::uint8_t predecessor = 0;
    std::uint8_t input_bit = 0;
    bool valid = false;
};

bool better_candidate(
    const std::int32_t candidate_metric,
    const std::uint8_t candidate_predecessor,
    const std::uint8_t candidate_input,
    const std::int32_t incumbent_metric,
    const Survivor& incumbent) {
    if (!incumbent.valid || candidate_metric < incumbent_metric) {
        return true;
    }
    if (candidate_metric > incumbent_metric) {
        return false;
    }
    if (candidate_predecessor != incumbent.predecessor) {
        return candidate_predecessor < incumbent.predecessor;
    }
    return candidate_input < incumbent.input_bit;
}

}  // namespace

HardViterbiDecoder::HardViterbiDecoder(const Trellis& trellis)
    : trellis_(trellis) {}

HardViterbiResult HardViterbiDecoder::decode_terminated_mother(
    const std::vector<std::uint8_t>& received_bits,
    const std::size_t codec_input_length,
    const std::size_t tail_length,
    const std::uint8_t initial_state,
    const std::uint8_t final_state) const {
    return decode_terminated_masked(
        received_bits,
        std::vector<std::uint8_t>(received_bits.size(), 1),
        codec_input_length,
        tail_length,
        initial_state,
        final_state);
}

HardViterbiResult HardViterbiDecoder::decode_terminated_masked(
    const std::vector<std::uint8_t>& received_bits,
    const std::vector<std::uint8_t>& observed_mask,
    const std::size_t codec_input_length,
    const std::size_t tail_length,
    const std::uint8_t initial_state,
    const std::uint8_t final_state) const {
    if (initial_state >= kStateCount || final_state >= kStateCount) {
        throw std::invalid_argument("Viterbi state is outside [0, 63]");
    }
    if (codec_input_length < tail_length) {
        throw std::invalid_argument("codec input length is smaller than tail length");
    }
    if (received_bits.size() != codec_input_length * kOutputBitsPerInput) {
        throw std::invalid_argument("hard Viterbi input length mismatch");
    }
    if (observed_mask.size() != received_bits.size()) {
        throw std::invalid_argument("hard Viterbi observed mask length mismatch");
    }
    for (const auto bit : received_bits) {
        if (bit > 1) {
            throw std::invalid_argument("hard Viterbi input is not binary");
        }
    }
    for (const auto mask : observed_mask) {
        if (mask > 1) {
            throw std::invalid_argument("hard Viterbi observed mask is not binary");
        }
    }

    std::array<std::int32_t, kStateCount> metrics{};
    std::array<std::int32_t, kStateCount> next_metrics{};
    metrics.fill(kInfiniteMetric);
    metrics[initial_state] = 0;
    std::vector<Survivor> survivors(codec_input_length * kStateCount);

    HardViterbiResult result;
    for (std::size_t time = 0; time < codec_input_length; ++time) {
        next_metrics.fill(kInfiniteMetric);
        auto* step_survivors = survivors.data() + time * kStateCount;
        std::fill(step_survivors, step_survivors + kStateCount, Survivor{});

        const std::uint8_t observed0 = received_bits[2 * time];
        const std::uint8_t observed1 = received_bits[2 * time + 1];
        for (std::size_t state = 0; state < kStateCount; ++state) {
            if (metrics[state] >= kInfiniteMetric) {
                continue;
            }
            for (std::uint8_t input = 0; input < 2; ++input) {
                const auto& branch = trellis_.branch(static_cast<std::uint8_t>(state), input);
                const std::int32_t branch_metric =
                    static_cast<std::int32_t>(observed_mask[2 * time] != 0 && observed0 != branch.output_bits[0]) +
                    static_cast<std::int32_t>(observed_mask[2 * time + 1] != 0 && observed1 != branch.output_bits[1]);
                if (metrics[state] > kInfiniteMetric - branch_metric) {
                    ++result.overflow_count;
                    continue;
                }
                const std::int32_t candidate = metrics[state] + branch_metric;
                auto& survivor = step_survivors[branch.next_state];
                if (survivor.valid && candidate == next_metrics[branch.next_state]) {
                    ++result.tie_count;
                }
                if (better_candidate(
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

        const auto minimum = *std::min_element(next_metrics.begin(), next_metrics.end());
        if (minimum >= kInfiniteMetric) {
            throw std::runtime_error("hard Viterbi has no reachable state");
        }
        for (auto& metric : next_metrics) {
            if (metric < kInfiniteMetric) {
                metric -= minimum;
            }
        }
        ++result.normalization_count;
        metrics = next_metrics;
    }

    if (metrics[final_state] >= kInfiniteMetric) {
        throw std::runtime_error("requested hard Viterbi final state is unreachable");
    }
    result.final_path_metric = metrics[final_state];
    result.traceback_final_state = final_state;
    result.codec_input_bits.resize(codec_input_length);
    std::uint8_t state = final_state;
    for (std::size_t time = codec_input_length; time > 0; --time) {
        const Survivor& survivor = survivors[(time - 1) * kStateCount + state];
        if (!survivor.valid) {
            throw std::runtime_error("invalid survivor during hard Viterbi traceback");
        }
        result.codec_input_bits[time - 1] = survivor.input_bit;
        state = survivor.predecessor;
    }
    if (state != initial_state) {
        throw std::runtime_error("hard Viterbi traceback did not reach initial state");
    }
    result.payload_bits.assign(
        result.codec_input_bits.begin(),
        result.codec_input_bits.end() - static_cast<std::ptrdiff_t>(tail_length));
    return result;
}

}  // namespace scl::cc
