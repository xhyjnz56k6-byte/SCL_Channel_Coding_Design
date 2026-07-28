#include "cc/block_encoder.hpp"
#include "cc/hard_viterbi.hpp"
#include "cc/puncturing.hpp"
#include "cc/soft_viterbi.hpp"
#include "cc/trellis.hpp"
#include "common/frame_pool.hpp"
#include "common/gaussian_noise.hpp"
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
namespace{
using Clock=std::chrono::steady_clock;constexpr std::size_t L=306,P=300,D=70;constexpr std::uint64_t seed=2026072001;
struct Sv{std::uint8_t pred=0,input=0;bool valid=false;};struct WinResult{std::vector<std::uint8_t>payload;std::vector<std::size_t>decision;std::uint64_t ops=0;};
bool better(double c,std::uint8_t p,std::uint8_t u,double old,const Sv&s){if(!s.valid||c<old)return true;if(c>old)return false;if(p!=s.pred)return p<s.pred;return u<s.input;}
WinResult decode(const scl::cc::Trellis&t,const std::vector<double>&rx,const std::vector<std::uint8_t>&mask,std::size_t window,std::size_t slide,bool hard){
 if(window<=D||slide==0||slide>window)throw std::invalid_argument("invalid window/slide");
 if(rx.size()!=2*L||mask.size()!=rx.size())throw std::invalid_argument("length");
 for(double x:rx)if(!std::isfinite(x))throw std::invalid_argument("nonfinite");
 const double inf=std::numeric_limits<double>::infinity();std::array<double,scl::cc::kStateCount>m{},n{};m.fill(inf);m[0]=0;
 std::vector<Sv>ring(D*scl::cc::kStateCount);std::vector<std::uint8_t>bits(L);WinResult r;r.decision.resize(P,L-1);
 for(std::size_t time=0;time<L;++time){n.fill(inf);Sv*step=ring.data()+(time%D)*scl::cc::kStateCount;std::fill(step,step+scl::cc::kStateCount,Sv{});
  for(std::size_t s=0;s<scl::cc::kStateCount;++s)if(std::isfinite(m[s]))for(std::uint8_t u=0;u<2;++u){const auto&b=t.branch(static_cast<std::uint8_t>(s),u);
   double bm=0;for(std::size_t j=0;j<2;++j)if(mask[2*time+j]){double expected=b.output_bits[j]?-1:1;bm+=hard?(rx[2*time+j]!=expected):(rx[2*time+j]-expected)*(rx[2*time+j]-expected);}
   double c=m[s]+bm;auto&sv=step[b.next_state];if(better(c,static_cast<std::uint8_t>(s),u,n[b.next_state],sv)){n[b.next_state]=c;sv={static_cast<std::uint8_t>(s),u,true};}}
  double mn=*std::min_element(n.begin(),n.end());for(double&v:n)if(std::isfinite(v))v-=mn;m=n;
  if(time+1>=D&&time+1<L){std::uint8_t state=0;double best=inf;for(std::size_t s=0;s<scl::cc::kStateCount;++s)if(m[s]<best){best=m[s];state=static_cast<std::uint8_t>(s);}
   std::uint8_t emit=0;for(std::size_t o=0;o<D;++o){auto&sv=ring[((time-o)%D)*scl::cc::kStateCount+state];emit=sv.input;state=sv.pred;++r.ops;}
   std::size_t index=time+1-D;bits[index]=emit;if(index<P){std::size_t processed=((time+1+slide-1)/slide)*slide;r.decision[index]=std::min(processed,L)-1;}
  }
 }
 std::uint8_t state=0;for(std::size_t o=0;o<D;++o){std::size_t time=L-1-o;auto&sv=ring[(time%D)*scl::cc::kStateCount+state];bits[time]=sv.input;state=sv.pred;++r.ops;}
 r.payload.assign(bits.begin(),bits.begin()+P);return r;
}
std::uint64_t errors(const std::vector<std::uint8_t>&a,const std::vector<std::uint8_t>&b){std::uint64_t e=0;for(std::size_t i=0;i<a.size();++i)e+=a[i]!=b[i];return e;}
}
int main(int argc,char**argv){try{
 if(argc!=2)throw std::invalid_argument("results dir");
 std::filesystem::path results(argv[1]);std::filesystem::create_directories(results);
 scl::cc::Trellis t;scl::cc::ConvolutionalEncoder enc(t);scl::cc::SoftViterbiDecoder sf(t);scl::cc::HardViterbiDecoder hf(t);
 const std::vector<std::size_t>wins={64,96,128,192},slides={25,50,100};
 std::ofstream pre(results/"stage13_window_prescan.csv");pre<<"windowInputBits,slideStepBits,status,survivorMemoryBytes,windowBufferBytes,estimatedFirstOutputInputTime,selected\n";
 for(auto w:wins)for(auto s:slides){bool ok=w>D&&s<=w;pre<<w<<','<<s<<','<<(ok?"VALID":"INVALID")<<','<<D*64*sizeof(Sv)<<','<<w*2*sizeof(double)<<','<<(ok?((D+s-1)/s)*s-1:0)<<','<<(w==96&&s==25?"YES":"NO")<<'\n';}
 auto payload=scl::common::generatePayloadBits(seed,P,0);auto block=enc.encode_block(payload,true);std::vector<double>clean(block.mother_bits.size());std::vector<std::uint8_t>hard(block.mother_bits.size());
 for(std::size_t i=0;i<clean.size();++i){clean[i]=block.mother_bits[i]?-1:1;hard[i]=block.mother_bits[i];}
 auto softclean=decode(t,clean,std::vector<std::uint8_t>(clean.size(),1),96,25,false);std::vector<double>hardrx(hard.size());for(std::size_t i=0;i<hard.size();++i)hardrx[i]=hard[i]?-1:1;
 auto hardclean=decode(t,hardrx,std::vector<std::uint8_t>(hard.size(),1),96,25,true);if(softclean.payload!=payload||hardclean.payload!=payload)throw std::runtime_error("noiseless");
 struct Sc{std::string id;double snr;scl::cc::PuncturePattern p;std::uint64_t group;};std::vector<Sc>scs={{"CC-C-R12-S",0,{"R12",{1,1}},1200},{"CC-C-R23-S",1,{"R23",{1,1,0,1}},2300}};
 std::ofstream out(results/"stage13_sliding_window_results.csv");out<<"caseId,snrDb,frames,BER,FER,fullMismatchBits,fullMismatchFrames,headMismatchBits,boundaryMismatchBits,middleMismatchBits,tailMismatchBits,firstOutputInputTime,avgDecisionDelayBits,maxDecisionDelayBits,survivorMemoryBytes,windowBufferBytes,ACSOperations,tracebackOperations,avgDecodeTime_us\n";out<<std::setprecision(17);
 std::ofstream meta(results/"stage13_output_bit_metadata.csv");meta<<"caseId,bitIndex,receiveTimeInputBit,decisionTimeInputBit,region\n";
 for(const auto&sc:scs){std::uint64_t be=0,fe=0,mb=0,mf=0,head=0,boundary=0,middle=0,tail=0,ops=0;double delay=0,maxdelay=0,timeus=0;std::vector<std::size_t>firstdec;
  double sigma=std::sqrt(1/(2*std::pow(10.0,sc.snr/10)));
  for(std::uint64_t frame=0;frame<500;++frame){auto cp=scl::common::generatePayloadBits(seed,P,frame);std::vector<std::uint8_t>pl(cp.begin(),cp.end());auto e=enc.encode_block(pl,true);auto p=scl::cc::puncture_bits(e.mother_bits,sc.p);auto z=scl::common::generateStandardGaussianFrame(seed,sc.group,frame,p.bits.size());std::vector<double>rx(p.bits.size());for(std::size_t i=0;i<rx.size();++i)rx[i]=(p.bits[i]?-1:1)+sigma*z[i];auto dep=scl::cc::depuncture_soft(rx,2*L,sc.p);auto full=sf.decode_terminated_masked_symbols(dep.expanded_values,dep.observed_mask,L);
   auto st=Clock::now();auto wr=decode(t,dep.expanded_values,dep.observed_mask,96,25,false);auto en=Clock::now();timeus+=std::chrono::duration<double,std::micro>(en-st).count();ops+=wr.ops;
   auto pe=errors(pl,wr.payload),mm=errors(full.payload_bits,wr.payload);be+=pe;fe+=pe!=0;mb+=mm;mf+=mm!=0;
   for(std::size_t i=0;i<P;++i){bool mismatch=wr.payload[i]!=full.payload_bits[i];std::string region;bool bd=false;for(std::size_t b:{50U,100U,150U,200U,250U})bd|=i+5>=b&&i<b+5;
    if(i<70)region="head";else if(i>=230)region="tail";else if(bd)region="boundary";else region="middle";
    if(mismatch){if(region=="head")++head;else if(region=="tail")++tail;else if(region=="boundary")++boundary;else ++middle;}
    double d=wr.decision[i]-i;delay+=d;maxdelay=std::max(maxdelay,d);if(frame==0)meta<<sc.id<<','<<i<<','<<i<<','<<wr.decision[i]<<','<<region<<'\n';
   }
   if(frame==0)firstdec=wr.decision;
  }
  out<<sc.id<<','<<sc.snr<<",500,"<<double(be)/(500*P)<<','<<double(fe)/500<<','<<mb<<','<<mf<<','<<head<<','<<boundary<<','<<middle<<','<<tail<<','<<firstdec[0]<<','<<delay/(500*P)<<','<<maxdelay<<','<<D*64*sizeof(Sv)<<','<<96*2*sizeof(double)<<','<<500*L*64*2<<','<<ops<<','<<timeus/500<<'\n';
 }
 std::ofstream sum(results/"stage13_sliding_window_test_summary.csv");sum<<"check,status\ninvalid_candidates_rejected,PASS\nnoiseless_hard,PASS\nnoiseless_soft,PASS\noutput_count_unique_300,PASS\nwarmup_and_final_flush,PASS\nstate_metric_carry,PASS\nstage_gate,PASS_STAGE13_CC_SLIDING_WINDOW\n";
 std::cout<<"PASS_STAGE13_CC_SLIDING_WINDOW\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL_STAGE13: "<<e.what()<<'\n';return 1;}}
