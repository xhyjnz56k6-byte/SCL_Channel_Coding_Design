#define main stage05_embedded_main
#include "../../stage05_awgn_trial/cpp/stage05_awgn_trial_runner.cpp"
#undef main

namespace {
constexpr auto kStartDomain12=
 static_cast<scl::bch::s2::stage01::RandomDomain>(0x424c4f434b535452ULL);
struct BlockPoint{Point awgn;std::string experiment;std::size_t parameterIndex;double ratio;};
struct BlockCounters: Counters{
 std::vector<std::uint64_t> latency;
 std::uint64_t totalBlockedSymbols=0,blockedRawErrorBits=0,nonBlockedRawErrorBits=0;
 std::uint64_t affectedBlocks=0,maxAffectedBlocks=0,startSum=0,minStart=UINT64_MAX,maxStart=0;
};
std::size_t lengthFor(double rho,std::size_t n){
 require(std::isfinite(rho)&&rho>=0&&rho<=1,"invalid ratio");
 return rho==0?0:std::min(n,std::max<std::size_t>(1,static_cast<std::size_t>(std::floor(rho*n+.5))));
}
std::size_t startFor(const scl::bch::s2::stage01::RandomIdentity& base,std::size_t n,
                     std::size_t l,std::size_t p){
 auto id=base;id.ebn0Index=(base.ebn0Index<<32U)^p;
 return l==n?0:static_cast<std::size_t>(
  scl::bch::s2::stage01::randomWord(id,kStartDomain12,0,0)%(n-l+1));
}
std::size_t affected(const CaseContract& c,std::size_t start,std::size_t length){
 if(length==0)return 0;std::size_t offset=0,count=0;
 for(auto blockLength:c.encodedLengthPerBlock){
  if(start<offset+blockLength&&start+length>offset)++count;offset+=blockLength;
 }return count;
}
void addBlock(BlockCounters& a,const BlockCounters& b){
 add(a,b);a.decodeTimeTotalNs+=b.decodeTimeTotalNs;a.latency.insert(a.latency.end(),b.latency.begin(),b.latency.end());
 a.totalBlockedSymbols+=b.totalBlockedSymbols;a.blockedRawErrorBits+=b.blockedRawErrorBits;
 a.nonBlockedRawErrorBits+=b.nonBlockedRawErrorBits;a.affectedBlocks+=b.affectedBlocks;
 a.maxAffectedBlocks=std::max(a.maxAffectedBlocks,b.maxAffectedBlocks);a.startSum+=b.startSum;
 a.minStart=std::min(a.minStart,b.minStart);a.maxStart=std::max(a.maxStart,b.maxStart);
}
BlockCounters simulate(const BlockPoint& p,std::uint64_t first,std::uint64_t count,std::uint64_t seed){
 const auto& c=scl::bch::s2::stage02::caseContract(p.awgn.id);BlockCounters r;
 const auto l=lengthFor(p.ratio,c.totalEncodedLength);
 const double sigma=std::sqrt(scl::bch::s2::stage01::awgnSigma2(c.actualRate,p.awgn.ebn0Db));
 r.latency.reserve(static_cast<std::size_t>(count));
 for(std::uint64_t frame=first;frame<first+count;++frame){
  const auto payload=payloadFrame("stage12_blockage_formal",c.caseId,p.awgn.ebn0Index,frame,c.payloadLength,seed);
  const auto encoded=scl::bch::s2::stage02::encodeFrame(c.id,payload).encodedBits;
  const scl::bch::s2::stage01::RandomIdentity id{seed,"stage12_blockage_formal",c.caseId,p.awgn.ebn0Index,frame};
  const auto z=scl::bch::s2::stage01::standardGaussianFrame(id,scl::bch::s2::stage01::RandomDomain::Awgn,encoded.size());
  const auto start=startFor(id,encoded.size(),l,p.parameterIndex);
  scl::common::BitVector hard(encoded.size(),0);
  for(std::size_t k=0;k<encoded.size();++k){
   const bool blocked=l>0&&k>=start&&k<start+l;
   const double y=(blocked?0.0:scl::bch::s2::stage01::bpsk(encoded[k]))+sigma*z[k];
   hard[k]=static_cast<scl::common::Bit>(scl::bch::s2::stage01::hardDecision(y));
   if(hard[k]!=encoded[k]){if(blocked)++r.blockedRawErrorBits;else ++r.nonBlockedRawErrorBits;}
  }
  auto begin=std::chrono::steady_clock::now();const auto decoded=decodeAudited(c,hard);
  auto end=std::chrono::steady_clock::now();const auto ns=static_cast<std::uint64_t>(
   std::chrono::duration_cast<std::chrono::nanoseconds>(end-begin).count());
  const auto errors=bitErrors(payload,decoded.payload);++r.totalFrames;r.totalPayloadBits+=c.payloadLength;
  r.payloadErrorBits+=errors;r.payloadErrorFrames+=errors!=0;r.decoderFailureFrames+=!decoded.reportedSuccess;
  r.miscorrectionFrames+=decoded.reportedSuccess&&errors!=0;r.undetectedErrorFrames+=decoded.allNoError&&errors!=0;
  r.trueSuccessFrames+=errors==0;r.noiseChecksum+=hashNoise(z);r.decodeTimeTotalNs+=ns;r.latency.push_back(ns);
  r.totalBlockedSymbols+=l;const auto ac=affected(c,start,l);r.affectedBlocks+=ac;r.maxAffectedBlocks=std::max<std::uint64_t>(r.maxAffectedBlocks,ac);
  r.startSum+=start;r.minStart=std::min<std::uint64_t>(r.minStart,start);r.maxStart=std::max<std::uint64_t>(r.maxStart,start);
 }return r;
}
std::vector<BlockPoint> readBlockPoints(const fs::path& path){
 std::ifstream in(path);require(bool(in),"cannot open blockage points");std::string line;std::getline(in,line);
 require(line=="experimentType,caseId,ebn0Index,ebn0Db,blockageParameterIndex,requestedBlockageRatio","point header mismatch");
 std::vector<BlockPoint> out;while(std::getline(in,line)){if(line.empty())continue;std::istringstream s(line);
  std::string ex,id,ei,db,pi,rho;std::getline(s,ex,',');std::getline(s,id,',');std::getline(s,ei,',');
  std::getline(s,db,',');std::getline(s,pi,',');std::getline(s,rho,',');
  out.push_back({{parseCase(id),id,std::stoull(ei),std::stod(db)},ex,std::stoull(pi),std::stod(rho)});}
 require(out.size()==104,"formal blockage point count must be 104");return out;
}
void header(std::ostream& o){o<<"stageId,gitCommit,experimentType,caseId,legendLabel,payloadLength,encodedLength,actualRate,"
"channelType,ebn0Db,snrDb,blockageAmplitude,requestedBlockageRatio,actualBlockageRatio,blockageLengthSymbols,"
"blockageStartPolicy,meanBlockageStart,minBlockageStart,maxBlockageStart,totalBlockedSymbols,blockedRawErrorBits,"
"nonBlockedRawErrorBits,blockedRawBer,nonBlockedRawBer,affectedCodeBlockCountTotal,meanAffectedCodeBlockCount,"
"maxAffectedCodeBlockCount,totalFrames,totalPayloadBits,payloadErrorBits,payloadErrorFrames,decoderFailureFrames,"
"miscorrectionFrames,undetectedErrorFrames,trueSuccessFrames,decodeTimeTotalNs,decodeTimeMeanNs,decodeTimeP50Ns,"
"decodeTimeP95Ns,decodeTimeP99Ns,ber,fer,decoderFailureRate,miscorrectionRate,undetectedErrorRate,trueSuccessRate,"
"stopReason,checkpointId,shardId,blockageParameterIndex\n";}
void row(std::ostream& o,const BlockPoint& p,const BlockCounters& c,const std::string& sha,const std::string& stop){
 const auto& x=scl::bch::s2::stage02::caseContract(p.awgn.id);const auto l=lengthFor(p.ratio,x.totalEncodedLength);
 auto rate=[](std::uint64_t a,std::uint64_t b){return b?double(a)/b:0.0;};
 const auto nonblocked=c.totalFrames*x.totalEncodedLength-c.totalBlockedSymbols;
 o<<std::setprecision(17)<<"stage12_blockage_formal,"<<sha<<','<<p.experiment<<','<<x.caseId<<','<<x.legendLabel<<','
 <<x.payloadLength<<','<<x.totalEncodedLength<<','<<x.actualRate<<",BLOCKAGE_AWGN,"<<p.awgn.ebn0Db<<','
 <<p.awgn.ebn0Db+10*std::log10(x.actualRate)<<",0,"<<p.ratio<<','<<double(l)/x.totalEncodedLength<<','<<l
 <<",RANDOM_PER_FRAME,"<<double(c.startSum)/c.totalFrames<<','<<c.minStart<<','<<c.maxStart<<','<<c.totalBlockedSymbols
 <<','<<c.blockedRawErrorBits<<','<<c.nonBlockedRawErrorBits<<','<<rate(c.blockedRawErrorBits,c.totalBlockedSymbols)
 <<','<<rate(c.nonBlockedRawErrorBits,nonblocked)<<','<<c.affectedBlocks<<','<<double(c.affectedBlocks)/c.totalFrames
 <<','<<c.maxAffectedBlocks<<','<<c.totalFrames<<','<<c.totalPayloadBits<<','<<c.payloadErrorBits<<','
 <<c.payloadErrorFrames<<','<<c.decoderFailureFrames<<','<<c.miscorrectionFrames<<','<<c.undetectedErrorFrames<<','
 <<c.trueSuccessFrames<<','<<c.decodeTimeTotalNs<<','<<c.decodeTimeTotalNs/c.totalFrames<<','
 <<percentile(c.latency,.5)<<','<<percentile(c.latency,.95)<<','<<percentile(c.latency,.99)<<','
 <<rate(c.payloadErrorBits,c.totalPayloadBits)<<','<<rate(c.payloadErrorFrames,c.totalFrames)<<','
 <<rate(c.decoderFailureFrames,c.totalFrames)<<','<<rate(c.miscorrectionFrames,c.totalFrames)<<','
 <<rate(c.undetectedErrorFrames,c.totalFrames)<<','<<rate(c.trueSuccessFrames,c.totalFrames)<<','<<stop
 <<",stage12_"<<p.experiment<<'_'<<x.caseId<<'_'<<p.parameterIndex<<",0,"<<p.parameterIndex<<'\n';
}
}
int main(int argc,char** argv){try{
 if(argc!=5)throw std::invalid_argument("usage: runner POINTS OUTPUT SEED GIT_COMMIT");
 auto points=readBlockPoints(argv[1]);fs::path output(argv[2]);fs::create_directories(output/"checkpoints");
 std::ofstream raw(output/"stage12_blockage_formal_result_raw.csv"),sum(output/"stage12_blockage_formal_result_summary.csv"),
 merge(output/"stage12_blockage_formal_merge_audit.csv");require(raw&&sum&&merge,"cannot create outputs");header(raw);header(sum);
 merge<<"experimentType,caseId,parameterIndex,totalFrames,integerAccountingPass,passed\n";
 for(const auto& p:points){BlockCounters c;std::string stop="CONTINUE";
  while(c.totalFrames<50000){auto n=std::min<std::uint64_t>(100,50000-c.totalFrames);addBlock(c,simulate(p,c.totalFrames,n,std::stoull(argv[3])));
   if(c.totalFrames>=5000&&c.payloadErrorFrames>=200){stop="TARGET_FRAME_ERRORS_REACHED";break;}}
  if(stop=="CONTINUE")stop="MAX_FRAMES_REACHED";const bool ok=c.trueSuccessFrames+c.payloadErrorFrames==c.totalFrames;
  require(ok&&c.totalFrames<=50000,"accounting/frame cap failed");row(raw,p,c,argv[4],stop);row(sum,p,c,argv[4],stop);
  merge<<p.experiment<<','<<p.awgn.caseId<<','<<p.parameterIndex<<','<<c.totalFrames<<','<<ok<<','<<ok<<'\n';
  std::ofstream cp(output/"checkpoints"/("stage12_"+p.experiment+"_"+p.awgn.caseId+"_"+std::to_string(p.parameterIndex)+".json"));
  cp<<"{\"nextFrameIndex\":"<<c.totalFrames<<",\"stopReason\":\""<<stop<<"\"}\n";
  std::cout<<p.experiment<<' '<<p.awgn.caseId<<" p"<<p.parameterIndex<<" frames "<<c.totalFrames<<" errors "<<c.payloadErrorFrames<<'\n';
 }std::cout<<"PASS_STAGE12_BLOCKAGE_FORMAL_RUNNER\n";return 0;
}catch(const std::exception&e){std::cerr<<"BLOCKED_STAGE12_BLOCKAGE_FORMAL_RUNNER: "<<e.what()<<'\n';return 1;}}
