#ifndef SCL_BCH_SEGMENTED_BCH15_LOOKUP_DECODER_HPP
#define SCL_BCH_SEGMENTED_BCH15_LOOKUP_DECODER_HPP
#include "bch_segmented/bch15_lookup_table.hpp"
namespace scl::bch::segmented { enum class Bch15DecodeStatus{NO_ERROR,CORRECTED_SINGLE_ERROR,POST_CHECK_FAILED,UNRECOGNIZED_SYNDROME}; struct Bch15DecodeDetail{common::BitVector decodedMessage,correctedCodeword,syndromeBefore,syndromeAfter;int correctedPosition=-1;bool lookupHit=false;Bch15DecodeStatus status=Bch15DecodeStatus::NO_ERROR;}; Bch15DecodeDetail decodeBch15Lookup(const common::BitVector&,const SyndromeTable&); }
#endif
