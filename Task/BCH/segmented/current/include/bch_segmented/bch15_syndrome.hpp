#ifndef SCL_BCH_SEGMENTED_BCH15_SYNDROME_HPP
#define SCL_BCH_SEGMENTED_BCH15_SYNDROME_HPP
#include "bch_segmented/bch15_types.hpp"
#include <cstdint>
namespace scl::bch::segmented {
struct Bch15SyndromeMetrics {
    std::uint64_t calculationCount = 0U;
    std::uint64_t bitTestCount = 0U;
    std::uint64_t xorCount = 0U;
    std::uint64_t shiftCount = 0U;
};
common::BitVector computeBch15Syndrome(const common::BitVector& received,
                                       Bch15SyndromeMetrics* metrics = nullptr);
unsigned syndromeValue(const common::BitVector& syndrome);
}
#endif
