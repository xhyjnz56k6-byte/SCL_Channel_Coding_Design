#ifndef SCL_COMMON_AWGN_CHANNEL_HPP
#define SCL_COMMON_AWGN_CHANNEL_HPP

#include "common/types.hpp"

namespace scl::common {

double ebN0Linear(double ebN0_dB);
double computeAwgnSigma(const CodeLengths& lengths, double ebN0_dB);
RealVector applyAwgn(const RealVector& symbols, const RealVector& standardNoise, double sigma);

}  // namespace scl::common

#endif  // SCL_COMMON_AWGN_CHANNEL_HPP
