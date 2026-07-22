#include "bch_block/bch_block.hpp"

#include <algorithm>
#include <set>
#include <stdexcept>

namespace scl::bch::block {
namespace {

std::int64_t modulo(std::int64_t value, std::int64_t modulus) {
    value %= modulus;
    return value < 0 ? value + modulus : value;
}

std::vector<Gf2m::Element> buildGenerator(const Gf2m& field, unsigned t) {
    std::vector<Gf2m::Element> polynomial(1U, 1U); // ascending coefficients
    // A binary BCH generator must include complete conjugacy classes.  The
    // consecutive designed roots alone are not generally closed under x->x^2.
    std::set<unsigned> exponents;
    const unsigned period = field.order() - 1U;
    for (unsigned root = 1U; root <= 2U * t; ++root) {
        unsigned exponent = root % period;
        do { exponents.insert(exponent); exponent = (2U * exponent) % period; } while (exponent != root % period);
    }
    for (unsigned root : exponents) {
        std::vector<Gf2m::Element> next(polynomial.size() + 1U, 0U);
        const Gf2m::Element a = field.alphaPower(root);
        for (std::size_t i = 0; i < polynomial.size(); ++i) {
            next[i] = field.add(next[i], field.multiply(polynomial[i], a));
            next[i + 1U] = field.add(next[i + 1U], polynomial[i]);
        }
        polynomial = next;
    }
    return polynomial;
}

common::BitVector binaryGenerator(const Gf2m& field, unsigned t) {
    const std::vector<Gf2m::Element> ascending = buildGenerator(field, t);
    common::BitVector descending(ascending.size(), 0U);
    for (std::size_t i = 0; i < ascending.size(); ++i) {
        if (ascending[i] > 1U) {
            throw std::runtime_error("BCH generator coefficient is not binary");
        }
        descending[ascending.size() - 1U - i] = static_cast<common::Bit>(ascending[i]);
    }
    return descending;
}

common::BitVector systematicEncode(const common::BitVector& information,
                                   const common::BitVector& generator) {
    const std::size_t parity = generator.size() - 1U;
    common::BitVector division(information.size() + parity, 0U);
    std::copy(information.begin(), information.end(), division.begin());
    for (std::size_t i = 0; i < information.size(); ++i) {
        if (division[i] == 0U) continue;
        for (std::size_t j = 0; j < generator.size(); ++j) division[i + j] ^= generator[j];
    }
    common::BitVector codeword = information;
    codeword.insert(codeword.end(), division.end() - static_cast<std::ptrdiff_t>(parity), division.end());
    return codeword;
}

common::BitVector polynomialRemainder(const common::BitVector& dividend,
                                      const common::BitVector& generator) {
    if (generator.size() < 2U || generator.front() != 1U) throw std::invalid_argument("invalid generator polynomial");
    common::validateBits(dividend, "dividend"); common::validateBits(generator, "generator");
    common::BitVector division = dividend;
    if (division.size() >= generator.size()) for (std::size_t i=0;i<=division.size()-generator.size();++i) if (division[i] != 0U)
        for (std::size_t j=0;j<generator.size();++j) division[i+j] ^= generator[j];
    return common::BitVector(division.end()-static_cast<std::ptrdiff_t>(generator.size()-1U), division.end());
}

std::vector<Gf2m::Element> syndromes(const Gf2m& field, const common::BitVector& word, unsigned t) {
    std::vector<Gf2m::Element> result(2U * t, 0U);
    for (unsigned j = 1U; j <= 2U * t; ++j) {
        for (std::size_t index = 0; index < word.size(); ++index) {
            if (word[index] != 0U) result[j - 1U] ^= field.alphaPower(static_cast<std::int64_t>(j) *
                static_cast<std::int64_t>(word.size() - 1U - index));
        }
    }
    return result;
}

std::vector<Gf2m::Element> berlekampMassey(const Gf2m& field,
                                            const std::vector<Gf2m::Element>& sequence) {
    std::vector<Gf2m::Element> locator(1U, 1U), backup(1U, 1U);
    std::size_t length = 0U, shift = 1U;
    Gf2m::Element lastDiscrepancy = 1U;
    for (std::size_t n = 0; n < sequence.size(); ++n) {
        Gf2m::Element discrepancy = sequence[n];
        for (std::size_t i = 1U; i <= length; ++i) discrepancy ^= field.multiply(locator[i], sequence[n - i]);
        if (discrepancy == 0U) { ++shift; continue; }
        const std::vector<Gf2m::Element> previous = locator;
        if (locator.size() < backup.size() + shift) locator.resize(backup.size() + shift, 0U);
        const Gf2m::Element scale = field.divide(discrepancy, lastDiscrepancy);
        for (std::size_t i = 0; i < backup.size(); ++i) locator[i + shift] ^= field.multiply(scale, backup[i]);
        if (2U * length <= n) { length = n + 1U - length; backup = previous; lastDiscrepancy = discrepancy; shift = 1U; }
        else ++shift;
    }
    locator.resize(length + 1U);
    return locator;
}

}  // namespace

Gf2m::Gf2m(unsigned degree, std::uint32_t primitivePolynomial) : degree_(degree) {
    if (degree < 2U || degree > 15U) throw std::invalid_argument("GF degree must be in [2,15]");
    order_ = 1U << degree_; mask_ = order_ - 1U;
    if ((primitivePolynomial >> degree_) != 1U || (primitivePolynomial & 1U) == 0U) {
        throw std::invalid_argument("primitive polynomial has invalid degree or constant term");
    }
    antilog_.assign(order_ - 1U, 0U); log_.assign(order_, -1);
    std::uint32_t value = 1U;
    for (std::uint32_t i = 0; i < order_ - 1U; ++i) {
        if (log_[value] != -1) throw std::invalid_argument("polynomial is not primitive");
        antilog_[i] = static_cast<Element>(value); log_[value] = static_cast<int>(i);
        value <<= 1U; if ((value & order_) != 0U) value ^= primitivePolynomial; value &= mask_;
    }
    if (value != 1U) throw std::invalid_argument("polynomial is not primitive");
}
unsigned Gf2m::degree() const { return degree_; }
std::uint32_t Gf2m::order() const { return order_; }
void Gf2m::validate(Element value) const { if (value >= order_) throw std::out_of_range("field element outside range"); }
Gf2m::Element Gf2m::add(Element a, Element b) const { validate(a); validate(b); return static_cast<Element>(a ^ b); }
Gf2m::Element Gf2m::multiply(Element a, Element b) const { validate(a); validate(b); return a == 0U || b == 0U ? 0U : antilog_[(log_[a] + log_[b]) % static_cast<int>(order_ - 1U)]; }
Gf2m::Element Gf2m::divide(Element a, Element b) const { validate(a); validate(b); if (b == 0U) throw std::domain_error("division by zero in GF"); return a == 0U ? 0U : antilog_[static_cast<std::size_t>(modulo(log_[a] - log_[b], order_ - 1U))]; }
Gf2m::Element Gf2m::inverse(Element a) const { if (a == 0U) throw std::domain_error("inverse of zero in GF"); return divide(1U, a); }
Gf2m::Element Gf2m::power(Element a, std::int64_t exponent) const { validate(a); if (a == 0U) { if (exponent < 0) throw std::domain_error("negative power of zero"); return exponent == 0 ? 1U : 0U; } return antilog_[static_cast<std::size_t>(modulo(static_cast<std::int64_t>(log_[a]) * exponent, order_ - 1U))]; }
Gf2m::Element Gf2m::alphaPower(std::int64_t exponent) const { return antilog_[static_cast<std::size_t>(modulo(exponent, order_ - 1U))]; }
int Gf2m::logarithm(Element a) const { validate(a); if (a == 0U) throw std::domain_error("logarithm of zero in GF"); return log_[a]; }
Gf2m::Element Gf2m::evaluate(const std::vector<Element>& c, Element x) const { validate(x); Element value = 0U; for (auto it = c.rbegin(); it != c.rend(); ++it) value = add(multiply(value, x), *it); return value; }

BlockBchProfile makeB200Profile() { Gf2m field(8U, 0x11DU); return {"BCH-B200",200U,255U,207U,7U,8U,6U,0x11DU,binaryGenerator(field,6U),{1,2,3,4,5,6,7,8,9,10,11,12}}; }
BlockBchProfile makeB300Profile() { Gf2m field(9U, 0x211U); return {"BCH-B300",300U,511U,421U,121U,9U,10U,0x211U,binaryGenerator(field,10U),{1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20}}; }
void validateProfile(const BlockBchProfile& p) { if (p.correctionCapability==0U || p.shorteningLength>p.motherK || p.motherN != (1U << p.fieldDegree) - 1U || p.motherK != p.payloadLength + p.shorteningLength || p.generatorPolynomial.size() != p.motherN - p.motherK + 1U || p.generatorRoots.size() != 2U * p.correctionCapability) throw std::invalid_argument("invalid BCH block profile"); common::validateBits(p.generatorPolynomial,"generatorPolynomial"); }
bool isCodewordDivisibleByGenerator(const common::BitVector& word, const common::BitVector& generator) { const auto remainder=polynomialRemainder(word,generator); return std::all_of(remainder.begin(),remainder.end(),[](common::Bit b){return b==0U;}); }
EncodeResult encodeShortened(const BlockBchProfile& p, const common::BitVector& payload) { validateProfile(p); if (payload.size()!=p.payloadLength) throw std::invalid_argument("payload length mismatch"); common::validateBits(payload,"payload"); EncodeResult r; r.payload=payload; r.shorteningLength=p.shorteningLength; r.motherInformation.assign(p.shorteningLength,0U); r.motherInformation.insert(r.motherInformation.end(),payload.begin(),payload.end()); r.motherCodeword=systematicEncode(r.motherInformation,p.generatorPolynomial); r.polynomialRemainder=polynomialRemainder(r.motherCodeword,p.generatorPolynomial); r.motherCodewordDivisibleByGenerator=std::all_of(r.polynomialRemainder.begin(),r.polynomialRemainder.end(),[](common::Bit b){return b==0U;}); r.parity.assign(r.motherCodeword.end()-static_cast<std::ptrdiff_t>(p.parityLength()),r.motherCodeword.end()); r.shortenedCodeword.assign(r.motherCodeword.begin()+static_cast<std::ptrdiff_t>(p.shorteningLength),r.motherCodeword.end()); return r; }
DecodeResult decodeShortened(const BlockBchProfile& p, const common::BitVector& received) { validateProfile(p); if(received.size()!=p.shortenedN()) throw std::invalid_argument("shortened codeword length mismatch"); common::validateBits(received,"received"); Gf2m field(p.fieldDegree,p.primitivePolynomial); DecodeResult r; r.receivedShortenedCodeword=received; common::BitVector mother(p.shorteningLength,0U); mother.insert(mother.end(),received.begin(),received.end()); r.receivedMotherCodeword=mother; r.syndromes=syndromes(field,mother,p.correctionCapability); r.allZeroSyndrome=std::all_of(r.syndromes.begin(),r.syndromes.end(),[](Gf2m::Element s){return s==0U;}); r.nonzeroSyndromeCount=static_cast<std::size_t>(std::count_if(r.syndromes.begin(),r.syndromes.end(),[](Gf2m::Element s){return s!=0U;})); r.locatorPolynomial={1U}; r.bmIterationCount=r.allZeroSyndrome?0U:r.syndromes.size(); r.status=DecodeStatus::DecodeFailure; if(r.allZeroSyndrome){r.status=DecodeStatus::NoError;}else{r.locatorPolynomial=berlekampMassey(field,r.syndromes);r.locatorDegree=r.locatorPolynomial.size()-1U;if(r.locatorDegree>p.correctionCapability){r.status=DecodeStatus::LocatorDegreeExceedsT;r.failureReason="locator degree exceeds t";}else{for(std::size_t i=0;i<mother.size();++i)if(field.evaluate(r.locatorPolynomial,field.alphaPower(-static_cast<std::int64_t>(mother.size()-1U-i)))==0U)r.motherErrorPositions.push_back(i);for(auto i:r.motherErrorPositions){if(i<p.shorteningLength)r.rootsInShortenedPrefix=true;else r.shortenedErrorPositions.push_back(i-p.shorteningLength);}if(r.motherErrorPositions.size()!=r.locatorDegree){r.status=DecodeStatus::InvalidRootCount;r.failureReason="root count differs from locator degree";}else if(r.rootsInShortenedPrefix){r.status=DecodeStatus::RootInShortenedPrefix;r.failureReason="root lies in shortened prefix";}else{for(auto i:r.motherErrorPositions)mother[i]^=1U;r.status=DecodeStatus::Corrected;}}r.postSyndromes=syndromes(field,mother,p.correctionCapability);r.postSyndromeZero=std::all_of(r.postSyndromes.begin(),r.postSyndromes.end(),[](Gf2m::Element s){return s==0U;});if(r.status==DecodeStatus::Corrected&&!r.postSyndromeZero){r.status=DecodeStatus::PostSyndromeNonzero;r.failureReason="post syndrome is nonzero";}}r.correctedMotherCodeword=mother;r.correctedShortenedCodeword.assign(mother.begin()+static_cast<std::ptrdiff_t>(p.shorteningLength),mother.end());r.payload.assign(mother.begin()+static_cast<std::ptrdiff_t>(p.shorteningLength),mother.begin()+static_cast<std::ptrdiff_t>(p.motherK));return r;}
DecodeResult decodeShortenedNoThrow(const BlockBchProfile& p,const common::BitVector& received){DecodeResult r;r.receivedShortenedCodeword=received;try{validateProfile(p);}catch(const std::exception&e){r.status=DecodeStatus::InvalidConfiguration;r.failureReason=e.what();return r;}if(received.size()!=p.shortenedN()){r.status=DecodeStatus::InvalidInputLength;r.failureReason="shortened codeword length mismatch";return r;}try{common::validateBits(received,"received");}catch(const std::exception&e){r.status=DecodeStatus::InvalidInputBits;r.failureReason=e.what();return r;}try{return decodeShortened(p,received);}catch(const std::exception&e){r.status=DecodeStatus::DecodeFailure;r.failureReason=e.what();return r;}}
std::string bitsToString(const common::BitVector& bits) { std::string s; s.reserve(bits.size()); for(common::Bit b:bits)s.push_back(b?'1':'0'); return s; }
std::string statusName(DecodeStatus s) { switch(s){case DecodeStatus::NoError:return "NO_ERROR";case DecodeStatus::Corrected:return "CORRECTED";case DecodeStatus::LocatorDegreeExceedsT:return "LOCATOR_DEGREE_EXCEEDS_T";case DecodeStatus::InvalidRootCount:return "INVALID_ROOT_COUNT";case DecodeStatus::RootInShortenedPrefix:return "ROOT_IN_SHORTENED_PREFIX";case DecodeStatus::PostSyndromeNonzero:return "POST_SYNDROME_NONZERO";case DecodeStatus::InvalidConfiguration:return "INVALID_CONFIGURATION";case DecodeStatus::InvalidInputLength:return "INVALID_INPUT_LENGTH";case DecodeStatus::InvalidInputBits:return "INVALID_INPUT_BITS";case DecodeStatus::RootOutOfRange:return "ROOT_OUT_OF_RANGE";case DecodeStatus::DecodeFailure:return "DECODE_FAILURE";} return "UNKNOWN"; }
}  // namespace scl::bch::block
