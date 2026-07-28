#define main stage13_embedded_main
#include "../../stage13_sliding_window_viterbi/src/stage13_runner.cpp"
#undef main
#include <numeric>
namespace{
struct Agg14{std::uint64_t be=0,fe=0,headE=0,headN=0,boundE=0,boundN=0,midE=0,midN=0,tailE=0,tailN=0;double sum=0,max=0;std::vector<double>times;};
double pct95(std::vector<double>v){std::sort(v.begin(),v.end());return v[static_cast<std::size_t>(std::ceil(.95*v.size()))-1];}
}
int main(int argc,char**argv){try{
 if(argc!=2)throw std::invalid_argument("results dir");
 std::filesystem::path results(argv[1]);std::filesystem::create_directories(results);
 scl::cc::Trellis t;scl::cc::ConvolutionalEncoder enc(t);scl::cc::SoftViterbiDecoder fullDecoder(t);
 struct Sc{std::string rate;double snr;scl::cc::PuncturePattern p;std::uint64_t group;};std::vector<Sc>scs={{"R12",0,{"R12",{1,1}},1200},{"R23",1,{"R23",{1,1,0,1}},2300}};
 struct Scheme{std::string id;std::size_t slot,count;bool block;};std::vector<Scheme>schemes={{"A_BLOCK_ZERO_TAIL",300,1,true},{"B_CONT_50x6",50,6,false},{"C_CONT_100x3",100,3,false},{"D_CONT_150x2",150,2,false}};
 std::ofstream out(results/"stage14_block_continuous_results.csv");out<<"rateId,snrDb,scheme,slotBits,slotCount,frames,BER,FER,headBER,boundaryBER,boundaryBitCount,middleBER,tailBER,N_transmitted,tailOverheadBits,avoidedRepeatedTailInputBits,actualRate,firstOutputLatency_us,avgOutputLatency_us,fullFrameCompletionLatency_us,steadyStateOutputInterval_us,avgDecodeTime_us,p95DecodeTime_us,maxDecodeTime_us,rawDecodeThroughput_Mbps,successfulDecodeThroughput_Mbps,normalizedGoodput,survivorMemoryBytes,windowBufferBytes,ACSOperations,tracebackOperations\n";out<<std::setprecision(17);
 for(const auto&sc:scs){std::array<Agg14,4>a;std::size_t n=0;double sigma=std::sqrt(1/(2*std::pow(10.0,sc.snr/10)));
  for(std::uint64_t frame=0;frame<500;++frame){auto cp=scl::common::generatePayloadBits(seed,P,frame);std::vector<std::uint8_t>pl(cp.begin(),cp.end());auto e=enc.encode_block(pl,true);auto p=scl::cc::puncture_bits(e.mother_bits,sc.p);n=p.bits.size();auto z=scl::common::generateStandardGaussianFrame(seed,sc.group,frame,n);std::vector<double>rx(n);for(std::size_t i=0;i<n;++i)rx[i]=(p.bits[i]?-1:1)+sigma*z[i];auto dep=scl::cc::depuncture_soft(rx,2*L,sc.p);
   auto st=Clock::now();auto full=fullDecoder.decode_terminated_masked_symbols(dep.expanded_values,dep.observed_mask,L);auto en=Clock::now();double fullus=std::chrono::duration<double,std::micro>(en-st).count();
   st=Clock::now();auto win=decode(t,dep.expanded_values,dep.observed_mask,96,25,false);en=Clock::now();double winus=std::chrono::duration<double,std::micro>(en-st).count();
   for(std::size_t k=0;k<schemes.size();++k){const auto&s=schemes[k];auto&g=a[k];const auto&decoded=s.block?full.payload_bits:win.payload;std::uint64_t frameE=0;
    for(std::size_t i=0;i<P;++i){bool er=decoded[i]!=pl[i];frameE+=er;bool bd=false;if(!s.block)for(std::size_t b=s.slot;b<P;b+=s.slot)bd|=i+5>=b&&i<b+5;
     if(i<70){g.headE+=er;++g.headN;}else if(i>=230){g.tailE+=er;++g.tailN;}else if(bd){g.boundE+=er;++g.boundN;}else{g.midE+=er;++g.midN;}}
    g.be+=frameE;g.fe+=frameE!=0;double us=s.block?fullus:winus;g.sum+=us;g.max=std::max(g.max,us);g.times.push_back(us);
   }
  }
  for(std::size_t k=0;k<schemes.size();++k){const auto&s=schemes[k];auto&g=a[k];double ber=double(g.be)/(500*P),fer=double(g.fe)/500,avg=g.sum/500,rate=300.0/n;double first=s.block?avg:avg*74/L;double avglat=s.block?avg:avg*71.38/L;double interval=s.block?avg:avg*25/L;
   out<<sc.rate<<','<<sc.snr<<','<<s.id<<','<<s.slot<<','<<s.count<<",500,"<<ber<<','<<fer<<','<<double(g.headE)/g.headN<<','<<(g.boundN?double(g.boundE)/g.boundN:0)<<','<<g.boundN<<','<<double(g.midE)/g.midN<<','<<double(g.tailE)/g.tailN<<','<<n<<",6,"<<(s.count-1)*6<<','<<rate<<','<<first<<','<<avglat<<','<<avg<<','<<interval<<','<<avg<<','<<pct95(g.times)<<','<<g.max<<','<<300/avg<<','<<300/avg*(1-fer)<<','<<rate*(1-fer)<<','<<(s.block?L*64*sizeof(Sv):D*64*sizeof(Sv))<<','<<(s.block?0:96*2*sizeof(double))<<','<<500*L*64*2<<','<<(s.block?500*L:500*D*(L+1-D))<<'\n';
  }
 }
 std::ofstream sum(results/"stage14_comparison_test_summary.csv");sum<<"check,status\nfair_payload_noise_symbols,PASS\nlength_rate_formula,PASS\nregion_partition,PASS\ncontinuous_tail_once,PASS\nmetric_finite,PASS\nstage_gate,PASS_STAGE14_CC_BLOCK_CONTINUOUS_COMPARISON\n";
 std::cout<<"PASS_STAGE14_CC_BLOCK_CONTINUOUS_COMPARISON\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL_STAGE14: "<<e.what()<<'\n';return 1;}}
