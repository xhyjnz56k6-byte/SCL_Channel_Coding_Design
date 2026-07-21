#ifndef SCL_BCH_SEGMENTED_BCH15_SYNDROME_HPP
#define SCL_BCH_SEGMENTED_BCH15_SYNDROME_HPP
#include "bch_segmented/bch15_types.hpp"
namespace scl::bch::segmented { common::BitVector computeBch15Syndrome(const common::BitVector& received); unsigned syndromeValue(const common::BitVector& syndrome); }
#endif
