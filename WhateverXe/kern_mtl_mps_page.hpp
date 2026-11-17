// Intel's plug-in for Metal Performance Shaders inside Apple's Tiger Lake Metal
// driver. MPS tries the plug-in's kernels before its own, and the plug-in builds
// them from sources that declare AIR functions with asm labels. The Metal
// compiler of macOS 26 rejects those ("illegal string literal in 'asm'") on any
// GPU, so every kernel fails to build and MPS falls back to its own: loading the
// network of one Vision image classification asks for 732 compilations that all
// fail, about 7 s instead of 0.3 s. The drivers Apple ships for its own Intel
// GPUs in macOS 26 carry the same sources.
// The plug-in calls isMPSIntelPluginEnabled() before every use, and that function
// is the only reader of MPSIntelPluginEnable in the bundle's Info.plist. Making
// it return false is that switch at 0, with the sealed Info.plist left alone.
// The page is matched by its offset, the function's first bytes and its complete
// SHA-256: the Metal driver of WhateverXe Graphics 0.4.4 for Tahoe.
#pragma once
#include "kern_uhd770_page.hpp"
namespace MetalMPSPlugin {
constexpr size_t PageSize=4096;
constexpr uint64_t FileOffset=0x2b000;
constexpr unsigned PatchOffset=0xb80; // isMPSIntelPluginEnabled() at 0x2bb80
static const uint8_t ReferenceSHA256[][32]{{0x5d,0xfe,0xc2,0xeb,0x44,0xba,0x73,0xa5,0xf3,0x52,0xe8,0x55,0xb3,0x40,0x66,0x3c,0xfb,0xa0,0xd2,0xc1,0x53,0xee,0x59,0x17,0x55,0x5e,0x30,0xe3,0x77,0x4c,0xc1,0xcc}};
// push %rbp; mov %rsp,%rbp; push %r14; push %rbx; sub $0x10,%rsp; lea cfstring(%rip),%rdi
static const uint8_t Original[]{0x55,0x48,0x89,0xe5,0x41,0x56,0x53,0x48,0x83,0xec,0x10,0x48,0x8d,0x3d};
static const uint8_t Replacement[]{0x31,0xc0,0xc3}; // xor %eax,%eax; ret
inline bool matches(const void *data,size_t size,uint64_t offset,bool validated,bool tainted) {
 if(!data || size!=PageSize || offset!=FileOffset || !validated || tainted)return false;
 if(memcmp(static_cast<const uint8_t *>(data)+PatchOffset,Original,sizeof(Original)))return false;
 for(const auto &digest:ReferenceSHA256)if(UHD770Page::matches(data,size,digest))return true;
 return false;
}
inline void apply(void *data) {memcpy(static_cast<uint8_t *>(data)+PatchOffset,Replacement,sizeof(Replacement));}
}
