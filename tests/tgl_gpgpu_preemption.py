#!/usr/bin/env python3
"""Execute the donor's real preemption setup in startGraphicsEngine on CPU-backed memory, no GPU access: with the object
preemption, selector and FF DOP corrections that production applies outside Tiger Lake, the GPGPU level written to the
global granularity register 0x20E4 and to 0x2580 is thread group (or mid-thread for the flags bit) before the command-level
correction and command level after it, whatever the flags; nothing else the block writes changes."""
from pathlib import Path
import hashlib,re,subprocess,sys,tempfile
source=(Path(__file__).resolve().parents[1]/'WhateverXe/kern_xe.cpp').read_text()
data=Path(sys.argv[1]).read_bytes()
# The donor the other native tests use, and the same file of the Graphics package with other code signatures: they
# differ only inside LC_CODE_SIGNATURE, so the executed block is the same.
assert hashlib.sha256(data).hexdigest() in ('bd1a21f5e622aadabdab6441f6b5c38ed73fa3053c783fdf0fb7e4b309f273d0',
 '6c8ab6cce50b9529679ee4fdf5b1c37d091677d945076f41cb4b7f8196c51449','567511bed855a5165cbc3615f61be7b4fcf607fde4fc5c48567fb127726d496e')
def array(name,**values):
 body=re.search(r'const uint8_t '+name+r'\[\] \{([^}]+)',source).group(1)
 for expression,value in values.items():
  assert body.count(expression)==1;body=body.replace(expression,str(value))
 return bytes(int(x,0) for x in body.split(','))
# The block: andl $0x2,%ecx; xorl $0x60002,%ecx becomes movl $0x60004,%ecx and a four-byte nop.
find,replace=array('gpgpuLevelFind'),array('gpgpuLevelReplace')
assert find==data[0x2515d:0x25166]==bytes.fromhex('83e10281f102000600')
assert replace==bytes.fromhex('b9040006000f1f4000')
assert 'address+0x2515D' in source and '"-wex-native-gpgpu-preempt"' in source
# The corrections production applies to the same block before it runs, outside Tiger Lake.
assert array('objectPreemptReplace')==bytes.fromhex('ba000001008990ec200000')
assert array('objectSelectorReplace')==bytes.fromhex('c780e020000000000040')
ffDop=array('ffDopReplace',**{'uint8_t(objectPreemptOn?3:2)':3})
assert ffDop==bytes.fromhex('ba030003008990ec200000ba0000010090')
code=r'''#include <sys/mman.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <fstream>
#include <vector>
#include <stdio.h>
extern "C" __attribute__((naked)) void run(void*,void*) {
 asm("pushq %r13\n movq %rsi,%r13\n callq *%rdi\n popq %r13\n retq");
}
static uint32_t at(const uint8_t *m,unsigned o){uint32_t v;memcpy(&v,m+o,4);return v;}
int main(int argc,char**argv){
 assert(argc==2);std::ifstream f(argv[1],std::ios::binary);std::vector<char>d((std::istreambuf_iterator<char>(f)),{});
 auto m=(uint8_t*)mmap(nullptr,d.size(),7,MAP_ANON|MAP_PRIVATE,-1,0);assert(m!=MAP_FAILED);memcpy(m,d.data(),d.size());m[0x251a1]=0xc3;
 const uint8_t ffDop[]={FFDOP},level[]={LEVEL};
 uint8_t owner[0x1300]={},a[0x3000],b[0x3000];const uint64_t flags[]={0,1ULL<<32,~0ULL};
 for(auto value:flags){
  memcpy(m+0x2514b,d.data()+0x2514b,0x251a1-0x2514b);
  m[0x2516d]=0;m[0x25190]=0;memcpy(m+0x25166,ffDop,sizeof(ffDop));
  memcpy(owner+0x1190,&value,8);
  for(unsigned i=0;i<sizeof(a);i++)a[i]=b[i]=(i*37+11)&255;
  void *base=a;memcpy(owner+0x1240,&base,8);run(m+0x2514b,owner);
  memcpy(m+0x2515d,level,sizeof(level));
  base=b;memcpy(owner+0x1240,&base,8);run(m+0x2514b,owner);
  const uint32_t native=(value>>32)&1?0x60000:0x60002;
  assert(at(a,0x20e4)==native && at(a,0x2580)==(native|0x10000));
  assert(at(b,0x20e4)==0x60004 && at(b,0x2580)==0x70004);
  assert(at(a,0x20ec)==0x30003 && at(b,0x20ec)==0x30003 && at(a,0x20e0)==0x40000000 && at(b,0x20e0)==0x40000000);
  assert(at(a,0x2214)==at(b,0x2214));
  for(unsigned i=0;i<sizeof(a);i++)if((i<0x20e4 || i>=0x20e8) && (i<0x2580 || i>=0x2584))assert(a[i]==b[i]);
  printf("flags=%llx: 20E4 %x -> %x, 2580 %x -> %x; 20EC, 20E0, 2214 and all other memory unchanged PASS\n",(unsigned long long)value,
   at(a,0x20e4),at(b,0x20e4),at(a,0x2580),at(b,0x2580));
 }
}
'''
code=code.replace('FFDOP',','.join(str(x) for x in ffDop)).replace('LEVEL',','.join(str(x) for x in replace))
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);(p/'test.cpp').write_text(code)
 subprocess.run(['clang++','-arch','x86_64','-std=c++14','-O2',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test'),sys.argv[1]],check=True)
print('Native CPU initialization test passed; GPU outcome untested')
