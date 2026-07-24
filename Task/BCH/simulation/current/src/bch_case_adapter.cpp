#include "bch_simulation/bch_case_adapter.hpp"

#include "bch_block/bch_block.hpp"
#include "bch_segmented/bch15_lookup_table.hpp"
#include "bch_segmented/bch15_segmented_adapter.hpp"

#include <sstream>
#include <stdexcept>

namespace scl::bch::simulation {
namespace {

const BchSimulationCase kS200{BchCaseId::S200, "BCH-S200", 200U, 285U, 200.0 / 285.0,
                              BchOrganization::Segmented, BchDecoderType::SyndromeLookup,
                              19U, 9U, 0U, 0U, 0U, 1U};
const BchSimulationCase kB200{BchCaseId::B200, "BCH-B200", 200U, 248U, 200.0 / 248.0,
                              BchOrganization::WholeBlockShortened, BchDecoderType::BerlekampMasseyChien,
                              0U, 0U, 255U, 207U, 7U, 6U};
const BchSimulationCase kS300{BchCaseId::S300, "BCH-S300", 300U, 420U, 300.0 / 420.0,
                              BchOrganization::Segmented, BchDecoderType::SyndromeLookup,
                              28U, 8U, 0U, 0U, 0U, 1U};
const BchSimulationCase kB300{BchCaseId::B300, "BCH-B300", 300U, 390U, 300.0 / 390.0,
                              BchOrganization::WholeBlockShortened, BchDecoderType::BerlekampMasseyChien,
                              0U, 0U, 511U, 421U, 121U, 10U};
const BchSimulationCase kB300426{BchCaseId::B300_426, "BCH-B300-426", 300U, 426U, 300.0 / 426.0,
                                 BchOrganization::WholeBlockShortened, BchDecoderType::BerlekampMasseyChien,
                                 0U, 0U, 511U, 385U, 85U, 14U};

void validateCase(const BchSimulationCase& value) {
    const BchSimulationCase& frozen = bchSimulationCase(value.id);
    if (value.caseName != frozen.caseName || value.payloadLength != frozen.payloadLength ||
        value.encodedLength != frozen.encodedLength || value.frameRate != frozen.frameRate ||
        value.organization != frozen.organization || value.decoderType != frozen.decoderType) {
        throw std::invalid_argument("BCH simulation case differs from frozen configuration");
    }
}

const block::BlockBchProfile& blockProfile(BchCaseId id) {
    if (id == BchCaseId::B200) {
        static const block::BlockBchProfile profile = block::makeB200Profile();
        return profile;
    }
    if (id == BchCaseId::B300) {
        static const block::BlockBchProfile profile = block::makeB300Profile();
        return profile;
    }
    if (id == BchCaseId::B300_426) {
        static const block::BlockBchProfile profile = block::makeB300426Profile();
        return profile;
    }
    throw std::invalid_argument("segmented case has no whole-block profile");
}

const segmented::SyndromeTable& segmentedSyndromeTable() {
    static const segmented::SyndromeTable table = segmented::buildBch15SyndromeTable();
    return table;
}

segmented::Bch15SegmentedCase segmentedCase(BchCaseId id) {
    if (id == BchCaseId::S200) return segmented::Bch15SegmentedCase::S200;
    if (id == BchCaseId::S300) return segmented::Bch15SegmentedCase::S300;
    throw std::invalid_argument("whole-block case has no segmented profile");
}

bool blockStatusIsSuccess(block::DecodeStatus status) {
    return status == block::DecodeStatus::NoError || status == block::DecodeStatus::Corrected;
}

}  // namespace

const BchSimulationCase& bchSimulationCase(BchCaseId id) {
    switch (id) {
        case BchCaseId::S200: return kS200;
        case BchCaseId::B200: return kB200;
        case BchCaseId::S300: return kS300;
        case BchCaseId::B300: return kB300;
        case BchCaseId::B300_426: return kB300426;
    }
    throw std::invalid_argument("unsupported BCH case id");
}

const BchSimulationCase& bchSimulationCase(const std::string& name) {
    for (BchCaseId id : {BchCaseId::S200, BchCaseId::B200, BchCaseId::S300, BchCaseId::B300, BchCaseId::B300_426}) {
        const auto& value = bchSimulationCase(id);
        if (value.caseName == name) return value;
    }
    throw std::invalid_argument("unsupported BCH case name");
}

void prepareBchCase(const BchSimulationCase& simulationCase) {
    validateCase(simulationCase);
    if (simulationCase.organization == BchOrganization::Segmented) {
        static_cast<void>(segmentedSyndromeTable());
    } else {
        static_cast<void>(blockProfile(simulationCase.id));
    }
}

EncodedBchFrame encodeBchFrame(const BchSimulationCase& simulationCase,
                               const common::BitVector& payload) {
    validateCase(simulationCase);
    if (payload.size() != simulationCase.payloadLength) {
        throw std::invalid_argument("payload length does not match BCH simulation case");
    }
    common::validateBits(payload, "BCH simulation payload");
    EncodedBchFrame result;
    result.simulationCase = simulationCase;
    if (simulationCase.organization == BchOrganization::Segmented) {
        result.codeword = segmented::encodeBch15Segmented(segmentedCase(simulationCase.id), payload).encodedBits;
    } else {
        result.codeword = block::encodeShortened(blockProfile(simulationCase.id), payload).shortenedCodeword;
    }
    if (result.codeword.size() != simulationCase.encodedLength) {
        throw std::logic_error("BCH adapter encoded length mismatch");
    }
    return result;
}

DecodedBchFrame decodeBchFrame(const BchSimulationCase& simulationCase,
                               const common::BitVector& receivedCodeword) {
    validateCase(simulationCase);
    if (receivedCodeword.size() != simulationCase.encodedLength) {
        throw std::invalid_argument("received length does not match BCH simulation case");
    }
    common::validateBits(receivedCodeword, "BCH simulation received codeword");
    DecodedBchFrame result;
    if (simulationCase.organization == BchOrganization::Segmented) {
        const auto decoded = segmented::decodeBch15Segmented(
            segmentedCase(simulationCase.id), receivedCodeword, segmentedSyndromeTable());
        result.payload = decoded.recoveredPayload;
        result.correctedBlockCount = decoded.frameDetail.correctedBlocks;
        result.noErrorBlockCount = decoded.frameDetail.noErrorBlocks;
        result.failedBlockCount = decoded.frameDetail.totalBlocks - decoded.frameDetail.reportedSuccessBlocks;
        result.reportedSuccess = result.failedBlockCount == 0U;
        result.decoderFailure = !result.reportedSuccess;
        result.frameStatus = result.decoderFailure ? "DECODER_FAILURE" :
                             (result.correctedBlockCount == 0U ? "NO_ERROR" : "CORRECTED");
        std::ostringstream detail;
        detail << "blocks=" << decoded.frameDetail.totalBlocks
               << ";noError=" << result.noErrorBlockCount
               << ";corrected=" << result.correctedBlockCount
               << ";failed=" << result.failedBlockCount;
        result.decodeDiagnostics = detail.str();
    } else {
        const auto decoded = block::decodeShortenedNoThrow(blockProfile(simulationCase.id), receivedCodeword);
        result.payload = decoded.payload;
        result.wholeBlockStatus = block::statusName(decoded.status);
        result.reportedSuccess = blockStatusIsSuccess(decoded.status);
        result.decoderFailure = !result.reportedSuccess;
        result.noErrorBlockCount = decoded.status == block::DecodeStatus::NoError ? 1U : 0U;
        result.correctedBlockCount = decoded.status == block::DecodeStatus::Corrected ? 1U : 0U;
        result.failedBlockCount = result.reportedSuccess ? 0U : 1U;
        result.frameStatus = result.wholeBlockStatus;
        std::ostringstream detail;
        detail << "nonzeroSyndromes=" << decoded.nonzeroSyndromeCount
               << ";locatorDegree=" << decoded.locatorDegree
               << ";roots=" << decoded.motherErrorPositions.size();
        result.decodeDiagnostics = detail.str();
    }
    return result;
}

void auditDecodedBchFrame(const common::BitVector& originalPayload, DecodedBchFrame& decoded) {
    decoded.trueSuccess = decoded.payload == originalPayload;
    decoded.miscorrected = decoded.reportedSuccess && !decoded.trueSuccess;
}

std::string organizationName(BchOrganization value) {
    return value == BchOrganization::Segmented ? "SEGMENTED" : "WHOLE_BLOCK_SHORTENED";
}

std::string decoderTypeName(BchDecoderType value) {
    return value == BchDecoderType::SyndromeLookup ? "SYNDROME_LOOKUP" : "BERLEKAMP_MASSEY_CHIEN";
}

}  // namespace scl::bch::simulation
