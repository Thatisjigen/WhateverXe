#!/usr/bin/env python3
"""Exercise the VA page validator and optionally replay the VA packet generator, CPU only.

Adapted from lymzzyh's tgl_va_vfe.py (lymzzyh/WhateverXe f9be946): the A7A0 scope,
two switches, and only the first video-processing output list. With the VA driver
image as argument the real pages are checked and the packet generator is replayed."""
from pathlib import Path
import argparse,hashlib,re,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('donor',nargs='?',type=Path);ap.add_argument('--intel-gen12',type=Path);args=ap.parse_args()
s=(root/'WhateverXe/kern_va_pages.hpp').read_text()
production=s[s.index('static mach_vm_address_t vaOriginalPage;'):]
header=(root/'WhateverXe/kern_local_va_vfe.hpp').read_text()
safeHeader=(root/'WhateverXe/kern_local_va_safe.hpp').read_text()
identity=re.search(r'ReferenceSHA256\[\]\{([^}]+)\}',header);expected=bytes(int(n,0) for n in identity[1].split(','))
first=re.search(r'\{0x786000,\{([^}]+)\}',safeHeader)
if args.donor:
 data=args.donor.read_bytes();page=data[0x2c000:0x2d000];assert hashlib.sha256(page).digest()==expected
 safe=data[0x786000:0x787000];assert hashlib.sha256(safe).digest()==bytes(int(n,0) for n in first[1].split(','))
else:
 page=bytearray((i*37+31)%256 for i in range(4096))
 for off,count,body in re.findall(r'\{0x([a-f0-9]+),(\d+),\{([^}]+)\},',header):
  value=bytes(int(n,0) for n in body.split(','));assert len(value)==int(count);off=int(off,16);page[off:off+len(value)]=value
 header=header[:identity.start(1)]+','.join(hex(v) for v in hashlib.sha256(page).digest())+header[identity.end(1):]
 # A synthetic first capability page with the expected count at its first list.
 safe=bytearray((i*53+7)%256 for i in range(4096));safe[0xfc4:0xfc8]=(2).to_bytes(4,'little')
 safeHeader=safeHeader[:first.start(1)]+','.join(hex(v) for v in hashlib.sha256(safe).digest())+safeHeader[first.end(1):]
code=r'''
#include "kern_local_va_vfe.hpp"
#include "kern_local_va_l3.hpp"
#include "kern_local_va_safe.hpp"
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
 assert(argc==3 || argc==4);auto page=read(argv[1]),safe=read(argv[2]);assert(page.size()==4096 && safe.size()==4096);unsigned cases=0;
 KernelPatcher patcher;IOPCIDevice gpu;
 // Scope: exact device and revision, no override, Tahoe, the route, and the renderer switch.
 for(unsigned bits=0;bits<32;++bits){
  const bool renderer=bits&1;routeOK=bits&2;kernel=bits&4?Tahoe:Other;
  auto profile=XELP::identify(0xa7a08086,bits&8?0x04:0x05,bits&16?0x9a498086:0xa7a08086);
  prepareVAPages(patcher,&gpu,profile,renderer);
  const bool scope=(bits&8) && !(bits&16);
  assert(vaGen12Enabled==(scope && renderer) && vaSafeEnabled==(scope && renderer));
  assert(vaPageHookReady==(scope && renderer && (bits&4) && routeOK));++cases;
 }
 kernel=Tahoe;routeOK=true;
 prepareVAPages(patcher,nullptr,XELP::identify(0xa7a08086,0x04),true);assert(!vaPageHookReady && !vaGen12Enabled);++cases;
 prepareVAPages(patcher,&gpu,XELP::identify(0x46808086,0x0c),true);assert(!vaPageHookReady && !vaSafeEnabled);++cases;
 for(const char *servicing:{"Darwin Kernel Version 25.6.0: other date; root:xnu-new/RELEASE_X86_64","Darwin Kernel Version 25.7.2: future date; root:xnu-next/RELEASE_X86_64"}) {
  version=servicing;prepareVAPages(patcher,&gpu,XELP::identify(0xa7a08086,0x04),true);assert(vaPageHookReady && vaGen12Enabled && vaSafeEnabled);++cases;
 }
 version="Darwin Kernel Version 24.6.0: Mon Jul 14 11:28:17 PDT 2025; root:xnu-11417.140.69~1/RELEASE_X86_64";
 prepareVAPages(patcher,&gpu,XELP::identify(0xa7a08086,0x04),true);assert(!vaPageHookReady && !vaGen12Enabled && !vaSafeEnabled);++cases;
 prepareVAPages(patcher,&gpu,XELP::identify(0xa7a08086,0x04),false);assert(!vaPageHookReady && !vaGen12Enabled && !vaSafeEnabled);++cases;
 version=tahoe;prepareVAPages(patcher,&gpu,XELP::identify(0xa7a08086,0x04),true);assert(vaPageHookReady && vaGen12Enabled && vaSafeEnabled);
 // The VFE packet generator: validated executable code pages only, rechecked under the write lock.
 for(unsigned condition=0;condition<11;++condition){
  auto data=page;racePage=data.data();originalCalls=0;vaVFEPages=vaL3Pages=vaSafePages=0;
  validation=condition==1?0x7:0xf;taint=condition==2?1:0;nxValue=condition==3?1:0;
  writeOK=condition!=4;race=condition==5;vaGen12Enabled=condition!=6;
  if(condition==7)data[200]^=1;
  int valid=-1,t=-1,nx=-1;
  auto offset=LocalVAVFE::FileOffset+(condition==8?4096:0);
  vaValidatePage((void*)1,(void*)2,offset,data.data(),condition==9?nullptr:&valid,&t,condition==10?nullptr:&nx);
  assert(originalCalls==1 && !writing);if(condition!=9)assert(valid==validation);assert(t==taint);if(condition!=10)assert(nx==nxValue);
  assert(vaVFEPages==(condition==0?1U:0U) && !vaL3Pages && !vaSafePages);
  if(condition==0){auto expected=page;LocalVAVFE::apply(expected.data());assert(data==expected);assert(!LocalVAVFE::matches(data.data(),4096,offset,true,false));}
  else if(condition!=5 && condition!=7)assert(data==page);
  ++cases;
 }
 vaGen12Enabled=true;
 // The capability list lives in a data page: NX does not exclude it, and only its first list is cleared.
 for(unsigned condition=0;condition<10;++condition){
  auto data=safe;racePage=data.data();originalCalls=0;vaVFEPages=vaL3Pages=vaSafePages=0;
  validation=condition==1?0x7:0xf;taint=condition==2?1:0;nxValue=condition==3?0:1;
  writeOK=condition!=4;race=condition==5;vaSafeEnabled=condition!=6;vaPageHookReady=condition!=9;
  if(condition==7)data[100]^=1;
  int valid=-1,t=-1,nx=-1;
  const uint64_t offset=0x786000+(condition==8?4096:0);
  vaValidatePage((void*)1,(void*)2,offset,data.data(),&valid,&t,&nx);
  assert(originalCalls==1 && !writing && valid==validation && t==taint && nx==nxValue);
  const bool patched=condition==0 || condition==3;
  assert(vaSafePages==(patched?1U:0U) && !vaVFEPages && !vaL3Pages);
  if(patched){auto expected=safe;memset(expected.data()+0xfc4,0,4);assert(data==expected);}
  else if(condition!=5 && condition!=7)assert(data==safe);
  ++cases;
 }
 vaSafeEnabled=vaPageHookReady=true;
 assert(!LocalVAVFE::matches(page.data(),4095,LocalVAVFE::FileOffset,true,false));
 printf("PASS: %u production callback cases: exact scope, both switches, validated pages, mutation race, permissions, NX and original outputs preserved\n",cases);
 if(argc==3)return 0;
 auto image=read(argv[3]);
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
 p=Path(tmp);(p/'kern_local_va_vfe.hpp').write_text(header);(p/'kern_local_va_safe.hpp').write_text(safeHeader)
 (p/'page.bin').write_bytes(page);(p/'safe.bin').write_bytes(safe);(p/'test.cpp').write_text(code)
 extra=[]
 if args.intel_gen12:
  # Generated constructors do not use MOS utilities; omit only that unused
  # platform include, preserving the actual Intel bitfields and constructors.
  oracle=(args.intel_gen12/'mhw_render_hwcmd_g12_X.cpp').read_text()
  assert oracle.count('#include "mos_utilities.h"')==1 and 'MOS_' not in oracle
  (p/'oracle.cpp').write_text(oracle.replace('#include "mos_utilities.h"',''))
  extra=['-DINTEL_GEN12_ORACLE','-I'+str(args.intel_gen12),str(p/'oracle.cpp')]
 subprocess.run(['clang++','-arch','x86_64','-std=c++17','-O1','-g','-I'+str(root/'WhateverXe'),str(p/'test.cpp'),'-o',str(p/'test')]+extra,check=True)
 subprocess.run([str(p/'test'),str(p/'page.bin'),str(p/'safe.bin')]+([str(args.donor.resolve())] if args.donor else []),check=True)
