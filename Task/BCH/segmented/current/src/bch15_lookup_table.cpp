#include "bch_segmented/bch15_lookup_table.hpp"
#include "common/sha256.hpp"
#include <sstream>
namespace scl::bch::segmented { SyndromeTable buildBch15SyndromeTable(){SyndromeTable t;std::ostringstream canonical;for(unsigned p=0;p<15;++p){common::BitVector e(15,0U);e[p]=1U;const unsigned s=syndromeValue(computeBch15Syndrome(e));t.entries[p]={s,p,e};canonical<<s<<','<<p<<'\n';}t.hash=common::sha256Hex(canonical.str());return t;} int lookupErrorPosition(const SyndromeTable& t,unsigned s){if(s==0U)return -1;for(const auto& e:t.entries)if(e.syndrome==s)return static_cast<int>(e.errorPosition);return -1;}}
