#ifndef SCL_COMMON_DEMODULATION_HPP
#define SCL_COMMON_DEMODULATION_HPP

#include "common/types.hpp"

namespace scl::common {

Bit hardDecisionBit(double received);
BitVector hardDecision(const RealVector& received);
double llrValue(double received, double sigma);
RealVector computeLlr(const RealVector& received, double sigma);
Bit llrSignDecisionBit(double llr);
BitVector llrSignDecision(const RealVector& llr);

}  // namespace scl::common

#endif  // SCL_COMMON_DEMODULATION_HPP
