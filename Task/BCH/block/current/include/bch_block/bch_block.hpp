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
};

BlockBchProfile makeB200Profile();
BlockBchProfile makeB300Profile();
void validateProfile(const BlockBchProfile& profile);

struct EncodeResult {
    common::BitVector motherInformation;
    common::BitVector motherCodeword;
    common::BitVector shortenedCodeword;
};
EncodeResult encodeShortened(const BlockBchProfile& profile, const common::BitVector& payload);

enum class DecodeStatus { NoError, Corrected, LocatorDegreeExceedsT, InvalidRootCount,
                           RootInShortenedPrefix, PostSyndromeNonzero };
struct DecodeResult {
    DecodeStatus status;
    common::BitVector payload;
    common::BitVector correctedMotherCodeword;
    common::BitVector correctedShortenedCodeword;
    std::vector<Gf2m::Element> syndromes;
    std::vector<Gf2m::Element> locatorPolynomial;
    std::vector<std::size_t> motherErrorPositions;
};
DecodeResult decodeShortened(const BlockBchProfile& profile, const common::BitVector& received);

std::string bitsToString(const common::BitVector& bits);
std::string statusName(DecodeStatus status);

}  // namespace scl::bch::block

#endif
