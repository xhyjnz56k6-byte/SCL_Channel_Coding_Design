#ifndef SCL_BCH_S2_STAGE02_CASE_CONTRACT_HPP
#define SCL_BCH_S2_STAGE02_CASE_CONTRACT_HPP

#include "common/types.hpp"

#include <cstddef>
#include <string>
#include <vector>

namespace scl::bch::s2::stage02 {

enum class CaseId {
    K200_S15,
    K200_M255K207,
    K200_M511K421,
    K200_M511K385,
    K300_S15,
    K300_M255K207,
    K300_M511K421,
    K300_M511K385
};

enum class Organization {
    Segmented15,
    ShortenedWholeBlock,
    ShortenedMultiBlock
};

struct PlotStyle {
    std::string id;
    std::string color;
    std::string lineStyle;
    std::string marker;
};

struct CaseContract {
    CaseId id;
    std::string caseId;
    std::string displayName;
    std::size_t payloadLength;
    std::size_t motherN;
    std::size_t motherK;
    unsigned motherT;
    std::string decoderType;
    Organization organization;
    std::size_t blockCount;
    std::vector<std::size_t> payloadPerBlock;
    std::vector<std::size_t> fillerPerBlock;
    std::vector<std::size_t> shorteningPerBlock;
    std::vector<std::size_t> encodedLengthPerBlock;
    std::size_t totalEncodedLength;
    double actualRate;
    std::string payloadReassemblyOrder;
    std::string systematicBitOrder;
    std::string parityBitOrder;
    std::string shortenedBitPolicy;
    std::string legendLabel;
    PlotStyle plotStyle;
    std::string ferDefinition;
    std::string latencyDefinition;
};

struct EncodedFrame {
    CaseId caseId;
    common::BitVector encodedBits;
    std::vector<std::size_t> blockOffsets;
};

struct DecodedFrame {
    CaseId caseId;
    common::BitVector payload;
    bool reportedSuccess = false;
    std::size_t failedBlocks = 0U;
};

const std::vector<CaseContract>& allCaseContracts();
const CaseContract& caseContract(CaseId id);
void validateCaseContract(const CaseContract& contract);
EncodedFrame encodeFrame(CaseId id, const common::BitVector& payload);
DecodedFrame decodeFrame(CaseId id, const common::BitVector& received);
const char* organizationName(Organization organization);

}  // namespace scl::bch::s2::stage02

#endif
