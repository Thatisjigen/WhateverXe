#include "../WhateverXe/kern_tgl_recovery.hpp"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <cstdint>

void completionCases() {
	using namespace TGLRecovery;
	alignas(16) static uint8_t em[0x1000];alignas(16) static volatile uint32_t stamps[64];
	static volatile uint32_t *table[64];
	struct Case {const char *name;int32_t count;uint32_t index,hw,issued;bool table;uint32_t expectHW;bool forced;};
	const Case cases[] {
		{"behind: raised to last issued",64,5,100,107,true,107,true},
		{"already complete: untouched",64,5,107,107,true,107,false},
		{"hardware ahead (wrap-safe): untouched",64,5,0x00000002,0xFFFFFFF0,true,0x00000002,false},
		{"wraps forward",64,5,0xFFFFFFF0,0x00000003,true,0x00000003,true},
		{"index out of range",64,64,1,9,true,1,false},
		{"no stamp table",64,5,1,9,false,1,false},
	};
	for (auto &c:cases) {
		memset(em,0,sizeof(em));
		for (unsigned i=0;i<64;++i){stamps[i]=0;table[i]=&stamps[i];}
		field<int32_t>(em,0x30)=c.count;field<volatile uint32_t **>(em,0x28)=c.table ? table : nullptr;
		const unsigned slot=c.index<64 ? c.index : 0;
		stamps[slot]=c.hw;field<uint32_t>(em,0xFC+24*(c.index<64 ? c.index : 0))=c.issued;
		const auto r=completeStamp(em,c.index);
		if (stamps[slot]!=c.expectHW || r.forced!=c.forced) {printf("FAIL %s hw=%x\n",c.name,stamps[slot]);assert(false);}
		// Never beyond the last issued value.
		if (r.forced) assert(stamps[slot]==c.issued);
	}
	assert(!completeStamp(nullptr,0).forced);
	puts("7 completion cases passed: raise to last issued only, never past it; complete, ahead, range, table and null untouched");
}

int main() {
	completionCases();
}
