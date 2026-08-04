#ifndef SCL_BCH_BLOCK_BCH_BLOCK_HPP
#define SCL_BCH_BLOCK_BCH_BLOCK_HPP

#include "common/types.hpp"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace scl::bch::block {

class Gf2m final {
public:
    using Element = std::uint16_t;
    Gf2m(unsigned degree, std::uint32_t primitivePolynomial);
    unsigned degree() const;
    std::uint32_t order() const;
    Element add(Element a, Element b) const;
    Element multiply(Element a, Element b) const;
    Element divide(Element a, Element b) const;
    Element inverse(Element a) const;
    Element power(Element a, std::int64_t exponent) const;
    Element alphaPower(std::int64_t exponent) const;
    int logarithm(Element a) const;
    Element evaluate(const std::vector<Element>& ascendingCoefficients, Element x) const;
    std::size_t tableBytes() const;
private:
    void validate(Element value) const;
    unsigned degree_;
    std::uint32_t order_;
    std::uint32_t mask_;
    std::vector<Element> antilog_;
    std::vector<int> log_;
};

struct BlockBchProfile {
    std::string caseName;
    std::size_t payloadLength;
    std::size_t motherN;
    std::size_t motherK;
    std::size_t shorteningLength;
    unsigned fieldDegree;
    unsigned correctionCapability;
    std::uint32_t primitivePolynomial;
    common::BitVector generatorPolynomial; // descending degree, leading coefficient first
    std::vector<unsigned> generatorRoots;
    std::size_t shortenedN() const { return motherN - shorteningLength; }
    std::size_t shortenedK() const { return motherK - shorteningLength; }
    std::size_t parityLength() const { return motherN - motherK; }
    double frameRate() const { return static_cast<double>(payloadLength) / shortenedN(); }
    unsigned designedDistance() const { return 2U * correctionCapability + 1U; }
    std::string bitOrderDescription() const { return "index 0 is highest polynomial degree"; }
    std::string shorteningPositionDescription() const { return "prepend known zeros to mother information, then delete prefix"; }
};

BlockBchProfile makeB200Profile();
BlockBchProfile makeB300Profile();
BlockBchProfile makeB300426Profile();
void validateProfile(const BlockBchProfile& profile);

struct EncodeResult {
    common::BitVector payload;
    common::BitVector motherInformation;
    common::BitVector motherCodeword;
    common::BitVector shortenedCodeword;
    common::BitVector parity;
    common::BitVector polynomialRemainder;
    bool motherCodewordDivisibleByGenerator = false;
    std::size_t shorteningLength = 0U;
};
EncodeResult encodeShortened(const BlockBchProfile& profile, const common::BitVector& payload);
bool isCodewordDivisibleByGenerator(const common::BitVector& codeword, const common::BitVector& generator);

enum class DecodeStatus { NoError, Corrected, LocatorDegreeExceedsT, InvalidRootCount,
                           RootInShortenedPrefix, PostSyndromeNonzero, InvalidConfiguration,
                           InvalidInputLength, InvalidInputBits, RootOutOfRange, DecodeFailure };
struct BlockOperationCounts {
    std::uint64_t gfAddCount = 0U;
    std::uint64_t gfMultiplyCount = 0U;
    std::uint64_t gfDivideCount = 0U;
    std::uint64_t gfInverseCount = 0U;
};
struct BlockDecodeMetrics {
    std::uint64_t syndromeValueCount = 0U;
    std::uint64_t syndromeEvaluationCount = 0U;
    std::uint64_t bmIterationCount = 0U;
    std::uint64_t bmDiscrepancyCount = 0U;
    std::uint64_t bmLocatorUpdateCount = 0U;
    std::uint64_t bmPolynomialCopyCount = 0U;
    std::uint64_t chienPositionTestCount = 0U;
    std::uint64_t chienPolynomialEvaluationCount = 0U;
    std::uint64_t chienRootCount = 0U;
    std::uint64_t bitFlipCount = 0U;
    std::uint64_t postSyndromeCheckCount = 0U;
    std::uint64_t decoderFailureCount = 0U;
    BlockOperationCounts syndromeOperations;
    BlockOperationCounts bmOperations;
    BlockOperationCounts chienOperations;
    BlockOperationCounts postSyndromeOperations;
};
struct BlockMemoryAccounting {
    std::size_t staticMemoryBytes = 0U;
    std::size_t decoderObjectBytes = 0U;
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
    const char* memoryMeasurementMethod = "EXACT_FROM_TYPE_AND_COUNT";
};
struct DecodeResult {
    DecodeStatus status;
    common::BitVector payload;
    common::BitVector correctedMotherCodeword;
    common::BitVector correctedShortenedCodeword;
    std::vector<Gf2m::Element> syndromes;
    std::vector<Gf2m::Element> locatorPolynomial;
    std::vector<std::size_t> motherErrorPositions;
    common::BitVector receivedShortenedCodeword;
    common::BitVector receivedMotherCodeword;
    bool allZeroSyndrome = false;
    std::size_t nonzeroSyndromeCount = 0U;
    std::size_t locatorDegree = 0U;
    std::vector<std::size_t> shortenedErrorPositions;
    bool rootsInShortenedPrefix = false;
    std::vector<Gf2m::Element> postSyndromes;
    bool postSyndromeZero = false;
    std::size_t bmIterationCount = 0U;
    std::string failureReason;
    BlockDecodeMetrics metrics;
    BlockMemoryAccounting memory;
};
DecodeResult decodeShortened(const BlockBchProfile& profile, const common::BitVector& received);
DecodeResult decodeShortenedNoThrow(const BlockBchProfile& profile, const common::BitVector& received);

std::string bitsToString(const common::BitVector& bits);
std::string statusName(DecodeStatus status);

}  // namespace scl::bch::block

#endif
