// Thread-group memory of Metal compute kernels in Apple's Tiger Lake Metal
// driver. The driver tells the GPU how much shared local memory one thread
// group gets as a size class in the kernel's interface descriptor
// (COCLGen8CommandTransport::PatchIDData): 1, 2, 4, 8, 16, 32 or 64 KB. The GPU
// runs as many groups of a kernel at once as fit in its shared local memory, so
// a smaller class keeps more groups alive together.
// On Raptor Lake-P the convolution kernel of Metal Performance Shaders that
// multiplies two matrices inside that memory (cnnConvArray_32x32_128, 8720
// bytes, the 16 KB class) now and then finds one 64-byte line of it zero: one
// term of the sum is missing for a block of 8x2 or 8x4 pixels, in about one
// 64x64 convolution in a hundred, and the results of a Vision request change
// from one run to the next. It happens with the 16 KB class (up to seven groups
// of that kernel alive in one dual subslice), eight times less often with the
// 32 KB class (four groups) and never with the 64 KB class (two groups).
// Requests that would get the 16 or the 32 KB class get the 64 KB one. Smaller
// requests keep their class.
// The page is matched by its offset, the two instructions that load those
// classes and its complete SHA-256: the Metal driver of WhateverXe Graphics
// 0.4.4 for Tahoe.
#pragma once
#include "kern_uhd770_page.hpp"
namespace MetalSLMClass {
constexpr size_t PageSize=4096;
constexpr uint64_t FileOffset=0x38000;
// PatchIDData at 0x38f64: mov $0x50000,%eax; jmp at 0x38fcc and mov $0x60000,%eax; jmp at 0x38fda.
// The class is bits 20:16 of that doubleword of the descriptor: the fourth byte of each instruction.
constexpr unsigned Class16KOffset=0xfcc,Class32KOffset=0xfda,ClassByte=3;
static const uint8_t ReferenceSHA256[][32]{{0x0d,0x27,0x64,0x7b,0x94,0x1c,0xbd,0x93,0x4c,0xf0,0xae,0x57,0x2b,0x35,0x25,0x49,0x46,0x28,0xbf,0xf3,0x6f,0x54,0x92,0x96,0x44,0x61,0x1f,0x66,0x1e,0xcd,0x00,0x0b}};
static const uint8_t Class16K[]{0xb8,0x00,0x00,0x05,0x00,0xeb,0x24};
static const uint8_t Class32K[]{0xb8,0x00,0x00,0x06,0x00,0xeb,0x16};
constexpr uint8_t Class64K=0x07;
inline bool matches(const void *data,size_t size,uint64_t offset,bool validated,bool tainted) {
 if(!data || size!=PageSize || offset!=FileOffset || !validated || tainted)return false;
 const auto p=static_cast<const uint8_t *>(data);
 if(memcmp(p+Class16KOffset,Class16K,sizeof(Class16K)) || memcmp(p+Class32KOffset,Class32K,sizeof(Class32K)))return false;
 for(const auto &digest:ReferenceSHA256)if(UHD770Page::matches(data,size,digest))return true;
 return false;
}
inline void apply(void *data) {
 const auto p=static_cast<uint8_t *>(data);
 p[Class16KOffset+ClassByte]=Class64K;p[Class32KOffset+ClassByte]=Class64K;
}
}
