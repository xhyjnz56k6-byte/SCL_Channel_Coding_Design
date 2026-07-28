#pragma once
#include "cc/block_encoder.hpp"
#include "cc/puncturing.hpp"
#include <cstddef>
#include <cstdint>
#include <vector>
namespace scl::cc::stage12 {
struct ContinuousState{std::uint8_t encoder_state=0;std::size_t puncture_phase=0,slot_index=0,payload_bits=0,mother_bits=0,transmitted_bits=0;};
struct SlotMetadata{std::size_t slot_index=0,payload_start=0,payload_count=0,mother_start=0,mother_count=0,transmitted_start=0,transmitted_count=0,initial_phase=0,final_phase=0;std::uint8_t initial_state=0,final_state=0;bool appended_tail=false;};
struct SlotResult{std::vector<std::uint8_t> mother_bits,transmitted_bits;SlotMetadata metadata;};
class ContinuousEncoder{
public:
 ContinuousEncoder(const Trellis&trellis,PuncturePattern pattern);
 SlotResult encode_slot(const std::vector<std::uint8_t>&payload,bool final_slot,bool append_tail_on_final);
 ContinuousState export_state()const;void import_state(const ContinuousState&state);void reset();
private:
 ConvolutionalEncoder encoder_;PuncturePattern pattern_;ContinuousState state_;
};
}
