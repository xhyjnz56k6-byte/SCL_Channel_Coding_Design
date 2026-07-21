#include "common/demodulation.hpp"

#include <cmath>
#include <stdexcept>

namespace scl::common {

Bit hardDecisionBit(double received) {
    if (!std::isfinite(received)) {
        throw std::invalid_argument("received value must be finite");
    }
    return received >= 0.0 ? static_cast<Bit>(0U) : static_cast<Bit>(1U);
}

BitVector hardDecision(const RealVector& received) {
    BitVector bits(received.size());
    for (std::size_t i = 0; i < received.size(); ++i) {
        bits[i] = hardDecisionBit(received[i]);
    }
    return bits;
}

double llrValue(double received, double sigma) {
    if (!std::isfinite(received) || !std::isfinite(sigma) || sigma <= 0.0) {
        throw std::invalid_argument("invalid LLR input");
    }
    return 2.0 * received / (sigma * sigma);
}

RealVector computeLlr(const RealVector& received, double sigma) {
    RealVector llr(received.size());
    for (std::size_t i = 0; i < received.size(); ++i) {
        llr[i] = llrValue(received[i], sigma);
    }
    return llr;
}

Bit llrSignDecisionBit(double llr) {
    if (!std::isfinite(llr)) {
        throw std::invalid_argument("LLR must be finite");
    }
    return llr >= 0.0 ? static_cast<Bit>(0U) : static_cast<Bit>(1U);
}

BitVector llrSignDecision(const RealVector& llr) {
    BitVector bits(llr.size());
    for (std::size_t i = 0; i < llr.size(); ++i) {
        bits[i] = llrSignDecisionBit(llr[i]);
    }
    return bits;
}

}  // namespace scl::common
