// The carry of 64-bit additions in the Intel graphics compiler that the Xe compiler adapter of WhateverXe Graphics
// loads (/Library/GPUBundles/XeCompilerAdapter.bundle/Contents/MacOS/libigc-tgl.dylib, the same file for every macOS).
// This GPU has no 64-bit integer instructions: the compiler adds 64-bit values with addc, which writes the carry to the
// accumulator, and a move from acc0.0 that reads it. The hardware writes that carry at the subregister offset of addc's
// destination, so vISA::HWConformity::fixAddcSubb gives an addc narrower than the native width whose destination is not
// GRF-aligned a temporary destination, and copies it out. This build creates that temporary with no alignment (Any):
// the register allocator placed it at r41.1 or r5.2, the carry went to acc0.1 or acc0.2, and the move read acc0.0,
// which still held the low doubleword of the multiplication before it. The move's own temporary is GRF-aligned
// already, because the compiler aligns the destination of every instruction that reads the accumulator.
// The 2-D convolution kernel of Metal Performance Shaders splits its tap index with a magic-number division,
// (mulhi(t,m)+t)>>s with a 33-bit sum. Its SIMD8 binary, and its SIMD16 one when MPSGraph fuses an addition after the
// convolution as it does for a bias, got that addc at r5.2 and r41.1: on Raptor Lake-P the taps whose wrong carry had
// any of its low s bits set got a huge row index and dropped out of the sum on every run, taps 1, 3, 5 and 7 of a 3x3
// kernel and the 42 taps of a 7x7 one whose index is not a multiple of 8.
// The correction asks for GRF alignment, 16 words on this compiler's 32-byte registers, the value the compiler uses for
// the move. The page is matched by its offset, the replaced bytes and its complete SHA-256. Reads of the file return the
// corrected page once it has been executed, so the adapter's check of the compiler's file accepts the corrected file too
// (kern_xe_adapter_hash_page.hpp), under the same switch.
#pragma once
#include "kern_uhd770_page.hpp"
namespace IGCAddcAlign {
constexpr size_t PageSize=4096;
constexpr uint64_t FileOffset=0x4ad000;
// vISA::HWConformity::fixAddcSubb: insertMovAfter(iter,inst->getDst(),type,bb,alignment) for the addc's destination.
constexpr unsigned Site=0xc23;
static const uint8_t ReferenceSHA256[][32]{{0x92,0x68,0xdb,0x2b,0x38,0x1a,0x65,0x52,0x4b,0x2e,0x57,0x20,0x0c,0xf7,0xe4,0x1e,0x42,0x21,0x12,0x61,0x2c,0xb2,0x19,0xe6,0xda,0xd3,0xdb,0xaf,0x4b,0x65,0xd2,0x4e}};
static const uint8_t Native[]{
 0x4c,0x8b,0x44,0x24,0x18,                          // movq  0x18(%rsp),%r8: the block
 0x41,0xb9,0x01,0x00,0x00,0x00,                     // movl  $1,%r9d: Any
 0xe8,0xdd,0xaa,0xfe,0xff};                         // callq vISA::HWConformity::insertMovAfter
static const uint8_t Corrected[]{
 0x4c,0x8b,0x44,0x24,0x18,                          // movq  0x18(%rsp),%r8
 0x41,0xb9,0x10,0x00,0x00,0x00,                     // movl  $16,%r9d: a whole 32-byte register
 0xe8,0xdd,0xaa,0xfe,0xff};                         // callq vISA::HWConformity::insertMovAfter
static_assert(sizeof(Native)==sizeof(Corrected),"the call keeps its place");
// The call reaches insertMovAfter at 0x498710.
static_assert(FileOffset+Site+sizeof(Native)-0x15523==0x498710,"the same callee");
inline bool matches(const void *data,size_t size,uint64_t offset,bool validated,bool tainted) {
 if(!data || size!=PageSize || offset!=FileOffset || !validated || tainted)return false;
 if(memcmp(static_cast<const uint8_t *>(data)+Site,Native,sizeof(Native)))return false;
 for(const auto &digest:ReferenceSHA256)if(UHD770Page::matches(data,size,digest))return true;
 return false;
}
inline void apply(void *data) {memcpy(static_cast<uint8_t *>(data)+Site,Corrected,sizeof(Corrected));}
}
