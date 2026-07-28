#include "continuous_encoder.hpp"
#include "cc/trellis.hpp"
#include <stdexcept>
namespace scl::cc::stage12 {
ContinuousEncoder::ContinuousEncoder(const Trellis&t,PuncturePattern p):encoder_(t),pattern_(std::move(p)){validate_puncture_pattern(pattern_);}
SlotResult ContinuousEncoder::encode_slot(const std::vector<std::uint8_t>&payload,bool final_slot,bool append_tail){
 if(append_tail&&!final_slot)throw std::invalid_argument("tail only allowed on final slot");
 SlotResult r;r.metadata.slot_index=state_.slot_index;r.metadata.payload_start=state_.payload_bits;r.metadata.payload_count=payload.size();
 r.metadata.mother_start=state_.mother_bits;r.metadata.transmitted_start=state_.transmitted_bits;r.metadata.initial_state=encoder_.state();r.metadata.initial_phase=state_.puncture_phase;
 encoder_.encode_segment(payload,r.mother_bits);if(append_tail){encoder_.encode_segment(std::vector<std::uint8_t>(kMemory,0),r.mother_bits);r.metadata.appended_tail=true;}
 auto p=puncture_bits(r.mother_bits,pattern_,state_.puncture_phase);r.transmitted_bits=std::move(p.bits);
 r.metadata.mother_count=r.mother_bits.size();r.metadata.transmitted_count=r.transmitted_bits.size();r.metadata.final_state=encoder_.state();r.metadata.final_phase=p.final_phase;
 state_.encoder_state=encoder_.state();state_.puncture_phase=p.final_phase;++state_.slot_index;state_.payload_bits+=payload.size();state_.mother_bits+=r.mother_bits.size();state_.transmitted_bits+=r.transmitted_bits.size();
 if(final_slot&&append_tail&&state_.encoder_state!=0)throw std::logic_error("final zero tail did not terminate");
 return r;
}
ContinuousState ContinuousEncoder::export_state()const{return state_;}
void ContinuousEncoder::import_state(const ContinuousState&s){if(s.encoder_state>=kStateCount||s.puncture_phase>=pattern_.keep_mask.size())throw std::invalid_argument("invalid continuous state");state_=s;encoder_.import_state(s.encoder_state);}
void ContinuousEncoder::reset(){state_={};encoder_.reset();}
}
