#include "bch_segmented/bch15_segmented_adapter.hpp"

#include "bch_segmented/bch15_encoder.hpp"

#include <algorithm>
#include <stdexcept>

namespace scl::bch::segmented {
namespace {

const Bch15SegmentedConfig kS200{Bch15SegmentedCase::S200, "BCH-S200", 200U, 11U, 15U, 19U, 9U, 285U};
const Bch15SegmentedConfig kS300{Bch15SegmentedCase::S300, "BCH-S300", 300U, 11U, 15U, 28U, 8U, 420U};

void validateConfig(const Bch15SegmentedConfig& config) {
    if (config.blockPayloadLength != 11U || config.encodedBlockLength != 15U ||
        config.blockCount * config.blockPayloadLength != config.payloadLength + config.fillerBits ||
        config.blockCount * config.encodedBlockLength != config.encodedLength) {
        throw std::logic_error("BCH segmented frozen configuration mismatch");
    }
}

common::CodeLengths makeLengths(const Bch15SegmentedConfig& config) {
    common::CodeLengths lengths;
    lengths.payloadLength = config.payloadLength;
    lengths.codecInputLength = config.payloadLength + config.fillerBits;
    lengths.encodedLength = config.encodedLength;
    lengths.transmittedLength = config.encodedLength;
    lengths.fillerLength = config.fillerBits;
    return lengths;
}

void addBlockStatistics(Bch15SegmentedFrameDetail& frame, const Bch15DecodeDetail& detail) {
    ++frame.totalBlocks;
    if (detail.status == Bch15DecodeStatus::NO_ERROR) ++frame.noErrorBlocks;
    if (detail.status == Bch15DecodeStatus::CORRECTED_SINGLE_ERROR) ++frame.correctedBlocks;
    if (detail.lookupHit) {
        ++frame.lookupHitBlocks;
    } else if (detail.status == Bch15DecodeStatus::UNRECOGNIZED_SYNDROME) {
        // syndrome=0 follows the NO_ERROR path and is not a lookup miss.
        ++frame.lookupMissBlocks;
    }
    if (detail.status == Bch15DecodeStatus::POST_CHECK_FAILED) ++frame.postCheckFailedBlocks;
    if (detail.status == Bch15DecodeStatus::UNRECOGNIZED_SYNDROME) ++frame.unrecognizedSyndromeBlocks;
    if (detail.status == Bch15DecodeStatus::NO_ERROR || detail.status == Bch15DecodeStatus::CORRECTED_SINGLE_ERROR) ++frame.reportedSuccessBlocks;
    // True miscorrection requires the original block as an oracle.  The
    // adapter preserves decoder facts; the test audit compares them to truth.
}

}  // namespace

const Bch15SegmentedConfig& bch15SegmentedConfig(Bch15SegmentedCase caseId) {
    if (caseId == Bch15SegmentedCase::S200) return kS200;
    if (caseId == Bch15SegmentedCase::S300) return kS300;
    throw std::invalid_argument("unsupported BCH segmented case");
}

Bch15SegmentedEncodeResult encodeBch15Segmented(Bch15SegmentedCase caseId,
                                                  const common::BitVector& payloadBits) {
    const Bch15SegmentedConfig& config = bch15SegmentedConfig(caseId);
    validateConfig(config);
    if (payloadBits.size() != config.payloadLength) throw std::invalid_argument("payload length does not match BCH case");
    common::validateBits(payloadBits, "BCH segmented payload");

    Bch15SegmentedEncodeResult result{config, makeLengths(config), payloadBits, {}};
    result.paddedMessageBits.insert(result.paddedMessageBits.end(), config.fillerBits, 0U);
    result.encodedBits.reserve(config.encodedLength);
    for (common::Length block = 0U; block < config.blockCount; ++block) {
        const auto begin = result.paddedMessageBits.begin() + static_cast<std::ptrdiff_t>(block * config.blockPayloadLength);
        const common::BitVector message(begin, begin + static_cast<std::ptrdiff_t>(config.blockPayloadLength));
        const common::BitVector codeword = encodeBch15Systematic(message);
        result.encodedBits.insert(result.encodedBits.end(), codeword.begin(), codeword.end());
    }
    if (result.encodedBits.size() != config.encodedLength) throw std::logic_error("encoded length mismatch");
    static_cast<void>(common::computeCodeRate(result.lengths));
    return result;
}

Bch15SegmentedDecodeResult decodeBch15Segmented(Bch15SegmentedCase caseId,
                                                  const common::BitVector& receivedBits,
                                                  const SyndromeTable& table) {
    const Bch15SegmentedConfig& config = bch15SegmentedConfig(caseId);
    validateConfig(config);
    if (receivedBits.size() != config.encodedLength) throw std::invalid_argument("encoded length does not match BCH case");
    common::validateBits(receivedBits, "BCH segmented received bits");

    Bch15SegmentedDecodeResult result;
    result.config = config;
    result.frameDetail.paddingBits = config.fillerBits;
    result.frameDetail.blockCount = config.blockCount;
    result.blockDetails.reserve(config.blockCount);
    result.recoveredPaddedMessage.reserve(config.payloadLength + config.fillerBits);
    for (common::Length block = 0U; block < config.blockCount; ++block) {
        const auto begin = receivedBits.begin() + static_cast<std::ptrdiff_t>(block * config.encodedBlockLength);
        const common::BitVector received(begin, begin + static_cast<std::ptrdiff_t>(config.encodedBlockLength));
        Bch15DecodeDetail detail = decodeBch15Lookup(received, table);
        result.recoveredPaddedMessage.insert(result.recoveredPaddedMessage.end(), detail.decodedMessage.begin(), detail.decodedMessage.end());
        addBlockStatistics(result.frameDetail, detail);
        result.blockDetails.push_back({block, std::move(detail)});
    }
    result.recoveredPayload.assign(result.recoveredPaddedMessage.begin(), result.recoveredPaddedMessage.begin() + static_cast<std::ptrdiff_t>(config.payloadLength));
    return result;
}

void auditBch15SegmentedRecovery(const common::BitVector& originalPayload,
                                  Bch15SegmentedDecodeResult& result) {
    validateConfig(result.config);
    if (originalPayload.size() != result.config.payloadLength) {
        throw std::invalid_argument("original payload length does not match BCH decoded case");
    }
    common::validateBits(originalPayload, "BCH segmented original payload");
    if (result.blockDetails.size() != result.config.blockCount ||
        result.recoveredPaddedMessage.size() != result.config.payloadLength + result.config.fillerBits ||
        result.recoveredPayload.size() != result.config.payloadLength) {
        throw std::invalid_argument("decoded result shape does not match BCH case");
    }

    common::BitVector padded = originalPayload;
    padded.insert(padded.end(), result.config.fillerBits, 0U);
    result.frameDetail.paddedInformationCorrectBlocks = 0U;
    result.frameDetail.paddedInformationWrongBlocks = 0U;
    result.frameDetail.originalPayloadCorrectBlocks = 0U;
    result.frameDetail.originalPayloadWrongBlocks = 0U;
    result.frameDetail.fillerOnlyInformationMismatchBlocks = 0U;
    result.frameDetail.reportedSuccessWrongBlockInformation = 0U;
    result.frameDetail.reportedSuccessWrongOriginalPayload = 0U;
    result.frameDetail.miscorrectedBlocks = 0U;
    for (common::Length block = 0U; block < result.config.blockCount; ++block) {
        const auto begin = padded.begin() + static_cast<std::ptrdiff_t>(block * result.config.blockPayloadLength);
        const common::BitVector expected(begin, begin + static_cast<std::ptrdiff_t>(result.config.blockPayloadLength));
        const auto& detail = result.blockDetails[block].decoder;
        const bool paddedInformationCorrect = detail.decodedMessage == expected;
        const bool reportedSuccess = detail.status == Bch15DecodeStatus::NO_ERROR ||
                                     detail.status == Bch15DecodeStatus::CORRECTED_SINGLE_ERROR;
        if (paddedInformationCorrect) {
            ++result.frameDetail.paddedInformationCorrectBlocks;
        } else {
            ++result.frameDetail.paddedInformationWrongBlocks;
            if (reportedSuccess) ++result.frameDetail.reportedSuccessWrongBlockInformation;
            if (detail.status == Bch15DecodeStatus::CORRECTED_SINGLE_ERROR) {
                ++result.frameDetail.miscorrectedBlocks;
            }
        }

        const common::Length payloadBitsInBlock =
            block + 1U == result.config.blockCount
                ? result.config.blockPayloadLength - result.config.fillerBits
                : result.config.blockPayloadLength;
        const bool originalPayloadCorrect = std::equal(
            detail.decodedMessage.begin(),
            detail.decodedMessage.begin() + static_cast<std::ptrdiff_t>(payloadBitsInBlock),
            expected.begin());
        if (originalPayloadCorrect) {
            ++result.frameDetail.originalPayloadCorrectBlocks;
            if (!paddedInformationCorrect) {
                ++result.frameDetail.fillerOnlyInformationMismatchBlocks;
            }
        } else {
            ++result.frameDetail.originalPayloadWrongBlocks;
            if (reportedSuccess) ++result.frameDetail.reportedSuccessWrongOriginalPayload;
        }
    }
}

}  // namespace scl::bch::segmented
