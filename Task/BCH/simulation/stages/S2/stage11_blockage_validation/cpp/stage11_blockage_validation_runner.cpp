#define main stage05_embedded_main
#include "../../stage05_awgn_trial/cpp/stage05_awgn_trial_runner.cpp"
#undef main

namespace {

constexpr auto kBlockageDomain =
    static_cast<scl::bch::s2::stage01::RandomDomain>(0x424c4f434b535452ULL);

std::size_t ratioLength(double rho, std::size_t n) {
    require(std::isfinite(rho) && rho >= 0.0 && rho <= 1.0, "invalid blockage ratio");
    if (rho == 0.0) return 0U;
    return std::min(n,std::max<std::size_t>(1U,
        static_cast<std::size_t>(std::floor(rho*static_cast<double>(n)+0.5))));
}

double blockSample(double x, double noise, std::size_t k, std::size_t start,
                   std::size_t length, double amplitude, std::size_t n) {
    require(std::isfinite(amplitude) && amplitude >= 0.0 && amplitude <= 1.0,
            "invalid blockage amplitude");
    require(length <= n && start <= n-length, "blockage interval out of bounds");
    return ((length > 0U && k >= start && k < start+length) ? amplitude : 1.0)*x+noise;
}

std::size_t randomStart(const scl::bch::s2::stage01::RandomIdentity& base,
                        std::size_t n, std::size_t length, std::size_t parameterIndex) {
    require(length <= n, "random blockage length exceeds frame");
    if (length == n) return 0U;
    auto identity=base;
    identity.ebn0Index=(base.ebn0Index<<32U)^parameterIndex;
    const auto word=scl::bch::s2::stage01::randomWord(identity,kBlockageDomain,0U,0U);
    return static_cast<std::size_t>(word%static_cast<std::uint64_t>(n-length+1U));
}

Counters simulateBlocked(const Point& point, std::uint64_t begin, std::uint64_t count,
                         std::uint64_t seed, double rho, std::size_t parameterIndex) {
    const auto& contract=scl::bch::s2::stage02::caseContract(point.id);
    Counters result;
    const auto length=ratioLength(rho,contract.totalEncodedLength);
    const double sigma=std::sqrt(scl::bch::s2::stage01::awgnSigma2(contract.actualRate,point.ebn0Db));
    for(std::uint64_t frame=begin;frame<begin+count;++frame) {
        const auto payload=payloadFrame("stage11_blockage_validation",contract.caseId,
                                        point.ebn0Index,frame,contract.payloadLength,seed);
        const auto encoded=scl::bch::s2::stage02::encodeFrame(contract.id,payload).encodedBits;
        const scl::bch::s2::stage01::RandomIdentity identity{
            seed,"stage11_blockage_validation",contract.caseId,point.ebn0Index,frame};
        const auto z=scl::bch::s2::stage01::standardGaussianFrame(
            identity,scl::bch::s2::stage01::RandomDomain::Awgn,encoded.size());
        const auto start=randomStart(identity,encoded.size(),length,parameterIndex);
        scl::common::BitVector hard(encoded.size(),0U);
        for(std::size_t k=0;k<encoded.size();++k) {
            const double y=blockSample(scl::bch::s2::stage01::bpsk(encoded[k]),sigma*z[k],
                                       k,start,length,0.0,encoded.size());
            hard[k]=static_cast<scl::common::Bit>(scl::bch::s2::stage01::hardDecision(y));
        }
        const auto decoded=decodeAudited(contract,hard);
        const auto errors=bitErrors(payload,decoded.payload);
        ++result.totalFrames; result.totalPayloadBits+=contract.payloadLength;
        result.payloadErrorBits+=errors; result.payloadErrorFrames+=errors!=0U;
        result.decoderFailureFrames+=!decoded.reportedSuccess;
        result.miscorrectionFrames+=decoded.reportedSuccess&&errors!=0U;
        result.undetectedErrorFrames+=decoded.allNoError&&errors!=0U;
        result.trueSuccessFrames+=errors==0U; result.noiseChecksum+=hashNoise(z);
    }
    return result;
}

void fixedVectors(const fs::path& output) {
    fs::create_directories(output);
    std::ofstream fixed(output/"stage11_blockage_validation_fixed_vectors.csv");
    std::ofstream cpp(output/"stage11_blockage_validation_cpp_outputs.csv");
    fixed<<"vectorId,k,encodedLength,bpsk,noise,start,length,amplitude\n";
    cpp<<"vectorId,k,isBlocked,received,hardBit\n";
    const double x[]={1,-1,1,1,-1,-1,1,1};
    const double z[]={.1,-.2,.3,-.4,.5,-.6,.7,-.8};
    for(std::size_t k=0;k<8U;++k) {
        const double y=blockSample(x[k],z[k],k,2U,3U,0.0,8U);
        fixed<<"RECT8,"<<k<<",8,"<<x[k]<<','<<z[k]<<",2,3,0\n";
        cpp<<"RECT8,"<<k<<','<<(k>=2U&&k<5U)<<','<<y<<','
           <<scl::bch::s2::stage01::hardDecision(y)<<'\n';
    }
}

void validate(const fs::path& output) {
    require(blockSample(1,.25,3,0,0,0,8)==1.25,"L=0 degeneration failed");
    require(blockSample(-1,.25,3,2,3,1,8)==-.75,"a=1 degeneration failed");
    require(blockSample(1,0,2,2,3,0,8)==0,"zero-noise blockage failed");
    require(blockSample(1,.25,2,2,3,0,8)==.25,"noise not retained in blockage");
    bool rejected=false; try{static_cast<void>(blockSample(1,0,0,0,9,0,8));}catch(...){rejected=true;}
    require(rejected,"length>N was not rejected");
    rejected=false; try{static_cast<void>(blockSample(1,0,0,6,3,0,8));}catch(...){rejected=true;}
    require(rejected,"start>N-L was not rejected");
    rejected=false; try{static_cast<void>(blockSample(1,0,0,0,1,-.1,8));}catch(...){rejected=true;}
    require(rejected,"invalid amplitude was not rejected");
    std::uint64_t negative=0;
    const scl::bch::s2::stage01::RandomIdentity stats{2026072711ULL,"stage11_stats","ALL",0,0};
    for(std::size_t i=0;i<100000U;++i)
        negative+=scl::bch::s2::stage01::standardGaussian(stats,kBlockageDomain,i)<0.0;
    const double blockedBer=static_cast<double>(negative)/100000.0;
    require(blockedBer>=.48&&blockedBer<=.52,"blocked raw BER statistical check failed");
    std::ofstream statistics(output/"stage11_blockage_validation_statistics.csv");
    statistics<<"sampleCount,negativeCount,blockedRawBer,lowerBound,upperBound,passed\n"
              <<"100000,"<<negative<<','<<blockedBer<<",0.48,0.52,1\n";
    const CaseId ids[]={CaseId::K200_S15,CaseId::K200_M255K207,CaseId::K200_M511K421,
      CaseId::K200_M511K385,CaseId::K300_S15,CaseId::K300_M255K207,
      CaseId::K300_M511K421,CaseId::K300_M511K385};
    std::ofstream cases(output/"stage11_blockage_validation_case_results.csv");
    cases<<"caseId,encodedLength,requestedBlockageRatio,blockageLengthSymbols,"
           "actualBlockageRatio,minStart,maxStart,resumePass,shardMergePass\n";
    cases<<std::setprecision(17);
    for(std::size_t i=0;i<8U;++i) {
        const auto& c=scl::bch::s2::stage02::caseContract(ids[i]);
        Point point{ids[i],c.caseId,i,8.0};
        auto all=simulateBlocked(point,0,24,2026072711ULL,.1,3);
        auto resumed=simulateBlocked(point,0,11,2026072711ULL,.1,3);
        add(resumed,simulateBlocked(point,11,13,2026072711ULL,.1,3));
        Counters merged; add(merged,simulateBlocked(point,0,8,2026072711ULL,.1,3));
        add(merged,simulateBlocked(point,8,8,2026072711ULL,.1,3));
        add(merged,simulateBlocked(point,16,8,2026072711ULL,.1,3));
        const auto l=ratioLength(.1,c.totalEncodedLength);
        std::size_t minS=c.totalEncodedLength,maxS=0;
        for(std::uint64_t f=0;f<24;++f) {
            const scl::bch::s2::stage01::RandomIdentity id{
              2026072711ULL,"stage11_blockage_validation",c.caseId,i,f};
            const auto s=randomStart(id,c.totalEncodedLength,l,3);
            minS=std::min(minS,s);maxS=std::max(maxS,s);
        }
        require(sameRaw(all,resumed)&&sameRaw(all,merged),"blockage resume/shard mismatch");
        cases<<c.caseId<<','<<c.totalEncodedLength<<",0.1,"<<l<<','
             <<static_cast<double>(l)/c.totalEncodedLength<<','<<minS<<','<<maxS<<",1,1\n";
    }
}

} // namespace

int main(int argc,char** argv) {
 try {
  if(argc!=2)throw std::invalid_argument("usage: stage11_blockage_validation_runner OUTPUT");
  const fs::path output(argv[1]); fixedVectors(output); validate(output);
  std::cout<<"PASS_STAGE11_BLOCKAGE_VALIDATION_RUNNER\n"; return 0;
 } catch(const std::exception& e) {
  std::cerr<<"BLOCKED_STAGE11_BLOCKAGE_VALIDATION_RUNNER: "<<e.what()<<'\n'; return 1;
 }
}
