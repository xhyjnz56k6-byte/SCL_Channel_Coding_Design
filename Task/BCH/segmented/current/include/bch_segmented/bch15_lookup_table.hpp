#ifndef SCL_BCH_SEGMENTED_BCH15_LOOKUP_TABLE_HPP
#define SCL_BCH_SEGMENTED_BCH15_LOOKUP_TABLE_HPP
#include "bch_segmented/bch15_syndrome.hpp"
#include <array>
#include <string>
namespace scl::bch::segmented { struct SyndromeEntry { unsigned syndrome; unsigned errorPosition; common::BitVector errorPattern; }; struct SyndromeTable { std::array<SyndromeEntry,15> entries; std::string hash; }; SyndromeTable buildBch15SyndromeTable(); int lookupErrorPosition(const SyndromeTable&,unsigned syndrome); }
#endif
