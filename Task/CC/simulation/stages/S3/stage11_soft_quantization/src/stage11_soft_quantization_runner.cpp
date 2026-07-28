#include "cc/block_encoder.hpp"
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

namespace {
using Clock=std::chrono::steady_clock;
constexpr std::uint64_t kSeed=2026072001ULL;
constexpr std::size_t kL=306,kPayload=300;
constexpr std::int32_t kMetricCap=1000000000;
struct Survivor{std::uint8_t predecessor=0,input=0;bool valid=false;};
struct Scenario{std::string id;double snr;scl::cc::PuncturePattern pattern;std::uint64_t group;};
struct QuantResult{std::vector<std::uint8_t> payload;std::uint64_t input_saturations=0,metric_saturations=0,overflows=0;};
struct Acc{std::uint64_t frames=0,be=0,fe=0,mb=0,mf=0,input_sat=0,metric_sat=0,overflow=0;
 double time_sum=0,time_max=0;std::vector<double> samples;};
std::uint64_t err(const std::vector<std::uint8_t>&a,const std::vector<std::uint8_t>&b){
 if(a.size()!=b.size())throw std::runtime_error("length mismatch");
 std::uint64_t n=0;
 for(std::size_t i=0;i<a.size();++i)n+=a[i]!=b[i];
 return n;}
bool better(std::int32_t c,std::uint8_t p,std::uint8_t u,std::int32_t old,const Survivor&s){
 if(!s.valid||c<old)return true;
 if(c>old)return false;
 if(p!=s.predecessor)return p<s.predecessor;
 return u<s.input;}

QuantResult decode_quantized(const scl::cc::Trellis&trellis,const std::vector<double>&received,
 const std::vector<std::uint8_t>&mask,int bits,double clip){
 if(bits<2||bits>8||!(clip>0)||received.size()!=2*kL||mask.size()!=received.size())
  throw std::invalid_argument("invalid quantized decoder configuration/input");
 const int qmax=(1<<(bits-1))-1;const double step=clip/qmax;
 std::vector<std::int16_t> q(received.size());QuantResult result;
 for(std::size_t i=0;i<received.size();++i){
  if(!std::isfinite(received[i]))throw std::invalid_argument("non-finite received symbol");
  long code=std::lround(received[i]/step);
  if(code>qmax){code=qmax;if(mask[i])++result.input_saturations;}
  if(code<-qmax){code=-qmax;if(mask[i])++result.input_saturations;}
  q[i]=static_cast<std::int16_t>(code);
 }
 const int expected0=static_cast<int>(std::lround(1.0/step));
 const int expected1=-expected0;
 std::array<std::int32_t,scl::cc::kStateCount> metric{},next{};
 metric.fill(kMetricCap);metric[0]=0;
 std::vector<Survivor> survivors(kL*scl::cc::kStateCount);
 for(std::size_t t=0;t<kL;++t){
  next.fill(kMetricCap);Survivor*st=survivors.data()+t*scl::cc::kStateCount;
  std::fill(st,st+scl::cc::kStateCount,Survivor{});
  for(std::size_t s=0;s<scl::cc::kStateCount;++s){if(metric[s]>=kMetricCap)continue;
   for(std::uint8_t u=0;u<2;++u){const auto&br=trellis.branch(static_cast<std::uint8_t>(s),u);
    const int d0=static_cast<int>(q[2*t])-(br.output_bits[0]?expected1:expected0);
    const int d1=static_cast<int>(q[2*t+1])-(br.output_bits[1]?expected1:expected0);
    std::int64_t candidate=metric[s]+(mask[2*t]?d0*d0:0)+(mask[2*t+1]?d1*d1:0);
    if(candidate>std::numeric_limits<std::int32_t>::max()){++result.overflows;candidate=kMetricCap;}
    if(candidate>kMetricCap){++result.metric_saturations;candidate=kMetricCap;}
    auto&sv=st[br.next_state];
    if(better(static_cast<std::int32_t>(candidate),static_cast<std::uint8_t>(s),u,next[br.next_state],sv)){
     next[br.next_state]=static_cast<std::int32_t>(candidate);sv={static_cast<std::uint8_t>(s),u,true};}
   }
  }
  const auto minimum=*std::min_element(next.begin(),next.end());
  if(minimum>=kMetricCap)throw std::runtime_error("no reachable quantized state");
  for(auto&v:next)if(v<kMetricCap)v-=minimum;
  metric=next;
 }
 std::vector<std::uint8_t> decoded(kL);std::uint8_t state=0;
 for(std::size_t t=kL;t>0;--t){const auto&sv=survivors[(t-1)*scl::cc::kStateCount+state];
  if(!sv.valid)throw std::runtime_error("invalid quantized survivor");
  decoded[t-1]=sv.input;state=sv.predecessor;}
 result.payload.assign(decoded.begin(),decoded.begin()+kPayload);return result;
}
double p95(std::vector<double>v){std::sort(v.begin(),v.end());return v[static_cast<std::size_t>(std::ceil(.95*v.size()))-1];}
void add(Acc&a,const std::vector<std::uint8_t>&payload,const std::vector<std::uint8_t>&decoded,
 const std::vector<std::uint8_t>&base,double us,const QuantResult*q=nullptr){
 auto e=err(payload,decoded),m=err(base,decoded);++a.frames;a.be+=e;a.fe+=e!=0;a.mb+=m;a.mf+=m!=0;
 a.time_sum+=us;a.time_max=std::max(a.time_max,us);a.samples.push_back(us);
 if(q){a.input_sat+=q->input_saturations;a.metric_sat+=q->metric_saturations;a.overflow+=q->overflows;}}
}

int main(int argc,char**argv){
 try{
  if(argc!=2)throw std::invalid_argument("expected results directory");
  const std::filesystem::path results(argv[1]);std::filesystem::create_directories(results);
  const std::vector<Scenario>scenarios={{"CC-B-R12-S",-0.5,{"R12_11",{1,1}},1200},
   {"CC-B-R12-S",0,{"R12_11",{1,1}},1200},{"CC-B-R23-S",0.5,{"R23_B_1101",{1,1,0,1}},2300},
   {"CC-B-R23-S",1,{"R23_B_1101",{1,1,0,1}},2300}};
  const scl::cc::Trellis trellis;scl::cc::ConvolutionalEncoder encoder(trellis);
  const scl::cc::SoftViterbiDecoder float_decoder(trellis);
  const std::vector<double>clips={2,3,4,6};std::array<std::uint64_t,4>pm{},ps{},po{};
  for(const auto&sc:scenarios){double sigma=std::sqrt(1/(2*std::pow(10.0,sc.snr/10)));
   for(std::uint64_t frame=0;frame<200;++frame){auto cp=scl::common::generatePayloadBits(kSeed,kPayload,frame);
    std::vector<std::uint8_t>payload(cp.begin(),cp.end());auto enc=encoder.encode_block(payload,true);
    auto punct=scl::cc::puncture_bits(enc.mother_bits,sc.pattern);auto noise=scl::common::generateStandardGaussianFrame(kSeed,sc.group,frame,punct.bits.size());
    std::vector<double>rx(punct.bits.size());for(std::size_t i=0;i<rx.size();++i)rx[i]=(punct.bits[i]? -1.0:1.0)+sigma*noise[i];
    auto dep=scl::cc::depuncture_soft(rx,2*kL,sc.pattern);
    auto base=float_decoder.decode_terminated_masked_symbols(dep.expanded_values,dep.observed_mask,kL).payload_bits;
    for(std::size_t c=0;c<clips.size();++c){auto q=decode_quantized(trellis,dep.expanded_values,dep.observed_mask,4,clips[c]);
     pm[c]+=q.payload!=base;ps[c]+=q.input_saturations;po[c]+=std::count(dep.observed_mask.begin(),dep.observed_mask.end(),1);}
   }
  }
  std::size_t selected=0;for(std::size_t c=1;c<clips.size();++c)
   if(pm[c]<pm[selected]||(pm[c]==pm[selected]&&ps[c]<ps[selected]))selected=c;
  std::ofstream pre(results/"stage11_quantization_prescan.csv");pre<<"clipMax,q4FloatMismatchFrames,inputSaturations,observedSymbols,selected\n";
  for(std::size_t c=0;c<clips.size();++c)pre<<clips[c]<<','<<pm[c]<<','<<ps[c]<<','<<po[c]<<','<<(c==selected?"YES":"NO")<<'\n';
  const double clip=clips[selected];const std::vector<int>bits={3,4,6};
  std::ofstream out(results/"stage11_soft_quantization_results.csv");
  out<<"caseId,snrDb,mode,bits,clipMax,step,frames,payloadBitErrors,payloadErrorFrames,BER,FER,floatMismatchBits,floatMismatchFrames,avgDecodeTime_us,p95DecodeTime_us,maxDecodeTime_us,rawThroughput_Mbps,inputSaturationCount,inputObservedCount,inputMemoryBytes,pathMetricMemoryBytes,survivorMemoryBytes,pathMetricSaturationCount,integerOverflowCount\n";
  out<<std::setprecision(17);
  for(const auto&sc:scenarios){std::array<Acc,4>a;double sigma=std::sqrt(1/(2*std::pow(10.0,sc.snr/10)));std::size_t n=0,observed=0;
   for(std::uint64_t frame=0;frame<1000;++frame){auto cp=scl::common::generatePayloadBits(kSeed,kPayload,frame);
    std::vector<std::uint8_t>payload(cp.begin(),cp.end());auto enc=encoder.encode_block(payload,true);
    auto punct=scl::cc::puncture_bits(enc.mother_bits,sc.pattern);n=punct.bits.size();auto noise=scl::common::generateStandardGaussianFrame(kSeed,sc.group,frame,n);
    std::vector<double>rx(n);for(std::size_t i=0;i<n;++i)rx[i]=(punct.bits[i]?-1.0:1.0)+sigma*noise[i];
    auto dep=scl::cc::depuncture_soft(rx,2*kL,sc.pattern);observed=std::count(dep.observed_mask.begin(),dep.observed_mask.end(),1);
    auto s=Clock::now();auto base=float_decoder.decode_terminated_masked_symbols(dep.expanded_values,dep.observed_mask,kL);auto e=Clock::now();
    add(a[0],payload,base.payload_bits,base.payload_bits,std::chrono::duration<double,std::micro>(e-s).count());
    for(std::size_t b=0;b<bits.size();++b){s=Clock::now();auto qr=decode_quantized(trellis,dep.expanded_values,dep.observed_mask,bits[b],clip);e=Clock::now();
     add(a[b+1],payload,qr.payload,base.payload_bits,std::chrono::duration<double,std::micro>(e-s).count(),&qr);}
   }
   for(std::size_t m=0;m<a.size();++m){const bool fl=m==0;int b=fl?64:bits[m-1];double step=fl?0:clip/((1<<(b-1))-1);const auto&v=a[m];
    out<<sc.id<<','<<sc.snr<<','<<(fl?"SOFT_FLOAT":"SOFT_Q"+std::to_string(b))<<','<<b<<','<<clip<<','<<step<<','<<v.frames<<','<<v.be<<','<<v.fe<<','<<double(v.be)/(v.frames*kPayload)<<','<<double(v.fe)/v.frames<<','<<v.mb<<','<<v.mf<<','<<v.time_sum/v.frames<<','<<p95(v.samples)<<','<<v.time_max<<','<<300/(v.time_sum/v.frames)<<','<<v.input_sat<<','<<observed*v.frames<<','<<(fl?n*8:(n*b+7)/8)<<','<<(fl?2*64*8:2*64*4)<<','<<kL*64*sizeof(Survivor)<<','<<v.metric_sat<<','<<v.overflow<<'\n';
   }
  }
  std::cout<<"PASS_STAGE11_CC_SOFT_QUANTIZATION_RUNNER clip="<<clip<<'\n';return 0;
 }catch(const std::exception&e){std::cerr<<"FAIL_STAGE11: "<<e.what()<<'\n';return 1;}
}
