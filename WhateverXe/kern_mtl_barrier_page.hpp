// The pending-barrier flag of a compute context in Apple's Tiger Lake Metal driver. -[MTLIGAccelCommandBuffer
// initContextStateDescriptorForEngine:] allocates a CHAL_INTEL::ChalContext with operator new (0x7b00 bytes, not
// zeroed) and its constructor clears the concurrent-dispatch flag at +0x7ac8 but not the pending-barrier flag next to
// it at +0x7ac9. ChalExecuteKernel gives a dispatch barrier mode 2 while that flag is set, a flush before its walker
// and none after it, and clears the flag; sampleCountersInBuffer with a barrier is what sets it on purpose.
// A new context starts with whatever the allocation held there. In a network run through MPSGraph about 40 % of the
// compute encoders began with the flag set, so their first dispatch ran without the PIPE_CONTROL that follows every
// walker of a serial encoder, and the next dispatch of the encoder read that dispatch's output before it was visible:
// a convolution got whole 64-byte lines of the old contents of the tensor that an element-wise kernel had just written,
// and the networks returned wrong values on new data, at random. Clearing the flag in the process when the encoder is
// created gave every dispatch its PIPE_CONTROL and right values; that PIPE_CONTROL alone is enough.
// The constructor's one-byte store of zero becomes a two-byte store of the register it has just cleared, so both flags
// start clear. The page also carries the SIMD choice correction (kern_mtl_simd_page.hpp); each has its own switch.
// The page is matched by its offset, the instructions from the cleared register to the store and its complete
// SHA-256: the Metal driver of WhateverXe Graphics 0.4.4 for Tahoe.
#pragma once
#include "kern_uhd770_page.hpp"
namespace MetalPendingBarrier {
constexpr size_t PageSize=4096;
constexpr uint64_t FileOffset=0x2c000;
// ChalContext::ChalContext() at 0x2c320: the last stores of its fields, from 0x2c3de.
constexpr unsigned Site=0x3de;
static const uint8_t ReferenceSHA256[][32]{{0xc5,0x08,0x0c,0x36,0x2a,0x45,0x44,0x79,0x0f,0x8c,0xf7,0x09,0x04,0xe0,0x90,0x5c,0x0a,0x51,0x12,0x90,0xa0,0xb6,0xf8,0x85,0x81,0xe6,0x21,0x53,0xd6,0x43,0x7a,0x07}};
static const uint8_t Native[]{
 0x31,0xc0,                                         // xorl  %eax,%eax
 0x89,0x83,0x98,0x7a,0x00,0x00,                     // movl  %eax,0x7a98(%rbx)
 0x48,0x89,0x83,0xa0,0x7a,0x00,0x00,                // movq  %rax,0x7aa0(%rbx)
 0xc6,0x83,0xc8,0x7a,0x00,0x00,0x00};               // movb  $0x0,0x7ac8(%rbx): the concurrent-dispatch flag only
static const uint8_t Corrected[]{
 0x31,0xc0,                                         // xorl  %eax,%eax
 0x89,0x83,0x98,0x7a,0x00,0x00,                     // movl  %eax,0x7a98(%rbx)
 0x48,0x89,0x83,0xa0,0x7a,0x00,0x00,                // movq  %rax,0x7aa0(%rbx)
 0x66,0x89,0x83,0xc8,0x7a,0x00,0x00};               // movw  %ax,0x7ac8(%rbx): and the pending-barrier flag
static_assert(sizeof(Native)==sizeof(Corrected),"the same instructions are replaced");
inline bool matches(const void *data,size_t size,uint64_t offset,bool validated,bool tainted) {
 if(!data || size!=PageSize || offset!=FileOffset || !validated || tainted)return false;
 if(memcmp(static_cast<const uint8_t *>(data)+Site,Native,sizeof(Native)))return false;
 for(const auto &digest:ReferenceSHA256)if(UHD770Page::matches(data,size,digest))return true;
 return false;
}
inline void apply(void *data) {memcpy(static_cast<uint8_t *>(data)+Site,Corrected,sizeof(Corrected));}
}
