#define main stage05_embedded_main
#include "../../stage05_awgn_trial/cpp/stage05_awgn_trial_runner.cpp"
#undef main

namespace {

std::vector<Point> readFormalPoints(const fs::path& path) {
    std::ifstream input(path);
    if(!input)throw std::runtime_error("cannot open formal point CSV");
    std::string line;
    std::getline(input,line);
    require(line=="caseId,ebn0Index,ebn0Db","formal point CSV header mismatch");
    std::vector<Point> points;
    while(std::getline(input,line)) {
        if(line.empty())continue;
        std::istringstream row(line);
        std::string id,index,db;
        std::getline(row,id,',');std::getline(row,index,',');std::getline(row,db,',');
        points.push_back({parseCase(id),id,static_cast<std::size_t>(std::stoull(index)),std::stod(db)});
    }
    require(points.size()==40U,"formal point count is not 40");
    return points;
}

Counters simulateFormalRange(const Point& point, std::uint64_t start, std::uint64_t count,
                             std::uint64_t seed) {
    const auto& contract=scl::bch::s2::stage02::caseContract(point.id);
    Counters result;
    result.decodeTimesNs.reserve(static_cast<std::size_t>(count));
    const double sigma=std::sqrt(scl::bch::s2::stage01::awgnSigma2(contract.actualRate,point.ebn0Db));
    for (std::uint64_t frame=start;frame<start+count;++frame) {
        const auto payload=payloadFrame("stage06_awgn_formal",contract.caseId,point.ebn0Index,
                                        frame,contract.payloadLength,seed);
        const auto encodeStart=std::chrono::steady_clock::now();
        const auto encoded=scl::bch::s2::stage02::encodeFrame(contract.id,payload).encodedBits;
        const auto encodeEnd=std::chrono::steady_clock::now();
        const scl::bch::s2::stage01::RandomIdentity identity{
            seed,"stage06_awgn_formal",contract.caseId,point.ebn0Index,frame};
        const auto z=scl::bch::s2::stage01::standardGaussianFrame(
            identity,scl::bch::s2::stage01::RandomDomain::Awgn,encoded.size());
        scl::common::BitVector hard(encoded.size(),0U);
        for (std::size_t i=0;i<encoded.size();++i) {
            hard[i]=static_cast<scl::common::Bit>(scl::bch::s2::stage01::hardDecision(
                scl::bch::s2::stage01::bpsk(encoded[i])+sigma*z[i]));
        }
        const auto decodeStart=std::chrono::steady_clock::now();
        const auto decoded=decodeAudited(contract,hard);
        const auto decodeEnd=std::chrono::steady_clock::now();
        const auto errors=bitErrors(payload,decoded.payload);
        const bool success=errors==0U;
        ++result.totalFrames;
        result.totalPayloadBits+=contract.payloadLength;
        result.payloadErrorBits+=errors;
        result.payloadErrorFrames+=!success;
        result.decoderFailureFrames+=!decoded.reportedSuccess;
        result.miscorrectionFrames+=decoded.reportedSuccess&&!success;
        result.undetectedErrorFrames+=decoded.allNoError&&!success;
        result.trueSuccessFrames+=success;
        result.noiseChecksum+=hashNoise(z);
        result.encodeTimeTotalNs+=static_cast<std::uint64_t>(
            std::chrono::duration_cast<std::chrono::nanoseconds>(encodeEnd-encodeStart).count());
        const auto decodeNs=static_cast<std::uint64_t>(
            std::chrono::duration_cast<std::chrono::nanoseconds>(decodeEnd-decodeStart).count());
        result.decodeTimeTotalNs+=decodeNs;
        result.decodeTimesNs.push_back(decodeNs);
    }
    return result;
}

void writeFormalCheckpoint(const fs::path& path,const Point& point,const Counters& c,
                           std::uint64_t seed,const std::string& configHash,
                           const std::string& gitCommit,const std::string& stopReason) {
    std::ofstream out(path);
    if(!out)throw std::runtime_error("cannot write formal checkpoint");
    out<<"{\n  \"stageId\": \"stage06_awgn_formal\",\n  \"caseId\": \""<<point.caseId
       <<"\",\n  \"ebn0Index\": "<<point.ebn0Index<<",\n  \"ebn0Db\": "<<point.ebn0Db
       <<",\n  \"nextFrameIndex\": "<<c.totalFrames<<",\n  \"masterSeed\": "<<seed
       <<",\n  \"configHash\": \""<<configHash<<"\",\n  \"gitCommit\": \""<<gitCommit
       <<"\",\n  \"totalFrames\": "<<c.totalFrames<<",\n  \"totalPayloadBits\": "<<c.totalPayloadBits
       <<",\n  \"payloadErrorBits\": "<<c.payloadErrorBits
       <<",\n  \"payloadErrorFrames\": "<<c.payloadErrorFrames
       <<",\n  \"decoderFailureFrames\": "<<c.decoderFailureFrames
       <<",\n  \"miscorrectionFrames\": "<<c.miscorrectionFrames
       <<",\n  \"undetectedErrorFrames\": "<<c.undetectedErrorFrames
       <<",\n  \"trueSuccessFrames\": "<<c.trueSuccessFrames
       <<",\n  \"noiseChecksum\": "<<c.noiseChecksum
       <<",\n  \"stopReason\": \""<<stopReason<<"\"\n}\n";
}

}  // namespace

int main(int argc,char** argv) {
    try {
        if(argc!=6)throw std::invalid_argument(
            "usage: stage06_awgn_formal_runner POINTS_CSV OUTPUT_DIR MASTER_SEED CONFIG_HASH GIT_COMMIT");
        const auto points=readFormalPoints(argv[1]);
        const fs::path output(argv[2]);
        const std::uint64_t seed=std::stoull(argv[3]);
        const std::string configHash=argv[4],gitCommit=argv[5];
        fs::create_directories(output/"checkpoints");
        std::ofstream results(output/"stage06_awgn_formal_results.csv");
        std::ofstream shards(output/"stage06_awgn_formal_shard_manifest.csv");
        std::ofstream merge(output/"stage06_awgn_formal_merge_audit.csv");
        if(!results||!shards||!merge)throw std::runtime_error("cannot open formal outputs");
        results<<"stageId,caseId,displayName,legendLabel,styleId,payloadLength,motherN,motherK,motherT,"
                 "blockCount,encodedLength,actualRate,ebn0Index,ebn0Db,snrLinear,snrDb,sigma2,masterSeed,"
                 "configHash,gitCommit,checkpointId,shardId,totalFrames,totalPayloadBits,payloadErrorBits,"
                 "payloadErrorFrames,decoderFailureFrames,miscorrectionFrames,undetectedErrorFrames,"
                 "trueSuccessFrames,ber,fer,encodeTimeTotalNs,decodeTimeTotalNs,encodeTimeMeanNs,"
                 "decodeTimeMeanNs,decodeTimeP50Ns,decodeTimeP95Ns,decodeTimeP99Ns,decodeTimeMaxNs,"
                 "noiseChecksum,stopReason\n";
        shards<<"caseId,ebn0Index,shardId,frameStart,frameCount,noiseChecksum\n";
        merge<<"caseId,ebn0Index,shardCount,totalFrames,rawAccountingPass,passed\n";
        results<<std::setprecision(17);
        for(const auto& point:points) {
            Counters counters;
            std::string stopReason="CONTINUE";
            while(counters.totalFrames<50000U) {
                auto one=simulateFormalRange(point,counters.totalFrames,1U,seed);
                add(counters,one);
                counters.encodeTimeTotalNs+=one.encodeTimeTotalNs;
                counters.decodeTimeTotalNs+=one.decodeTimeTotalNs;
                counters.decodeTimesNs.push_back(one.decodeTimesNs.front());
                if(counters.totalFrames>=5000U&&counters.payloadErrorFrames>=200U) {
                    stopReason="TARGET_FRAME_ERRORS_REACHED"; break;
                }
                if(counters.totalFrames%1000U==0U) {
                    writeFormalCheckpoint(output/"checkpoints"/
                        ("stage06_awgn_formal_"+point.caseId+"_"+std::to_string(point.ebn0Index)+".json"),
                        point,counters,seed,configHash,gitCommit,"CONTINUE");
                }
            }
            if(stopReason=="CONTINUE")stopReason="MAX_FRAMES_REACHED";
            const std::string checkpointId="formal_"+point.caseId+"_"+std::to_string(point.ebn0Index);
            writeFormalCheckpoint(output/"checkpoints"/("stage06_awgn_formal_"+point.caseId+"_"+
                std::to_string(point.ebn0Index)+".json"),point,counters,seed,configHash,gitCommit,stopReason);
            const auto& contract=scl::bch::s2::stage02::caseContract(point.id);
            const double sigma2=scl::bch::s2::stage01::awgnSigma2(contract.actualRate,point.ebn0Db);
            results<<"stage06_awgn_formal,"<<contract.caseId<<','<<contract.displayName<<','
                   <<contract.legendLabel<<','<<contract.plotStyle.id<<','<<contract.payloadLength<<','
                   <<contract.motherN<<','<<contract.motherK<<','<<contract.motherT<<','
                   <<contract.blockCount<<','<<contract.totalEncodedLength<<','<<contract.actualRate<<','
                   <<point.ebn0Index<<','<<point.ebn0Db<<','<<1.0/sigma2<<','
                   <<scl::bch::s2::stage01::snrDb(contract.actualRate,point.ebn0Db)<<','<<sigma2<<','
                   <<seed<<','<<configHash<<','<<gitCommit<<','<<checkpointId<<",0,"
                   <<counters.totalFrames<<','<<counters.totalPayloadBits<<','<<counters.payloadErrorBits<<','
                   <<counters.payloadErrorFrames<<','<<counters.decoderFailureFrames<<','
                   <<counters.miscorrectionFrames<<','<<counters.undetectedErrorFrames<<','
                   <<counters.trueSuccessFrames<<','
                   <<static_cast<double>(counters.payloadErrorBits)/counters.totalPayloadBits<<','
                   <<static_cast<double>(counters.payloadErrorFrames)/counters.totalFrames<<','
                   <<counters.encodeTimeTotalNs<<','<<counters.decodeTimeTotalNs<<','
                   <<counters.encodeTimeTotalNs/counters.totalFrames<<','
                   <<counters.decodeTimeTotalNs/counters.totalFrames<<','
                   <<percentile(counters.decodeTimesNs,0.50)<<','<<percentile(counters.decodeTimesNs,0.95)<<','
                   <<percentile(counters.decodeTimesNs,0.99)<<','
                   <<*std::max_element(counters.decodeTimesNs.begin(),counters.decodeTimesNs.end())<<','
                   <<counters.noiseChecksum<<','<<stopReason<<'\n';
            shards<<point.caseId<<','<<point.ebn0Index<<",0,0,"<<counters.totalFrames<<','
                  <<counters.noiseChecksum<<'\n';
            const bool accounting=counters.trueSuccessFrames+counters.payloadErrorFrames==counters.totalFrames;
            merge<<point.caseId<<','<<point.ebn0Index<<",1,"<<counters.totalFrames<<','
                 <<accounting<<','<<accounting<<'\n';
            require(accounting,"formal raw accounting failed");
            std::cout<<point.caseId<<" point "<<point.ebn0Index<<" frames "<<counters.totalFrames
                     <<" errors "<<counters.payloadErrorFrames<<" "<<stopReason<<'\n';
        }
        std::cout<<"PASS_STAGE06_AWGN_FORMAL_RUNNER\n";
        return 0;
    } catch(const std::exception& error) {
        std::cerr<<"BLOCKED_STAGE06_AWGN_FORMAL_RUNNER: "<<error.what()<<'\n';
        return 1;
    }
}
