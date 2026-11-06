// From Samran Ahmad's WhateverXe-RaptorLakeP (samranahmad09/WhateverXe-RaptorLakeP, kern_rplp_iog.hpp at f4ed412 and
// 9657f2b, BSD-3-Clause, the same license as this plugin): the subset that the window-server wait fix needs. Kept as
// his: the IOFBController and IOFramebuffer field offsets, pointer(), object() and wsStart(). Reduced here: Globals
// holds the controller list head alone, and the record keeps a presence flag where his kept the controller's address,
// so no kernel address reaches the registry. His sampler and his display-pipe and accelerator records are not imported.
//
// The offsets are those of the installed IOGraphicsFamily objects: 585.2 on his machine, and read identical in 600
// (IOFBController::computeState, copyController and alias; IOFramebuffer::open, close and extGetAttribute). A pointer
// is followed only when it looks like one.
#ifndef KERN_RPLP_IOG_HPP
#define KERN_RPLP_IOG_HPP
#include <stdint.h>
namespace RPLPIOG {
// IOFBController: the next controller of the family's list, the inline null-terminated framebuffer array, the work
// bytes, the window-server wait byte and the cached computed-state word.
constexpr uint32_t ControllerNext=0x10,ControllerFBs=0x18,ControllerWsWait=0x1B4,
    ControllerNeedsWork=0x1B5,ControllerDidWork=0x1B6,ControllerAsyncWork=0x1B7,ControllerComputed=0x1BC;
// IOFramebuffer and its private part
constexpr uint32_t FBFlags=0x170,FBPendingPower=0x199,FBPrivate=0x1C8,PrivateController=0x0,
    PrivateSent=0x4F0,PrivateAcked=0x4F4;
constexpr unsigned MaxControllers=4,MaxFBsPerController=32;
struct Globals {uint64_t controllers {};};
inline bool pointer(uint64_t p) {return p>=0xFFFFFF8000000000ULL && p<0xFFFFFFFFFFFFF000ULL && !(p&7);}
inline bool object(uint64_t p) {return p>=0xFFFFFF8000000000ULL && p<0xFFFFFFFFFFFFF000ULL;}
// -wex-rplp-wsstart (his rounds 55 and 56): a controller whose framebuffers the window server never opens keeps its
// window-server wait byte set for good, and the family's systemWork (public IOGraphics 585.1) sends the power-down
// notification to the server, and afterwards the early WillSleep to the accelerators, only while no controller has
// that byte set. wsStart() walks the family's controller list and, for a controller whose every framebuffer
// `isPlaceholder` admits (the caller decides by class), writes the wait byte and the controller's cached
// computed-state word to zero when `clear` is set. Round 56 showed the byte alone changes nothing: the family's
// computeState() returns the cached word (+0x1BC) unless the controller has pending work, and the placeholder's
// controller never has any, so its stale word (the wait bit and "server acknowledged power on") stays in the aggregate
// for good. A zero word is the transparent one: the placeholder then gates nothing. r[0..3] the controllers (1 where
// one was found), r[4..7] per controller: wait before | wait after << 8 | framebuffers << 16 | all placeholders << 24
// | cleared << 25 | computed before << 32 (16 bits) | computed after << 48 (16 bits); r[8] the controllers seen; r[9]
// the mask cleared this call.
template<class Mem,class IsPlaceholder> unsigned wsStart(Mem &m,const Globals &g,IsPlaceholder isPlaceholder,bool clear,uint64_t (&r)[12]) {
    for(auto &v:r)v=0;
    uint64_t c=g.controllers ? m.read64(g.controllers) : 0;
    unsigned n=0;
    for(;n<MaxControllers && pointer(c);++n) {
        r[n]=1;
        const uint8_t wait=m.read8(c+ControllerWsWait);
        const uint32_t computed=m.read32(c+ControllerComputed);
        unsigned fbs=0;bool placeholder=true;
        for(unsigned j=0;j<MaxFBsPerController;++j) {
            const auto fb=m.read64(c+ControllerFBs+8*j);
            if(!pointer(fb))break;
            ++fbs;
            if(!isPlaceholder(fb))placeholder=false;
        }
        uint64_t v=uint64_t(wait)|uint64_t(fbs)<<16|uint64_t(fbs && placeholder)<<24|uint64_t(computed&0xFFFFU)<<32;
        if(fbs && placeholder && clear && (wait || computed)) {
            if(wait)m.write8(c+ControllerWsWait,0);
            if(computed)m.write32(c+ControllerComputed,0);
            v|=1ULL<<25;r[9]|=1U<<n;
        }
        v|=uint64_t(m.read8(c+ControllerWsWait))<<8|uint64_t(m.read32(c+ControllerComputed)&0xFFFFU)<<48;
        r[4+n]=v;
        c=m.read64(c+ControllerNext);
    }
    r[8]=n;
    return n;
}
}
#endif
