#pragma once

#include "cc/trellis.hpp"

#include <cstddef>
#include <cstdint>
#include <vector>

namespace scl::cc {

struct SoftViterbiResult {
    std::vector<std::uint8_t> codec_input_bits;
    std::vector<std::uint8_t> payload_bits;
    double final_path_metric = 0.0;
    std::size_t normalization_count = 0;
    std::size_t tie_count = 0;
    std::size_t non_finite_metric_count = 0;
    std::uint8_t traceback_final_state = 0;
};

class SoftViterbiDecoder {
public:
    explicit SoftViterbiDecoder(const Trellis& trellis);

    SoftViterbiResult decode_terminated_symbols(
        const std::vector<double>& received_symbols,
        std::size_t codec_input_length,
        std::size_t tail_length = kMemory,
        std::uint8_t initial_state = 0,
        std::uint8_t final_state = 0) const;

    SoftViterbiResult decode_terminated_masked_symbols(
        const std::vector<double>& expanded_symbols,
        const std::vector<std::uint8_t>& observed_mask,
        std::size_t codec_input_length,
        std::size_t tail_length = kMemory,
        std::uint8_t initial_state = 0,
        std::uint8_t final_state = 0) const;

private:
    const Trellis& trellis_;
};

}  // namespace scl::cc
