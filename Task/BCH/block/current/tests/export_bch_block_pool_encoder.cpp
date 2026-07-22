#include "bch_block/bch_block.hpp"
#include "common/frame_pool.hpp"
#include <fstream>
#include <iostream>

int main(int argc,char**argv){
 if(argc!=4){std::cerr<<"usage: export_bch_block_pool_encoder k200.json k300.json output.csv\n";return 2;}
 std::ofstream out(argv[3]);if(!out)return 3;
 out<<"caseName,frameIndex,payload,motherInformation,parity,motherCodeword,shortenedCodeword,remainder,divisible\n";
 for(const auto& item:{std::pair{scl::bch::block::makeB200Profile(),argv[1]},std::pair{scl::bch::block::makeB300Profile(),argv[2]}}){
  scl::common::PackedFramePoolReader reader(item.second); for(std::uint64_t i=0;i<100;++i){const auto e=scl::bch::block::encodeShortened(item.first,reader.readFrame(i).payloadBits);out<<item.first.caseName<<','<<i<<','<<scl::bch::block::bitsToString(e.payload)<<','<<scl::bch::block::bitsToString(e.motherInformation)<<','<<scl::bch::block::bitsToString(e.parity)<<','<<scl::bch::block::bitsToString(e.motherCodeword)<<','<<scl::bch::block::bitsToString(e.shortenedCodeword)<<','<<scl::bch::block::bitsToString(e.polynomialRemainder)<<','<<e.motherCodewordDivisibleByGenerator<<'\n';}
 }
}
