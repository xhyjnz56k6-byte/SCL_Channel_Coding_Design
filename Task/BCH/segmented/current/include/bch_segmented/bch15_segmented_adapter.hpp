#ifndef SCL_BCH_SEGMENTED_BCH15_SEGMENTED_ADAPTER_HPP
#define SCL_BCH_SEGMENTED_BCH15_SEGMENTED_ADAPTER_HPP

#include "bch_segmented/bch15_lookup_decoder.hpp"

#include <string>
#include <vector>

namespace scl::bch::segmented {

enum class Bch15SegmentedCase { S200, S300 };

struct Bch15SegmentedConfig {
    Bch15SegmentedCase caseId;
    const char* name;
    common::Length payloadLength;
    common::Length blockPayloadLength;
    common::Length encodedBlockLength;
    common::Length blockCount;
    common::Length fillerBits;
    common::Length encodedLength;
};

struct Bch15SegmentedBlockDetail {
    common::Length blockIndex = 0U;
    Bch15DecodeDetail decoder;
};

struct Bch15SegmentedFrameDetail {
    common::Length totalBlocks = 0U;
    common::Length noErrorBlocks = 0U;
    common::Length correctedBlocks = 0U;
    common::Length lookupHitBlocks = 0U;
    common::Length lookupMissBlocks = 0U;
    common::Length postCheckFailedBlocks = 0U;
    common::Length unrecognizedSyndromeBlocks = 0U;
    common::Length reportedSuccessBlocks = 0U;
    // These compare each recovered 11-bit block with the padded encoder
    // input.  They intentionally include the terminal filler positions.
    common::Length paddedInformationCorrectBlocks = 0U;
    common::Length paddedInformationWrongBlocks = 0U;
    // These compare only the information positions that belong to the
    // original payload.  The terminal filler positions are excluded.
    common::Length originalPayloadCorrectBlocks = 0U;
    common::Length originalPayloadWrongBlocks = 0U;
    common::Length fillerOnlyInformationMismatchBlocks = 0U;
    common::Length reportedSuccessWrongBlockInformation = 0U;
    common::Length reportedSuccessWrongOriginalPayload = 0U;
    common::Length miscorrectedBlocks = 0U;
    common::Length paddingBits = 0U;
    common::Length blockCount = 0U;
};

struct Bch15SegmentedEncodeResult {
    Bch15SegmentedConfig config;
    common::CodeLengths lengths;
    common::BitVector paddedMessageBits;
    common::BitVector encodedBits;
};

struct Bch15SegmentedDecodeResult {
    Bch15SegmentedConfig config;
    common::BitVector recoveredPayload;
    common::BitVector recoveredPaddedMessage;
    std::vector<Bch15SegmentedBlockDetail> blockDetails;
    Bch15SegmentedFrameDetail frameDetail;
};

const Bch15SegmentedConfig& bch15SegmentedConfig(Bch15SegmentedCase caseId);
Bch15SegmentedEncodeResult encodeBch15Segmented(Bch15SegmentedCase caseId,
                                                  const common::BitVector& payloadBits);
Bch15SegmentedDecodeResult decodeBch15Segmented(Bch15SegmentedCase caseId,
                                                  const common::BitVector& receivedBits,
                                                  const SyndromeTable& table);
void auditBch15SegmentedRecovery(const common::BitVector& originalPayload,
                                  Bch15SegmentedDecodeResult& result);

}  // namespace scl::bch::segmented

#endif
