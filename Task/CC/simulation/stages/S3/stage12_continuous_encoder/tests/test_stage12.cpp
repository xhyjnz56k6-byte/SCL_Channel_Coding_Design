#include "continuous_encoder.hpp"
#include "cc/trellis.hpp"
#include "common/frame_pool.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace scl::cc;
int main(int argc,char**argv){
 try{if(argc!=2)throw std::invalid_argument("results dir");std::filesystem::create_directories(argv[1]);Trellis t;
  const std::vector<PuncturePattern>patterns={{"R12",{1,1}},{"R23",{1,1,0,1}},{"R34",{1,1,0,1,1,0}}};
  std::ofstream meta(std::filesystem::path(argv[1])/"stage12_slot_metadata.csv");meta<<"pattern,slotSize,slotIndex,payloadStart,payloadCount,initialState,finalState,initialPhase,finalPhase,motherCount,transmittedCount,appendedTail\n";
  for(const auto&p:patterns)for(std::size_t slot:{50U,100U,150U})for(std::uint64_t frame=0;frame<100;++frame){
   auto payload=scl::common::generatePayloadBits(2026072001,300,frame);ConvolutionalEncoder block(t);auto expected=block.encode_block(payload,true);auto expected_p=puncture_bits(expected.mother_bits,p);
   scl::cc::stage12::ContinuousEncoder c(t,p);std::vector<std::uint8_t>mother,tx;
   for(std::size_t start=0;start<payload.size();start+=slot){std::vector<std::uint8_t>part(payload.begin()+start,payload.begin()+start+slot);bool last=start+slot==payload.size();auto r=c.encode_slot(part,last,last);
    mother.insert(mother.end(),r.mother_bits.begin(),r.mother_bits.end());tx.insert(tx.end(),r.transmitted_bits.begin(),r.transmitted_bits.end());
    if(frame==0)meta<<p.id<<','<<slot<<','<<r.metadata.slot_index<<','<<r.metadata.payload_start<<','<<r.metadata.payload_count<<','<<int(r.metadata.initial_state)<<','<<int(r.metadata.final_state)<<','<<r.metadata.initial_phase<<','<<r.metadata.final_phase<<','<<r.metadata.mother_count<<','<<r.metadata.transmitted_count<<','<<r.metadata.appended_tail<<'\n';
   }
   auto state=c.export_state();if(mother!=expected.mother_bits||tx!=expected_p.bits||state.encoder_state!=0||state.payload_bits!=300)throw std::runtime_error("segmented equivalence");
   scl::cc::stage12::ContinuousEncoder a(t,p),b(t,p);std::vector<std::uint8_t>x(payload.begin(),payload.begin()+100),y(payload.begin()+100,payload.end()),out1,out2;
   auto r1=a.encode_slot(x,false,false);b.import_state(a.export_state());auto r2=b.encode_slot(y,true,true);out1=r1.transmitted_bits;out1.insert(out1.end(),r2.transmitted_bits.begin(),r2.transmitted_bits.end());if(out1!=expected_p.bits)throw std::runtime_error("state migration");
   scl::cc::stage12::ContinuousEncoder stream(t,p);std::vector<std::uint8_t>stream_m;for(std::size_t start=0;start<300;start+=slot){std::vector<std::uint8_t>part(payload.begin()+start,payload.begin()+start+slot);auto r=stream.encode_slot(part,start+slot==300,false);stream_m.insert(stream_m.end(),r.mother_bits.begin(),r.mother_bits.end());}
   ConvolutionalEncoder direct(t);std::vector<std::uint8_t>direct_m;direct.encode_segment(payload,direct_m);if(stream_m!=direct_m)throw std::runtime_error("unterminated stream");
  }
  bool rejected=false;try{scl::cc::stage12::ContinuousEncoder c(t,patterns[1]);c.encode_slot({1},false,true);}catch(const std::invalid_argument&){rejected=true;}if(!rejected)throw std::runtime_error("middle tail accepted");
  std::ofstream summary(std::filesystem::path(argv[1])/"stage12_continuous_encoder_test_summary.csv");summary<<"check,status\nsegmented_equivalence,PASS\nstate_export_import,PASS\nno_loss_or_duplicate,PASS\nfinal_zero_state,PASS\npuncture_phase_carry,PASS\nunterminated_stream,PASS\nnegative_middle_tail,PASS\nstage_gate,PASS_STAGE12_CC_CONTINUOUS_ENCODER\n";
  std::cout<<"PASS_STAGE12_CC_CONTINUOUS_ENCODER\n";return 0;}catch(const std::exception&e){std::cerr<<"FAIL_STAGE12: "<<e.what()<<'\n';return 1;}}
