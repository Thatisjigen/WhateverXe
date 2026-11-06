// From Samran Ahmad's tests/rplp_iog.cpp (samranahmad09/WhateverXe-RaptorLakeP, 9657f2b, BSD-3-Clause): the wsStart part,
// against a fake memory. Adapted to this plugin's header: the record keeps a presence flag where his kept the controller's
// address, and only the controller and framebuffer fields that wsStart reads are laid out.
#include "kern_rplp_iog.hpp"
#include <assert.h>
#include <map>
#include <stdio.h>
using namespace RPLPIOG;
struct Mem {
    std::map<uint64_t,uint8_t> b;
    unsigned reads {};
    void put8(uint64_t a,uint8_t v) {b[a]=v;}
    unsigned writes {};
    void write8(uint64_t a,uint8_t v) {++writes;b[a]=v;}
    void write32(uint64_t a,uint32_t v) {++writes;put32(a,v);}
    void put32(uint64_t a,uint32_t v) {for(unsigned i=0;i<4;++i)b[a+i]=uint8_t(v>>(8*i));}
    void put64(uint64_t a,uint64_t v) {for(unsigned i=0;i<8;++i)b[a+i]=uint8_t(v>>(8*i));}
    uint8_t read8(uint64_t a) {++reads;auto it=b.find(a);return it==b.end() ? 0 : it->second;}
    uint32_t read32(uint64_t a) {uint32_t v=0;for(unsigned i=0;i<4;++i)v|=uint32_t(read8(a+i))<<(8*i);return v;}
    uint64_t read64(uint64_t a) {uint64_t v=0;for(unsigned i=0;i<8;++i)v|=uint64_t(read8(a+i))<<(8*i);return v;}
};
constexpr uint64_t K=0xFFFFFF8010000000ULL;
int main() {
    assert(pointer(K) && !pointer(K+4) && !pointer(0) && !pointer(0x1000) && object(K+4) && !object(0));
    Mem m;
    // Two controllers in the family's list: the first with three real framebuffers (wait byte 0x6, cached state 0x1048),
    // the second with one placeholder (wait byte 0x1, cached state 0x8). The framebuffer arrays lie inline (fFbs[]).
    const uint64_t c0=K+0x10000,c1=K+0x20000,fb0=K+0x30000,fb1=K+0x31000,fb2=K+0x32000,fb3=K+0x33000,gList=K+0xD0020;
    m.put64(gList,c0);
    m.put64(c0+ControllerNext,c1);m.put64(c1+ControllerNext,0);
    const uint64_t array0=c0+ControllerFBs,array1=c1+ControllerFBs;
    m.put8(c0+ControllerWsWait,0x6);m.put8(c0+ControllerNeedsWork,1);m.put8(c0+ControllerDidWork,2);m.put8(c0+ControllerAsyncWork,0);m.put32(c0+ControllerComputed,0x1048);
    m.put8(c1+ControllerWsWait,0x1);m.put32(c1+ControllerComputed,0x8);
    m.put64(array0,fb0);m.put64(array0+8,fb1);m.put64(array0+16,fb2);m.put64(array0+24,0);
    m.put64(array1,fb3);m.put64(array1+8,0);
    Globals g;g.controllers=gList;
    // wsStart: the second controller (one placeholder framebuffer, wait byte set, cached state 0x8) gets its byte and its
    // cached state word zeroed; the first (three real framebuffers, wait 0x6, state 0x1048) is left alone; without
    // `clear` nothing is written but the same is reported.
    {
        auto placeholder=[&](uint64_t fb) {return fb==fb3;};
        uint64_t r[12];m.writes=0;
        assert(wsStart(m,g,placeholder,false,r)==2 && r[0]==1 && r[1]==1 && r[2]==0 && r[3]==0 && r[8]==2 && r[9]==0 && m.writes==0);
        assert(r[4]==(0x6ULL|0x6ULL<<8|3ULL<<16|0x1048ULL<<32|0x1048ULL<<48) && r[5]==(0x1ULL|0x1ULL<<8|1ULL<<16|1ULL<<24|0x8ULL<<32|0x8ULL<<48));
        assert(wsStart(m,g,placeholder,true,r)==2 && r[9]==0x2 && m.writes==2 && m.read8(c1+ControllerWsWait)==0 && m.read32(c1+ControllerComputed)==0 &&
            m.read8(c0+ControllerWsWait)==0x6 && m.read32(c0+ControllerComputed)==0x1048);
        assert(r[4]==(0x6ULL|0x6ULL<<8|3ULL<<16|0x1048ULL<<32|0x1048ULL<<48) && r[5]==(0x1ULL|0ULL<<8|1ULL<<16|1ULL<<24|1ULL<<25|0x8ULL<<32|0ULL<<48));
        assert(wsStart(m,g,placeholder,true,r)==2 && r[9]==0 && m.writes==2);   // already clear: nothing written
        // The cached word alone comes back (a recompute): only the word is written.
        m.put32(c1+ControllerComputed,0x48);
        assert(wsStart(m,g,placeholder,true,r)==2 && r[9]==0x2 && m.writes==3 && m.read32(c1+ControllerComputed)==0 && r[5]==(0x1ULL<<16|1ULL<<24|1ULL<<25|0x48ULL<<32));
        m.put8(c1+ControllerWsWait,1);
        auto none=[](uint64_t) {return false;};
        assert(wsStart(m,g,none,true,r)==2 && r[9]==0 && m.writes==3 && r[5]==(0x1ULL|0x1ULL<<8|1ULL<<16));
        Globals empty;
        assert(wsStart(m,empty,placeholder,true,r)==0 && r[8]==0);
        // A list head that holds nothing, and a controller whose array is empty: walked, never cleared.
        m.put64(gList,0);
        assert(wsStart(m,g,placeholder,true,r)==0 && r[8]==0 && m.writes==3);
        m.put64(gList,c1);m.put64(array1,0);
        assert(wsStart(m,g,placeholder,true,r)==1 && r[9]==0 && m.writes==3 && r[4]==(0x1ULL|0x1ULL<<8));
    }
    puts("rplp_iog: ok");
    return 0;
}
