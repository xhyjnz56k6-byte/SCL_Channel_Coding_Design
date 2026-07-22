#include "bch_segmented/bch15_encoder.hpp"
#include "bch_segmented/bch15_lookup_decoder.hpp"
#include "bch_segmented/bch15_segmented_adapter.hpp"

#include <filesystem>
#include <fstream>
#include <stdexcept>

using namespace scl::bch::segmented;

namespace {
std::string bits(const scl::common::BitVector& v) { std::string s; for (auto b : v) s += static_cast<char>('0' + b); return s; }
std::string status(Bch15DecodeStatus value) {
    switch (value) { case Bch15DecodeStatus::NO_ERROR: return "NO_ERROR"; case Bch15DecodeStatus::CORRECTED_SINGLE_ERROR: return "CORRECTED_SINGLE_ERROR"; case Bch15DecodeStatus::POST_CHECK_FAILED: return "POST_CHECK_FAILED"; default: return "UNRECOGNIZED_SYNDROME"; }
}
scl::common::BitVector message(unsigned index) { scl::common::BitVector v(11U,0U); for(unsigned i=0;i<11U;++i) v[i]=(index >> (10U-i))&1U; return v; }
void checked(std::ofstream& out, const std::string& name) { out.flush(); if (!out) throw std::runtime_error("cannot write " + name); }
}

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::runtime_error("usage: export_bch06_cpp_reference <output-dir>");
        std::filesystem::path root(argv[1]); std::filesystem::create_directories(root);
        std::ofstream encoder(root / "cpp_encoder_reference.csv"), syndrome(root / "cpp_syndrome_reference.csv"), noError(root / "cpp_no_error_decode.csv"), single(root / "cpp_single_error_decode.csv");
        if(!encoder||!syndrome||!noError||!single) throw std::runtime_error("cannot open output");
        encoder << "messageIndex,messageBits,parityBits,codewordBits,syndromeBits,syndromeValue\n";
        syndrome << "errorPosition,syndromeBits,syndromeValue\n";
        noError << "messageIndex,messageBits,receivedBits,syndromeBefore,syndromeAfter,lookupHit,correctedPosition,status,correctedCodeword,decodedMessage\n";
        single << "messageIndex,errorPosition,receivedBits,syndromeBefore,syndromeAfter,lookupHit,correctedPosition,status,correctedCodeword,decodedMessage\n";
        const SyndromeTable table=buildBch15SyndromeTable();
        for(unsigned p=0;p<15U;++p) { scl::common::BitVector e(15U,0U); e[p]=1U; auto s=computeBch15Syndrome(e); syndrome<<p<<','<<bits(s)<<','<<syndromeValue(s)<<'\n'; }
        for(unsigned index=0;index<2048U;++index) {
            auto m=message(index); auto c=encodeBch15Systematic(m); auto s=computeBch15Syndrome(c);
            encoder<<index<<','<<bits(m)<<','<<bits(scl::common::BitVector(c.begin()+11,c.end()))<<','<<bits(c)<<','<<bits(s)<<','<<syndromeValue(s)<<'\n';
            auto d=decodeBch15Lookup(c,table);
            noError<<index<<','<<bits(m)<<','<<bits(c)<<','<<bits(d.syndromeBefore)<<','<<bits(d.syndromeAfter)<<','<<(d.lookupHit?"true":"false")<<','<<d.correctedPosition<<','<<status(d.status)<<','<<bits(d.correctedCodeword)<<','<<bits(d.decodedMessage)<<'\n';
            for(unsigned p=0;p<15U;++p) { auto r=c; r[p]^=1U; auto x=decodeBch15Lookup(r,table); single<<index<<','<<p<<','<<bits(r)<<','<<bits(x.syndromeBefore)<<','<<bits(x.syndromeAfter)<<','<<(x.lookupHit?"true":"false")<<','<<x.correctedPosition<<','<<status(x.status)<<','<<bits(x.correctedCodeword)<<','<<bits(x.decodedMessage)<<'\n'; }
        }
        checked(encoder,"encoder"); checked(syndrome,"syndrome"); checked(noError,"noError"); checked(single,"single");
        return 0;
    } catch(const std::exception& e) { return 1; }
}
