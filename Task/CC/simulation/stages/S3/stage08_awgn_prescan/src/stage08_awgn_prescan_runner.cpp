#include "cc/block_encoder.hpp"
#include "cc/hard_viterbi.hpp"
#include "cc/puncturing.hpp"
#include "cc/soft_viterbi.hpp"
#include "cc/trellis.hpp"
#include "common/frame_pool.hpp"
#include "common/gaussian_noise.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using Clock=std::chrono::steady_clock;
constexpr std::uint64_t kSeed=2026072001ULL;
struct Rate {std::string id; scl::cc::PuncturePattern pattern; std::uint64_t noise_group;};
struct Acc {
    std::uint64_t frames=0,bits=0,bit_errors=0,frame_errors=0;
    double encode_us=0,decode_us=0,max_encode_us=0,max_decode_us=0;
    std::vector<double> decode_samples;
};
struct PairResult {Acc hard;Acc soft;double snr=0,rate=0,sigma2=0;std::size_t n=0;};

std::uint64_t errors(const std::vector<std::uint8_t>& a,const std::vector<std::uint8_t>& b){
    std::uint64_t value=0;for(std::size_t i=0;i<a.size();++i)value+=a[i]!=b[i];return value;
}
double percentile95(std::vector<double> values){
    if(values.empty()){
        return 0;
    }
    std::sort(values.begin(),values.end());
    return values[static_cast<std::size_t>(std::ceil(0.95*values.size()))-1];
}
bool stop(const Acc& a,std::uint64_t min_frames,std::uint64_t target,std::uint64_t max_frames){
    return (a.frames>=min_frames&&a.frame_errors>=target)||a.frames>=max_frames;
}

PairResult simulate(const Rate& rate,double snr_db,std::uint64_t min_frames,
                    std::uint64_t target_errors,std::uint64_t max_frames){
    const scl::cc::Trellis trellis;scl::cc::ConvolutionalEncoder encoder(trellis);
    const scl::cc::HardViterbiDecoder hard_decoder(trellis);
    const scl::cc::SoftViterbiDecoder soft_decoder(trellis);
    PairResult result;result.snr=snr_db;result.sigma2=1.0/(2.0*std::pow(10.0,snr_db/10.0));
    const double sigma=std::sqrt(result.sigma2);
    for(std::uint64_t frame=0;frame<max_frames;++frame){
        const auto common_payload=scl::common::generatePayloadBits(kSeed,300,frame);
        std::vector<std::uint8_t> payload(common_payload.begin(),common_payload.end());
        const auto encode_start=Clock::now();
        const auto encoded=encoder.encode_block(payload,true);
        const auto punctured=scl::cc::puncture_bits(encoded.mother_bits,rate.pattern);
        const auto encode_end=Clock::now();
        if(result.n==0){result.n=punctured.bits.size();result.rate=300.0/result.n;}
        const auto z=scl::common::generateStandardGaussianFrame(
            kSeed,rate.noise_group,frame,punctured.bits.size());
        std::vector<double> received(punctured.bits.size());
        std::vector<std::uint8_t> hard_bits(punctured.bits.size());
        for(std::size_t i=0;i<received.size();++i){
            received[i]=(punctured.bits[i]==0?1.0:-1.0)+sigma*z[i];
            hard_bits[i]=received[i]>=0?0:1;
        }
        const auto hard_dep=scl::cc::depuncture_hard(hard_bits,612,rate.pattern);
        const auto soft_dep=scl::cc::depuncture_soft(received,612,rate.pattern);
        const auto hard_start=Clock::now();
        const auto hard=hard_decoder.decode_terminated_masked(
            hard_dep.expanded_bits,hard_dep.observed_mask,306);
        const auto hard_end=Clock::now();
        const auto soft_start=Clock::now();
        const auto soft=soft_decoder.decode_terminated_masked_symbols(
            soft_dep.expanded_values,soft_dep.observed_mask,306);
        const auto soft_end=Clock::now();
        const double enc=std::chrono::duration<double,std::micro>(encode_end-encode_start).count();
        const double hard_us=std::chrono::duration<double,std::micro>(hard_end-hard_start).count();
        const double soft_us=std::chrono::duration<double,std::micro>(soft_end-soft_start).count();
        const auto he=errors(payload,hard.payload_bits),se=errors(payload,soft.payload_bits);
        for(auto* acc:{&result.hard,&result.soft}){
            ++acc->frames;acc->bits+=300;acc->encode_us+=enc;acc->max_encode_us=std::max(acc->max_encode_us,enc);
        }
        result.hard.bit_errors+=he;result.hard.frame_errors+=he!=0;
        result.soft.bit_errors+=se;result.soft.frame_errors+=se!=0;
        result.hard.decode_us+=hard_us;result.hard.max_decode_us=std::max(result.hard.max_decode_us,hard_us);
        result.soft.decode_us+=soft_us;result.soft.max_decode_us=std::max(result.soft.max_decode_us,soft_us);
        result.hard.decode_samples.push_back(hard_us);result.soft.decode_samples.push_back(soft_us);
        if(stop(result.hard,min_frames,target_errors,max_frames)&&
           stop(result.soft,min_frames,target_errors,max_frames))break;
    }
    return result;
}

void write_row(std::ofstream& out,const Rate& rate,const std::string& decoder,
               const PairResult& pair,const Acc& a,const std::string& phase){
    const double ber=static_cast<double>(a.bit_errors)/a.bits;
    const double fer=static_cast<double>(a.frame_errors)/a.frames;
    const double ebn0=pair.snr-10.0*std::log10(pair.rate);
    const double avg_dec=a.decode_us/a.frames;
    const double raw=300.0/(avg_dec);
    const std::string stop_reason=a.frames>=2000?"MAX_FRAMES_REACHED":"TARGET_ERRORS_REACHED";
    out<<phase<<",CC-B-"<<rate.id<<'-'<<decoder<<','<<pair.snr<<','<<ebn0<<','
       <<pair.rate<<','<<pair.sigma2<<','<<pair.n<<','<<a.frames<<','<<a.bit_errors<<','
       <<a.frame_errors<<','<<ber<<','<<fer<<','<<(1-fer)<<','
       <<a.encode_us/a.frames<<','<<a.max_encode_us<<','<<avg_dec<<','
       <<percentile95(a.decode_samples)<<','<<a.max_decode_us<<','<<raw<<','
       <<raw*(1-fer)<<','<<pair.rate*(1-fer)<<','<<stop_reason<<'\n';
}
}

int main(int argc,char** argv){
    try{
        if(argc!=2)throw std::invalid_argument("expected results directory");
        const std::filesystem::path results(argv[1]);std::filesystem::create_directories(results);
        const std::vector<Rate> rates={
            {"R12",{"R12_11",{1,1}},1200},
            {"R23",{"R23_B_1101",{1,1,0,1}},2300},
            {"R34",{"R34_B_110110",{1,1,0,1,1,0}},3400}};
        const std::vector<double> smoke_snr={-2,-1,0,1,2,3,4};
        std::ofstream smoke(results/"stage08_awgn_prescan_smoke_results.csv");
        std::ofstream points(results/"stage08_awgn_prescan_point_results.csv");
        const std::string header="phase,caseId,snrDb,ebN0Db,actualRate,sigmaSquared,N_transmitted,"
            "framesProcessed,payloadBitErrors,payloadErrorFrames,BER,FER,payloadSuccessRate,"
            "avgEncodeTime_us,maxEncodeTime_us,avgDecodeTime_us,p95DecodeTime_us,maxDecodeTime_us,"
            "rawDecodeThroughput_Mbps,successfulDecodeThroughput_Mbps,normalizedGoodput,stopReason\n";
        smoke<<header;points<<header;smoke<<std::setprecision(17);points<<std::setprecision(17);
        std::ofstream ranges(results/"stage08_awgn_prescan_formal_recommendations.csv");
        ranges<<"rateId,hardCenterSnrDb,softCenterSnrDb,prescanMinSnrDb,prescanMaxSnrDb,formalSuggestedMinSnrDb,formalSuggestedMaxSnrDb\n";
        for(const auto& rate:rates){
            std::vector<PairResult> smoke_values;
            for(double snr:smoke_snr){
                auto value=simulate(rate,snr,60,1000000,60);smoke_values.push_back(value);
                write_row(smoke,rate,"H",value,value.hard,"smoke");
                write_row(smoke,rate,"S",value,value.soft,"smoke");
            }
            auto center=[&](bool soft_case){
                double best=0,diff=10;
                for(const auto& value:smoke_values){
                    const auto& a=soft_case?value.soft:value.hard;
                    const double fer=static_cast<double>(a.frame_errors)/a.frames;
                    if(std::abs(fer-0.5)<diff){diff=std::abs(fer-0.5);best=value.snr;}
                }return best;
            };
            const double hc=center(false),sc=center(true);
            const double low=std::max(-3.0,std::min(hc,sc)-0.5);
            const double high=std::min(5.0,std::max(hc,sc)+2.0);
            for(double snr=low;snr<=high+1e-9;snr+=0.5){
                auto value=simulate(rate,snr,300,30,2000);
                write_row(points,rate,"H",value,value.hard,"prescan");
                write_row(points,rate,"S",value,value.soft,"prescan");
            }
            ranges<<rate.id<<','<<hc<<','<<sc<<','<<low<<','<<high<<','
                  <<low<<','<<high<<'\n';
        }
        std::cout<<"PASS_STAGE08_CC_AWGN_PRESCAN_RUNNER\n";return 0;
    }catch(const std::exception& e){std::cerr<<"FAIL_STAGE08: "<<e.what()<<'\n';return 1;}
}
