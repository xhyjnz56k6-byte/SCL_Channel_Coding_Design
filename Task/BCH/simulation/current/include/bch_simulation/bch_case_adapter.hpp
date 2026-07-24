#ifndef SCL_BCH_SIMULATION_BCH_CASE_ADAPTER_HPP
#define SCL_BCH_SIMULATION_BCH_CASE_ADAPTER_HPP

#include "common/types.hpp"

#include <cstddef>
#include <string>

namespace scl::bch::simulation {

enum class BchCaseId { S200, B200, S300, B300, B300_426 };
enum class BchOrganization { Segmented, WholeBlockShortened };
enum class BchDecoderType { SyndromeLookup, BerlekampMasseyChien };

struct BchSimulationCase {
    BchCaseId id;
    std::string caseName;
    common::Length payloadLength;
    common::Length encodedLength;
    double frameRate;
    BchOrganization organization;
    BchDecoderType decoderType;
    common::Length segmentCount = 0U;
    common::Length fillerLength = 0U;
    common::Length motherN = 0U;
    common::Length motherK = 0U;
    common::Length shorteningLength = 0U;
    unsigned correctionCapability = 0U;
};

struct EncodedBchFrame {
    BchSimulationCase simulationCase;
    common::BitVector codeword;
};

struct DecodedBchFrame {
    common::BitVector payload;
    bool reportedSuccess = false;
    bool trueSuccess = false;
    bool miscorrected = false;
    bool decoderFailure = true;
    std::string frameStatus;
    common::Length failedBlockCount = 0U;
    common::Length correctedBlockCount = 0U;
    common::Length noErrorBlockCount = 0U;
    std::string wholeBlockStatus = "NOT_APPLICABLE";
    std::string decodeDiagnostics;
};

const BchSimulationCase& bchSimulationCase(BchCaseId id);
const BchSimulationCase& bchSimulationCase(const std::string& caseName);
void prepareBchCase(const BchSimulationCase& simulationCase);
EncodedBchFrame encodeBchFrame(const BchSimulationCase& simulationCase,
                               const common::BitVector& payload);
DecodedBchFrame decodeBchFrame(const BchSimulationCase& simulationCase,
                               const common::BitVector& receivedCodeword);
void auditDecodedBchFrame(const common::BitVector& originalPayload, DecodedBchFrame& decoded);
std::string organizationName(BchOrganization organization);
std::string decoderTypeName(BchDecoderType decoderType);

}  // namespace scl::bch::simulation

#endif
