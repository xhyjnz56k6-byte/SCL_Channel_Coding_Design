#ifndef SCL_BCH_SIMULATION_BCH_CASE_ADAPTER_HPP
#define SCL_BCH_SIMULATION_BCH_CASE_ADAPTER_HPP

#include "common/types.hpp"

#include <cstddef>
#include <cstdint>
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

struct BchFrameComplexity {
    std::uint64_t segmentCount = 0U;
    std::uint64_t initialSyndromeCount = 0U;
    std::uint64_t nonzeroSyndromeCount = 0U;
    std::uint64_t syndromeCalculationCount = 0U;
    std::uint64_t syndromeBitTestCount = 0U;
    std::uint64_t syndromeXorCount = 0U;
    std::uint64_t syndromeShiftCount = 0U;
    std::uint64_t tableLookupCount = 0U;
    std::uint64_t lookupHitCount = 0U;
    std::uint64_t lookupMissCount = 0U;
    std::uint64_t bitFlipCount = 0U;
    std::uint64_t postSyndromeCheckCount = 0U;
    std::uint64_t syndromeValueCount = 0U;
    std::uint64_t syndromeEvaluationCount = 0U;
    std::uint64_t bmIterationCount = 0U;
    std::uint64_t bmDiscrepancyCount = 0U;
    std::uint64_t bmLocatorUpdateCount = 0U;
    std::uint64_t bmPolynomialCopyCount = 0U;
    std::uint64_t chienPositionTestCount = 0U;
    std::uint64_t chienPolynomialEvaluationCount = 0U;
    std::uint64_t chienRootCount = 0U;
    std::uint64_t gfAddCount = 0U;
    std::uint64_t gfMultiplyCount = 0U;
    std::uint64_t gfDivideCount = 0U;
    std::uint64_t gfInverseCount = 0U;
    std::uint64_t correctedSegmentCount = 0U;
    std::uint64_t failedSegmentCount = 0U;
    std::uint64_t miscorrectedSegmentCount = 0U;
    std::uint64_t reportedSuccessButPayloadWrongCount = 0U;
    std::uint64_t locatorDegree = 0U;
    std::uint64_t rootCount = 0U;
    std::uint64_t decoderFailureCount = 0U;
    std::uint64_t miscorrectionCount = 0U;
};

struct BchFrameMemory {
    std::size_t staticMemoryBytes = 0U;
    std::size_t decoderObjectBytes = 0U;
    std::size_t lookupTableBytes = 0U;
    std::size_t gfTableBytes = 0U;
    std::size_t syndromeBufferBytes = 0U;
    std::size_t locatorPolynomialBytes = 0U;
    std::size_t temporaryPolynomialBytes = 0U;
    std::size_t receivedBufferBytes = 0U;
    std::size_t correctedBufferBytes = 0U;
    std::size_t payloadBufferBytes = 0U;
    std::size_t perFrameWorkspaceBytes = 0U;
    std::size_t peakWorkspaceBytes = 0U;
    std::size_t totalDecoderMemoryBytes = 0U;
    std::string memoryMeasurementMethod;
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
    BchFrameComplexity complexity;
    BchFrameMemory memory;
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
