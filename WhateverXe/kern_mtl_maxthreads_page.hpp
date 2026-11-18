// The maximum thread count of a compute pipeline in Apple's Tiger Lake Metal driver. The driver stores the kernel's
// SIMD width times the hardware threads of a subslice, at most 1024 (-[MTLIGComputePipelineState storeCompilerOutput:]):
// 1024 for a SIMD32 kernel, 896 for a SIMD16 one and 448 for a SIMD8 one. Apps that size their thread groups from
// maxTotalThreadsPerThreadgroup then run groups of 896 or 448 threads, while kernels written for OpenCL-style devices
// assume a power of two there. A tree reduction over the group (for (offset = size / 2; offset > 0; offset >>= 1))
// drops terms with 896 threads: a face tracking kernel that the Xe compiler adapter of WhateverXe Graphics builds in
// SIMD16 only summed its boxes to about 57 % of the true value with 896 threads per group, and right with 512 or 256.
// The same kernel returns early before its barriers; with a group that is not a power of two, part of a group can
// return while the rest waits at the barrier.
// The getter returns the largest power of two not above the stored maximum: 512 for SIMD16 kernels, 256 for SIMD8
// ones, 1024 unchanged. Every group an app sizes from it fits the kernel as before; the driver's own value is unchanged.
// The page is matched by its offset, the getter's 17 bytes and its complete SHA-256: the Metal driver of WhateverXe
// Graphics 0.4.4 for Tahoe.
#pragma once
#include "kern_uhd770_page.hpp"
namespace MetalPow2MaxThreads {
constexpr size_t PageSize=4096;
constexpr uint64_t FileOffset=0x81000;
// -[MTLIGComputePipelineState maxTotalThreadsPerThreadgroup] at 0x819d4, followed at once by the next method.
constexpr unsigned Site=0x9d4;
static const uint8_t ReferenceSHA256[][32]{{0x2b,0xfb,0x62,0xdf,0xcd,0x0a,0x89,0x54,0x3d,0x06,0x32,0x54,0xbb,0xc2,0x06,0xb5,0x66,0xf4,0x09,0x34,0xb1,0xc4,0xd7,0xc0,0x62,0x6f,0xe2,0x98,0xfa,0xbf,0xc6,0xb3}};
static const uint8_t Native[]{
 0x55,                                              // pushq %rbp
 0x48,0x89,0xe5,                                    // movq  %rsp,%rbp
 0x48,0x8b,0x05,0xf1,0x84,0x41,0x00,                // movq  _OBJC_IVAR_$_..._maxTotalThreadsPerThreadgroup(%rip),%rax
 0x48,0x8b,0x04,0x07,                               // movq  (%rdi,%rax),%rax
 0x5d,                                              // popq  %rbp
 0xc3};                                             // retq
static const uint8_t Corrected[]{
 0x48,0x8b,0x05,0xf5,0x84,0x41,0x00,                // movq  the same ivar offset(%rip),%rax
 0x0f,0xbd,0x0c,0x07,                               // bsrl  (%rdi,%rax),%ecx: the highest set bit of the maximum
 0x31,0xc0,                                         // xorl  %eax,%eax
 0x0f,0xab,0xc8,                                    // btsl  %ecx,%eax
 0xc3};                                             // retq
static_assert(sizeof(Native)==sizeof(Corrected),"the getter keeps its size");
// Both loads must reach the same ivar offset variable at 0x499ed0.
static_assert(Site+11+0x4184f1==Site+7+0x4184f5,"the same ivar offset variable");
inline bool matches(const void *data,size_t size,uint64_t offset,bool validated,bool tainted) {
 if(!data || size!=PageSize || offset!=FileOffset || !validated || tainted)return false;
 if(memcmp(static_cast<const uint8_t *>(data)+Site,Native,sizeof(Native)))return false;
 for(const auto &digest:ReferenceSHA256)if(UHD770Page::matches(data,size,digest))return true;
 return false;
}
inline void apply(void *data) {memcpy(static_cast<uint8_t *>(data)+Site,Corrected,sizeof(Corrected));}
}
