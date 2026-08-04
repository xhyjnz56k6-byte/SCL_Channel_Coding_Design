#include "bch_segmented/bch15_syndrome.hpp"
#include <stdexcept>
namespace scl::bch::segmented {
common::BitVector computeBch15Syndrome(const common::BitVector& received,
                                       Bch15SyndromeMetrics* metrics) {
    if (received.size() != 15U) throw std::invalid_argument("BCH15 received length");
    common::validateBits(received, "received");
    if (metrics != nullptr) ++metrics->calculationCount;
    auto work = received;
    for (unsigned i = 0; i < 11U; ++i) {
        if (metrics != nullptr) ++metrics->bitTestCount;
        if (work[i] == 0U) continue;
        work[i] ^= 1U;
        work[i + 3U] ^= 1U;
        work[i + 4U] ^= 1U;
        if (metrics != nullptr) {
            metrics->xorCount += 3U;
            ++metrics->shiftCount;
        }
    }
    return common::BitVector(work.end() - 4, work.end());
}
unsigned syndromeValue(const common::BitVector& syndrome) {
    if (syndrome.size() != 4U) throw std::invalid_argument("syndrome length");
    common::validateBits(syndrome, "syndrome");
    return (syndrome[0] << 3U) | (syndrome[1] << 2U) | (syndrome[2] << 1U) | syndrome[3];
}
}
