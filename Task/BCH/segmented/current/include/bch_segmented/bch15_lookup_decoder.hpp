#ifndef SCL_BCH_SEGMENTED_BCH15_LOOKUP_DECODER_HPP
#define SCL_BCH_SEGMENTED_BCH15_LOOKUP_DECODER_HPP

#include "bch_segmented/bch15_lookup_table.hpp"

namespace scl::bch::segmented {

enum class Bch15DecodeStatus {
    NO_ERROR,
    CORRECTED_SINGLE_ERROR,
    POST_CHECK_FAILED,
    UNRECOGNIZED_SYNDROME
};

struct Bch15DecodeDetail {
    common::BitVector decodedMessage;
    common::BitVector correctedCodeword;
    common::BitVector syndromeBefore;
    common::BitVector syndromeAfter;
    int correctedPosition = -1;
    bool lookupHit = false;
    std::uint64_t initialSyndromeCount = 0U;
    std::uint64_t nonzeroSyndromeCount = 0U;
    std::uint64_t tableLookupCount = 0U;
    std::uint64_t lookupHitCount = 0U;
    std::uint64_t lookupMissCount = 0U;
    std::uint64_t bitFlipCount = 0U;
    std::uint64_t postSyndromeCheckCount = 0U;
    Bch15SyndromeMetrics syndromeMetrics;
    Bch15DecodeStatus status = Bch15DecodeStatus::NO_ERROR;
};

Bch15DecodeDetail decodeBch15Lookup(const common::BitVector& received,
                                     const SyndromeTable& table);

}  // namespace scl::bch::segmented

#endif
