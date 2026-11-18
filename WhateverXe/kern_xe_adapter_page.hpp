// Compute pipelines with a maximum thread count, in the Xe compiler adapter of WhateverXe Graphics 0.4.4
// (/Library/GPUBundles/XeCompilerAdapter.bundle/Contents/MacOS/adapter.dylib, the same file for every
// macOS). The compiler service hands the adapter the pipeline's state, 216 bytes. For a compute request
// the adapter compiles only an all-zero state and answers anything else with "Xe compiler unsupported
// compute state". A MTLComputePipelineDescriptor whose maxTotalThreadsPerThreadgroup is set puts that
// number at offset 0x9c, where Apple's Intel compiler plug-in read it and handed it to IGC as
// pipeline_max_total_threads_per_threadgroup. Apps that size their thread groups from their own kernels
// set it, and their pipelines failed in a few milliseconds.
// The adapter compiles the same way with or without that number, and the Metal driver gives every pipeline
// the maximum its compiled kernel supports (its SIMD width times the hardware threads of a subslice, at
// most 1024), whatever the request: apps that dispatch within the pipeline's maximum, as Metal requires,
// run as with the default. The correction lets that one field through, up to 1024; every other byte must
// still be zero.
// The page is matched by its offset, the replaced bytes and its complete SHA-256.
#pragma once
#include "kern_uhd770_page.hpp"
namespace XeAdapterComputeLimit {
constexpr size_t PageSize=4096;
constexpr uint64_t FileOffset=0;
// _XeBuildUntranslated: the compute state check, from after "cmpl $0x3,%r14d; jne" to the refusal at 0xe4b.
constexpr unsigned Site=0xe0a;
static const uint8_t ReferenceSHA256[][32]{{0x3f,0x4c,0x41,0xf8,0xdf,0x63,0x0a,0x76,0x9b,0xc8,0xd4,0x0b,0x7b,0x2f,0xf5,0x60,0x8c,0x15,0x9c,0xd1,0x47,0xe0,0x6f,0x68,0x28,0xb3,0x3f,0x13,0xb9,0x79,0x8a,0xf7}};
// Bytes 4..0xd6 of the state must be zero, then 0xf73 checks the suffix byte 0xd7.
static const uint8_t Native[]{
 0xb8,0x07,0x00,0x00,0x00,0x80,0x7c,0x06,0xfd,0x00,0x75,0x35,0x66,0x2e,0x0f,0x1f,0x84,0x00,0x00,0x00,0x00,0x00,
 0x80,0x7c,0x06,0xfe,0x00,0x75,0x24,0x80,0x7c,0x06,0xff,0x00,0x75,0x1d,0x48,0x3d,0xd7,0x00,0x00,0x00,0x0f,0x84,
 0x39,0x01,0x00,0x00,0x80,0x3c,0x06,0x00,0x75,0x0b,0x48,0x83,0xc0,0x04,0x80,0x7c,0x06,0xfd,0x00,0x74,0xd5};
// The same check with bytes 0x9c..0x9f skipped, after requiring that doubleword to be at most 1024.
static const uint8_t Corrected[]{
 0x81,0xbe,0x9c,0x00,0x00,0x00,0x00,0x04,0x00,0x00, // cmpl $0x400,0x9c(%rsi)
 0x77,0x35,                                         // ja   0xe4b (refusal)
 0xb8,0x04,0x00,0x00,0x00,                          // movl $4,%eax
 0x3d,0x9c,0x00,0x00,0x00,                          // cmpl $0x9c,%eax
 0x75,0x05,                                         // jne  0xe27
 0xb8,0xa0,0x00,0x00,0x00,                          // movl $0xa0,%eax
 0x80,0x3c,0x06,0x00,                               // cmpb $0,(%rsi,%rax)
 0x75,0x1e,                                         // jne  0xe4b (refusal)
 0xff,0xc0,                                         // incl %eax
 0x3d,0xd7,0x00,0x00,0x00,                          // cmpl $0xd7,%eax
 0x75,0xe5,                                         // jne  0xe1b
 0xe9,0x38,0x01,0x00,0x00,                          // jmp  0xf73 (suffix check)
 0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc,0xcc};
static_assert(sizeof(Native)==sizeof(Corrected) && Site+sizeof(Native)==0xe4b,"the refusal stays at 0xe4b");
inline bool matches(const void *data,size_t size,uint64_t offset,bool validated,bool tainted) {
 if(!data || size!=PageSize || offset!=FileOffset || !validated || tainted)return false;
 if(memcmp(static_cast<const uint8_t *>(data)+Site,Native,sizeof(Native)))return false;
 for(const auto &digest:ReferenceSHA256)if(UHD770Page::matches(data,size,digest))return true;
 return false;
}
inline void apply(void *data) {memcpy(static_cast<uint8_t *>(data)+Site,Corrected,sizeof(Corrected));}
}
