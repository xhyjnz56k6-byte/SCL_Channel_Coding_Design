#ifndef SCL_BCH_SEGMENTED_BCH15_TYPES_HPP
#define SCL_BCH_SEGMENTED_BCH15_TYPES_HPP

#include "common/types.hpp"

namespace scl::bch::segmented {

constexpr common::Length kBch15MessageLength = 11U;
constexpr common::Length kBch15ParityLength = 4U;
constexpr common::Length kBch15CodewordLength = 15U;

}  // namespace scl::bch::segmented

#endif  // SCL_BCH_SEGMENTED_BCH15_TYPES_HPP
