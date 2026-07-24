#include "bch_block/bch_block.hpp"
#include <fstream>
#include <iostream>

int main(int argc,char**argv){if(argc!=2)return 2;std::ofstream out(argv[1]);if(!out)return 3;out<<"fieldDegree,operation,a,b,result\n";
 for(const auto&p:{scl::bch::block::makeB200Profile(),scl::bch::block::makeB300Profile(),scl::bch::block::makeB300426Profile()}){scl::bch::block::Gf2m f(p.fieldDegree,p.primitivePolynomial);const unsigned period=f.order()-1U;
  for(unsigned e=0;e<period;++e)out<<p.fieldDegree<<",alpha,"<<e<<",,"<<f.alphaPower(e)<<'\n';
  for(unsigned a=1;a<f.order();++a){out<<p.fieldDegree<<",log,"<<a<<",,"<<f.logarithm(a)<<'\n';out<<p.fieldDegree<<",inverse,"<<a<<",,"<<f.inverse(a)<<'\n';}
  for(unsigned i=0;i<256;++i){auto a=static_cast<scl::bch::block::Gf2m::Element>((i*37U+11U)%f.order());auto b=static_cast<scl::bch::block::Gf2m::Element>((i*53U+7U)%period+1U);out<<p.fieldDegree<<",multiply,"<<a<<','<<b<<','<<f.multiply(a,b)<<'\n';out<<p.fieldDegree<<",divide,"<<a<<','<<b<<','<<f.divide(a,b)<<'\n';std::vector<scl::bch::block::Gf2m::Element> c={1U,a,b};out<<p.fieldDegree<<",evaluate,"<<a<<','<<b<<','<<f.evaluate(c,b)<<'\n';}
 }}
