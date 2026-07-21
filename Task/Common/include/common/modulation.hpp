#ifndef SCL_COMMON_MODULATION_HPP
#define SCL_COMMON_MODULATION_HPP

#include "common/types.hpp"

namespace scl::common {

double bpskSymbol(Bit bit);
RealVector bpskModulate(const BitVector& bits);

}  // namespace scl::common

#endif  // SCL_COMMON_MODULATION_HPP
