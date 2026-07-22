#include "bch_block/bch_block.hpp"
#include "common/frame_pool.hpp"

#include <algorithm>
#include <iostream>
#include <random>
#include <stdexcept>

namespace {
using scl::common::BitVector;
using namespace scl::bch::block;

void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }

BitVector payload(std::size_t length, std::uint64_t seed) {
    BitVector result(length, 0U);
    for (std::size_t i = 0; i < length; ++i)
        result[i] = scl::common::deterministicPayloadBit(seed, length, 0U, i);
    return result;
}

void testField(const Gf2m& field) {
    for (std::uint32_t a = 0; a < field.order(); ++a) {
        require(field.add(static_cast<Gf2m::Element>(a), 0U) == a, "additive identity");
        require(field.add(static_cast<Gf2m::Element>(a), static_cast<Gf2m::Element>(a)) == 0U, "additive inverse");
        require(field.multiply(static_cast<Gf2m::Element>(a), 1U) == a, "multiplicative identity");
        if (a != 0U) { require(field.multiply(static_cast<Gf2m::Element>(a), field.inverse(static_cast<Gf2m::Element>(a))) == 1U, "inverse identity"); require(field.alphaPower(field.logarithm(static_cast<Gf2m::Element>(a))) == a, "log/antilog"); }
    }
    require(field.alphaPower(static_cast<std::int64_t>(field.order()) - 1) == 1U, "field period");
    require(field.alphaPower(-1) == field.inverse(2U), "negative exponent");
    std::mt19937 generator(20260722U + field.degree());
    for (unsigned count = 0; count < 20000U; ++count) {
        const auto a = static_cast<Gf2m::Element>(generator() % field.order());
        const auto b = static_cast<Gf2m::Element>(generator() % field.order());
        const auto c = static_cast<Gf2m::Element>(generator() % field.order());
        require(field.multiply(a, field.add(b,c)) == field.add(field.multiply(a,b),field.multiply(a,c)), "distributivity");
    }
}

void testProfile(const BlockBchProfile& profile) {
    validateProfile(profile);
    Gf2m field(profile.fieldDegree, profile.primitivePolynomial);
    std::vector<Gf2m::Element> ascending(profile.generatorPolynomial.size());
    for (std::size_t i = 0; i < ascending.size(); ++i) ascending[i] = profile.generatorPolynomial[ascending.size()-1U-i];
    for (unsigned root : profile.generatorRoots) require(field.evaluate(ascending, field.alphaPower(root)) == 0U, "generator root mismatch");
    for (std::uint64_t seed = 0; seed < 108U; ++seed) {
        const BitVector original = payload(profile.payloadLength, 0xBC70700ULL + seed);
        const EncodeResult encoded = encodeShortened(profile, original);
        require(encoded.motherInformation.size() == profile.motherK, "mother information length");
        require(encoded.motherCodeword.size() == profile.motherN, "mother word length");
        require(encoded.shortenedCodeword.size() == profile.motherN-profile.shorteningLength, "shortened length");
        require(std::equal(original.begin(), original.end(), encoded.shortenedCodeword.begin()), "systematic payload");
        DecodeResult clean = decodeShortened(profile, encoded.shortenedCodeword);
        require(clean.payload == original && clean.status == DecodeStatus::NoError, "noiseless decode");
        for (std::size_t position = 0; position < encoded.shortenedCodeword.size(); ++position) {
            BitVector received = encoded.shortenedCodeword; received[position] ^= 1U;
            DecodeResult decoded = decodeShortened(profile, received);
            require(decoded.payload == original && decoded.status == DecodeStatus::Corrected, "single error correction");
        }
    }
    std::mt19937 generator(20260722U + static_cast<unsigned>(profile.payloadLength));
    for (unsigned weight = 2U; weight <= profile.correctionCapability; ++weight) {
        for (unsigned sample = 0U; sample < 100U; ++sample) {
            const BitVector original = payload(profile.payloadLength, 100000U + weight * 1000U + sample);
            BitVector received = encodeShortened(profile, original).shortenedCodeword;
            std::vector<std::size_t> choices(received.size()); for (std::size_t i=0;i<choices.size();++i) choices[i]=i;
            std::shuffle(choices.begin(), choices.end(), generator);
            for (unsigned i=0;i<weight;++i) received[choices[i]] ^= 1U;
            DecodeResult decoded = decodeShortened(profile, received);
            require(decoded.payload == original && decoded.status == DecodeStatus::Corrected, "correctable multi-error");
        }
    }
}
}

int main() {
    try {
        testField(Gf2m(8U, 0x11DU)); testField(Gf2m(9U, 0x211U));
        bool threw = false; try { Gf2m(8U,0x101U); } catch (const std::invalid_argument&) { threw=true; } require(threw,"invalid polynomial rejection");
        threw=false; try { Gf2m(8U,0x11DU).inverse(0U); } catch (const std::domain_error&) { threw=true; } require(threw,"zero inverse rejection");
        testProfile(makeB200Profile()); testProfile(makeB300Profile());
        std::cout << "PASS_BCH_BLOCK_CORE_TEST\n";
    } catch (const std::exception& error) { std::cerr << "FAIL: " << error.what() << '\n'; return 1; }
}
