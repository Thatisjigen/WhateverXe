// The SIMD width of small Metal compute dispatches in Apple's Tiger Lake Metal driver. A compute pipeline keeps up to
// three kernel binaries, one for each SIMD width the compiler built, and at every dispatch
// CHAL_INTEL::ChalContext::ChalExecuteKernel picks one: the SIMD8 binary when the whole dispatch fits in the GPU's
// hardware threads eight lanes at a time (5376 threads on a 96-EU GPU), otherwise the SIMD16 binary when it fits
// sixteen lanes at a time, otherwise the first binary.
// On Raptor Lake-P the SIMD8 binary of the 2-D convolution kernel of Metal Performance Shaders (ndArrayConvolution2D),
// as the Xe compiler adapter of WhateverXe Graphics builds it, leaves terms out of the sum: with a 3x3 kernel the
// taps 1, 3, 5 and 7 are missing from every output, the same way on every run, while its SIMD16 binary is right. A
// convolution with 42 thread groups of 128 threads or fewer (a 32x32 output with 32 channels) failed, one with 43 or
// more (a 33x33 output, or 32x32 with 64 channels) did not. Image networks run such small convolutions all the time.
// The selection no longer prefers the SIMD8 binary: a dispatch that fits runs the SIMD16 one, as every larger dispatch
// already did. A pipeline without a SIMD16 binary still runs its first one.
// The page is matched by its offset, the two replaced instructions and its complete SHA-256: the Metal driver of
// WhateverXe Graphics 0.4.4 for Tahoe.
#pragma once
#include "kern_uhd770_page.hpp"
namespace MetalSIMDChoice {
constexpr size_t PageSize=4096;
constexpr uint64_t FileOffset=0x2c000;
// ChalExecuteKernel at 0x2c848, after its scan of the binaries: without a SIMD8 binary, go on to the SIMD16 test.
constexpr unsigned Site=0x8bf;
static const uint8_t ReferenceSHA256[][32]{{0xc5,0x08,0x0c,0x36,0x2a,0x45,0x44,0x79,0x0f,0x8c,0xf7,0x09,0x04,0xe0,0x90,0x5c,0x0a,0x51,0x12,0x90,0xa0,0xb6,0xf8,0x85,0x81,0xe6,0x21,0x53,0xd6,0x43,0x7a,0x07}};
static const uint8_t Native[]{
 0x45,0x85,0xff,                                    // testl %r15d,%r15d (index of the SIMD8 binary, or -1)
 0x78,0x1c};                                        // js   0x2c8e0 (the SIMD16 test)
static const uint8_t Corrected[]{
 0xeb,0x1f,                                         // jmp  0x2c8e0 (the SIMD16 test)
 0x0f,0x1f,0x00};                                   // nopl (%rax)
static_assert(sizeof(Native)==sizeof(Corrected),"the same instructions are replaced");
inline bool matches(const void *data,size_t size,uint64_t offset,bool validated,bool tainted) {
 if(!data || size!=PageSize || offset!=FileOffset || !validated || tainted)return false;
 if(memcmp(static_cast<const uint8_t *>(data)+Site,Native,sizeof(Native)))return false;
 for(const auto &digest:ReferenceSHA256)if(UHD770Page::matches(data,size,digest))return true;
 return false;
}
inline void apply(void *data) {memcpy(static_cast<uint8_t *>(data)+Site,Corrected,sizeof(Corrected));}
}
