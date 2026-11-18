// The Xe compiler adapter of WhateverXe Graphics checks the Intel graphics compiler it loads
// (/Library/GPUBundles/XeCompilerAdapter.bundle/Contents/MacOS/adapter.dylib, the same file for every macOS). Its
// _verified reads libigc-tgl.dylib from disk, hashes the whole file with SHA-256 and refuses the compiler with "Xe
// compiler backend hash mismatch" unless the digest is the one of the shipped file. A page that the code-signing
// validator route corrects in memory is also what reads of the file return, while reads made before that page is first
// executed return the shipped bytes. With the carry correction of the compiler (kern_igc_addc_page.hpp) the first
// compiler service of a boot therefore loaded the compiler, corrected its page, and every compiler service started
// after it refused the compiler: no new Metal pipeline could be built on the GPU until the next boot.
// The check accepts both digests, the shipped file and the shipped file with that one byte corrected, and nothing else.
// The comparison in _verified, on the adapter's first page, calls a helper placed in the zero padding at the end of
// the adapter's __TEXT segment, on its third page. The helper compares the digest with the shipped value, still read
// from the adapter's own constant, and with the corrected one stored beside it.
// Both pages are matched by their offset, the replaced bytes and their complete SHA-256. The first page also carries
// the adapter's UUID: a matching first page means the same file, so the third page the call reaches matches too.
#pragma once
#include "kern_uhd770_page.hpp"
namespace XeAdapterBackendHash {
constexpr size_t PageSize=4096;
constexpr uint64_t CallOffset=0,HelperOffset=0x2000;
// _verified: the digest of the file at -0x8040(%rbp), the shipped digest at 0x2030 (bytes 0-15) and 0x2020 (16-31).
constexpr unsigned CallSite=0xc24,HelperSite=0x830;
// The first page is the one XeAdapterComputeLimit corrects too, with the same identity.
static const uint8_t CallSHA256[][32]{{0x3f,0x4c,0x41,0xf8,0xdf,0x63,0x0a,0x76,0x9b,0xc8,0xd4,0x0b,0x7b,0x2f,0xf5,0x60,0x8c,0x15,0x9c,0xd1,0x47,0xe0,0x6f,0x68,0x28,0xb3,0x3f,0x13,0xb9,0x79,0x8a,0xf7}};
static const uint8_t HelperSHA256[][32]{{0x9a,0x3b,0x20,0x0d,0xaa,0x00,0x15,0xa6,0xa3,0x14,0xea,0x4b,0x7c,0x53,0x52,0x9a,0x72,0x80,0x71,0xb8,0x06,0x1d,0x0b,0xb8,0x9a,0x2c,0xba,0x52,0x0b,0xc1,0x7d,0xe7}};
static const uint8_t CallNative[]{
 0x66,0x0f,0x6f,0x85,0xd0,0x7f,0xff,0xff,           // movdqa -0x8030(%rbp),%xmm0
 0x66,0x0f,0xef,0x05,0xec,0x13,0x00,0x00,           // pxor   0x2020(%rip),%xmm0
 0x66,0x0f,0x6f,0x8d,0xc0,0x7f,0xff,0xff,           // movdqa -0x8040(%rbp),%xmm1
 0x66,0x0f,0xef,0x0d,0xec,0x13,0x00,0x00,           // pxor   0x2030(%rip),%xmm1
 0x66,0x0f,0xeb,0xc8,                               // por    %xmm0,%xmm1
 0x31,0xc0,                                         // xorl   %eax,%eax
 0x66,0x0f,0x38,0x17,0xc9,                          // ptest  %xmm1,%xmm1
 0x0f,0x94,0xc0,                                    // sete   %al
 0xeb,0x02};                                        // jmp    0xc56: return
static const uint8_t CallCorrected[]{
 0x48,0x8d,0xbd,0xc0,0x7f,0xff,0xff,                // leaq   -0x8040(%rbp),%rdi: the digest
 0xe8,0x00,0x1c,0x00,0x00,                          // callq  0x2830: the helper
 0xeb,0x24,                                         // jmp    0xc56: return
 0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,
 0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc};
// At 0x2830, after the last byte of __unwind_info at 0x282b: returns 1 in %eax for either digest, 0 otherwise.
static const uint8_t HelperCorrected[]{
 0xf3,0x0f,0x6f,0x07,                               // movdqu (%rdi),%xmm0: bytes 0-15
 0xf3,0x0f,0x6f,0x4f,0x10,                          // movdqu 0x10(%rdi),%xmm1: bytes 16-31
 0x66,0x0f,0x6f,0xd0,                               // movdqa %xmm0,%xmm2
 0x66,0x0f,0x6f,0xd9,                               // movdqa %xmm1,%xmm3
 0x66,0x0f,0xef,0x05,0xe7,0xf7,0xff,0xff,           // pxor   0x2030(%rip),%xmm0: shipped, bytes 0-15
 0x66,0x0f,0xef,0x0d,0xcf,0xf7,0xff,0xff,           // pxor   0x2020(%rip),%xmm1: shipped, bytes 16-31
 0x66,0x0f,0xeb,0xc1,                               // por    %xmm1,%xmm0
 0x66,0x0f,0xef,0x15,0x23,0x00,0x00,0x00,           // pxor   0x2880(%rip),%xmm2: corrected, bytes 0-15
 0x66,0x0f,0xef,0x1d,0x2b,0x00,0x00,0x00,           // pxor   0x2890(%rip),%xmm3: corrected, bytes 16-31
 0x66,0x0f,0xeb,0xd3,                               // por    %xmm3,%xmm2
 0x31,0xc0,                                         // xorl   %eax,%eax
 0x66,0x0f,0x38,0x17,0xc0,                          // ptest  %xmm0,%xmm0
 0x74,0x05,                                         // je     0x2877
 0x66,0x0f,0x38,0x17,0xd2,                          // ptest  %xmm2,%xmm2
 0x0f,0x94,0xc0,                                    // sete   %al
 0xc3,                                              // retq
 0xcc,0xcc,0xcc,0xcc,0xcc,
 // 0x2880: SHA-256 of libigc-tgl.dylib with IGCAddcAlign's byte, 16-byte aligned for pxor.
 0x6c,0x2d,0xa9,0x78,0x99,0x19,0xb9,0x27,0xc4,0x39,0x8e,0xc6,0x58,0x0d,0x5b,0x39,
 0x14,0xa4,0x78,0xc0,0xc2,0xea,0x6a,0x86,0x1f,0x3d,0x3d,0xd2,0xe9,0x56,0xac,0x3b};
static_assert(sizeof(CallNative)==sizeof(CallCorrected) && CallSite+sizeof(CallNative)==0xc54,"0xc54 stays the refusal of a missing file");
static_assert(CallOffset+CallSite+12+0x1c00==HelperOffset+HelperSite,"the call reaches the helper");
static_assert(sizeof(HelperCorrected)==0x70 && HelperSite+0x50==0x880,"the corrected digest sits at 0x2880");
inline bool matchesCall(const void *data,size_t size,uint64_t offset,bool validated,bool tainted) {
 if(!data || size!=PageSize || offset!=CallOffset || !validated || tainted)return false;
 if(memcmp(static_cast<const uint8_t *>(data)+CallSite,CallNative,sizeof(CallNative)))return false;
 for(const auto &digest:CallSHA256)if(UHD770Page::matches(data,size,digest))return true;
 return false;
}
inline bool matchesHelper(const void *data,size_t size,uint64_t offset,bool validated,bool tainted) {
 if(!data || size!=PageSize || offset!=HelperOffset || !validated || tainted)return false;
 const auto *bytes=static_cast<const uint8_t *>(data)+HelperSite;
 for(size_t i=0;i<sizeof(HelperCorrected);++i)if(bytes[i])return false;
 for(const auto &digest:HelperSHA256)if(UHD770Page::matches(data,size,digest))return true;
 return false;
}
inline void applyCall(void *data) {memcpy(static_cast<uint8_t *>(data)+CallSite,CallCorrected,sizeof(CallCorrected));}
inline void applyHelper(void *data) {memcpy(static_cast<uint8_t *>(data)+HelperSite,HelperCorrected,sizeof(HelperCorrected));}
}
