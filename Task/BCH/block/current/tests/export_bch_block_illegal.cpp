#include "bch_block/bch_block.hpp"
#include <fstream>
using namespace scl::bch::block;
int main(int argc,char**argv){if(argc!=2)return 2;std::ofstream o(argv[1]);o<<"category,status\n";auto p=makeB200Profile();auto w=encodeShortened(p,scl::common::BitVector(200,0U)).shortenedCodeword;
 auto emit=[&](const char*n,const BlockBchProfile&q,const scl::common::BitVector&v){o<<n<<','<<statusName(decodeShortenedNoThrow(q,v).status)<<'\n';};
 emit("decoder_short",p,scl::common::BitVector(w.size()-1,0));emit("decoder_long",p,scl::common::BitVector(w.size()+1,0));auto bad=w;bad[0]=2;emit("decoder_nonbinary",p,bad);auto q=p;q.motherN--;emit("decoder_invalid_profile",q,w);
 auto gf=[&](const char*n,auto fn){try{fn();o<<n<<",NO_EXCEPTION\n";}catch(...){o<<n<<",EXCEPTION\n";}};Gf2m f(8,0x11D);gf("gf_divide_zero",[&]{f.divide(1,0);});gf("gf_inverse_zero",[&]{f.inverse(0);});gf("gf_log_zero",[&]{f.logarithm(0);});gf("gf_element_range",[&]{f.multiply(256,1);});gf("gf_zero_negative_power",[&]{f.power(0,-1);});gf("gf_nonprimitive",[&]{Gf2m x(8,0x11B);(void)x;});}
