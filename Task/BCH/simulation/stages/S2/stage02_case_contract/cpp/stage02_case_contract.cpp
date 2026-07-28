#include "stage02_case_contract.hpp"

#include "bch_block/bch_block.hpp"
#include "bch_segmented/bch15_lookup_table.hpp"
#include "bch_segmented/bch15_segmented_adapter.hpp"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>

namespace scl::bch::s2::stage02 {
namespace {

using block::BlockBchProfile;

PlotStyle style(const char* id, const char* color, const char* line, const char* marker) {
    return {id, color, line, marker};
}

CaseContract makeContract(
    CaseId id, const char* caseId, const char* displayName, std::size_t payloadLength,
    std::size_t motherN, std::size_t motherK, unsigned motherT, const char* decoder,
    Organization organization, std::vector<std::size_t> payloadPerBlock,
    std::vector<std::size_t> fillerPerBlock, std::vector<std::size_t> shorteningPerBlock,
    std::vector<std::size_t> encodedLengthPerBlock, const char* legend, PlotStyle plotStyle) {
    const std::size_t totalEncoded = std::accumulate(
        encodedLengthPerBlock.begin(), encodedLengthPerBlock.end(), std::size_t{0U});
    return {
        id, caseId, displayName, payloadLength, motherN, motherK, motherT, decoder, organization,
        payloadPerBlock.size(), std::move(payloadPerBlock), std::move(fillerPerBlock),
        std::move(shorteningPerBlock), std::move(encodedLengthPerBlock), totalEncoded,
        static_cast<double>(payloadLength) / static_cast<double>(totalEncoded),
        "BLOCK_ASCENDING_PAYLOAD_CONCATENATION",
        "INDEX_0_HIGHEST_DEGREE;SYSTEMATIC_PAYLOAD_THEN_PARITY",
        "GENERATOR_DESCENDING_DEGREE",
        organization == Organization::Segmented15
            ? "NO_SHORTENING;FINAL_INFORMATION_FILLER_IS_ZERO_AND_REMOVED_AFTER_DECODE"
            : "PREPEND_KNOWN_ZERO_INFORMATION_BITS_AND_DO_NOT_TRANSMIT_PREFIX",
        legend, std::move(plotStyle),
        "FRAME_ERROR_IF_ANY_RECOVERED_PAYLOAD_BIT_DIFFERS",
        "ONE_FRAME_DECODE_ELAPSED_TIME_INCLUDING_ALL_BLOCKS"
    };
}

const std::vector<CaseContract> kContracts{
    makeContract(CaseId::K200_S15, "K200_S15", "BCH15分块200", 200U, 15U, 11U, 1U,
                 "SYNDROME_LOOKUP", Organization::Segmented15,
                 {11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,2U},
                 {0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,9U},
                 std::vector<std::size_t>(19U, 0U), std::vector<std::size_t>(19U, 15U),
                 "分块200", style("STYLE_1", "C0", "-", "o")),
    makeContract(CaseId::K200_M255K207, "K200_M255K207", "BCH255整块200", 200U,
                 255U, 207U, 6U, "BERLEKAMP_MASSEY_CHIEN",
                 Organization::ShortenedWholeBlock, {200U}, {0U}, {7U}, {248U},
                 "255整块200", style("STYLE_2", "C1", "--", "s")),
    makeContract(CaseId::K200_M511K421, "K200_M511K421", "BCH421整块200", 200U,
                 511U, 421U, 10U, "BERLEKAMP_MASSEY_CHIEN",
                 Organization::ShortenedWholeBlock, {200U}, {0U}, {221U}, {290U},
                 "421整块200", style("STYLE_3", "C2", "-.", "^")),
    makeContract(CaseId::K200_M511K385, "K200_M511K385", "BCH385整块200", 200U,
                 511U, 385U, 14U, "BERLEKAMP_MASSEY_CHIEN",
                 Organization::ShortenedWholeBlock, {200U}, {0U}, {185U}, {326U},
                 "385整块200", style("STYLE_4", "C3", ":", "D")),
    makeContract(CaseId::K300_S15, "K300_S15", "BCH15分块300", 300U, 15U, 11U, 1U,
                 "SYNDROME_LOOKUP", Organization::Segmented15,
                 {11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,11U,3U},
                 {0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,0U,8U},
                 std::vector<std::size_t>(28U, 0U), std::vector<std::size_t>(28U, 15U),
                 "分块300", style("STYLE_1", "C0", "-", "o")),
    makeContract(CaseId::K300_M255K207, "K300_M255K207", "BCH255双块300", 300U,
                 255U, 207U, 6U, "BERLEKAMP_MASSEY_CHIEN",
                 Organization::ShortenedMultiBlock, {150U, 150U}, {0U, 0U}, {57U, 57U},
                 {198U, 198U}, "255双块300", style("STYLE_2", "C1", "--", "s")),
    makeContract(CaseId::K300_M511K421, "K300_M511K421", "BCH421整块300", 300U,
                 511U, 421U, 10U, "BERLEKAMP_MASSEY_CHIEN",
                 Organization::ShortenedWholeBlock, {300U}, {0U}, {121U}, {390U},
                 "421整块300", style("STYLE_3", "C2", "-.", "^")),
    makeContract(CaseId::K300_M511K385, "K300_M511K385", "BCH385整块300", 300U,
                 511U, 385U, 14U, "BERLEKAMP_MASSEY_CHIEN",
                 Organization::ShortenedWholeBlock, {300U}, {0U}, {85U}, {426U},
                 "385整块300", style("STYLE_4", "C3", ":", "D"))
};

BlockBchProfile profileFromMother(const CaseContract& contract, std::size_t block) {
    BlockBchProfile profile;
    if (contract.motherN == 255U) profile = block::makeB200Profile();
    else if (contract.motherK == 421U) profile = block::makeB300Profile();
    else if (contract.motherK == 385U) profile = block::makeB300426Profile();
    else throw std::invalid_argument("unsupported whole-block mother profile");
    profile.caseName = contract.caseId + "_BLOCK_" + std::to_string(block);
    profile.payloadLength = contract.payloadPerBlock.at(block);
    profile.shorteningLength = contract.shorteningPerBlock.at(block);
    block::validateProfile(profile);
    return profile;
}

const std::vector<BlockBchProfile>& blockProfiles(CaseId id) {
    static const auto k200_255 = [] { const auto& c=caseContract(CaseId::K200_M255K207); return std::vector<BlockBchProfile>{profileFromMother(c,0)}; }();
    static const auto k200_421 = [] { const auto& c=caseContract(CaseId::K200_M511K421); return std::vector<BlockBchProfile>{profileFromMother(c,0)}; }();
    static const auto k200_385 = [] { const auto& c=caseContract(CaseId::K200_M511K385); return std::vector<BlockBchProfile>{profileFromMother(c,0)}; }();
    static const auto k300_255 = [] { const auto& c=caseContract(CaseId::K300_M255K207); return std::vector<BlockBchProfile>{profileFromMother(c,0),profileFromMother(c,1)}; }();
    static const auto k300_421 = [] { const auto& c=caseContract(CaseId::K300_M511K421); return std::vector<BlockBchProfile>{profileFromMother(c,0)}; }();
    static const auto k300_385 = [] { const auto& c=caseContract(CaseId::K300_M511K385); return std::vector<BlockBchProfile>{profileFromMother(c,0)}; }();
    switch (id) {
        case CaseId::K200_M255K207: return k200_255;
        case CaseId::K200_M511K421: return k200_421;
        case CaseId::K200_M511K385: return k200_385;
        case CaseId::K300_M255K207: return k300_255;
        case CaseId::K300_M511K421: return k300_421;
        case CaseId::K300_M511K385: return k300_385;
        default: throw std::invalid_argument("segmented case has no block profile");
    }
}

const segmented::SyndromeTable& syndromeTable() {
    static const auto table = segmented::buildBch15SyndromeTable();
    return table;
}

}  // namespace

const std::vector<CaseContract>& allCaseContracts() {
    return kContracts;
}

const CaseContract& caseContract(CaseId id) {
    const auto found = std::find_if(kContracts.begin(), kContracts.end(),
        [id](const CaseContract& value) { return value.id == id; });
    if (found == kContracts.end()) throw std::invalid_argument("unsupported BCH S2 case id");
    return *found;
}

void validateCaseContract(const CaseContract& c) {
    if (c.caseId.empty() || c.displayName.empty() || c.legendLabel.empty() || c.plotStyle.id.empty() ||
        c.payloadLength == 0U || c.totalEncodedLength == 0U || c.blockCount == 0U ||
        c.blockCount != c.payloadPerBlock.size() || c.blockCount != c.fillerPerBlock.size() ||
        c.blockCount != c.shorteningPerBlock.size() || c.blockCount != c.encodedLengthPerBlock.size()) {
        throw std::invalid_argument("invalid BCH S2 case contract shape");
    }
    const std::size_t payloadSum = std::accumulate(c.payloadPerBlock.begin(), c.payloadPerBlock.end(), std::size_t{0U});
    const std::size_t encodedSum = std::accumulate(c.encodedLengthPerBlock.begin(), c.encodedLengthPerBlock.end(), std::size_t{0U});
    if (payloadSum != c.payloadLength || encodedSum != c.totalEncodedLength ||
        std::abs(c.actualRate - static_cast<double>(c.payloadLength) / c.totalEncodedLength) > 1e-15) {
        throw std::invalid_argument("BCH S2 case aggregate length/rate mismatch");
    }
    for (std::size_t i = 0; i < c.blockCount; ++i) {
        if (c.encodedLengthPerBlock[i] > 1000U) throw std::invalid_argument("block exceeds 1000 transmitted bits");
        if (c.organization == Organization::Segmented15) {
            if (c.payloadPerBlock[i] + c.fillerPerBlock[i] != 11U ||
                c.shorteningPerBlock[i] != 0U || c.encodedLengthPerBlock[i] != 15U) {
                throw std::invalid_argument("segmented block length mismatch");
            }
        } else if (c.payloadPerBlock[i] + c.shorteningPerBlock[i] != c.motherK ||
                   c.encodedLengthPerBlock[i] != c.motherN - c.shorteningPerBlock[i] ||
                   c.fillerPerBlock[i] != 0U) {
            throw std::invalid_argument("shortened block length mismatch");
        }
    }
}

EncodedFrame encodeFrame(CaseId id, const common::BitVector& payload) {
    const auto& c = caseContract(id);
    validateCaseContract(c);
    if (payload.size() != c.payloadLength) throw std::invalid_argument("payload length differs from contract");
    common::validateBits(payload, "stage02 payload");
    EncodedFrame result{id, {}, {0U}};
    if (c.organization == Organization::Segmented15) {
        const auto segmentedId = c.payloadLength == 200U
            ? segmented::Bch15SegmentedCase::S200 : segmented::Bch15SegmentedCase::S300;
        result.encodedBits = segmented::encodeBch15Segmented(segmentedId, payload).encodedBits;
        for (std::size_t block = 1U; block <= c.blockCount; ++block) {
            result.blockOffsets.push_back(block * 15U);
        }
    } else {
        const auto& profiles = blockProfiles(id);
        std::size_t payloadOffset = 0U;
        for (std::size_t blockIndex = 0; blockIndex < c.blockCount; ++blockIndex) {
            const std::size_t count = c.payloadPerBlock[blockIndex];
            const common::BitVector blockPayload(
                payload.begin() + static_cast<std::ptrdiff_t>(payloadOffset),
                payload.begin() + static_cast<std::ptrdiff_t>(payloadOffset + count));
            const auto encoded = block::encodeShortened(profiles[blockIndex], blockPayload);
            result.encodedBits.insert(result.encodedBits.end(),
                                      encoded.shortenedCodeword.begin(), encoded.shortenedCodeword.end());
            result.blockOffsets.push_back(result.encodedBits.size());
            payloadOffset += count;
        }
    }
    if (result.encodedBits.size() != c.totalEncodedLength ||
        result.blockOffsets.size() != c.blockCount + 1U) {
        throw std::logic_error("encoded frame differs from contract");
    }
    return result;
}

DecodedFrame decodeFrame(CaseId id, const common::BitVector& received) {
    const auto& c = caseContract(id);
    validateCaseContract(c);
    if (received.size() != c.totalEncodedLength) throw std::invalid_argument("received length differs from contract");
    common::validateBits(received, "stage02 received");
    DecodedFrame result{id, {}, true, 0U};
    if (c.organization == Organization::Segmented15) {
        const auto segmentedId = c.payloadLength == 200U
            ? segmented::Bch15SegmentedCase::S200 : segmented::Bch15SegmentedCase::S300;
        const auto decoded = segmented::decodeBch15Segmented(segmentedId, received, syndromeTable());
        result.payload = decoded.recoveredPayload;
        result.failedBlocks = decoded.frameDetail.totalBlocks - decoded.frameDetail.reportedSuccessBlocks;
        result.reportedSuccess = result.failedBlocks == 0U;
    } else {
        const auto& profiles = blockProfiles(id);
        std::size_t encodedOffset = 0U;
        for (std::size_t blockIndex = 0; blockIndex < c.blockCount; ++blockIndex) {
            const std::size_t count = c.encodedLengthPerBlock[blockIndex];
            const common::BitVector blockReceived(
                received.begin() + static_cast<std::ptrdiff_t>(encodedOffset),
                received.begin() + static_cast<std::ptrdiff_t>(encodedOffset + count));
            const auto decoded = block::decodeShortenedNoThrow(profiles[blockIndex], blockReceived);
            const bool success = decoded.status == block::DecodeStatus::NoError ||
                                 decoded.status == block::DecodeStatus::Corrected;
            result.failedBlocks += success ? 0U : 1U;
            result.payload.insert(result.payload.end(), decoded.payload.begin(), decoded.payload.end());
            encodedOffset += count;
        }
        result.reportedSuccess = result.failedBlocks == 0U;
    }
    if (result.payload.size() != c.payloadLength) throw std::logic_error("decoded payload differs from contract");
    return result;
}

const char* organizationName(Organization organization) {
    switch (organization) {
        case Organization::Segmented15: return "SEGMENTED_15_11";
        case Organization::ShortenedWholeBlock: return "SHORTENED_WHOLE_BLOCK";
        case Organization::ShortenedMultiBlock: return "SHORTENED_MULTI_BLOCK";
    }
    return "INVALID";
}

}  // namespace scl::bch::s2::stage02
