#include "bch_segmented/bch15_encoder.hpp"

#include <array>
#include <fstream>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using scl::common::Bit;
using scl::common::BitVector;
using scl::bch::segmented::kBch15CodewordLength;
using scl::bch::segmented::kBch15MessageLength;

struct ReferenceVector { const char* name; const char* message; const char* parity; const char* codeword; };

BitVector bitsFromText(const std::string& text) {
    BitVector bits; bits.reserve(text.size());
    for (char c : text) { if (c != '0' && c != '1') throw std::runtime_error("invalid fixture bit"); bits.push_back(static_cast<Bit>(c - '0')); }
    return bits;
}
std::string textFromBits(const BitVector& bits) { std::string text; text.reserve(bits.size()); for (Bit bit : bits) text.push_back(static_cast<char>('0' + bit)); return text; }
BitVector messageFromDecimal(unsigned value) { BitVector bits(kBch15MessageLength, 0U); for (std::size_t i=0;i<kBch15MessageLength;++i) bits[i]=static_cast<Bit>((value >> (10U-i)) & 1U); return bits; }

// Independent test-only path: explicit descending-coefficient polynomial long division.
BitVector referenceEncode(const BitVector& message) {
    if (message.size()!=kBch15MessageLength) throw std::runtime_error("reference length");
    BitVector dividend=message; dividend.insert(dividend.end(),4U,0U);
    const std::array<Bit,5> generator{{1U,0U,0U,1U,1U}};
    for(std::size_t i=0;i<kBch15MessageLength;++i) if(dividend[i]) for(std::size_t j=0;j<generator.size();++j) dividend[i+j]^=generator[j];
    BitVector result=message; result.insert(result.end(),dividend.end()-4,dividend.end()); return result;
}
BitVector remainder(const BitVector& codeword) {
    BitVector work=codeword; const std::array<Bit,5> generator{{1U,0U,0U,1U,1U}};
    for(std::size_t i=0;i<kBch15MessageLength;++i) if(work[i]) for(std::size_t j=0;j<generator.size();++j) work[i+j]^=generator[j];
    return BitVector(work.end()-4,work.end());
}
void require(bool value,const std::string& why){if(!value)throw std::runtime_error(why);}

}  // namespace

int main(int argc,char** argv) {
    try {
        const std::string outputDir=argc>1?argv[1]:".";
        const std::array<ReferenceVector,6> fixtures{{
            {"zero","00000000000","0000","000000000000000"}, {"highest","10000000000","1001","100000000001001"},
            {"lowest","00000000001","0011","000000000010011"}, {"ones","11111111111","1111","111111111111111"},
            {"alternating_one","10101010101","1011","101010101011011"}, {"alternating_zero","01010101010","0100","010101010100100"}}};
        for(const auto& f:fixtures){ const BitVector reference=referenceEncode(bitsFromText(f.message)); require(textFromBits(reference)==f.codeword,std::string("fixture derivation ")+f.name); require(textFromBits(BitVector(reference.end()-4,reference.end()))==f.parity,"fixture parity"); }
        for(const auto& text:std::array<const char*,6>{{"00000000000","11111111111","10000000000","00000000001","10101010101","01010101010"}}) (void)scl::bch::segmented::encodeBch15Systematic(bitsFromText(text));
        bool lengthError=false, bitError=false; try{(void)scl::bch::segmented::encodeBch15Systematic(BitVector(10,0U));}catch(const std::invalid_argument&){lengthError=true;} try{BitVector bad(11,0U);bad[0]=2U;(void)scl::bch::segmented::encodeBch15Systematic(bad);}catch(const std::invalid_argument&){bitError=true;} require(lengthError&&bitError,"invalid input rejection");
        std::ofstream csv(outputDir+"/all_bch15_codewords.csv"); csv<<"inputDecimal,messageBits,parityBits,codewordBits,remainder,validCodeword\n";
        std::set<std::string> unique; unsigned remainderMismatch=0,systematicMismatch=0,referenceMismatch=0;
        for(unsigned value=0;value<2048U;++value){ const BitVector message=messageFromDecimal(value); const BitVector primary=scl::bch::segmented::encodeBch15Systematic(message); const BitVector ref=referenceEncode(message); const BitVector rem=remainder(primary); require(primary.size()==kBch15CodewordLength,"codeword length"); if(!std::equal(message.begin(),message.end(),primary.begin()))++systematicMismatch; if(primary!=ref)++referenceMismatch; if(rem!=BitVector(4,0U))++remainderMismatch; unique.insert(textFromBits(primary)); csv<<value<<','<<textFromBits(message)<<','<<textFromBits(BitVector(primary.end()-4,primary.end()))<<','<<textFromBits(primary)<<','<<textFromBits(rem)<<','<<(rem==BitVector(4,0U)?"true":"false")<<'\n'; }
        const unsigned duplicates=2048U-static_cast<unsigned>(unique.size()); require(remainderMismatch==0&&systematicMismatch==0&&referenceMismatch==0&&duplicates==0,"exhaustive verification");
        std::ofstream summary(outputDir+"/test_summary.csv"); summary<<"metric,value\nencodedCount,2048\nremainderMismatch,"<<remainderMismatch<<"\nsystematicBitMismatch,"<<systematicMismatch<<"\nduplicateCodewordCount,"<<duplicates<<"\nindependentReferenceMismatch,"<<referenceMismatch<<"\nfixedVectorMismatch,0\nexhaustive2048Mismatch,0\n";
        std::cout<<"BCH15 encoder PASS: 2048/2048\n"; return 0;
    } catch(const std::exception& error) { std::cerr<<"BCH15 encoder FAIL: "<<error.what()<<'\n'; return 1; }
}
