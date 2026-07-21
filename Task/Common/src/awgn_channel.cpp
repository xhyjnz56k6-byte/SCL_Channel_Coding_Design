#include "common/awgn_channel.hpp"

#include <cmath>
#include <stdexcept>

namespace scl::common {

double ebN0Linear(double ebN0_dB) {
    if (!std::isfinite(ebN0_dB)) {
        throw std::invalid_argument("ebN0_dB must be finite");
    }
    return std::pow(10.0, ebN0_dB / 10.0);
}

double computeAwgnSigma(const CodeLengths& lengths, double ebN0_dB) {
    const double rate = computeCodeRate(lengths);
    const double linear = ebN0Linear(ebN0_dB);
    const double sigma = std::sqrt(1.0 / (2.0 * rate * linear));
    if (!std::isfinite(sigma) || sigma <= 0.0) {
        throw std::invalid_argument("invalid AWGN sigma");
    }
    return sigma;
}

RealVector applyAwgn(const RealVector& symbols, const RealVector& standardNoise, double sigma) {
    if (symbols.size() != standardNoise.size()) {
        throw std::invalid_argument("AWGN symbol/noise length mismatch");
    }
    if (!std::isfinite(sigma) || sigma < 0.0) {
        throw std::invalid_argument("sigma must be finite and non-negative");
    }
    RealVector received(symbols.size());
    for (std::size_t i = 0; i < symbols.size(); ++i) {
        received[i] = symbols[i] + sigma * standardNoise[i];
    }
    return received;
}

}  // namespace scl::common
