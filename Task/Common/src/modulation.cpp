#include "common/modulation.hpp"

namespace scl::common {

double bpskSymbol(Bit bit) {
    validateBit(bit, "bpsk bit");
    return bit == 0U ? 1.0 : -1.0;
}

RealVector bpskModulate(const BitVector& bits) {
    validateBits(bits, "bpsk bits");
    RealVector symbols(bits.size());
    for (std::size_t i = 0; i < bits.size(); ++i) {
        symbols[i] = bpskSymbol(bits[i]);
    }
    return symbols;
}

}  // namespace scl::common
