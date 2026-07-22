#include "bch_block/bch_block.hpp"
#include <fstream>
#include <iostream>

namespace {
scl::common::BitVector vectorFor(std::size_t length, unsigned pattern) {
    scl::common::BitVector bits(length, 0U);
    for (std::size_t i=0;i<length;++i) {
        if (pattern==1U) bits[i]=1U;
        else if (pattern==2U) bits[i]=static_cast<scl::common::Bit>(i%2U);
        else if (pattern==3U) bits[i]=static_cast<scl::common::Bit>((i+1U)%2U);
        else if (pattern>=4U) bits[i]=static_cast<scl::common::Bit>(((i*37U+pattern*19U+11U)%101U)<50U);
    }
    return bits;
}
std::string numbers(const std::vector<scl::bch::block::Gf2m::Element>& values) { std::string text; for(auto v:values){if(!text.empty())text+=':';text+=std::to_string(v);}return text; }
std::string positions(const std::vector<std::size_t>& values) { std::string text; for(auto v:values){if(!text.empty())text+=':';text+=std::to_string(v);}return text; }
}
int main(int argc, char** argv) {
    if(argc!=2) return 2; std::ofstream out(argv[1]); if(!out)return 3;
    out << "caseName,pattern,errorKind,payload,motherCodeword,shortenedCodeword,received,syndromes,locator,rootPositions,correctedShortened,decodedPayload,status\n";
    for(const auto& p:{scl::bch::block::makeB200Profile(),scl::bch::block::makeB300Profile()}) for(unsigned pattern=0;pattern<208;++pattern) {
        const auto payload=vectorFor(p.payloadLength,pattern); const auto encoded=scl::bch::block::encodeShortened(p,payload);
        for(unsigned error=0;error<7;++error) { auto received=encoded.shortenedCodeword;
            std::string name="NONE"; if(error==1){received[0]^=1U;name="FIRST";} if(error==2){received.back()^=1U;name="LAST";} if(error==3){name="T";for(unsigned j=0;j<p.correctionCapability;++j)received[(j*29U+7U)%received.size()]^=1U;}
            if(error>=4){ name=error==4?"T_PLUS_1":(error==5?"T_PLUS_2":"HIGH_WEIGHT"); unsigned weight=error==4?p.correctionCapability+1U:(error==5?p.correctionCapability+2U:p.correctionCapability+5U); for(unsigned j=0;j<weight;++j)received[(j*29U+7U)%received.size()]^=1U; }
            const auto decoded=scl::bch::block::decodeShortened(p,received);
            out<<p.caseName<<','<<pattern<<','<<name<<','<<scl::bch::block::bitsToString(payload)<<','<<scl::bch::block::bitsToString(encoded.motherCodeword)<<','<<scl::bch::block::bitsToString(encoded.shortenedCodeword)<<','<<scl::bch::block::bitsToString(received)<<','<<numbers(decoded.syndromes)<<','<<numbers(decoded.locatorPolynomial)<<','<<positions(decoded.motherErrorPositions)<<','<<scl::bch::block::bitsToString(decoded.correctedShortenedCodeword)<<','<<scl::bch::block::bitsToString(decoded.payload)<<','<<scl::bch::block::statusName(decoded.status)<<'\n';
        }
    }
}
