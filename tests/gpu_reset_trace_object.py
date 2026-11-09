#!/usr/bin/env python3
"""The reset trace names an object by the order it first met it, never by its address; extracted helper, no hardware."""
from pathlib import Path
import subprocess,tempfile
repo=Path(__file__).resolve().parents[1]
s=(repo/'WhateverXe/kern_xe.cpp').read_text()
a=s.index('static const void *gpuResetTraceObjects[');b=s.index('static void gpuResetTrace(uint32_t event',a)
trace=s[b:s.index('static bool gpuResetTraceSerialize',b)]
assert 'e.object=gpuResetTraceObjectID(object)' in trace,'the ring entry must carry the object number'
assert 'reinterpret_cast<uint64_t>(object)' not in trace,'the ring entry must not carry the address'
fixture=r'''
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <thread>
#include <vector>
#define arrsize(a) (sizeof(a)/sizeof((a)[0]))
#include "object.inc"
#define CHECK(c) do{if(!(c)){std::fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#c);std::exit(1);}}while(0)
int main(){
 static int objects[400];
 const uint64_t size=arrsize(gpuResetTraceObjects);
 CHECK(gpuResetTraceObjectID(nullptr)==0);
 // First met, first numbered; the same object keeps its number.
 CHECK(gpuResetTraceObjectID(&objects[7])==1);
 CHECK(gpuResetTraceObjectID(&objects[3])==2);
 CHECK(gpuResetTraceObjectID(&objects[7])==1);
 // Four threads meeting the same hundred objects agree on every number, and no two objects share one.
 uint64_t seen[4][100];
 std::vector<std::thread> threads;
 for(int t=0;t<4;++t)threads.emplace_back([&seen,t]{for(int i=0;i<100;++i)seen[t][i]=gpuResetTraceObjectID(&objects[100+(t%2?99-i:i)]);});
 for(auto &t:threads)t.join();
 uint64_t number[100];
 for(int i=0;i<100;++i)number[i]=gpuResetTraceObjectID(&objects[100+i]);
 for(int t=0;t<4;++t)for(int i=0;i<100;++i)CHECK(seen[t][i]==number[t%2?99-i:i]);
 for(int i=0;i<100;++i){CHECK(number[i]>=3 && number[i]<=102);for(int j=0;j<i;++j)CHECK(number[i]!=number[j]);}
 // A number is never an address: it stays within the table, and past the table it is all ones.
 for(int i=200;i<400;++i){const auto id=gpuResetTraceObjectID(&objects[i]);CHECK(id==~0ULL || (id>=1 && id<=size));}
 CHECK(gpuResetTraceObjectID(&objects[399])==~0ULL);
 CHECK(gpuResetTraceObjectID(&objects[7])==1 && gpuResetTraceObjectID(&objects[3])==2);
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='gpu-reset-trace-object-') as d:
    d=Path(d);(d/'object.inc').write_text(s[a:b]);(d/'fixture.cpp').write_text(fixture)
    subprocess.run(['clang++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(d),str(d/'fixture.cpp'),'-o',str(d/'check')],check=True)
    subprocess.run([str(d/'check')],check=True)
    # The same checks without the sanitizers' serialisation, so the threads really race.
    subprocess.run(['clang++','-std=c++17','-O2','-fsanitize=thread','-I',str(d),str(d/'fixture.cpp'),'-o',str(d/'race')],check=True)
    subprocess.run([str(d/'race')],check=True)
