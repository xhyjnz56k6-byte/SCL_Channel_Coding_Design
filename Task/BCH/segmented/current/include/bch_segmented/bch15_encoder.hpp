#ifndef SCL_BCH_SEGMENTED_BCH15_ENCODER_HPP
#define SCL_BCH_SEGMENTED_BCH15_ENCODER_HPP

#include "bch_segmented/bch15_types.hpp"

namespace scl::bch::segmented {

common::BitVector encodeBch15Systematic(const common::BitVector& messageBits);

}  // namespace scl::bch::segmented

#endif  // SCL_BCH_SEGMENTED_BCH15_ENCODER_HPP
