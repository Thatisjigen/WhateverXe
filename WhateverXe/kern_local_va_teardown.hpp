// The second-level batch buffer of the HEVC decoder in Apple's Tiger Lake VA driver. The Gen12 decoder allocates it
// (Mhw_AllocateBb, a buffer named "BatchBuffer") whenever it sizes its variable resources, in the long slice format as
// well, but the decoder's resource destructor at 0x772f0 frees it (Mhw_FreeBb) only inside the block for the short
// format, behind that format's flag at +0xbae. Every long-format decoder left that buffer behind when it was destroyed,
// and with it a reference on the IOAccelShared the decoder had opened for its session: the driver released its shared
// and its device, the device and the three video contexts closed, and the accelerator's shared user client stayed open.
// A process that creates decoders again and again, as VTDecoderXPCService does for a video wallpaper that restarts its
// clip, piled up one IGAccelSharedUserClient and one buffer per decoder, until the accelerator refused new clients and
// every process that opened the GPU afterwards failed with kIOReturnUnsupported from IOServiceOpen.
// The block now frees the batch buffer first, whatever the format, and then tests the flag for the eight short-format
// resources that follow, as before. Mhw_FreeBb and the resource release it calls accept a buffer that was never
// allocated: the decoder's constructor leaves it null, which the allocation path checks before allocating.
// The page is matched by its offset, the replaced instructions and its complete SHA-256: the VA driver of WhateverXe
// Graphics 0.4.0 and 0.4.4 for Tahoe.
#pragma once
#include "kern_uhd770_page.hpp"
namespace LocalVAHEVCTeardown {
constexpr size_t PageSize=4096;
constexpr uint64_t FileOffset=0x77000;
// The short-format block of the destructor, from 0x775a1 to the loop condition at 0x775d4; %rax holds the decoder and
// -0x30(%rbp) a copy of it, -0x24(%rbp) is the loop counter, 0x77623 is the code after the block.
constexpr unsigned Site=0x5a1;
static const uint8_t ReferenceSHA256[][32]{{0x50,0x91,0x76,0x4c,0x6a,0x25,0xa3,0x63,0xcf,0x8a,0x6e,0x63,0x71,0x5b,0xcc,0x49,0xfc,0x96,0x52,0xba,0x7f,0xc5,0xc1,0x41,0xcb,0x67,0x6b,0x5f,0x26,0x89,0xa0,0x15}};
static const uint8_t Native[]{
 0xf6,0x80,0xae,0x0b,0x00,0x00,0x01,               // testb $0x1,0xbae(%rax): the short-format flag
 0x0f,0x84,0x75,0x00,0x00,0x00,                    // je    0x77623: past the whole block
 0x48,0x8b,0x45,0xd0,                              // movq  -0x30(%rbp),%rax
 0x48,0x8b,0x78,0x10,                              // movq  0x10(%rax),%rdi: the OS interface
 0x48,0x05,0x50,0x52,0x00,0x00,                    // addq  $0x5250,%rax: the batch buffer
 0x31,0xc9,                                        // xorl  %ecx,%ecx
 0x89,0xca,                                        // movl  %ecx,%edx: no buffer list
 0x48,0x89,0xc6,                                   // movq  %rax,%rsi
 0xe8,0x58,0x99,0xfc,0xff,                         // callq 0x40f20: Mhw_FreeBb
 0xe9,0x00,0x00,0x00,0x00,                         // jmp   0x775cd
 0xc7,0x45,0xdc,0x00,0x00,0x00,0x00};              // movl  $0x0,-0x24(%rbp): the loop over the eight resources
static const uint8_t Corrected[]{
 0x48,0x8b,0x78,0x10,                              // movq  0x10(%rax),%rdi: the OS interface
 0x48,0x8d,0xb0,0x50,0x52,0x00,0x00,               // leaq  0x5250(%rax),%rsi: the batch buffer
 0x31,0xd2,                                        // xorl  %edx,%edx: no buffer list
 0xe8,0x6d,0x99,0xfc,0xff,                         // callq 0x40f20: Mhw_FreeBb, for every format
 0x48,0x8b,0x45,0xd0,                              // movq  -0x30(%rbp),%rax
 0xf6,0x80,0xae,0x0b,0x00,0x00,0x01,               // testb $0x1,0xbae(%rax): the short-format flag
 0x74,0x63,                                        // je    0x77623: past the loop
 0xc7,0x45,0xdc,0x00,0x00,0x00,0x00,               // movl  $0x0,-0x24(%rbp)
 0xeb,0x0b,                                        // jmp   0x775d4: the loop condition
 0x0f,0x1f,0x80,0x00,0x00,0x00,0x00,               // nopl  (unreached)
 0x0f,0x1f,0x40,0x00};                             // nopl  (unreached)
static_assert(sizeof(Native)==sizeof(Corrected) && Site+sizeof(Native)==0x5d4,"the block up to the loop condition is replaced");
inline bool matches(const void *data,size_t size,uint64_t offset,bool validated,bool tainted) {
 if(!data || size!=PageSize || offset!=FileOffset || !validated || tainted)return false;
 if(memcmp(static_cast<const uint8_t *>(data)+Site,Native,sizeof(Native)))return false;
 for(const auto &digest:ReferenceSHA256)if(UHD770Page::matches(data,size,digest))return true;
 return false;
}
inline void apply(void *data) {memcpy(static_cast<uint8_t *>(data)+Site,Corrected,sizeof(Corrected));}
}
