#include "bch_segmented/bch15_lookup_decoder.hpp"

#include <stdexcept>

namespace scl::bch::segmented {

Bch15DecodeDetail decodeBch15Lookup(const common::BitVector& received,
                                     const SyndromeTable& table) {
    if (received.size() != 15U) {
        throw std::invalid_argument("BCH15 decode input length must be 15");
    }
    common::validateBits(received, "received");

    Bch15DecodeDetail detail;
    detail.correctedCodeword = received;
    detail.syndromeBefore = computeBch15Syndrome(received);

    const unsigned syndrome = syndromeValue(detail.syndromeBefore);
    const int position = lookupErrorPosition(table, syndrome);

    if (position < 0) {
        detail.status = syndrome == 0U ? Bch15DecodeStatus::NO_ERROR
                                       : Bch15DecodeStatus::UNRECOGNIZED_SYNDROME;
        detail.syndromeAfter = detail.syndromeBefore;
    } else {
        detail.lookupHit = true;
        detail.correctedPosition = position;

        // A caller may supply an externally corrupted table.  Do not index a
        // received codeword unless the table position is within BCH(15,11,1).
        if (position < 15) {
            detail.correctedCodeword[static_cast<std::size_t>(position)] ^= 1U;
            detail.syndromeAfter = computeBch15Syndrome(detail.correctedCodeword);
            detail.status = syndromeValue(detail.syndromeAfter) == 0U
                                ? Bch15DecodeStatus::CORRECTED_SINGLE_ERROR
                                : Bch15DecodeStatus::POST_CHECK_FAILED;
        } else {
            detail.syndromeAfter = detail.syndromeBefore;
            detail.status = Bch15DecodeStatus::POST_CHECK_FAILED;
        }
    }

    detail.decodedMessage = common::BitVector(detail.correctedCodeword.begin(),
                                               detail.correctedCodeword.begin() + 11);
    return detail;
}

}  // namespace scl::bch::segmented
