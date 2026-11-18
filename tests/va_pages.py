#!/usr/bin/env python3
"""Exercise the VA page validator and optionally replay the VA packet generator, CPU only.

Adapted from lymzzyh's tgl_va_vfe.py (lymzzyh/WhateverXe f9be946): the A7A0 scope,
two switches, and only the first video-processing output list. With the VA driver
image as argument the real pages are checked and the packet generator is replayed."""
from pathlib import Path
import argparse,hashlib,re,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('donor',nargs='?',type=Path);ap.add_argument('--intel-gen12',type=Path);ap.add_argument('--metal',type=Path)
ap.add_argument('--adapter',type=Path);ap.add_argument('--igc',type=Path);args=ap.parse_args()
s=(root/'WhateverXe/kern_va_pages.hpp').read_text()
production=s[s.index('static mach_vm_address_t vaOriginalPage;'):]
header=(root/'WhateverXe/kern_local_va_vfe.hpp').read_text()
safeHeader=(root/'WhateverXe/kern_local_va_safe.hpp').read_text()
identity=re.search(r'ReferenceSHA256\[\]\{([^}]+)\}',header);expected=bytes(int(n,0) for n in identity[1].split(','))
first=re.search(r'\{0x786000,\{([^}]+)\}',safeHeader)
pixelHeader=(root/'WhateverXe/kern_local_va_pixel.hpp').read_text()
pfirst=re.search(r'\{0x2b000,\{([^}]+)\}',pixelHeader)
mpsHeader=(root/'WhateverXe/kern_mtl_mps_page.hpp').read_text()
mpsIdentity=re.search(r'ReferenceSHA256\[\]\[32\]\{\{([^}]+)\}\}',mpsHeader)
mpsOriginal=bytes(int(n,0) for n in re.search(r'Original\[\]\{([^}]+)\}',mpsHeader)[1].split(','))
if args.metal:
 # The Metal driver image: its real page must be the one the header names.
 mps=args.metal.read_bytes()[0x2b000:0x2c000];assert hashlib.sha256(mps).digest()==bytes(int(n,0) for n in mpsIdentity[1].split(','))
 assert mps[0xb80:0xb80+len(mpsOriginal)]==mpsOriginal
else:
 # A synthetic page carrying the first bytes of isMPSIntelPluginEnabled() where the driver has them.
 mps=bytearray((i*41+3)%256 for i in range(4096));mps[0xb80:0xb80+len(mpsOriginal)]=mpsOriginal
 mpsHeader=mpsHeader[:mpsIdentity.start(1)]+','.join(hex(v) for v in hashlib.sha256(mps).digest())+mpsHeader[mpsIdentity.end(1):]
slmHeader=(root/'WhateverXe/kern_mtl_slm_page.hpp').read_text()
slmIdentity=re.search(r'ReferenceSHA256\[\]\[32\]\{\{([^}]+)\}\}',slmHeader)
slm16,slm32=(bytes(int(n,0) for n in re.search(name+r'\[\]\{([^}]+)\}',slmHeader)[1].split(',')) for name in ('Class16K','Class32K'))
if args.metal:
 slm=args.metal.read_bytes()[0x38000:0x39000];assert hashlib.sha256(slm).digest()==bytes(int(n,0) for n in slmIdentity[1].split(','))
 assert slm[0xfcc:0xfcc+len(slm16)]==slm16 and slm[0xfda:0xfda+len(slm32)]==slm32
else:
 # A synthetic page carrying the two instructions that load the 16 and 32 KB classes where the driver has them.
 slm=bytearray((i*59+7)%256 for i in range(4096));slm[0xfcc:0xfcc+len(slm16)]=slm16;slm[0xfda:0xfda+len(slm32)]=slm32
 slmHeader=slmHeader[:slmIdentity.start(1)]+','.join(hex(v) for v in hashlib.sha256(slm).digest())+slmHeader[slmIdentity.end(1):]
limitHeader=(root/'WhateverXe/kern_xe_adapter_page.hpp').read_text()
limitIdentity=re.search(r'ReferenceSHA256\[\]\[32\]\{\{([^}]+)\}\}',limitHeader)
limitNative=bytes(int(n,0) for n in re.search(r'Native\[\]\{([^}]+)\}',limitHeader)[1].split(','))
limitSite=int(re.search(r'Site=(0x[0-9a-f]+)',limitHeader)[1],16)
hashHeader=(root/'WhateverXe/kern_xe_adapter_hash_page.hpp').read_text()
callIdentity=re.search(r'CallSHA256\[\]\[32\]\{\{([^}]+)\}\}',hashHeader)
callNative=bytes(int(n,0) for n in re.sub(r'//[^\n]*','',re.search(r'CallNative\[\]\{([^}]+)\}',hashHeader)[1]).split(','))
callSite=int(re.search(r'CallSite=(0x[0-9a-f]+)',hashHeader)[1],16)
if args.adapter:
 # The Xe compiler adapter of WhateverXe Graphics: its real first page must be the one the header names.
 limit=args.adapter.read_bytes()[0:4096];assert hashlib.sha256(limit).digest()==bytes(int(n,0) for n in limitIdentity[1].split(','))
 assert limit[limitSite:limitSite+len(limitNative)]==limitNative
 # The same page carries _verified's comparison, under the same identity in the other header.
 assert limit[callSite:callSite+len(callNative)]==callNative and hashlib.sha256(limit).digest()==bytes(int(n,0) for n in callIdentity[1].split(','))
else:
 # A synthetic page carrying the adapter's compute state check and _verified's comparison where the adapter has them.
 limit=bytearray((i*67+13)%256 for i in range(4096));limit[limitSite:limitSite+len(limitNative)]=limitNative
 limit[callSite:callSite+len(callNative)]=callNative
 limitHeader=limitHeader[:limitIdentity.start(1)]+','.join(hex(v) for v in hashlib.sha256(limit).digest())+limitHeader[limitIdentity.end(1):]
 hashHeader=hashHeader[:callIdentity.start(1)]+','.join(hex(v) for v in hashlib.sha256(limit).digest())+hashHeader[callIdentity.end(1):]
simdHeader=(root/'WhateverXe/kern_mtl_simd_page.hpp').read_text()
simdIdentity=re.search(r'ReferenceSHA256\[\]\[32\]\{\{([^}]+)\}\}',simdHeader)
simdNative=bytes(int(n,0) for n in re.sub(r'//[^\n]*','',re.search(r'Native\[\]\{([^}]+)\}',simdHeader)[1]).split(','))
simdSite=int(re.search(r'Site=(0x[0-9a-f]+)',simdHeader)[1],16);simdOffset=int(re.search(r'FileOffset=(0x[0-9a-f]+)',simdHeader)[1],16)
barrierHeader=(root/'WhateverXe/kern_mtl_barrier_page.hpp').read_text()
barrierIdentity=re.search(r'ReferenceSHA256\[\]\[32\]\{\{([^}]+)\}\}',barrierHeader)
barrierNative=bytes(int(n,0) for n in re.sub(r'//[^\n]*','',re.search(r'Native\[\]\{([^}]+)\}',barrierHeader)[1]).split(','))
barrierSite=int(re.search(r'Site=(0x[0-9a-f]+)',barrierHeader)[1],16)
assert int(re.search(r'FileOffset=(0x[0-9a-f]+)',barrierHeader)[1],16)==simdOffset
if args.metal:
 simd=args.metal.read_bytes()[simdOffset:simdOffset+4096];assert hashlib.sha256(simd).digest()==bytes(int(n,0) for n in simdIdentity[1].split(','))
 assert simd[simdSite:simdSite+len(simdNative)]==simdNative
 # The same page carries ChalContext's constructor, under the same identity in the other header.
 assert simd[barrierSite:barrierSite+len(barrierNative)]==barrierNative and hashlib.sha256(simd).digest()==bytes(int(n,0) for n in barrierIdentity[1].split(','))
else:
 # A synthetic page carrying the branch of the binary choice and the constructor's stores where the driver has them.
 simd=bytearray((i*71+19)%256 for i in range(4096));simd[simdSite:simdSite+len(simdNative)]=simdNative
 simd[barrierSite:barrierSite+len(barrierNative)]=barrierNative
 simdHeader=simdHeader[:simdIdentity.start(1)]+','.join(hex(v) for v in hashlib.sha256(simd).digest())+simdHeader[simdIdentity.end(1):]
 barrierHeader=barrierHeader[:barrierIdentity.start(1)]+','.join(hex(v) for v in hashlib.sha256(simd).digest())+barrierHeader[barrierIdentity.end(1):]
maxHeader=(root/'WhateverXe/kern_mtl_maxthreads_page.hpp').read_text()
maxIdentity=re.search(r'ReferenceSHA256\[\]\[32\]\{\{([^}]+)\}\}',maxHeader)
maxNative=bytes(int(n,0) for n in re.sub(r'//[^\n]*','',re.search(r'Native\[\]\{([^}]+)\}',maxHeader)[1]).split(','))
maxSite=int(re.search(r'Site=(0x[0-9a-f]+)',maxHeader)[1],16);maxOffset=int(re.search(r'FileOffset=(0x[0-9a-f]+)',maxHeader)[1],16)
if args.metal:
 maxPage=args.metal.read_bytes()[maxOffset:maxOffset+4096];assert hashlib.sha256(maxPage).digest()==bytes(int(n,0) for n in maxIdentity[1].split(','))
 assert maxPage[maxSite:maxSite+len(maxNative)]==maxNative
else:
 # A synthetic page carrying the maxTotalThreadsPerThreadgroup getter where the driver has it.
 maxPage=bytearray((i*73+29)%256 for i in range(4096));maxPage[maxSite:maxSite+len(maxNative)]=maxNative
 maxHeader=maxHeader[:maxIdentity.start(1)]+','.join(hex(v) for v in hashlib.sha256(maxPage).digest())+maxHeader[maxIdentity.end(1):]
addcHeader=(root/'WhateverXe/kern_igc_addc_page.hpp').read_text()
addcIdentity=re.search(r'ReferenceSHA256\[\]\[32\]\{\{([^}]+)\}\}',addcHeader)
addcNative=bytes(int(n,0) for n in re.sub(r'//[^\n]*','',re.search(r'Native\[\]\{([^}]+)\}',addcHeader)[1]).split(','))
addcSite=int(re.search(r'Site=(0x[0-9a-f]+)',addcHeader)[1],16);addcOffset=int(re.search(r'FileOffset=(0x[0-9a-f]+)',addcHeader)[1],16)
if args.igc:
 # The Intel graphics compiler of WhateverXe Graphics: its real page must be the one the header names.
 addcPage=args.igc.read_bytes()[addcOffset:addcOffset+4096];assert hashlib.sha256(addcPage).digest()==bytes(int(n,0) for n in addcIdentity[1].split(','))
 assert addcPage[addcSite:addcSite+len(addcNative)]==addcNative
else:
 # A synthetic page carrying fixAddcSubb's call where the compiler has it.
 addcPage=bytearray((i*79+37)%256 for i in range(4096));addcPage[addcSite:addcSite+len(addcNative)]=addcNative
 addcHeader=addcHeader[:addcIdentity.start(1)]+','.join(hex(v) for v in hashlib.sha256(addcPage).digest())+addcHeader[addcIdentity.end(1):]
helperIdentity=re.search(r'HelperSHA256\[\]\[32\]\{\{([^}]+)\}\}',hashHeader)
helperCorrected=bytes(int(n,0) for n in re.sub(r'//[^\n]*','',re.search(r'HelperCorrected\[\]\{([^}]+)\}',hashHeader)[1]).split(','))
helperSite=int(re.search(r'HelperSite=(0x[0-9a-f]+)',hashHeader)[1],16)
if args.adapter:
 # The adapter's third page: zero padding after __unwind_info where the helper goes.
 helperPage=args.adapter.read_bytes()[0x2000:0x3000];assert hashlib.sha256(helperPage).digest()==bytes(int(n,0) for n in helperIdentity[1].split(','))
 assert not any(helperPage[helperSite:helperSite+len(helperCorrected)])
else:
 # A synthetic third page with that padding.
 helperPage=bytearray((i*83+41)%256 for i in range(4096));helperPage[helperSite:helperSite+len(helperCorrected)]=bytes(len(helperCorrected))
 hashHeader=hashHeader[:helperIdentity.start(1)]+','.join(hex(v) for v in hashlib.sha256(helperPage).digest())+hashHeader[helperIdentity.end(1):]
if args.igc:
 # The corrected digest beside the helper is the digest of the whole compiler file with the compiler's correction.
 addcCorrected=bytes(int(n,0) for n in re.sub(r'//[^\n]*','',re.search(r'Corrected\[\]\{([^}]+)\}',addcHeader)[1]).split(','))
 igcFile=bytearray(args.igc.read_bytes());igcFile[addcOffset+addcSite:addcOffset+addcSite+len(addcCorrected)]=addcCorrected
 assert hashlib.sha256(igcFile).digest()==helperCorrected[0x50:0x70]
if args.donor:
 data=args.donor.read_bytes();page=data[0x2c000:0x2d000];assert hashlib.sha256(page).digest()==expected
 safe=data[0x786000:0x787000];assert hashlib.sha256(safe).digest()==bytes(int(n,0) for n in first[1].split(','))
 pixel=data[0x2b000:0x2c000];assert hashlib.sha256(pixel).digest()==bytes(int(n,0) for n in pfirst[1].split(','))
else:
 page=bytearray((i*37+31)%256 for i in range(4096))
 for off,count,body in re.findall(r'\{0x([a-f0-9]+),(\d+),\{([^}]+)\},',header):
  value=bytes(int(n,0) for n in body.split(','));assert len(value)==int(count);off=int(off,16);page[off:off+len(value)]=value
 header=header[:identity.start(1)]+','.join(hex(v) for v in hashlib.sha256(page).digest())+header[identity.end(1):]
 # A synthetic first capability page with the expected count at its first list.
 safe=bytearray((i*53+7)%256 for i in range(4096));safe[0xfc4:0xfc8]=(2).to_bytes(4,'little')
 safeHeader=safeHeader[:first.start(1)]+','.join(hex(v) for v in hashlib.sha256(safe).digest())+safeHeader[first.end(1):]
 # A synthetic capability-builder page carrying every original byte of the pixel patches.
 pixel=bytearray((i*29+11)%256 for i in range(4096))
 for off,size,before,after in re.findall(r'\{0x([0-9a-f]+),(\d+),\{([^}]+)\},\{([^}]+)\}\}',pixelHeader[pfirst.end():]):
  value=bytes(int(n,0) for n in before.split(','));assert len(value)==int(size);pixel[int(off,16):int(off,16)+len(value)]=value
 pixelHeader=pixelHeader[:pfirst.start(1)]+','.join(hex(v) for v in hashlib.sha256(pixel).digest())+pixelHeader[pfirst.end(1):]
code=r'''
#include "kern_local_va_vfe.hpp"
#include "kern_local_va_l3.hpp"
#include "kern_local_va_safe.hpp"
#include "kern_local_va_pixel.hpp"
#include "kern_mtl_mps_page.hpp"
#include "kern_mtl_slm_page.hpp"
#include "kern_xe_adapter_page.hpp"
#include "kern_mtl_simd_page.hpp"
#include "kern_mtl_maxthreads_page.hpp"
#include "kern_igc_addc_page.hpp"
#include "kern_xe_adapter_hash_page.hpp"
#include "kern_mtl_barrier_page.hpp"
#include "kern_xelp_platform.hpp"
#include "kern_xelp_os.hpp"
#include <cassert>
#include <cstdio>
#include <fstream>
#include <vector>
#include <string>
#include <sys/mman.h>
#ifdef INTEL_GEN12_ORACLE
#include "mhw_render_hwcmd_g12_X.h"
#endif
using mach_vm_address_t=uintptr_t;using vnode_t=void*;using memory_object_t=void*;using memory_object_offset_t=uint64_t;
constexpr size_t PAGE_SIZE=4096;constexpr int KERN_SUCCESS=0;
enum KernelVersion {Tahoe=25,Other=24};static KernelVersion kernel=Tahoe;static auto getKernelVersion(){return kernel;}
static bool routeOK=true,writeOK=true,race=false,writing=false;static uint8_t *racePage;
static const char *tahoe="Darwin Kernel Version 25.6.0: Mon Oct 12 00:33:09 PDT 2026; root:xnu-12377.161.15.701.48~2/RELEASE_X86_64";
static const char *version=tahoe;
struct IOPCIDevice{};struct OSSerialize{};
struct OSData{static OSData *withBytes(const void*,size_t){static OSData d;return &d;}bool serialize(OSSerialize*){return true;}void release(){}};
struct OSSerializer{static OSSerializer *forTarget(void*,bool(*)(void*,void*,OSSerialize*)){static OSSerializer d;return &d;}void release(){}};
struct IORegistryEntry{static IORegistryEntry *getRegistryRoot(){static IORegistryEntry r;return &r;}void setProperty(const char*,bool){}void setProperty(const char*,OSSerializer*){}};
namespace MachInfo {int setKernelWriting(bool enabled,int){if(enabled && !writeOK)return 1;writing=enabled;if(enabled && race)racePage[4095]^=1;return 0;}}
unsigned originalCalls;int validation=15,taint=0,nxValue=0;
static void original(vnode_t n,memory_object_t p,uint64_t o,const void*d,int*v,int*t,int*nx){assert(n==(void*)1 && p==(void*)2 && d);++originalCalls;if(v)*v=validation;if(t)*t=taint;if(nx)*nx=nxValue;}
struct KernelPatcher{static constexpr int KernelID=0,kernelWriteLock=1;struct RouteRequest{template<class F>RouteRequest(const char*,F,uintptr_t&v){v=(uintptr_t)original;}};bool routeMultipleLong(int,RouteRequest*,int){return routeOK;}void clearError(){}};
PRODUCTION
static std::vector<uint8_t> read(const char*p){std::ifstream f(p,std::ios::binary);assert(f);return {(std::istreambuf_iterator<char>(f)),{}};}
static void walker(void*,uint32_t*x,uint32_t*y,unsigned i){*x=16+i;*y=32+i;}
template<class T>void put(uint8_t*p,unsigned o,T v){memcpy(p+o,&v,sizeof(v));}
int main(int argc,char**argv){
 assert(argc==13);auto page=read(argv[1]),safe=read(argv[2]),pixel=read(argv[3]),mps=read(argv[4]),slm=read(argv[5]),limit=read(argv[8]),simd=read(argv[9]),maxPage=read(argv[10]),addcPage=read(argv[11]),helperPage=read(argv[12]);
 assert(page.size()==4096 && safe.size()==4096 && pixel.size()==4096 && mps.size()==4096 && slm.size()==4096 && limit.size()==4096 && simd.size()==4096 && maxPage.size()==4096 && addcPage.size()==4096 && helperPage.size()==4096);unsigned cases=0;
 const bool haveImage=strcmp(argv[6],"-"),haveMetal=strcmp(argv[7],"-");
 KernelPatcher patcher;IOPCIDevice gpu;
 // Scope: exact device and revision, no override, Tahoe, the route, and the renderer switch.
 for(unsigned bits=0;bits<32;++bits){
  const bool renderer=bits&1;routeOK=bits&2;kernel=bits&4?Tahoe:Other;
  auto profile=XELP::identify(0xa7a08086,bits&8?0x04:0x05,bits&16?0x9a498086:0xa7a08086);
  prepareVAPages(patcher,&gpu,profile,renderer);
  const bool scope=(bits&8) && !(bits&16);
  assert(vaGen12Enabled==(scope && renderer) && vaSafeEnabled==(scope && renderer) && vaPixelEnabled==(scope && renderer));
  assert(vaPageHookReady==(scope && renderer && (bits&4) && routeOK));
  // Intel's MPS plug-in: off for every GPU this kext drives on Tahoe, whatever the VA switch says.
  assert(mpsPluginOffReady==(profile.admitted() && (bits&4) && routeOK));
  // The thread-group memory class: this device and revision only, whatever the VA switch says.
  assert(slmClassReady==(scope && (bits&4) && routeOK));
  prepareVAPages(patcher,&gpu,profile,renderer,true);assert(!mpsPluginOffReady && slmClassReady==(scope && (bits&4) && routeOK));
  prepareVAPages(patcher,&gpu,profile,renderer,false,true);assert(!slmClassReady && mpsPluginOffReady==(profile.admitted() && (bits&4) && routeOK));
  // The compiler adapter's thread limit: every GPU this kext drives on Tahoe, like the MPS plug-in, and its own switch.
  assert(computeLimitReady==(profile.admitted() && (bits&4) && routeOK));
  prepareVAPages(patcher,&gpu,profile,renderer,false,false,true);assert(!computeLimitReady && slmClassReady==(scope && (bits&4) && routeOK));
  // The SIMD choice for small compute dispatches: this device and revision only, like the memory class, and its own switch.
  assert(simdChoiceReady==(scope && (bits&4) && routeOK));
  prepareVAPages(patcher,&gpu,profile,renderer,false,false,false,true);assert(!simdChoiceReady && slmClassReady==(scope && (bits&4) && routeOK));
  assert(computeLimitReady==(profile.admitted() && (bits&4) && routeOK));
  // The power-of-two maximum: every GPU this kext drives on Tahoe, like the adapter's thread limit, and its own switch.
  assert(pow2MaxReady==(profile.admitted() && (bits&4) && routeOK));
  prepareVAPages(patcher,&gpu,profile,renderer,false,false,false,false,true);assert(!pow2MaxReady && simdChoiceReady==(scope && (bits&4) && routeOK));
  assert(computeLimitReady==(profile.admitted() && (bits&4) && routeOK));
  // The compiler's carry destination: every GPU this kext drives on Tahoe, like the adapter, and its own switch.
  assert(addcAlignReady==(profile.admitted() && (bits&4) && routeOK));
  prepareVAPages(patcher,&gpu,profile,renderer,false,false,false,false,false,true);assert(!addcAlignReady && pow2MaxReady==(profile.admitted() && (bits&4) && routeOK));
  assert(mpsPluginOffReady==(profile.admitted() && (bits&4) && routeOK));
  // The pending-barrier flag of new compute contexts: every GPU this kext drives on Tahoe, like the adapter, and its own switch.
  assert(barrierFlagReady==(profile.admitted() && (bits&4) && routeOK));
  prepareVAPages(patcher,&gpu,profile,renderer,false,false,false,false,false,false,true);assert(!barrierFlagReady && simdChoiceReady==(scope && (bits&4) && routeOK));
  assert(addcAlignReady==(profile.admitted() && (bits&4) && routeOK));
  assert(vaPageHookReady==(scope && renderer && (bits&4) && routeOK));++cases;
 }
 kernel=Tahoe;routeOK=true;
 prepareVAPages(patcher,nullptr,XELP::identify(0xa7a08086,0x04),true);assert(!vaPageHookReady && !vaGen12Enabled && !vaPixelEnabled && !mpsPluginOffReady && !slmClassReady && !computeLimitReady && !simdChoiceReady && !pow2MaxReady && !addcAlignReady && !barrierFlagReady);++cases;
 prepareVAPages(patcher,&gpu,XELP::identify(0x46808086,0x0c),true);assert(!vaPageHookReady && !vaSafeEnabled && !vaPixelEnabled && !slmClassReady && !simdChoiceReady);
 assert(mpsPluginOffReady==XELP::identify(0x46808086,0x0c).admitted() && pow2MaxReady==XELP::identify(0x46808086,0x0c).admitted());
 assert(addcAlignReady==XELP::identify(0x46808086,0x0c).admitted() && barrierFlagReady==XELP::identify(0x46808086,0x0c).admitted());++cases;
 for(const char *servicing:{"Darwin Kernel Version 25.6.0: other date; root:xnu-new/RELEASE_X86_64","Darwin Kernel Version 25.7.2: future date; root:xnu-next/RELEASE_X86_64"}) {
  version=servicing;prepareVAPages(patcher,&gpu,XELP::identify(0xa7a08086,0x04),true);assert(vaPageHookReady && vaGen12Enabled && vaSafeEnabled && vaPixelEnabled);++cases;
 }
 version="Darwin Kernel Version 24.6.0: Mon Jul 14 11:28:17 PDT 2025; root:xnu-11417.140.69~1/RELEASE_X86_64";
 prepareVAPages(patcher,&gpu,XELP::identify(0xa7a08086,0x04),true);assert(!vaPageHookReady && !vaGen12Enabled && !vaSafeEnabled && !vaPixelEnabled && !mpsPluginOffReady && !slmClassReady && !computeLimitReady && !simdChoiceReady && !pow2MaxReady && !addcAlignReady && !barrierFlagReady);++cases;
 prepareVAPages(patcher,&gpu,XELP::identify(0xa7a08086,0x04),false);assert(!vaPageHookReady && !vaGen12Enabled && !vaSafeEnabled && !vaPixelEnabled);++cases;
 version=tahoe;prepareVAPages(patcher,&gpu,XELP::identify(0xa7a08086,0x04),false);assert(!vaPageHookReady && slmClassReady && simdChoiceReady && pow2MaxReady && addcAlignReady && barrierFlagReady);++cases;
 prepareVAPages(patcher,&gpu,XELP::identify(0xa7a08086,0x04),true);assert(vaPageHookReady && vaGen12Enabled && vaSafeEnabled && vaPixelEnabled && slmClassReady);
 // The VFE packet generator: validated executable code pages only, rechecked under the write lock.
 for(unsigned condition=0;condition<11;++condition){
  auto data=page;racePage=data.data();originalCalls=0;vaVFEPages=vaL3Pages=vaSafePages=vaPixelPages=0;
  validation=condition==1?0x7:0xf;taint=condition==2?1:0;nxValue=condition==3?1:0;
  writeOK=condition!=4;race=condition==5;vaGen12Enabled=condition!=6;
  if(condition==7)data[200]^=1;
  int valid=-1,t=-1,nx=-1;
  auto offset=LocalVAVFE::FileOffset+(condition==8?4096:0);
  vaValidatePage((void*)1,(void*)2,offset,data.data(),condition==9?nullptr:&valid,&t,condition==10?nullptr:&nx);
  assert(originalCalls==1 && !writing);if(condition!=9)assert(valid==validation);assert(t==taint);if(condition!=10)assert(nx==nxValue);
  assert(vaVFEPages==(condition==0?1U:0U) && !vaL3Pages && !vaSafePages && !vaPixelPages);
  if(condition==0){auto expected=page;LocalVAVFE::apply(expected.data());assert(data==expected);assert(!LocalVAVFE::matches(data.data(),4096,offset,true,false));}
  else if(condition!=5 && condition!=7)assert(data==page);
  ++cases;
 }
 vaGen12Enabled=true;
 // The capability list lives in a data page: NX does not exclude it, and only its first list is cleared.
 for(unsigned condition=0;condition<10;++condition){
  auto data=safe;racePage=data.data();originalCalls=0;vaVFEPages=vaL3Pages=vaSafePages=vaPixelPages=0;
  validation=condition==1?0x7:0xf;taint=condition==2?1:0;nxValue=condition==3?0:1;
  writeOK=condition!=4;race=condition==5;vaSafeEnabled=condition!=6;vaPageHookReady=condition!=9;
  if(condition==7)data[100]^=1;
  int valid=-1,t=-1,nx=-1;
  const uint64_t offset=0x786000+(condition==8?4096:0);
  vaValidatePage((void*)1,(void*)2,offset,data.data(),&valid,&t,&nx);
  assert(originalCalls==1 && !writing && valid==validation && t==taint && nx==nxValue);
  const bool patched=condition==0 || condition==3;
  assert(vaSafePages==(patched?1U:0U) && !vaVFEPages && !vaL3Pages && !vaPixelPages);
  if(patched){auto expected=safe;memset(expected.data()+0xfc4,0,4);assert(data==expected);}
  else if(condition!=5 && condition!=7)assert(data==safe);
  ++cases;
 }
 vaSafeEnabled=vaPageHookReady=true;
 // The pixel-transfer capabilities: a code page, so validated, untainted and executable only.
 for(unsigned condition=0;condition<10;++condition){
  auto data=pixel;racePage=data.data();originalCalls=0;vaVFEPages=vaL3Pages=vaSafePages=vaPixelPages=0;
  validation=condition==1?0x7:0xf;taint=condition==2?1:0;nxValue=condition==3?1:0;
  writeOK=condition!=4;race=condition==5;vaPixelEnabled=condition!=6;vaPageHookReady=condition!=9;
  if(condition==7)data[64]^=1;
  int valid=-1,t=-1,nx=-1;
  const uint64_t offset=0x2b000+(condition==8?4096:0);
  vaValidatePage((void*)1,(void*)2,offset,data.data(),&valid,&t,&nx);
  assert(originalCalls==1 && !writing && valid==validation && t==taint && nx==nxValue);
  assert(vaPixelPages==(condition==0?1U:0U) && !vaVFEPages && !vaL3Pages && !vaSafePages);
  if(!condition){auto expected=pixel;LocalVAPixel::apply(expected.data(),1);assert(data==expected);assert(LocalVAPixel::match(data.data(),4096,offset,true,false)==-1);}
  else if(condition!=5 && condition!=7)assert(data==pixel);
  ++cases;
 }
 vaPixelEnabled=vaPageHookReady=true;
 // Intel's MPS plug-in page: a code page of another image at the offset of a pixel page. Its switch alone decides.
 unsigned mpsCases=0;
 for(unsigned condition=0;condition<11;++condition){
  auto data=mps;racePage=data.data();originalCalls=0;vaVFEPages=vaL3Pages=vaSafePages=vaPixelPages=mpsPluginPages=0;
  validation=condition==1?0x7:0xf;taint=condition==2?1:0;nxValue=condition==3?1:0;
  writeOK=condition!=4;race=condition==5;mpsPluginOffReady=condition!=6;vaPageHookReady=condition!=9;
  vaGen12Enabled=vaSafeEnabled=vaPixelEnabled=condition!=10;
  if(condition==7)data[64]^=1;
  int valid=-1,t=-1,nx=-1;
  const uint64_t offset=MetalMPSPlugin::FileOffset+(condition==8?4096:0);
  vaValidatePage((void*)1,(void*)2,offset,data.data(),&valid,&t,&nx);
  assert(originalCalls==1 && !writing && valid==validation && t==taint && nx==nxValue);
  const bool patched=condition==0 || condition==9 || condition==10;
  assert(mpsPluginPages==(patched?1U:0U) && !vaVFEPages && !vaL3Pages && !vaSafePages && !vaPixelPages);
  if(patched){auto expected=mps;const uint8_t off[]{0x31,0xc0,0xc3};memcpy(expected.data()+0xb80,off,sizeof(off));assert(data==expected);
   assert(!MetalMPSPlugin::matches(data.data(),4096,offset,true,false));}
  else if(condition!=5 && condition!=7)assert(data==mps);
  ++mpsCases;
 }
 mpsPluginOffReady=vaPageHookReady=vaGen12Enabled=vaSafeEnabled=vaPixelEnabled=true;writeOK=true;race=false;validation=15;taint=nxValue=0;
 // The pixel page of the VA driver sits at the same offset: neither correction takes the other's page.
 assert(!MetalMPSPlugin::matches(pixel.data(),4096,0x2b000,true,false) && LocalVAPixel::match(mps.data(),4096,0x2b000,true,false)==-1);
 printf("PASS: %u MPS plug-in page cases: its own switch, validated executable pages only, mutation race, and independence from the VA switches\n",mpsCases);
 // The page of the Metal driver that turns a thread-group memory size into its class. Its switch alone decides.
 unsigned slmCases=0;
 for(unsigned condition=0;condition<11;++condition){
  auto data=slm;racePage=data.data();originalCalls=0;vaVFEPages=vaL3Pages=vaSafePages=vaPixelPages=mpsPluginPages=slmClassPages=0;
  validation=condition==1?0x7:0xf;taint=condition==2?1:0;nxValue=condition==3?1:0;
  writeOK=condition!=4;race=condition==5;slmClassReady=condition!=6;vaPageHookReady=condition!=9;
  vaGen12Enabled=vaSafeEnabled=vaPixelEnabled=mpsPluginOffReady=condition!=10;
  if(condition==7)data[64]^=1;
  int valid=-1,t=-1,nx=-1;
  const uint64_t offset=MetalSLMClass::FileOffset+(condition==8?4096:0);
  vaValidatePage((void*)1,(void*)2,offset,data.data(),&valid,&t,&nx);
  assert(originalCalls==1 && !writing && valid==validation && t==taint && nx==nxValue);
  const bool patched=condition==0 || condition==9 || condition==10;
  assert(slmClassPages==(patched?1U:0U) && !mpsPluginPages && !vaVFEPages && !vaL3Pages && !vaSafePages && !vaPixelPages);
  if(patched){auto expected=slm;expected[0xfcf]=7;expected[0xfdd]=7;assert(data==expected);
   assert(!MetalSLMClass::matches(data.data(),4096,offset,true,false));}
  else if(condition!=5 && condition!=7)assert(data==slm);
  ++slmCases;
 }
 slmClassReady=mpsPluginOffReady=vaPageHookReady=vaGen12Enabled=vaSafeEnabled=vaPixelEnabled=true;writeOK=true;race=false;validation=15;taint=nxValue=0;
 // Two pages of the same image: neither correction takes the other's.
 assert(!MetalMPSPlugin::matches(slm.data(),4096,MetalSLMClass::FileOffset,true,false) && !MetalSLMClass::matches(mps.data(),4096,MetalMPSPlugin::FileOffset,true,false));
 printf("PASS: %u thread-group memory class page cases: its own switch, validated executable pages only, mutation race, and independence from the other switches\n",slmCases);
 // The first page of the Xe compiler adapter, another image, with its compute state check. Its switch alone decides.
 unsigned limitCases=0;
 for(unsigned condition=0;condition<11;++condition){
  auto data=limit;racePage=data.data();originalCalls=0;vaVFEPages=vaL3Pages=vaSafePages=vaPixelPages=mpsPluginPages=slmClassPages=computeLimitPages=adapterHashPages=0;
  validation=condition==1?0x7:0xf;taint=condition==2?1:0;nxValue=condition==3?1:0;
  writeOK=condition!=4;race=condition==5;computeLimitReady=condition!=6;vaPageHookReady=condition!=9;addcAlignReady=false;
  vaGen12Enabled=vaSafeEnabled=vaPixelEnabled=mpsPluginOffReady=slmClassReady=condition!=10;
  if(condition==7)data[64]^=1;
  int valid=-1,t=-1,nx=-1;
  const uint64_t offset=XeAdapterComputeLimit::FileOffset+(condition==8?4096:0);
  vaValidatePage((void*)1,(void*)2,offset,data.data(),&valid,&t,&nx);
  assert(originalCalls==1 && !writing && valid==validation && t==taint && nx==nxValue);
  const bool patched=condition==0 || condition==9 || condition==10;
  assert(computeLimitPages==(patched?1U:0U) && !adapterHashPages && !slmClassPages && !mpsPluginPages && !vaVFEPages && !vaL3Pages && !vaSafePages && !vaPixelPages);
  if(patched){auto expected=limit;memcpy(expected.data()+XeAdapterComputeLimit::Site,XeAdapterComputeLimit::Corrected,sizeof(XeAdapterComputeLimit::Corrected));
   assert(data==expected);assert(!XeAdapterComputeLimit::matches(data.data(),4096,offset,true,false));}
  else if(condition!=5 && condition!=7)assert(data==limit);
  ++limitCases;
 }
 computeLimitReady=addcAlignReady=slmClassReady=mpsPluginOffReady=vaPageHookReady=vaGen12Enabled=vaSafeEnabled=vaPixelEnabled=true;writeOK=true;race=false;validation=15;taint=nxValue=0;
 // Pages of other images: no correction takes another's.
 assert(!XeAdapterComputeLimit::matches(slm.data(),4096,XeAdapterComputeLimit::FileOffset,true,false) && !XeAdapterComputeLimit::matches(mps.data(),4096,XeAdapterComputeLimit::FileOffset,true,false));
 assert(!MetalSLMClass::matches(limit.data(),4096,MetalSLMClass::FileOffset,true,false) && !MetalMPSPlugin::matches(limit.data(),4096,MetalMPSPlugin::FileOffset,true,false));
 printf("PASS: %u compiler adapter page cases: its own switch, validated executable pages only, mutation race, and independence from the other switches\n",limitCases);
 // The adapter's check of the compiler's file: _verified's comparison on the same first page, with and without the
 // compute state correction, then the helper on its third page. The compiler carry switch decides both.
 unsigned hashCases=0;
 for(unsigned both=0;both<2;++both)for(unsigned condition=0;condition<11;++condition){
  auto data=limit;racePage=data.data();originalCalls=0;
  vaVFEPages=vaL3Pages=vaSafePages=vaPixelPages=mpsPluginPages=slmClassPages=computeLimitPages=simdChoicePages=pow2MaxPages=addcAlignPages=adapterHashPages=0;
  validation=condition==1?0x7:0xf;taint=condition==2?1:0;nxValue=condition==3?1:0;
  writeOK=condition!=4;race=condition==5;addcAlignReady=condition!=6;computeLimitReady=both;vaPageHookReady=condition!=9;
  vaGen12Enabled=vaSafeEnabled=vaPixelEnabled=mpsPluginOffReady=slmClassReady=simdChoiceReady=pow2MaxReady=condition!=10;
  if(condition==7)data[64]^=1;
  int valid=-1,t=-1,nx=-1;
  const uint64_t offset=XeAdapterBackendHash::CallOffset+(condition==8?4096:0);
  vaValidatePage((void*)1,(void*)2,offset,data.data(),&valid,&t,&nx);
  assert(originalCalls==1 && !writing && valid==validation && t==taint && nx==nxValue);
  const bool hashed=condition==0 || condition==9 || condition==10,limited=both && (hashed || condition==6);
  assert(adapterHashPages==(hashed?1U:0U) && computeLimitPages==(limited?1U:0U) && !addcAlignPages && !pow2MaxPages && !simdChoicePages);
  assert(!slmClassPages && !mpsPluginPages && !vaVFEPages && !vaL3Pages && !vaSafePages && !vaPixelPages);
  if(hashed || limited){auto expected=limit;
   if(limited)memcpy(expected.data()+XeAdapterComputeLimit::Site,XeAdapterComputeLimit::Corrected,sizeof(XeAdapterComputeLimit::Corrected));
   if(hashed)memcpy(expected.data()+XeAdapterBackendHash::CallSite,XeAdapterBackendHash::CallCorrected,sizeof(XeAdapterBackendHash::CallCorrected));
   assert(data==expected);assert(!XeAdapterBackendHash::matchesCall(data.data(),4096,offset,true,false));}
  else if(condition!=5 && condition!=7)assert(data==limit);
  ++hashCases;
 }
 for(unsigned condition=0;condition<11;++condition){
  auto data=helperPage;racePage=data.data();originalCalls=0;
  vaVFEPages=vaL3Pages=vaSafePages=vaPixelPages=mpsPluginPages=slmClassPages=computeLimitPages=simdChoicePages=pow2MaxPages=addcAlignPages=adapterHashPages=0;
  validation=condition==1?0x7:0xf;taint=condition==2?1:0;nxValue=condition==3?1:0;
  writeOK=condition!=4;race=condition==5;addcAlignReady=condition!=6;vaPageHookReady=condition!=9;
  vaGen12Enabled=vaSafeEnabled=vaPixelEnabled=mpsPluginOffReady=slmClassReady=computeLimitReady=simdChoiceReady=pow2MaxReady=condition!=10;
  if(condition==7)data[64]^=1;
  int valid=-1,t=-1,nx=-1;
  const uint64_t offset=XeAdapterBackendHash::HelperOffset+(condition==8?4096:0);
  vaValidatePage((void*)1,(void*)2,offset,data.data(),&valid,&t,&nx);
  assert(originalCalls==1 && !writing && valid==validation && t==taint && nx==nxValue);
  const bool patched=condition==0 || condition==9 || condition==10;
  assert(adapterHashPages==(patched?1U:0U) && !computeLimitPages && !addcAlignPages && !pow2MaxPages && !simdChoicePages);
  assert(!slmClassPages && !mpsPluginPages && !vaVFEPages && !vaL3Pages && !vaSafePages && !vaPixelPages);
  if(patched){auto expected=helperPage;memcpy(expected.data()+XeAdapterBackendHash::HelperSite,XeAdapterBackendHash::HelperCorrected,sizeof(XeAdapterBackendHash::HelperCorrected));
   assert(data==expected);assert(!XeAdapterBackendHash::matchesHelper(data.data(),4096,offset,true,false));}
  else if(condition!=5 && condition!=7)assert(data==helperPage);
  ++hashCases;
 }
 addcAlignReady=computeLimitReady=slmClassReady=mpsPluginOffReady=simdChoiceReady=pow2MaxReady=vaPageHookReady=vaGen12Enabled=vaSafeEnabled=vaPixelEnabled=true;writeOK=true;race=false;validation=15;taint=nxValue=0;
 // Pages of other images: no correction takes another's.
 for(const auto *other:{&slm,&mps,&page,&helperPage})assert(!XeAdapterBackendHash::matchesCall(other->data(),4096,XeAdapterBackendHash::CallOffset,true,false));
 for(const auto *other:{&slm,&mps,&page,&limit})assert(!XeAdapterBackendHash::matchesHelper(other->data(),4096,XeAdapterBackendHash::HelperOffset,true,false));
 assert(!XeAdapterComputeLimit::matches(helperPage.data(),4096,XeAdapterComputeLimit::FileOffset,true,false));
 {
  // The helper, on the corrected third page and run on its own: 1 for the shipped digest, read from the page's own
  // constant at 0x2030 and 0x2020, and for the corrected one stored beside it; 0 for a digest with one bit changed.
  auto corrected=helperPage;XeAdapterBackendHash::applyHelper(corrected.data());
  auto *code=(uint8_t*)mmap(nullptr,4096,7,MAP_ANON|MAP_PRIVATE,-1,0);assert(code!=MAP_FAILED);memcpy(code,corrected.data(),4096);
  const auto accepts=[&](const uint8_t *digest){return ((int(*)(const uint8_t *))(code+XeAdapterBackendHash::HelperSite))(digest);};
  uint8_t shipped[32],corr[32],zero[32]{};memcpy(shipped,corrected.data()+0x30,16);memcpy(shipped+16,corrected.data()+0x20,16);
  memcpy(corr,XeAdapterBackendHash::HelperCorrected+0x50,32);
  assert(accepts(shipped)==1 && accepts(corr)==1 && accepts(zero)==0);
  for(unsigned bit=0;bit<256;++bit){uint8_t a[32],b[32];memcpy(a,shipped,32);memcpy(b,corr,32);a[bit/8]^=1<<(bit%8);b[bit/8]^=1<<(bit%8);
   assert(accepts(a)==0 && accepts(b)==0);}
  munmap(code,4096);
 }
 printf("PASS: %u adapter compiler-file check cases: the compiler carry switch, both corrections of the first page, validated executable pages only, mutation race; the helper accepts the shipped and the corrected digest only\n",hashCases);
 // The page of the Metal driver that chooses a kernel binary for each dispatch, at the offset of the VA driver's VFE page.
 // Its switch alone decides.
 unsigned simdCases=0;
 for(unsigned condition=0;condition<11;++condition){
  auto data=simd;racePage=data.data();originalCalls=0;vaVFEPages=vaL3Pages=vaSafePages=vaPixelPages=mpsPluginPages=slmClassPages=computeLimitPages=simdChoicePages=0;
  validation=condition==1?0x7:0xf;taint=condition==2?1:0;nxValue=condition==3?1:0;
  writeOK=condition!=4;race=condition==5;simdChoiceReady=condition!=6;vaPageHookReady=condition!=9;barrierFlagReady=false;barrierFlagPages=0;
  vaGen12Enabled=vaSafeEnabled=vaPixelEnabled=mpsPluginOffReady=slmClassReady=computeLimitReady=condition!=10;
  if(condition==7)data[64]^=1;
  int valid=-1,t=-1,nx=-1;
  const uint64_t offset=MetalSIMDChoice::FileOffset+(condition==8?4096:0);
  vaValidatePage((void*)1,(void*)2,offset,data.data(),&valid,&t,&nx);
  assert(originalCalls==1 && !writing && valid==validation && t==taint && nx==nxValue);
  const bool patched=condition==0 || condition==9 || condition==10;
  assert(simdChoicePages==(patched?1U:0U) && !barrierFlagPages && !computeLimitPages && !slmClassPages && !mpsPluginPages && !vaVFEPages && !vaL3Pages && !vaSafePages && !vaPixelPages);
  if(patched){auto expected=simd;memcpy(expected.data()+MetalSIMDChoice::Site,MetalSIMDChoice::Corrected,sizeof(MetalSIMDChoice::Corrected));
   assert(data==expected);assert(!MetalSIMDChoice::matches(data.data(),4096,offset,true,false));}
  else if(condition!=5 && condition!=7)assert(data==simd);
  ++simdCases;
 }
 simdChoiceReady=computeLimitReady=slmClassReady=mpsPluginOffReady=vaPageHookReady=vaGen12Enabled=vaSafeEnabled=vaPixelEnabled=true;writeOK=true;race=false;validation=15;taint=nxValue=0;
 // The VA driver's VFE page has the same offset; the other pages are other code. No correction takes another's page.
 assert(!MetalSIMDChoice::matches(page.data(),4096,MetalSIMDChoice::FileOffset,true,false) && !LocalVAVFE::matches(simd.data(),4096,LocalVAVFE::FileOffset,true,false));
 assert(!MetalSIMDChoice::matches(slm.data(),4096,MetalSIMDChoice::FileOffset,true,false) && !MetalSIMDChoice::matches(mps.data(),4096,MetalSIMDChoice::FileOffset,true,false));
 assert(!MetalSIMDChoice::matches(limit.data(),4096,MetalSIMDChoice::FileOffset,true,false) && !XeAdapterComputeLimit::matches(simd.data(),4096,XeAdapterComputeLimit::FileOffset,true,false));
 assert(!MetalSLMClass::matches(simd.data(),4096,MetalSLMClass::FileOffset,true,false) && !MetalMPSPlugin::matches(simd.data(),4096,MetalMPSPlugin::FileOffset,true,false));
 printf("PASS: %u SIMD choice page cases: its own switch, validated executable pages only, mutation race, and independence from the other switches and from the VFE page at the same offset\n",simdCases);
 // The same page with ChalContext's constructor. Its switch alone decides; with the SIMD choice's switch on too, both
 // corrections land at once.
 unsigned barrierCases=0;
 for(unsigned condition=0;condition<12;++condition){
  auto data=simd;racePage=data.data();originalCalls=0;
  vaVFEPages=vaL3Pages=vaSafePages=vaPixelPages=mpsPluginPages=slmClassPages=computeLimitPages=simdChoicePages=pow2MaxPages=addcAlignPages=adapterHashPages=barrierFlagPages=0;
  validation=condition==1?0x7:0xf;taint=condition==2?1:0;nxValue=condition==3?1:0;
  writeOK=condition!=4;race=condition==5;barrierFlagReady=condition!=6;vaPageHookReady=condition!=9;simdChoiceReady=condition==11;
  vaGen12Enabled=vaSafeEnabled=vaPixelEnabled=mpsPluginOffReady=slmClassReady=computeLimitReady=pow2MaxReady=addcAlignReady=condition!=10;
  if(condition==7)data[64]^=1;
  int valid=-1,t=-1,nx=-1;
  const uint64_t offset=MetalPendingBarrier::FileOffset+(condition==8?4096:0);
  vaValidatePage((void*)1,(void*)2,offset,data.data(),&valid,&t,&nx);
  assert(originalCalls==1 && !writing && valid==validation && t==taint && nx==nxValue);
  const bool patched=condition==0 || condition==9 || condition==10 || condition==11;
  assert(barrierFlagPages==(patched?1U:0U) && simdChoicePages==(condition==11?1U:0U) && !computeLimitPages && !slmClassPages && !mpsPluginPages);
  assert(!pow2MaxPages && !addcAlignPages && !adapterHashPages && !vaVFEPages && !vaL3Pages && !vaSafePages && !vaPixelPages);
  if(patched){auto expected=simd;memcpy(expected.data()+MetalPendingBarrier::Site,MetalPendingBarrier::Corrected,sizeof(MetalPendingBarrier::Corrected));
   if(condition==11)memcpy(expected.data()+MetalSIMDChoice::Site,MetalSIMDChoice::Corrected,sizeof(MetalSIMDChoice::Corrected));
   assert(data==expected);assert(!MetalPendingBarrier::matches(data.data(),4096,offset,true,false) && !MetalSIMDChoice::matches(data.data(),4096,offset,true,false));}
  else if(condition!=5 && condition!=7)assert(data==simd);
  ++barrierCases;
 }
 barrierFlagReady=simdChoiceReady=pow2MaxReady=addcAlignReady=computeLimitReady=slmClassReady=mpsPluginOffReady=vaPageHookReady=vaGen12Enabled=vaSafeEnabled=vaPixelEnabled=true;writeOK=true;race=false;validation=15;taint=nxValue=0;
 // Pages of the same images and of other images, and the VA driver's VFE page at the same offset: none is taken.
 for(const auto *other:{&page,&slm,&mps,&limit,&maxPage,&addcPage,&helperPage})assert(!MetalPendingBarrier::matches(other->data(),4096,MetalPendingBarrier::FileOffset,true,false));
 printf("PASS: %u pending-barrier flag cases: its own switch, the SIMD choice on the same page, validated executable pages only, mutation race, independence from the other pages\n",barrierCases);
 // The page of the Metal driver with the maxTotalThreadsPerThreadgroup getter. Its switch alone decides.
 unsigned maxCases=0;
 for(unsigned condition=0;condition<11;++condition){
  auto data=maxPage;racePage=data.data();originalCalls=0;
  vaVFEPages=vaL3Pages=vaSafePages=vaPixelPages=mpsPluginPages=slmClassPages=computeLimitPages=simdChoicePages=pow2MaxPages=0;
  validation=condition==1?0x7:0xf;taint=condition==2?1:0;nxValue=condition==3?1:0;
  writeOK=condition!=4;race=condition==5;pow2MaxReady=condition!=6;vaPageHookReady=condition!=9;
  vaGen12Enabled=vaSafeEnabled=vaPixelEnabled=mpsPluginOffReady=slmClassReady=computeLimitReady=simdChoiceReady=condition!=10;
  if(condition==7)data[64]^=1;
  int valid=-1,t=-1,nx=-1;
  const uint64_t offset=MetalPow2MaxThreads::FileOffset+(condition==8?4096:0);
  vaValidatePage((void*)1,(void*)2,offset,data.data(),&valid,&t,&nx);
  assert(originalCalls==1 && !writing && valid==validation && t==taint && nx==nxValue);
  const bool patched=condition==0 || condition==9 || condition==10;
  assert(pow2MaxPages==(patched?1U:0U) && !simdChoicePages && !computeLimitPages && !slmClassPages && !mpsPluginPages && !vaVFEPages && !vaL3Pages && !vaSafePages && !vaPixelPages);
  if(patched){auto expected=maxPage;memcpy(expected.data()+MetalPow2MaxThreads::Site,MetalPow2MaxThreads::Corrected,sizeof(MetalPow2MaxThreads::Corrected));
   assert(data==expected);assert(!MetalPow2MaxThreads::matches(data.data(),4096,offset,true,false));}
  else if(condition!=5 && condition!=7)assert(data==maxPage);
  ++maxCases;
 }
 pow2MaxReady=simdChoiceReady=computeLimitReady=slmClassReady=mpsPluginOffReady=vaPageHookReady=vaGen12Enabled=vaSafeEnabled=vaPixelEnabled=true;writeOK=true;race=false;validation=15;taint=nxValue=0;
 // Pages of the same image and of other images: no correction takes another's.
 for(const auto *other:{&simd,&slm,&mps,&limit,&page})assert(!MetalPow2MaxThreads::matches(other->data(),4096,MetalPow2MaxThreads::FileOffset,true,false));
 assert(!MetalSIMDChoice::matches(maxPage.data(),4096,MetalSIMDChoice::FileOffset,true,false) && !MetalSLMClass::matches(maxPage.data(),4096,MetalSLMClass::FileOffset,true,false));
 assert(!MetalMPSPlugin::matches(maxPage.data(),4096,MetalMPSPlugin::FileOffset,true,false) && !XeAdapterComputeLimit::matches(maxPage.data(),4096,XeAdapterComputeLimit::FileOffset,true,false));
 printf("PASS: %u maximum thread count page cases: its own switch, validated executable pages only, mutation race, and independence from the other switches\n",maxCases);
 // The page of the compiler with fixAddcSubb's call. Its switch alone decides.
 unsigned addcCases=0;
 for(unsigned condition=0;condition<11;++condition){
  auto data=addcPage;racePage=data.data();originalCalls=0;
  vaVFEPages=vaL3Pages=vaSafePages=vaPixelPages=mpsPluginPages=slmClassPages=computeLimitPages=simdChoicePages=pow2MaxPages=addcAlignPages=0;
  validation=condition==1?0x7:0xf;taint=condition==2?1:0;nxValue=condition==3?1:0;
  writeOK=condition!=4;race=condition==5;addcAlignReady=condition!=6;vaPageHookReady=condition!=9;
  vaGen12Enabled=vaSafeEnabled=vaPixelEnabled=mpsPluginOffReady=slmClassReady=computeLimitReady=simdChoiceReady=pow2MaxReady=condition!=10;
  if(condition==7)data[64]^=1;
  int valid=-1,t=-1,nx=-1;
  const uint64_t offset=IGCAddcAlign::FileOffset+(condition==8?4096:0);
  vaValidatePage((void*)1,(void*)2,offset,data.data(),&valid,&t,&nx);
  assert(originalCalls==1 && !writing && valid==validation && t==taint && nx==nxValue);
  const bool patched=condition==0 || condition==9 || condition==10;
  assert(addcAlignPages==(patched?1U:0U) && !pow2MaxPages && !simdChoicePages && !computeLimitPages && !slmClassPages && !mpsPluginPages && !vaVFEPages && !vaL3Pages && !vaSafePages && !vaPixelPages);
  if(patched){auto expected=addcPage;memcpy(expected.data()+IGCAddcAlign::Site,IGCAddcAlign::Corrected,sizeof(IGCAddcAlign::Corrected));
   assert(data==expected);assert(!IGCAddcAlign::matches(data.data(),4096,offset,true,false));}
  else if(condition!=5 && condition!=7)assert(data==addcPage);
  ++addcCases;
 }
 addcAlignReady=pow2MaxReady=simdChoiceReady=computeLimitReady=slmClassReady=mpsPluginOffReady=vaPageHookReady=vaGen12Enabled=vaSafeEnabled=vaPixelEnabled=true;writeOK=true;race=false;validation=15;taint=nxValue=0;
 // Pages of the same images and of other images: no correction takes another's.
 for(const auto *other:{&maxPage,&simd,&slm,&mps,&limit,&page})assert(!IGCAddcAlign::matches(other->data(),4096,IGCAddcAlign::FileOffset,true,false));
 assert(!MetalPow2MaxThreads::matches(addcPage.data(),4096,MetalPow2MaxThreads::FileOffset,true,false) && !MetalSIMDChoice::matches(addcPage.data(),4096,MetalSIMDChoice::FileOffset,true,false));
 assert(!MetalSLMClass::matches(addcPage.data(),4096,MetalSLMClass::FileOffset,true,false) && !MetalMPSPlugin::matches(addcPage.data(),4096,MetalMPSPlugin::FileOffset,true,false));
 assert(!XeAdapterComputeLimit::matches(addcPage.data(),4096,XeAdapterComputeLimit::FileOffset,true,false));
 {
  // One byte changes: the alignment fixAddcSubb asks for its addc's temporary, from Any (1) to 16 words.
  auto corrected=addcPage;IGCAddcAlign::apply(corrected.data());unsigned changed=0;
  for(unsigned i=0;i<4096;++i)changed+=corrected[i]!=addcPage[i];
  assert(changed==1 && addcPage[IGCAddcAlign::Site+7]==0x01 && corrected[IGCAddcAlign::Site+7]==0x10);
 }
 printf("PASS: %u compiler carry page cases: its own switch, validated executable pages only, mutation race, independence from the other switches, one byte changed\n",addcCases);
 if(haveMetal){
  // The real function, corrected and called: it returns false at once, without reading the bundle's Info.plist.
  auto image=read(argv[7]);assert(image.size()>=MetalSLMClass::FileOffset+4096);
  auto code=(uint8_t*)mmap(nullptr,4096,7,MAP_ANON|MAP_PRIVATE,-1,0);assert(code!=MAP_FAILED);memcpy(code,image.data()+MetalMPSPlugin::FileOffset,4096);
  assert(MetalMPSPlugin::matches(code,4096,MetalMPSPlugin::FileOffset,true,false));MetalMPSPlugin::apply(code);
  unsigned changed=0;for(unsigned i=0;i<4096;++i)changed+=code[i]!=image[MetalMPSPlugin::FileOffset+i];assert(changed==3);
  assert(!((bool(*)())(code+MetalMPSPlugin::PatchOffset))());munmap(code,4096);
  puts("PASS: isMPSIntelPluginEnabled() of the real Metal driver returns false after the correction; three bytes change");
  // The real class computation, before and after the correction, run on its own: the instructions of PatchIDData from the
  // load of the requested size (0x38f78) to where every branch has stored the class (0x38ffe), between a frame and a return.
  const uint8_t frame[]{0x55,0x48,0x89,0xe5,0x48,0x83,0xec,0x40},back[]{0x48,0x8b,0x45,0xd0,0xc9,0xc3};
  const unsigned from=0xf78,to=0xffe;
  const auto classOf=[&](const uint8_t *source,uint32_t bytes){
   memcpy(code,frame,sizeof(frame));memcpy(code+sizeof(frame),source+from,to-from);memcpy(code+sizeof(frame)+to-from,back,sizeof(back));
   uint8_t packet[0x90]{};memcpy(packet+0x88,&bytes,sizeof(bytes));
   return unsigned(((uint64_t(*)(void *,void *))code)(nullptr,packet)>>16);
  };
  code=(uint8_t*)mmap(nullptr,4096,7,MAP_ANON|MAP_PRIVATE,-1,0);assert(code!=MAP_FAILED);
  const uint8_t *native=image.data()+MetalSLMClass::FileOffset;std::vector<uint8_t> corrected(native,native+4096);
  assert(MetalSLMClass::matches(corrected.data(),4096,MetalSLMClass::FileOffset,true,false));MetalSLMClass::apply(corrected.data());
  changed=0;for(unsigned i=0;i<4096;++i)changed+=corrected[i]!=native[i];assert(changed==2);
  const struct {uint32_t bytes;unsigned before,after;} sizes[]{{0,0,0},{1,1,1},{1024,1,1},{1025,2,2},{4096,3,3},{4097,4,4},{8192,4,4},
   {8193,5,7},{8720,5,7},{16384,5,7},{16385,6,7},{32768,6,7},{32769,7,7},{65536,7,7}};
  for(const auto &s:sizes)assert(classOf(native,s.bytes)==s.before && classOf(corrected.data(),s.bytes)==s.after);
  munmap(code,4096);
  puts("PASS: the real class computation of the Metal driver gives the 64 KB class to every size above 8 KB after the correction and the same classes as before up to 8 KB; two bytes change");
  // The real choice of a kernel binary, before and after the correction, run on its own: ChalExecuteKernel from its entry
  // (0x2c848) to where it jumps on with the chosen binary in %rsi (0x2c915), which it returns here instead.
  const uint8_t *nativeChoice=image.data()+MetalSIMDChoice::FileOffset;std::vector<uint8_t> correctedChoice(nativeChoice,nativeChoice+4096);
  assert(MetalSIMDChoice::matches(correctedChoice.data(),4096,MetalSIMDChoice::FileOffset,true,false));MetalSIMDChoice::apply(correctedChoice.data());
  changed=0;for(unsigned i=0;i<4096;++i)changed+=correctedChoice[i]!=nativeChoice[i];assert(changed==sizeof(MetalSIMDChoice::Corrected));
  code=(uint8_t*)mmap(nullptr,4096,7,MAP_ANON|MAP_PRIVATE,-1,0);assert(code!=MAP_FAILED);
  const unsigned entry=0x848,leave=0x915;const uint8_t give[]{0x48,0x89,0xf0,0xc3};
  const auto choose=[&](const uint8_t *source,void *const *binaries,uint64_t groups,uint64_t threads){
   memcpy(code,source+entry,leave-entry);memcpy(code+leave-entry,give,sizeof(give));
   // The context's hardware threads: 56 for one thread group and 672 in all (a 96-EU GPU).
   std::vector<uint8_t> context(0xd60);const uint32_t perGroup=56,total=672;memcpy(context.data()+0xd4c,&perGroup,4);memcpy(context.data()+0xd58,&total,4);
   const uint64_t perGroupSize[3]{threads,1,1},grid[3]{groups,1,1};
   return ((void *(*)(void *,void *const *,const uint64_t *,const uint64_t *))code)(context.data(),binaries,perGroupSize,grid);
  };
  // Decoded binaries: CompiledSIMD8, CompiledSIMD16 and CompiledSIMD32 at 0x280, 0x281 and 0x282.
  static uint8_t b8[0x300],b16[0x300],b32[0x300];b8[0x280]=1;b16[0x281]=1;b32[0x282]=1;
  void *const both[3]{b16,b8,nullptr},*const only8[3]{b8,nullptr,nullptr},*const three[3]{b32,b16,b8};
  const struct {void *const *binaries;uint64_t groups,threads;const void *before,*after;} choices[]{
   {both,32,128,b8,b16},{both,42,128,b8,b16},{both,43,128,b16,b16},{both,84,128,b16,b16},{both,85,128,b16,b16},
   {both,1,512,b16,b16},{both,0,128,b16,b16},{only8,32,128,b8,b8},{only8,85,128,b8,b8},{three,32,128,b8,b16},{three,85,128,b32,b32}};
  for(const auto &c:choices)assert(choose(nativeChoice,c.binaries,c.groups,c.threads)==c.before && choose(correctedChoice.data(),c.binaries,c.groups,c.threads)==c.after);
  munmap(code,4096);
  puts("PASS: the real binary choice of the Metal driver runs the SIMD16 binary for every dispatch that fits it after the correction, the SIMD8 one only without a SIMD16 binary, and the same binaries as before above that; five bytes change");
  // The real getter, before and after the correction, run on its own. Its RIP-relative load is pointed at an ivar offset
  // variable of this test, the only change; the object holds the stored maximum at that offset.
  const uint8_t *nativeMax=image.data()+MetalPow2MaxThreads::FileOffset;std::vector<uint8_t> correctedMax(nativeMax,nativeMax+4096);
  assert(MetalPow2MaxThreads::matches(correctedMax.data(),4096,MetalPow2MaxThreads::FileOffset,true,false));MetalPow2MaxThreads::apply(correctedMax.data());
  changed=0;for(unsigned i=0;i<4096;++i)changed+=correctedMax[i]!=nativeMax[i];assert(changed==16);
  code=(uint8_t*)mmap(nullptr,4096,7,MAP_ANON|MAP_PRIVATE,-1,0);assert(code!=MAP_FAILED);
  const auto getMax=[&](const uint8_t *source,uint64_t stored){
   memcpy(code,source+MetalPow2MaxThreads::Site,sizeof(MetalPow2MaxThreads::Native));
   const uint64_t ivarOffset=0x20;memcpy(code+0x800,&ivarOffset,8);
   const bool native=code[0]==0x55;const unsigned at=native?7:3,end=native?11:7;const int32_t disp=int32_t(0x800-end);memcpy(code+at,&disp,4);
   uint64_t object[8]{};object[4]=stored;
   return ((uint64_t(*)(void *))code)(object);
  };
  const struct {uint64_t stored,before,after;} maxima[]{{8,8,8},{255,255,128},{256,256,256},{448,448,256},{512,512,512},{896,896,512},{1000,1000,512},{1024,1024,1024}};
  for(const auto &m:maxima)assert(getMax(nativeMax,m.stored)==m.before && getMax(correctedMax.data(),m.stored)==m.after);
  munmap(code,4096);
  puts("PASS: the real maxTotalThreadsPerThreadgroup getter returns the stored maximum before the correction and the largest power of two not above it after; 16 bytes change");
  // The real stores at the end of ChalContext's constructor, before and after the correction, run on their own on a
  // context that holds a pattern, as an allocation that is not zeroed can.
  const uint8_t *nativeContext=image.data()+MetalPendingBarrier::FileOffset;std::vector<uint8_t> correctedContext(nativeContext,nativeContext+4096);
  assert(MetalPendingBarrier::matches(correctedContext.data(),4096,MetalPendingBarrier::FileOffset,true,false));MetalPendingBarrier::apply(correctedContext.data());
  changed=0;for(unsigned i=0;i<4096;++i)changed+=correctedContext[i]!=nativeContext[i];assert(changed==5);
  code=(uint8_t*)mmap(nullptr,4096,7,MAP_ANON|MAP_PRIVATE,-1,0);assert(code!=MAP_FAILED);
  const auto construct=[&](const uint8_t *source){
   const uint8_t enter[]{0x53,0x48,0x89,0xfb},leave[]{0x5b,0xc3};  // pushq %rbx; movq %rdi,%rbx; ...; popq %rbx; retq
   memcpy(code,enter,sizeof(enter));memcpy(code+sizeof(enter),source+MetalPendingBarrier::Site,sizeof(MetalPendingBarrier::Native));
   memcpy(code+sizeof(enter)+sizeof(MetalPendingBarrier::Native),leave,sizeof(leave));
   std::vector<uint8_t> context(0x7b00,0xa5);((void(*)(void *))code)(context.data());return context;
  };
  const auto before=construct(nativeContext),after=construct(correctedContext.data());
  assert(before[0x7ac8]==0 && before[0x7ac9]==0xa5 && after[0x7ac8]==0 && after[0x7ac9]==0);
  for(unsigned i=0;i<0x7b00;++i)if(i!=0x7ac9)assert(before[i]==after[i]);
  munmap(code,4096);
  puts("PASS: the real constructor stores leave the pending-barrier flag as the allocation held it before the correction and clear it after; nothing else changes; five bytes change");
 }
 assert(!LocalVAVFE::matches(page.data(),4095,LocalVAVFE::FileOffset,true,false));
 printf("PASS: %u production callback cases: exact scope, both switches, validated pages, mutation race, permissions, NX and original outputs preserved\n",cases);
 if(!haveImage)return 0;
 auto image=read(argv[6]);
 // The pixel-transfer pages of the real image: both match, and every patch lands where expected.
 for(unsigned i=0;i<LocalVAPixel::PageCount;++i) {
  const auto &p=LocalVAPixel::Pages[i];assert(p.offset+4096<=image.size());
  std::vector<uint8_t> copy(image.begin()+p.offset,image.begin()+p.offset+4096);
  assert(LocalVAPixel::match(copy.data(),4096,p.offset,true,false)==int(i));LocalVAPixel::apply(copy.data(),i);
  for(unsigned j=0;j<p.count;++j)assert(!memcmp(copy.data()+p.patches[j].offset,p.patches[j].after,p.patches[j].size));
  assert(LocalVAPixel::match(copy.data(),4096,p.offset,true,false)==-1);
 }
 // lymzzyh's tables against the real image: every page and site still matches.
 for(unsigned i=0;i<LocalVASafe::PageCount;++i) {
  const auto &table=LocalVASafe::Pages[i];assert(table.offset+4096<=image.size());
  auto pageCopy=std::vector<uint8_t>(image.begin()+table.offset,image.begin()+table.offset+4096);
  assert(LocalVASafe::match(pageCopy.data(),4096,table.offset,true,false)==int(i));
 }
 auto mapped=(uint8_t*)mmap(nullptr,image.size(),7,MAP_ANON|MAP_PRIVATE,-1,0);assert(mapped!=MAP_FAILED);memcpy(mapped,image.data(),image.size());
 assert(LocalVAVFE::matches(mapped+0x2c000,4096,0x2c000,true,false));
 // The real L3 page through the production validator, independently of the VFE page.
 for(unsigned condition=0;condition<8;++condition){
  std::vector<uint8_t> l3(image.begin()+0x1000,image.begin()+0x2000);auto originalL3=l3;
  originalCalls=0;vaL3Pages=0;vaPageHookReady=true;vaGen12Enabled=condition!=1;
  validation=condition==2?0x7:0xf;taint=condition==3?1:0;nxValue=condition==4?1:0;
  writeOK=condition!=5;race=condition==6;racePage=l3.data();if(condition==7)l3[200]^=1;
  int valid=0,t=0,nx=0;vaValidatePage((void*)1,(void*)2,0x1000,l3.data(),&valid,&t,&nx);
  assert(originalCalls==1 && valid==validation && t==taint && nx==nxValue && !writing);
  assert(vaL3Pages==(condition==0?1U:0U));
  if(!condition){LocalVAL3::apply(originalL3.data());assert(l3==originalL3);}
 }
 puts("PASS: eight L3 page callback cases, including NX/taint rejection and a raced page");
 std::vector<uint8_t> owner(0xa900),table(0x100),object(0x5000),baseline;unsigned nativeCases=0;
 put(table.data(),0x78,&walker);
 for(unsigned count:{0U,1U,2U})for(unsigned threads:{32U,112U,224U,672U,1024U})for(unsigned curbe:{0U,32U,256U,1024U})for(unsigned mode=0;mode<5;++mode){
  for(unsigned patched=0;patched<2;++patched){
   memset(object.data(),0,object.size());put(object.data(),0,table.data());put(object.data(),8,owner.data());
   put(object.data(),0x128,count);put(object.data(),0x160,curbe);object[0x124]=mode!=0;
   put(object.data(),0x41cc,mode?mode-1:0);put(object.data(),0x41d0,mode?mode-1:0);
   put(owner.data(),0xa868,threads);
   memcpy(mapped+0x2c000,page.data(),4096);memcpy(mapped+0x1000,image.data()+0x1000,4096);
   if(patched){LocalVAVFE::apply(mapped+0x2c000);assert(LocalVAL3::matches(mapped+0x1000,4096,0x1000,true,false));LocalVAL3::apply(mapped+0x1000);}
   ((void(*)(void*))(mapped+0x2c84a))(object.data());
   if(!patched){baseline=object;continue;}
   for(unsigned i=0;i<count;++i){
    auto old=(uint32_t*)(baseline.data()+0x427c+36*i);auto out=(uint32_t*)(object.data()+0x427c+36*i);
    assert(old[0]==0x70000007 && out[0]==old[0]);assert((out[3]>>16)==threads-1 && (out[3]&0xff00)==0x1000);
    assert(out[3]==(old[3]|0x40));assert(out[6]==0 && out[7]==0 && out[8]==0);
#ifdef INTEL_GEN12_ORACLE
    mhw_render_g12_X::MEDIA_VFE_STATE_CMD oracle;
    oracle.DW3.MaximumNumberOfThreads=threads-1;oracle.DW3.NumberOfUrbEntries=16;
    oracle.DW5.CurbeAllocationSize=curbe>>5;oracle.DW5.UrbEntryAllocationSize=((2016-(curbe>>5))/16)-1;
    assert(!memcmp(out,&oracle,sizeof(oracle)));
#endif
    old[3]|=0x40;old[6]=old[7]=old[8]=0;
   }
   assert(*(uint32_t*)(object.data()+0x41e4)==0x11000001);
   assert(*(uint32_t*)(object.data()+0x41e8)==0xb134 && *(uint32_t*)(object.data()+0x41ec)==0xd0000020);
   put(baseline.data(),0x41e8,uint32_t(0xb134));put(baseline.data(),0x41ec,uint32_t(0xd0000020));
   assert(object==baseline);++nativeCases;
  }
 }
 munmap(mapped,image.size());printf("PASS: %u native packet-generator comparisons, both branches; only Gen12 VFE fields and L3 register/value change; no GPU calls\n",nativeCases);
}
'''.replace('PRODUCTION',production)
with tempfile.TemporaryDirectory(prefix='wex-va-pages-') as tmp:
 p=Path(tmp);(p/'kern_local_va_vfe.hpp').write_text(header);(p/'kern_local_va_safe.hpp').write_text(safeHeader);(p/'kern_local_va_pixel.hpp').write_text(pixelHeader)
 (p/'kern_mtl_mps_page.hpp').write_text(mpsHeader);(p/'mps.bin').write_bytes(mps)
 (p/'kern_mtl_slm_page.hpp').write_text(slmHeader);(p/'slm.bin').write_bytes(slm)
 (p/'kern_xe_adapter_page.hpp').write_text(limitHeader);(p/'limit.bin').write_bytes(limit)
 (p/'kern_mtl_simd_page.hpp').write_text(simdHeader);(p/'simd.bin').write_bytes(simd);(p/'kern_mtl_barrier_page.hpp').write_text(barrierHeader)
 (p/'kern_mtl_maxthreads_page.hpp').write_text(maxHeader);(p/'max.bin').write_bytes(maxPage)
 (p/'kern_igc_addc_page.hpp').write_text(addcHeader);(p/'addc.bin').write_bytes(addcPage)
 (p/'kern_xe_adapter_hash_page.hpp').write_text(hashHeader);(p/'helper.bin').write_bytes(helperPage)
 (p/'page.bin').write_bytes(page);(p/'safe.bin').write_bytes(safe);(p/'pixel.bin').write_bytes(pixel);(p/'test.cpp').write_text(code)
 extra=[]
 if args.intel_gen12:
  # Generated constructors do not use MOS utilities; omit only that unused
  # platform include, preserving the actual Intel bitfields and constructors.
  oracle=(args.intel_gen12/'mhw_render_hwcmd_g12_X.cpp').read_text()
  assert oracle.count('#include "mos_utilities.h"')==1 and 'MOS_' not in oracle
  (p/'oracle.cpp').write_text(oracle.replace('#include "mos_utilities.h"',''))
  extra=['-DINTEL_GEN12_ORACLE','-I'+str(args.intel_gen12),str(p/'oracle.cpp')]
 subprocess.run(['clang++','-arch','x86_64','-std=c++17','-O1','-g','-I'+str(root/'WhateverXe'),str(p/'test.cpp'),'-o',str(p/'test')]+extra,check=True)
 subprocess.run([str(p/'test'),str(p/'page.bin'),str(p/'safe.bin'),str(p/'pixel.bin'),str(p/'mps.bin'),str(p/'slm.bin'),
  str(args.donor.resolve()) if args.donor else '-',str(args.metal.resolve()) if args.metal else '-',str(p/'limit.bin'),str(p/'simd.bin'),str(p/'max.bin'),str(p/'addc.bin'),str(p/'helper.bin')],check=True)
